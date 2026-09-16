#!/usr/bin/env python3
"""False-positive sweep over human prose nobody wrote for this repository.

`eval/corpus/` is authored by hand, and EVAL.md says plainly that this is its
central limitation: the samples were written by one person who knew what the
linter checks. Every false-positive number measured there carries that caveat.

This harness removes the caveat for one class of text. The Python standard
library ships thousands of words of documentation written by hundreds of people
over three decades, none of whom had heard of this tool. It is on every machine
that can run the linter, it needs no network, and it is unambiguously
human-written. That makes it the best available independent negative set.

What it is NOT: a sample of the prose this skill targets. API reference is a
genre of its own, heavy on identifiers, aligned tables, terse imperative
fragments, and deliberate terminology repetition. A high score here can mean the
linter is wrong OR that reference documentation is simply not report prose. So
the gate is deliberately loose and outcome-shaped: the median must stay under a
ceiling, and no single category may run away. Read a regression as "go and look",
not as "the linter broke".

    python3 eval/human_baseline.py            # report, and write the baseline
    python3 eval/human_baseline.py --check    # fail (exit 1) on a regression

Docstrings differ between Python versions, so the report records the version it
ran on and `--check` compares aggregates with tolerance rather than per-module
scores.
"""
from __future__ import annotations

import argparse
import collections
import importlib
import inspect
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lib  # noqa: E402

RESULTS_PATH = os.path.join(HERE, "human_baseline_results.json")

# Standard-library modules with substantial prose in their docstrings. Chosen for
# volume and variety of author, not to make any number look good.
MODULES = (
    "argparse", "asyncio", "collections", "csv", "dataclasses", "decimal",
    "difflib", "email", "fractions", "functools", "hashlib", "http",
    "itertools", "json", "logging", "pathlib", "random", "re", "shutil",
    "socket", "sqlite3", "ssl", "statistics", "subprocess", "tempfile",
    "textwrap", "typing", "unittest", "urllib",
)

MIN_WORDS = 150            # below this a density means nothing
MIN_DOCSTRING_CHARS = 200  # a one-line docstring is not prose

# Gate values. Generous on purpose: see the module docstring on why a score here
# is not directly comparable to a score on report prose.
MAX_MEDIAN_SCORE = 12.0
MAX_WORST_SCORE = 26.0
MAX_CATEGORY_SHARE = 0.45  # no single category may own more of the total


def module_prose(name):
    """All substantial docstrings in one module, joined."""
    try:
        mod = importlib.import_module(name)
    except Exception:                      # noqa: BLE001 - optional stdlib module
        return None
    parts = []
    if isinstance(mod.__doc__, str) and mod.__doc__.strip():
        parts.append(inspect.cleandoc(mod.__doc__))
    seen = set()
    for attr, obj in vars(mod).items():
        # Only functions and classes carry prose of their own. Two other kinds of
        # attribute used to leak in, and both made the sweep measure the wrong text:
        # - an imported module (`logging.os`, `email.message`) contributed that
        #   module's docstring, so the result depended on import order; under pytest
        #   `email` scored 34.2 against 17.7 in a plain run;
        # - a constant (`socket.AF_INET`, `argparse.SUPPRESS`) answers `__doc__` with
        #   its type's docstring, so `int`'s text was scored 172 times in `sqlite3`.
        if attr.startswith("_") or not (inspect.isclass(obj) or inspect.isroutine(obj)):
            continue
        doc = getattr(obj, "__doc__", None)
        if isinstance(doc, str) and len(doc) >= MIN_DOCSTRING_CHARS and doc not in seen:
            seen.add(doc)
            parts.append(inspect.cleandoc(doc))
    return "\n\n".join(parts)


