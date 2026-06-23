#!/usr/bin/env python3
"""Per-category ablation: how much does each linter category contribute to
separating the human and AI corpus subsets?

For each scoring category, re-score the corpus with that category's weight set to
0 and recompute ROC AUC and best-F1 accuracy. The DROP from the full-model
baseline is the category's contribution. On a corpus this well-separated the top
two metrics tie at 0, so the category's share of the AI-subset score mass breaks
the tie and surfaces which tells actually drive the AI scores.

  python3 ablation.py            # recompute and write eval/ablation_results.json
  python3 ablation.py --check    # fail if the baseline separation drifts

Pure standard library. Exits 0 (or 1 under --check on drift).

HONESTY NOTE: contribution is measured ON THIS authored corpus only. A category
that contributes 0 here may still be the decisive tell on text in the wild. The
linter is a floor, not ground truth.
"""
from __future__ import annotations

import argparse
import json
import sys

import lib


def _records(scored_hits, dap, weights):
    return [{"label": r["label"], "score": dap.score(r["hits"], r["words"], weights)}
            for r in scored_hits]


def build_results():
    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    items = lib.read_corpus(lib.load_labels())
    analyzed = lib.analyze_corpus(dap, items, patterns)  # analyze once, re-score many

    base_weights = dap.resolve_weights(patterns)
    base_records = _records(analyzed, dap, base_weights)
    base_auc = lib.auc(base_records)
    _bt, base_best, _rows = lib.sweep(base_records)
    base_acc = base_best["accuracy"]

    cat_points, total_points = lib.category_score_mass(dap, items, patterns)

    rows = []
    for category in sorted(dap.CATEGORY_WEIGHTS):
        weights = dap.resolve_weights(lib.patterns_with_zeroed(patterns, category))
        recs = _records(analyzed, dap, weights)
        a = lib.auc(recs)
        _t, best, _r = lib.sweep(recs)
        pts = cat_points.get(category, 0.0)
        rows.append({
            "category": category,
            "weight": base_weights.get(category),
            "auc": lib.round4(a),
            "auc_drop": lib.round4(base_auc - a) if a is not None else None,
            "best_f1_acc": best["accuracy"],
            "acc_drop": lib.round4(base_acc - best["accuracy"]),
            "ai_score_share": lib.round4(pts / total_points) if total_points else 0.0,
        })
    rows.sort(key=lambda r: ((r["auc_drop"] or 0.0), r["acc_drop"], r["ai_score_share"]),
              reverse=True)
    return {"baseline_auc": lib.round4(base_auc),
            "baseline_best_f1_acc": base_acc, "rows": rows}


def print_report(out):
    print("=" * 78)
    print("Per-category ablation -- contribution to human/AI separation")
    print("baseline (full model): AUC %.4f   best-F1 accuracy %.4f"
          % (out["baseline_auc"], out["baseline_best_f1_acc"]))
    print("=" * 78)
    print()
    print("  %-22s %6s %8s %9s %8s %9s" % (
        "category", "weight", "AUC", "AUCdrop", "accdrop", "AIshare"))
    print("  " + "-" * 68)
    for r in out["rows"]:
        print("  %-22s %6.1f %8.4f %9.4f %8.4f %8.1f%%" % (
            r["category"], r["weight"], r["auc"], r["auc_drop"] or 0.0,
            r["acc_drop"], 100 * r["ai_score_share"]))
    print()
    top_share = [r for r in out["rows"] if r["ai_score_share"] > 0][:6]
    print("Top drivers of the AI scores (by score-mass share): %s"
          % ", ".join("%s %.0f%%" % (r["category"], 100 * r["ai_score_share"])
                      for r in top_share))
    print()
    print("HONESTY NOTE: contribution is measured on this small authored corpus")
    print("only. A 0-drop category may still be decisive on real text. Floor, not truth.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="compare against committed ablation_results.json; exit 1 on drift")
    ap.add_argument("--tol", type=float, default=1e-4)
    args = ap.parse_args(argv)

    out = build_results()

    if args.check:
        try:
            with open(lib.ABLATION_RESULTS_PATH, encoding="utf-8") as fh:
                golden = json.load(fh)
        except (OSError, ValueError) as exc:
            sys.stderr.write("error: cannot read golden: %s\n" % exc)
            return 2
        diffs = lib.compare_ablation(out, golden, tol=args.tol)
        if diffs:
            sys.stderr.write("ABLATION REGRESSION: baseline separation drifted.\n")
            for d in diffs:
                sys.stderr.write("  %s\n" % d)
            sys.stderr.write("If intentional, run `python3 eval/ablation.py` to regenerate.\n")
            return 1
        print("ablation --check: OK (baseline matches within tol=%g)" % args.tol)
        return 0

    print_report(out)
    with open(lib.ABLATION_RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print()
    print("Wrote %s" % lib.ABLATION_RESULTS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
