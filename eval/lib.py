"""Shared helpers for the human-voice evaluation suite.

One home for: loading the linter (resilient to the single-file-vs-package
layout), loading the labeled corpus, the canonical classification metrics
(confusion / metrics / sweep / auc), per-register and per-category breakdowns,
deterministic bootstrap confidence intervals, the regression-gate comparator,
and corpus-integrity validation.

Pure standard library. The three eval scripts import from here so the metric
math lives in exactly one place (previously auc() and metrics() were duplicated
across run_eval.py and ablation.py with subtly different rounding).
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CORPUS = os.path.join(HERE, "corpus")
LABELS_PATH = os.path.join(CORPUS, "LABELS.json")
SKILL_DIR = os.path.join(REPO, "skills", "human-voice", "scripts")
DETECTOR_PATH = os.path.join(SKILL_DIR, "detect_ai_prose.py")
PATTERNS_PATH = os.path.join(SKILL_DIR, "ai_prose_patterns.json")
RESULTS_PATH = os.path.join(HERE, "results.json")
ABLATION_RESULTS_PATH = os.path.join(HERE, "ablation_results.json")

DEFAULT_THRESHOLD = 5.0
BOOTSTRAP_SEED = 1729      # fixed so CI bounds are reproducible across runs
BOOTSTRAP_ITERS = 2000

# The only symbols the eval depends on from the linter. Keeping this list here
# makes the import boundary explicit: if the linter reorganizes, load_detector
# fails loudly with a clear message instead of deep inside a metric.
DETECTOR_MODULE_NAME = "detect_ai_prose"
DETECTOR_API = ("load_patterns", "lint", "analyze", "score",
                "resolve_weights", "CATEGORY_WEIGHTS")

_CI_CAVEAT = ("n is small and the corpus is authored; this interval reflects "
              "resampling variance within the fixed set, not sampling from "
              "real-world text.")


def load_detector():
    """Import the linter whether it is a single file or a package behind a shim."""
    if SKILL_DIR not in sys.path:
        sys.path.insert(0, SKILL_DIR)
    try:
        mod = importlib.import_module(DETECTOR_MODULE_NAME)
    except Exception:
        spec = importlib.util.spec_from_file_location(DETECTOR_MODULE_NAME, DETECTOR_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    missing = [name for name in DETECTOR_API if not hasattr(mod, name)]
    if missing:
        raise RuntimeError("linter is missing required API symbols: %s" % missing)
    return mod


def load_patterns(dap):
    return dap.load_patterns(PATTERNS_PATH)


def load_labels():
    with open(LABELS_PATH, encoding="utf-8") as fh:
        return json.load(fh)["labels"]


# Labels carry an optional "group" tag for hard-negative subsets. It defaults to
# the label, so the binary human/ai corpus is unchanged. "esl" marks careful
# non-native / formal-human negatives (still label "human", tracked for a
# dedicated FPR). "over_corrected" marks the anti-AI-costume class (its own label
# and directory), excluded from the binary metrics and scored on its own.
BINARY_LABELS = ("ai", "human")
HARD_NEG_DIRS = ("esl_formal", "over_corrected")


def _group_of(meta):
    return meta.get("group", meta["label"])


def read_corpus(labels):
    """Return [{file, label, register, group, text}, ...] sorted by file."""
    items = []
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(CORPUS, rel), encoding="utf-8") as fh:
            items.append({"file": rel, "label": meta["label"],
                          "register": meta["register"], "group": _group_of(meta),
                          "text": fh.read()})
    return items


def score_corpus(dap, patterns, labels):
    """Per-file records: file, label, register, group, score, verdict, words."""
    records = []
    for item in read_corpus(labels):
        res = dap.lint(item["text"], register=item["register"], dialect=None,
                       patterns=patterns)
        records.append({"file": item["file"], "label": item["label"],
                        "register": item["register"], "group": item["group"],
                        "score": res["score"], "verdict": res["verdict"],
                        "words": res["words"]})
    return records


def binary_records(records):
    """Just the human/ai records the floor-score classifier is evaluated on."""
    return [r for r in records if r["label"] in BINARY_LABELS]


def subset_fpr(records, threshold, group=None):
    """False-positive rate over human records (optionally one group, e.g. esl).

    Every record considered here is label 'human', so a score at/above the
    threshold is a false positive. Returns (rate, flagged, n).
    """
    subset = [r for r in records if r["label"] == "human"
              and (group is None or r["group"] == group)]
    flagged = sum(1 for r in subset if r["score"] >= threshold)
    n = len(subset)
    return (flagged / n if n else 0.0), flagged, n


def costume_eval(dap, items, patterns, threshold):
    """Evaluate the over-corrected ('anti-AI costume') class.

    These are human-authored but should be FLAGGED, so we report recall: the
    fraction scoring at/above threshold, and the fraction that specifically
    trips a costume category (over_correction or internet_tells). Excluded from
    the binary AUC so they never pollute precision.
    """
    costume_cats = {"over_correction", "internet_tells"}
    targets = [it for it in items if it["label"] == "over_corrected"]
    n = len(targets)
    flagged = caught = 0
    for it in targets:
        hits, _report, _words = dap.analyze(it["text"], it["register"], None, patterns)
        sc = dap.score(hits, _words, dap.resolve_weights(patterns))
        if sc >= threshold:
            flagged += 1
        if any(h.category in costume_cats for h in hits):
            caught += 1
    return {
        "n": n,
        "flagged_rate": round4(flagged / n) if n else None,
        "costume_category_rate": round4(caught / n) if n else None,
        "flagged": flagged,
        "costume_caught": caught,
        "threshold": threshold,
    }


def analyze_corpus(dap, items, patterns):
    """Analyze each file once, returning hits+words so ablation can re-score
    under different weights without re-running every check (37x speedup)."""
    out = []
    for item in items:
        hits, _report, words = dap.analyze(item["text"], item["register"], None, patterns)
        out.append({"label": item["label"], "register": item["register"],
                    "hits": hits, "words": words})
    return out


# --------------------------------------------------------------------------
# Canonical metrics (single implementation; round only at the output boundary)
# --------------------------------------------------------------------------

def round4(x):
    return round(x, 4) if x is not None else None


def confusion(records, threshold):
    """Predict 'ai' iff score >= threshold. Return tp, fp, tn, fn (positive=ai)."""
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
    human_fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "precision": round4(precision),
        "recall": round4(recall),
        "f1": round4(f1),
        "accuracy": round4(accuracy),
        "human_subset_false_positive_rate": round4(human_fpr),
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
    """Threshold maximizing F1 (tie-break: fewer human FP, higher acc, lower th)."""
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
    """ROC AUC via the Mann-Whitney rank statistic (unrounded). Positive='ai'.

    Returns the raw float so bootstrap/ablation keep full precision; round at
    the serialization boundary with round4().
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
    return wins / (len(pos) * len(neg))


