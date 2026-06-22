#!/usr/bin/env python3
"""Evaluate the human-voice linter's FLOOR score as a binary AI/human classifier.

Loads the labeled calibration corpus under eval/corpus/, scores every file with
the bundled detector (imported, not shelled out), and treats the floor score as
a one-dimensional classifier: predict "ai" when score >= threshold.

Reports, both at the default "watch" boundary (5.0) and at a swept best-F1
threshold: precision, recall, F1, accuracy, the confusion matrix, and the
false-positive rate on the human subset specifically. Writes eval/results.json.

Pure standard library. Runs offline. Exits 0.

IMPORTANT HONESTY NOTE: the corpus is small and AUTHORED to exhibit (human) or
avoid (... wait, reversed) the exact tells the linter scores. These numbers
measure calibration and internal separation, not real-world accuracy. The linter
is a FLOOR, never ground truth -- a skeptical human read is the real test.
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
RESULTS_PATH = os.path.join(HERE, "results.json")

# The linter's default "watch" boundary: score < 5 reads clean.
DEFAULT_THRESHOLD = 5.0


def load_detector():
    spec = importlib.util.spec_from_file_location("detect_ai_prose", DETECTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_labels():
    with open(LABELS_PATH, encoding="utf-8") as fh:
        return json.load(fh)["labels"]


def score_corpus(dap, patterns, labels):
    """Return a list of per-file records: filename, label, register, score, verdict."""
    records = []
    for rel, meta in sorted(labels.items()):
        path = os.path.join(CORPUS, rel)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        res = dap.lint(text, register=meta["register"], dialect=None, patterns=patterns)
        records.append({
            "file": rel,
            "label": meta["label"],
            "register": meta["register"],
            "score": res["score"],
            "verdict": res["verdict"],
            "words": res["words"],
        })
    return records


def confusion(records, threshold):
    """Predict 'ai' iff score >= threshold. Return tp, fp, tn, fn.

    Positive class = 'ai'.
    """
    tp = fp = tn = fn = 0
    for r in records:
        pred_ai = r["score"] >= threshold
        actual_ai = r["label"] == "ai"
        if pred_ai and actual_ai:
            tp += 1
        elif pred_ai and not actual_ai:
            fp += 1
        elif not pred_ai and not actual_ai:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def metrics(tp, fp, tn, fn):
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0
    # False-positive rate among genuinely human texts: fp / (fp + tn).
    human_fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "human_subset_false_positive_rate": round(human_fpr, 4),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def candidate_thresholds(records):
    """Midpoints between sorted unique scores, plus the extremes."""
    scores = sorted({r["score"] for r in records})
    cands = set()
    cands.add(scores[0] - 0.1 if scores else 0.0)
    cands.add(scores[-1] + 0.1 if scores else 0.0)
    for i in range(len(scores)):
        cands.add(scores[i])
        if i + 1 < len(scores):
            cands.add(round((scores[i] + scores[i + 1]) / 2, 3))
    return sorted(c for c in cands if c >= 0)


def sweep(records):
    """Find the threshold maximizing F1 (tie-break: fewer human false positives,
    then higher accuracy, then lower threshold)."""
    best = None
    rows = []
    for th in candidate_thresholds(records):
        m = metrics(*confusion(records, th))
        rows.append((th, m))
        key = (m["f1"], -m["human_subset_false_positive_rate"], m["accuracy"], -th)
        if best is None or key > best[0]:
            best = (key, th, m)
    return best[1], best[2], rows


def auc(records):
    """ROC AUC via rank statistic (Mann-Whitney U). Positive = 'ai'.

    Higher score should mean more AI-like. AUC = P(score_ai > score_human),
    with ties counted as 0.5.
    """
    pos = [r["score"] for r in records if r["label"] == "ai"]
    neg = [r["score"] for r in records if r["label"] == "human"]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return round(wins / (len(pos) * len(neg)), 4)


def fmt_table(records):
    lines = []
    lines.append("  %-38s %-6s %-10s %8s  %s" % ("file", "label", "register", "score", "verdict"))
    lines.append("  " + "-" * 78)
    for r in sorted(records, key=lambda x: (x["label"], x["file"])):
        lines.append("  %-38s %-6s %-10s %8.1f  %s" % (
            r["file"], r["label"], r["register"], r["score"], r["verdict"]))
    return "\n".join(lines)


def fmt_metrics(title, threshold, m):
    c = m["confusion"]
    return "\n".join([
        "%s (threshold = %.2f; predict AI when score >= threshold)" % (title, threshold),
        "  precision %.3f   recall %.3f   F1 %.3f   accuracy %.3f" % (
            m["precision"], m["recall"], m["f1"], m["accuracy"]),
        "  human-subset false-positive rate: %.3f  (%d of %d human files flagged)" % (
            m["human_subset_false_positive_rate"], c["fp"], c["fp"] + c["tn"]),
        "  confusion: tp=%d fp=%d tn=%d fn=%d  (positive class = AI)" % (
            c["tp"], c["fp"], c["tn"], c["fn"]),
    ])


def main():
    dap = load_detector()
    patterns = dap.load_patterns(os.path.join(REPO, "skills", "human-voice",
                                              "scripts", "ai_prose_patterns.json"))
    labels = load_labels()
    records = score_corpus(dap, patterns, labels)

    n_human = sum(1 for r in records if r["label"] == "human")
    n_ai = sum(1 for r in records if r["label"] == "ai")

    default_m = metrics(*confusion(records, DEFAULT_THRESHOLD))
    best_th, best_m, sweep_rows = sweep(records)
    roc_auc = auc(records)

    print("=" * 80)
    print("human-voice linter floor-score evaluation")
    print("corpus: %d files (%d human, %d ai)   [authored synthetic calibration set]"
          % (len(records), n_human, n_ai))
    print("=" * 80)
    print()
    print("Per-file scores:")
    print(fmt_table(records))
    print()
    hs = sorted(r["score"] for r in records if r["label"] == "human")
    asc = sorted(r["score"] for r in records if r["label"] == "ai")
    print("Score separation:")
    print("  human scores: min %.1f  max %.1f" % (hs[0], hs[-1]))
    print("  ai scores:    min %.1f  max %.1f" % (asc[0], asc[-1]))
    print("  ROC AUC (rank-based, ties=0.5): %s" % roc_auc)
    print()
    print(fmt_metrics("DEFAULT boundary", DEFAULT_THRESHOLD, default_m))
    print()
    print(fmt_metrics("SWEPT best-F1 threshold", best_th, best_m))
    print()
    print("Note: this corpus is small and authored to exhibit/avoid the exact")
    print("tells the linter scores. These numbers measure calibration, not")
    print("real-world detection. The linter is a FLOOR, not ground truth.")

    out = {
        "corpus_size": len(records),
        "n_human": n_human,
        "n_ai": n_ai,
        "roc_auc": roc_auc,
        "default_threshold": DEFAULT_THRESHOLD,
        "default": default_m,
        "best_threshold": best_th,
        "best": best_m,
        "sweep": [{"threshold": th, "f1": m["f1"], "precision": m["precision"],
                   "recall": m["recall"], "accuracy": m["accuracy"],
                   "human_fpr": m["human_subset_false_positive_rate"]}
                  for th, m in sweep_rows],
        "records": records,
        "_note": ("Authored synthetic calibration corpus; measures internal "
                  "separation/calibration, not real-world accuracy. Linter is a floor."),
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print()
    print("Wrote %s" % RESULTS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
