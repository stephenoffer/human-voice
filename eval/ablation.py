#!/usr/bin/env python3
"""Per-category ablation: how much does each linter category contribute to
separating the human and AI corpus subsets?

For each scoring category, we re-score the whole corpus with that category's
weight set to 0 and recompute two separation measures:

  * ROC AUC  -- rank probability that an AI file outscores a human file
                (1.0 = perfect separation, 0.5 = chance).
  * best-F1 accuracy -- accuracy at the per-ablation best-F1 threshold.

The DROP from the full-model baseline is the category's contribution: a large
positive drop means the category does real separating work on this corpus; a
zero drop means it never fires on these samples (or is redundant with others).

Pure standard library. Prints a ranked table. Exits 0.

HONESTY NOTE: contribution is measured ON THIS authored corpus only. A category
that contributes 0 here may still be the decisive tell on text in the wild --
absence of evidence here is not evidence the category is useless. The linter is
a floor, not ground truth.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CORPUS = os.path.join(HERE, "corpus")
LABELS_PATH = os.path.join(CORPUS, "LABELS.json")
DETECTOR_PATH = os.path.join(REPO, "skills", "human-voice", "scripts", "detect_ai_prose.py")
PATTERNS_PATH = os.path.join(REPO, "skills", "human-voice", "scripts", "ai_prose_patterns.json")


def load_detector():
    spec = importlib.util.spec_from_file_location("detect_ai_prose", DETECTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_labels():
    with open(LABELS_PATH, encoding="utf-8") as fh:
        return json.load(fh)["labels"]


def read_corpus(labels):
    items = []
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(CORPUS, rel), encoding="utf-8") as fh:
            items.append((rel, meta["label"], meta["register"], fh.read()))
    return items


def score_all(dap, items, patterns):
    """Return list of (label, score). Re-runs analyze with the given patterns so
    the (possibly zeroed) category weights take effect."""
    weights = dap.resolve_weights(patterns)
    out = []
    for _rel, label, register, text in items:
        hits, _report, words = dap.analyze(text, register, None, patterns)
        sc = dap.score(hits, words, weights)
        out.append((label, sc))
    return out


def category_score_mass(dap, items, patterns):
    """For each category, the share of total AI-subset floor score it contributes.

    Even when the classes are separated with huge margin (so zeroing one weight
    does not change AUC), this shows which tells drive the AI scores -- a more
    discriminating view of per-category importance on a saturated corpus.
    """
    weights = dap.resolve_weights(patterns)
    cat_points = {c: 0.0 for c in dap.CATEGORY_WEIGHTS}
    total = 0.0
    for _rel, label, register, text in items:
        if label != "ai":
            continue
        hits, _report, words = dap.analyze(text, register, None, patterns)
        if not words:
            continue
        per_word = 1000.0 / words
        for h in hits:
            w = weights.get(h.category, 1.0)
            cat_points[h.category] += w * per_word
            total += w * per_word
    return cat_points, total


def auc(scored):
    pos = [s for lbl, s in scored if lbl == "ai"]
    neg = [s for lbl, s in scored if lbl == "human"]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


def best_f1_accuracy(scored):
    """Accuracy at the threshold that maximizes F1 (positive class = ai)."""
    scores = sorted({s for _l, s in scored})
    cands = set()
    for i in range(len(scores)):
        cands.add(scores[i])
        if i + 1 < len(scores):
            cands.add((scores[i] + scores[i + 1]) / 2)
    cands.add((scores[0] - 0.1) if scores else 0.0)
    cands.add((scores[-1] + 0.1) if scores else 0.0)
    best_acc, best_f1 = 0.0, -1.0
    for th in cands:
        tp = fp = tn = fn = 0
        for lbl, s in scored:
            pred = s >= th
            ai = lbl == "ai"
            if pred and ai: tp += 1
            elif pred and not ai: fp += 1
            elif not pred and not ai: tn += 1
            else: fn += 1
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        acc = (tp + tn) / len(scored)
        if f1 > best_f1:
            best_f1, best_acc = f1, acc
    return best_acc, best_f1


def patterns_with_zeroed(patterns, category):
    """Copy of patterns with category_weights[category] forced to 0."""
    p = dict(patterns)
    cw = dict(p.get("category_weights") or {})
    cw[category] = 0.0
    p["category_weights"] = cw
    return p


def main():
    dap = load_detector()
    patterns = dap.load_patterns(PATTERNS_PATH)
    labels = load_labels()
    items = read_corpus(labels)

    base_scored = score_all(dap, items, patterns)
    base_auc = auc(base_scored)
    base_acc, base_f1 = best_f1_accuracy(base_scored)
    cat_points, total_points = category_score_mass(dap, items, patterns)

    rows = []
    for category in sorted(dap.CATEGORY_WEIGHTS):
        ablated = patterns_with_zeroed(patterns, category)
        scored = score_all(dap, items, ablated)
        a = auc(scored)
        acc, _f1 = best_f1_accuracy(scored)
        pts = cat_points.get(category, 0.0)
        rows.append({
            "category": category,
            "weight": dap.resolve_weights(patterns).get(category),
            "auc": a,
            "auc_drop": round(base_auc - a, 4) if a is not None else None,
            "best_f1_acc": acc,
            "acc_drop": round(base_acc - acc, 4),
            "ai_score_share": round(pts / total_points, 4) if total_points else 0.0,
        })

    # Rank by AUC drop, then accuracy drop, then share of AI score mass. On a
    # saturated corpus the first two tie at 0, so score-mass share breaks the tie
    # and surfaces the categories actually driving the AI scores.
    rows.sort(key=lambda r: ((r["auc_drop"] or 0.0), r["acc_drop"], r["ai_score_share"]),
              reverse=True)

    print("=" * 78)
    print("Per-category ablation -- contribution to human/AI separation")
    print("baseline (full model): AUC %.4f   best-F1 accuracy %.4f" % (base_auc, base_acc))
    print("=" * 78)
    print()
    print("  %-22s %6s %8s %9s %8s %9s" % (
        "category", "weight", "AUC", "AUCdrop", "accdrop", "AIshare"))
    print("  " + "-" * 68)
    for r in rows:
        print("  %-22s %6.1f %8.4f %9.4f %8.4f %8.1f%%" % (
            r["category"], r["weight"], r["auc"], r["auc_drop"],
            r["acc_drop"], 100 * r["ai_score_share"]))
    print()
    print("AUCdrop/accdrop = loss of separation when this weight is zeroed.")
    print("AIshare = this category's share of the total AI-subset floor score.")
    print()
    contributors = [r["category"] for r in rows if (r["auc_drop"] or 0) > 0 or r["acc_drop"] > 0]
    top_share = [r for r in rows if r["ai_score_share"] > 0][:6]
    if contributors:
        print("Categories that change separation on this corpus: %s"
              % ", ".join(contributors))
    else:
        print("No single category changes separation: the classes are separated")
        print("with so much margin that zeroing any one weight leaves AUC at baseline.")
    print("Top drivers of the AI scores (by score-mass share): %s"
          % ", ".join("%s %.0f%%" % (r["category"], 100 * r["ai_score_share"])
                      for r in top_share))
    print()
    print("HONESTY NOTE: contribution is measured on this small authored corpus")
    print("only. A 0-drop category may still be decisive on real text. Floor, not truth.")

    out_path = os.path.join(HERE, "ablation_results.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"baseline_auc": base_auc, "baseline_best_f1_acc": base_acc,
                   "rows": rows}, fh, indent=2)
    print()
    print("Wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
