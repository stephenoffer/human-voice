#!/usr/bin/env python3
"""Evaluate the human-voice linter's FLOOR score as a binary AI/human classifier.

Scores every file in the labeled calibration corpus, treats the floor score as a
one-dimensional classifier (predict "ai" when score >= threshold), and reports —
at the default "watch" boundary (5.0) and a swept best-F1 threshold — precision,
recall, F1, accuracy, the confusion matrix, the human-subset false-positive rate,
ROC AUC, a per-register breakdown, and bootstrap confidence intervals.

  python3 run_eval.py            # recompute and write eval/results.json (the golden)
  python3 run_eval.py --check    # recompute in memory, fail if it drifts from the golden

Pure standard library. Runs offline.

HONESTY NOTE: the corpus is small and AUTHORED to exhibit (ai) or avoid (human)
the exact tells the linter scores. These numbers measure calibration and internal
separation, not real-world accuracy. The linter is a FLOOR, never ground truth.
"""
from __future__ import annotations

import argparse
import json
import sys

import lib


def build_report():
    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    labels = lib.load_labels()
    records = lib.score_corpus(dap, patterns, labels)
    items = lib.read_corpus(labels)

    n_human = sum(1 for r in records if r["label"] == "human")
    n_ai = sum(1 for r in records if r["label"] == "ai")
    default_m = lib.metrics(*lib.confusion(records, lib.DEFAULT_THRESHOLD))
    best_th, best_m, sweep_rows = lib.sweep(records)

    cat_points, total_points = lib.category_score_mass(dap, items, patterns)
    by_cat = {c: lib.round4(p / total_points) for c, p in cat_points.items()
              if total_points and p > 0}

    out = {
        "corpus_size": len(records),
        "n_human": n_human,
        "n_ai": n_ai,
        "roc_auc": lib.round4(lib.auc(records)),
        "confidence_intervals": {
            "roc_auc": lib.auc_ci(records),
            "default_f1": lib.f1_ci(records),
            "default_human_fpr": lib.fpr_ci(records),
        },
        "default_threshold": lib.DEFAULT_THRESHOLD,
        "default": default_m,
        "best_threshold": best_th,
        "best": best_m,
        "by_register": lib.metrics_by_register(records, lib.DEFAULT_THRESHOLD),
        "by_category_ai_share": dict(sorted(by_cat.items(),
                                            key=lambda kv: -kv[1])),
        "sweep": [{"threshold": th, "f1": m["f1"], "precision": m["precision"],
                   "recall": m["recall"], "accuracy": m["accuracy"],
                   "human_fpr": m["human_subset_false_positive_rate"]}
                  for th, m in sweep_rows],
        "records": records,
        "_note": ("Authored synthetic calibration corpus; measures internal "
                  "separation/calibration, not real-world accuracy. Linter is a floor."),
    }
    return out, labels, dap


def fmt_table(records):
    lines = ["  %-38s %-6s %-10s %8s  %s" % ("file", "label", "register", "score", "verdict"),
             "  " + "-" * 78]
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


def print_report(out):
    print("=" * 80)
    print("human-voice linter floor-score evaluation")
    print("corpus: %d files (%d human, %d ai)   [authored synthetic calibration set]"
          % (out["corpus_size"], out["n_human"], out["n_ai"]))
    print("=" * 80)
    print()
    print("Per-file scores:")
    print(fmt_table(out["records"]))
    print()
    print("  ROC AUC (rank-based, ties=0.5): %s" % out["roc_auc"])
    print()
    print(fmt_metrics("DEFAULT boundary", out["default_threshold"], out["default"]))
    print()
    print(fmt_metrics("SWEPT best-F1 threshold", out["best_threshold"], out["best"]))
    print()
    print("Per-register breakdown (threshold %.1f):" % out["default_threshold"])
    print("  %-12s %3s %5s %4s %8s %7s %7s" % (
        "register", "n", "human", "ai", "AUC", "F1", "h-FPR"))
    for reg, b in out["by_register"].items():
        m = b["metrics"]
        auc_s = "  n/a" if b["single_class"] else "%6.3f" % b["auc"]
        print("  %-12s %3d %5d %4d %8s %7.3f %7.3f%s" % (
            reg, b["n"], b["n_human"], b["n_ai"], auc_s, m["f1"],
            m["human_subset_false_positive_rate"],
            "  *single-class" if b["single_class"] else ""))
    print()
    ci = out["confidence_intervals"]
    print("95%% bootstrap CIs (stratified, seed=%d, %d iters):"
          % (lib.BOOTSTRAP_SEED, lib.BOOTSTRAP_ITERS))
    print("  ROC AUC    %.3f  [%.3f, %.3f]" % (ci["roc_auc"]["point"],
          ci["roc_auc"]["lo"], ci["roc_auc"]["hi"]))
    print("  F1@%.1f     %.3f  [%.3f, %.3f]" % (out["default_threshold"],
          ci["default_f1"]["point"], ci["default_f1"]["lo"], ci["default_f1"]["hi"]))
    print("  human-FPR  %.3f  [%.3f, %.3f]" % (ci["default_human_fpr"]["point"],
          ci["default_human_fpr"]["lo"], ci["default_human_fpr"]["hi"]))
    print("  Note: intervals reflect resampling variance of an AUTHORED corpus.")
    print()
    print("Note: this corpus is small and authored to exhibit/avoid the exact")
    print("tells the linter scores. These numbers measure calibration, not")
    print("real-world detection. The linter is a FLOOR, not ground truth.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="compare against the committed results.json; exit 1 on drift")
    ap.add_argument("--tol", type=float, default=1e-4,
                    help="tolerance for non-exact gated metrics (default 1e-4)")
    args = ap.parse_args(argv)

    out, labels, dap = build_report()

    corpus_problems = lib.validate_corpus(labels, dap)
    for p in corpus_problems:
        sys.stderr.write("corpus: %s\n" % p)

    if args.check:
        try:
            with open(lib.RESULTS_PATH, encoding="utf-8") as fh:
                golden = json.load(fh)
        except (OSError, ValueError) as exc:
            sys.stderr.write("error: cannot read golden %s: %s\n" % (lib.RESULTS_PATH, exc))
            return 2
        diffs = lib.compare_results(out, golden, tol=args.tol)
        if diffs or corpus_problems:
            sys.stderr.write("EVAL REGRESSION: metrics drifted from the committed baseline.\n")
            for d in diffs:
                sys.stderr.write("  %s\n" % d)
            sys.stderr.write("If this change is intentional, run `python3 eval/run_eval.py` "
                             "to regenerate results.json and review the diff.\n")
            return 1
        print("eval --check: OK (metrics match the committed baseline within tol=%g)" % args.tol)
        return 0

    print_report(out)
    with open(lib.RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print()
    print("Wrote %s" % lib.RESULTS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