def sweep():
    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    rows = []
    per_category = collections.Counter()
    for name in MODULES:
        text = module_prose(name)
        if not text:
            continue
        res = dap.lint(text, register="technical", dialect=None, patterns=patterns)
        # Filter on the words the linter scored, not on raw whitespace tokens: a
        # docstring heavy with signatures and examples can pass a raw count while
        # leaving too little prose for any density to mean something.
        if res["words"] < MIN_WORDS:
            continue
        rows.append({"module": name, "score": res["score"], "words": res["words"],
                     "verdict": res["verdict"]})
        for hit in res["hits"]:
            per_category[hit["category"]] += 1
    rows.sort(key=lambda r: -r["score"])
    scores = sorted(r["score"] for r in rows)
    total_hits = sum(per_category.values()) or 1
    return {
        "python": "%d.%d" % sys.version_info[:2],
        "modules": len(rows),
        "median_score": scores[len(scores) // 2] if scores else 0.0,
        "mean_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "worst_score": scores[-1] if scores else 0.0,
        "flagged_at_5": sum(1 for s in scores if s >= lib.DEFAULT_THRESHOLD),
        "top_category": per_category.most_common(1)[0][0] if per_category else None,
        "top_category_share": round(per_category.most_common(1)[0][1] / total_hits, 4)
        if per_category else 0.0,
        "category_counts": dict(per_category.most_common()),
        "rows": rows,
    }


def gate(report):
    """Return a list of failures against the fixed ceilings (empty = OK)."""
    problems = []
    if report["median_score"] > MAX_MEDIAN_SCORE:
        problems.append("median score %.1f exceeds the ceiling of %.1f"
                        % (report["median_score"], MAX_MEDIAN_SCORE))
    if report["worst_score"] > MAX_WORST_SCORE:
        problems.append("worst score %.1f exceeds the ceiling of %.1f"
                        % (report["worst_score"], MAX_WORST_SCORE))
    if report["top_category_share"] > MAX_CATEGORY_SHARE:
        problems.append("%r is %.0f%% of all findings, over the %.0f%% ceiling; one "
                        "check is running away on human text"
                        % (report["top_category"], report["top_category_share"] * 100,
                           MAX_CATEGORY_SHARE * 100))
    return problems


def render(report):
    out = ["=" * 74,
           "Human-prose false-positive sweep: Python %s standard library docstrings"
           % report["python"],
           "not authored for this repository; see the module docstring on what it "
           "does and does not show",
           "=" * 74, ""]
    out.append("  module           score  words   verdict")
    out.append("  " + "-" * 46)
    for r in report["rows"]:
        out.append("  %-15s %6.1f  %5d   %s"
                   % (r["module"], r["score"], r["words"], r["verdict"]))
    out.append("")
    out.append("modules %d   median %.1f (ceiling %.1f)   worst %.1f (ceiling %.1f)"
               % (report["modules"], report["median_score"], MAX_MEDIAN_SCORE,
                  report["worst_score"], MAX_WORST_SCORE))
    out.append("flagged at %.1f: %d of %d"
               % (lib.DEFAULT_THRESHOLD, report["flagged_at_5"], report["modules"]))
    out.append("")
    out.append("Findings by category (a runaway here is the signal to watch):")
    for cat, n in list(report["category_counts"].items())[:10]:
        out.append("  %-22s %5d  %4.1f%%"
                   % (cat, n, 100.0 * n / max(1, sum(report["category_counts"].values()))))
    out.append("")
    out.append("Reference documentation is not report prose. Treat a rise here as a")
    out.append("prompt to read the new findings, not as proof the linter regressed.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the sweep breaches a ceiling; write nothing")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    report = sweep()
    if not report["modules"]:
        sys.stderr.write("error: no stdlib module produced enough prose to score\n")
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))

    problems = gate(report)
    if args.check:
        if problems:
            sys.stderr.write("human-baseline --check FAILED:\n")
            for p in problems:
                sys.stderr.write("  - %s\n" % p)
            return 1
        print("\nhuman-baseline --check: OK (within every ceiling)")
        return 0

    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("\nWrote %s" % RESULTS_PATH)
    if problems:
        sys.stderr.write("warning: this run breaches a ceiling:\n")
        for p in problems:
            sys.stderr.write("  - %s\n" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