def metrics_by_register(records, threshold):
    """Per-register confusion/metrics + auc (auc undefined for single-class)."""
    regs = {}
    for r in records:
        regs.setdefault(r["register"], []).append(r)
    out = {}
    for reg, recs in sorted(regs.items()):
        n_human = sum(1 for r in recs if r["label"] == "human")
        n_ai = sum(1 for r in recs if r["label"] == "ai")
        out[reg] = {
            "n": len(recs), "n_human": n_human, "n_ai": n_ai,
            "auc": round4(auc(recs)),
            "metrics": metrics(*confusion(recs, threshold)),
            "single_class": (n_human == 0 or n_ai == 0),
        }
    return out


def category_score_mass(dap, items, patterns):
    """Per-category share of total AI-subset floor score (cat_points, total)."""
    weights = dap.resolve_weights(patterns)
    cat_points = {c: 0.0 for c in dap.CATEGORY_WEIGHTS}
    total = 0.0
    for item in items:
        if item["label"] != "ai":
            continue
        hits, _report, words = dap.analyze(item["text"], item["register"], None, patterns)
        if not words:
            continue
        per_word = 1000.0 / words
        for h in hits:
            w = weights.get(h.category, 1.0)
            cat_points[h.category] = cat_points.get(h.category, 0.0) + w * per_word
            total += w * per_word
    return cat_points, total


def patterns_with_zeroed(patterns, category):
    """Copy of patterns with category_weights[category] forced to 0."""
    p = dict(patterns)
    cw = dict(p.get("category_weights") or {})
    cw[category] = 0.0
    p["category_weights"] = cw
    return p


# --------------------------------------------------------------------------
# Bootstrap confidence intervals (stdlib, deterministic via a fixed seed)
# --------------------------------------------------------------------------

def _percentile(sorted_vals, q):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    frac = idx - lo
    if lo + 1 < len(sorted_vals):
        return sorted_vals[lo] + frac * (sorted_vals[lo + 1] - sorted_vals[lo])
    return sorted_vals[lo]


