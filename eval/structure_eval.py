#!/usr/bin/env python3
"""Recall and false-positive gate for the content-architecture checks.

`restatement`, `section_balance` and `depth_drift` read a document as a plan: what
it says twice, how it shares words between sections, and whether every section
is written for the same reader. None of that shows up in `eval/corpus/`, where
every sample is a single short section. So this harness measures the three checks
on their own.

Positives are `eval/structure/ai/`: six multi-section documents in the shape an
agent produces when asked for a design doc, a postmortem, a README, an options
analysis, a migration plan and an onboarding guide. Like the main corpus they are
authored, and EXPECTED below names the finding each one was written to carry. The
recall number shows the checks see what they claim to see. It does not show how
often agents write this way.

Negatives are everything in the repository that a person is meant to read as
competent prose: the human and ESL corpus classes, the project's own README,
CONTRIBUTING, EVAL and CHANGELOG, the skill's references, and every shipped
"after" example. None of them may fire.

The committed negatives are short or written by this project. The independent
test is a directory of long human markdown nobody wrote for this repo, and there
is no licence to vendor one. Point `--human-dir` at any local tree of READMEs and
manuals (a Homebrew Cellar or a node_modules folder works) and the harness sweeps
every markdown file between 400 and 6,000 words with four or more headings. The
calibration run behind the shipped thresholds is recorded in EVAL.md.

    python3 eval/structure_eval.py                 # report
    python3 eval/structure_eval.py --check         # exit 1 on a missed positive or a fired negative
    python3 eval/structure_eval.py --human-dir /opt/homebrew/Cellar
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import lib  # noqa: E402

CATEGORIES = ("restatement", "section_balance", "depth_drift")

# Each positive and the finding it carries. A file may fire more than this; it may
# not fire less.
EXPECTED = {
    "s01_design_doc.md": {"restatement", "section_balance"},
    "s02_postmortem.md": {"section_balance", "depth_drift"},
    "s03_readme.md": {"depth_drift"},
    "s04_analysis.md": {"section_balance"},
    "s05_migration.md": {"section_balance"},
    "s06_onboarding.md": {"restatement"},
}

NEGATIVE_GLOBS = (
    "eval/corpus/human/*.md",
    "eval/corpus/esl_formal/*.md",
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "eval/EVAL.md",
    "skills/human-voice/SKILL.md",
    "skills/human-voice/STYLE-GUIDE.md",
    "skills/human-voice/references/*.md",
    "skills/human-voice/examples/*after.md",
)

HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


def architecture_hits(dap, patterns, path, register="technical"):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    hits, report, _wc = dap.analyze(text, register, None, patterns)
    return [h for h in hits if h.category in CATEGORIES], report


def sweep_dir(dap, patterns, root):
    """Every long, sectioned markdown file under `root`, deduplicated by content."""
    seen = set()
    files = fired = 0
    by_cat = {c: 0 for c in CATEGORIES}
    examples = []
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            if not name.lower().endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            words = len(text.split())
            if not 400 <= words <= 6000 or len(HEADING_RE.findall(text)) < 4:
                continue
            key = hash(text)
            if key in seen:
                continue
            seen.add(key)
            files += 1
            hits, _r = architecture_hits(dap, patterns, path)
            cats = {h.category for h in hits}
            if cats:
                fired += 1
                for c in cats:
                    by_cat[c] += 1
                if len(examples) < 10:
                    examples.append((path, sorted(cats)))
    return files, fired, by_cat, examples


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if a positive misses its finding or a negative fires")
    ap.add_argument("--human-dir", help="sweep a local tree of human markdown for false positives")
    args = ap.parse_args()

    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    problems = []

    print("positives (eval/structure/ai/)")
    for name, want in sorted(EXPECTED.items()):
        hits, _r = architecture_hits(dap, patterns, os.path.join(HERE, "structure", "ai", name))
        got = {h.category for h in hits}
        missing = want - got
        print("  %-22s want %-40s got %s%s" % (
            name, ",".join(sorted(want)), ",".join(sorted(got)) or "-",
            "   MISSED " + ",".join(sorted(missing)) if missing else ""))
        if missing:
            problems.append("%s missed %s" % (name, sorted(missing)))
    on_disk = {os.path.basename(p) for p in glob.glob(os.path.join(HERE, "structure", "ai", "*.md"))}
    for extra in sorted(on_disk - set(EXPECTED)):
        problems.append("%s has no entry in EXPECTED" % extra)

    negatives = sorted({p for g in NEGATIVE_GLOBS for p in glob.glob(os.path.join(ROOT, g))})
    fired = []
    for path in negatives:
        hits, _r = architecture_hits(dap, patterns, path)
        if hits:
            fired.append((os.path.relpath(path, ROOT), hits))
    print("\nnegatives: %d files, %d fired" % (len(negatives), len(fired)))
    for rel, hits in fired:
        for h in hits[:3]:
            print("  %s L%d %s: %s" % (rel, h.line, h.category, h.text))
        problems.append("%s fired %s" % (rel, sorted({h.category for h in hits})))

    if args.human_dir:
        files, n_fired, by_cat, examples = sweep_dir(dap, patterns, args.human_dir)
        print("\nhuman sweep: %s" % args.human_dir)
        print("  %d long sectioned files, %d fired (%.1f%%)" % (
            files, n_fired, 100.0 * n_fired / files if files else 0.0))
        for c in CATEGORIES:
            print("  %-16s %d" % (c, by_cat[c]))
        for path, cats in examples:
            print("  fired: %s %s" % (path, cats))

    if args.check:
        if problems:
            print("\nstructure --check: FAIL")
            for p in problems:
                print("  - " + p)
            return 1
        print("\nstructure --check: OK (%d positives caught, %d negatives quiet)"
              % (len(EXPECTED), len(negatives)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