def bootstrap_ci(records, stat_fn, iters=BOOTSTRAP_ITERS, seed=BOOTSTRAP_SEED,
                 alpha=0.05):
    """Stratified percentile bootstrap CI for stat_fn(records).

    Resamples the human and AI subsets independently (with replacement) to keep
    the class balance fixed, which avoids degenerate single-class resamples.
    """
    pos = [r for r in records if r["label"] == "ai"]
    neg = [r for r in records if r["label"] == "human"]
    point = stat_fn(records)
    rng = random.Random(seed)
    samples = []
    for _ in range(iters):
        resampled = ([rng.choice(pos) for _ in pos] +
                     [rng.choice(neg) for _ in neg])
        v = stat_fn(resampled)
        if v is not None:
            samples.append(v)
    samples.sort()
    return {
        "point": round4(point),
        "lo": round4(_percentile(samples, alpha / 2)),
        "hi": round4(_percentile(samples, 1 - alpha / 2)),
        "iters": iters,
        "seed": seed,
        "method": "stratified percentile bootstrap",
        "caveat": _CI_CAVEAT,
    }


def auc_ci(records):
    return bootstrap_ci(records, auc)


def f1_ci(records, threshold=DEFAULT_THRESHOLD):
    return bootstrap_ci(records, lambda rs: metrics(*confusion(rs, threshold))["f1"])


def fpr_ci(records, threshold=DEFAULT_THRESHOLD):
    return bootstrap_ci(
        records,
        lambda rs: metrics(*confusion(rs, threshold))["human_subset_false_positive_rate"])


# --------------------------------------------------------------------------
# Regression gating + corpus integrity
# --------------------------------------------------------------------------

# (path-in-dict, exact?) gated fields. Exact = any change is a regression;
# otherwise compared within tolerance.
_GATED = [
    ("corpus_size", True), ("n_human", True), ("n_ai", True),
    ("best_threshold", True),
    ("roc_auc", False),
    ("default.f1", False), ("default.accuracy", False),
    ("default.human_subset_false_positive_rate", False),
    ("best.f1", False),
    ("default.confusion.tp", True), ("default.confusion.fp", True),
    ("default.confusion.tn", True), ("default.confusion.fn", True),
]


def _dig(obj, path):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def compare_results(live, golden, tol=1e-4):
    """Return a list of drift messages (empty = within gate)."""
    diffs = []
    for path, exact in _GATED:
        lv, gv = _dig(live, path), _dig(golden, path)
        if lv is None or gv is None:
            if lv != gv:
                diffs.append("%s: golden=%r live=%r (missing on one side)" % (path, gv, lv))
            continue
        if exact:
            if lv != gv:
                diffs.append("%s: golden=%r live=%r" % (path, gv, lv))
        elif abs(float(lv) - float(gv)) > tol:
            diffs.append("%s: golden=%.4f live=%.4f (delta %.4f > %.4f)"
                         % (path, gv, lv, abs(lv - gv), tol))
    return diffs


def compare_ablation(live, golden, tol=1e-4):
    diffs = []
    for key in ("baseline_auc", "baseline_best_f1_acc"):
        lv, gv = live.get(key), golden.get(key)
        if lv is None or gv is None or abs(float(lv) - float(gv)) > tol:
            diffs.append("%s: golden=%r live=%r" % (key, gv, lv))
    return diffs


def validate_corpus(labels, dap):
    """Return a list of corpus-integrity problems (empty = OK)."""
    problems = []
    disk = set()
    for sub in ("ai", "human") + HARD_NEG_DIRS:
        d = os.path.join(CORPUS, sub)
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith(".md"):
                    disk.add("%s/%s" % (sub, fn))
    labeled = set(labels)
    for orphan in sorted(disk - labeled):
        problems.append("corpus file not in LABELS.json: %s" % orphan)
    for dangling in sorted(labeled - disk):
        problems.append("LABELS.json entry has no file: %s" % dangling)
    registers = set(getattr(dap, "REGISTERS", []))
    for rel, meta in sorted(labels.items()):
        if meta.get("label") not in ("ai", "human", "over_corrected"):
            problems.append("%s: label must be 'ai', 'human', or 'over_corrected'" % rel)
        if registers and meta.get("register") not in registers:
            problems.append("%s: unknown register %r" % (rel, meta.get("register")))
    return problems


__all__ = [
    "HERE", "REPO", "CORPUS", "LABELS_PATH", "SKILL_DIR", "DETECTOR_PATH",
    "PATTERNS_PATH", "RESULTS_PATH", "ABLATION_RESULTS_PATH",
    "DEFAULT_THRESHOLD", "BOOTSTRAP_SEED", "BOOTSTRAP_ITERS", "DETECTOR_API",
    "load_detector", "load_patterns", "load_labels", "read_corpus",
    "score_corpus", "analyze_corpus", "round4", "confusion", "metrics",
    "candidate_thresholds", "sweep", "auc", "metrics_by_register",
    "category_score_mass", "patterns_with_zeroed", "bootstrap_ci", "auc_ci",
    "f1_ci", "fpr_ci", "compare_results", "compare_ablation", "validate_corpus",
    "BINARY_LABELS", "HARD_NEG_DIRS", "binary_records", "subset_fpr",
    "costume_eval",
]
