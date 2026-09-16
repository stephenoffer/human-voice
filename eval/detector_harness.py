#!/usr/bin/env python3
"""Optional scaffold for measuring rewrites against an EXTERNAL AI detector.

The human-voice linter is a FLOOR: it catches surface tells but does not compute
perplexity or log-prob curvature the way commercial detectors (GPTZero,
Originality.ai, Sapling, DetectGPT) do. To know whether a rewrite actually moves
an external detector's score, you have to call that detector. This script is the
place to wire that up.

DEFAULT PATH IS OFFLINE AND MAKES NO NETWORK CALLS. It runs a detector only when
an API key env var is set. With no key it prints a clear "skipped" message and
exits 0, so it is safe to run in CI or on an airgapped machine.

------------------------------------------------------------------------------
HOW TO WIRE A REAL DETECTOR
------------------------------------------------------------------------------
1. Pick a detector and get an API key. Set it in the environment, e.g.:

       export GPTZERO_API_KEY=sk-...

2. The request shapes live in `human_voice_linter/detector.py` (GPTZero,
   Originality.ai, Sapling, Winston), shared with the skill's `verify_detector.py`
   gate so there is one copy. Those shapes have NOT been exercised against a
   live API from this repo, so treat the first run as a smoke test: a stale shape
   prints ERR(...) for each file rather than crashing, and the fix is one entry in
   the `DETECTORS` table. Standard library only (urllib), so the zero-dependency
   promise holds.

3. What to look at. `--pairs` scores just the shipped before/after example pairs,
   which is the measurement you actually want: same claim, two voices, does the
   detector move? It prints the mean drop in p(AI) across pairs. The full run also
   prints mean p(AI) per corpus class — if the detector does not put `human` well
   below `ai` and `ai_modern`, its verdicts on this corpus mean little and you
   should not tune anything to them.

------------------------------------------------------------------------------
HONESTY NOTE
------------------------------------------------------------------------------
External detectors are themselves biased and unreliable. Liang et al. (2023)
showed GPT detectors systematically misclassify non-native-English writing as
AI-generated. A detector score is evidence, not truth. The goal of human-voice
is genuinely better writing, not a passing detector score; do not tune the
skill to game any single detector.
"""

import os
import sys

import lib

CORPUS = lib.CORPUS

# The request shapes, key discovery, and the probe live in the skill package, so
# the skill works when copied to ~/.claude/skills/ without this eval directory.
_dap = lib.load_detector()
sys.path.insert(0, lib.SKILL_DIR)
from human_voice_linter import detector as D  # noqa: E402

DETECTORS = D.DETECTORS
KEY_ENV_VARS = D.KEY_ENV_VARS
find_api_key = D.find_api_key
_dig_path = D.dig


def call_detector(text, api_key, key_var="GPTZERO_API_KEY", timeout=30):
    """Thin alias kept for callers of the older name."""
    return D.probe(text, api_key, key_var, timeout=timeout)


# Register for each shipped example pair, so the floor column is scored the way
# the skill would score it rather than always as `technical`.
PAIR_REGISTER = {"academic": "academic", "casual": "casual", "email": "email",
                 "marketing": "marketing", "modern-ai": "technical",
                 "syntax-signature": "technical",
                 "architecture": "technical",
                 "cliche-metaphor": "technical", "over-corrected": "technical"}


def example_pairs():
    """The shipped before/after example pairs, which are what you actually want
    to measure: does the rewrite move a detector, on the same claim?"""
    ex = os.path.join(os.path.dirname(lib.SKILL_DIR), "examples")
    pairs = []
    if not os.path.isdir(ex):
        return pairs
    for fn in sorted(os.listdir(ex)):
        if not fn.endswith("-before.md"):
            continue
        stem = fn[:-len("-before.md")]
        after = os.path.join(ex, stem + "-after.md")
        if os.path.isfile(after):
            pairs.append((stem, os.path.join(ex, fn), after))
    return pairs


def run_offline_summary():
    """The default, network-free path: just report the linter floor scores and
    explain what the online path would add."""
    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    labels = lib.load_labels()
    print("Offline path: linter floor scores only (no external detector called).")
    print()
    print("  %-38s %-6s %8s" % ("file", "label", "floor"))
    print("  " + "-" * 56)
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(CORPUS, rel), encoding="utf-8") as fh:
            text = fh.read()
        res = dap.lint(text, register=meta["register"], dialect=None, patterns=patterns)
        print("  %-38s %-6s %8.1f" % (rel, meta["label"], res["score"]))


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def run_online(key_var, api_key, pairs_only=False):
    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    name = DETECTORS.get(key_var, {}).get("name", key_var)
    print("Online path: %s (via %s)." % (name, key_var))
    print("(External detectors are biased; treat scores as evidence, not truth.)")
    print()

    def score_one(text, register):
        res = dap.lint(text, register=register, dialect=None, patterns=patterns)
        try:
            return res["score"], call_detector(text, api_key, key_var), None
        except Exception as exc:  # never crash the harness on a bad response
            return res["score"], None, "%s: %s" % (type(exc).__name__, exc)

    print("Example before/after pairs (does the rewrite move the detector?):")
    print("  %-22s %8s %8s %10s %10s" % ("pair", "floor.b", "floor.a", "det.b", "det.a"))
    print("  " + "-" * 64)
    deltas = []
    for stem, bpath, apath in example_pairs():
        with open(bpath, encoding="utf-8") as fh:
            btext = fh.read()
        with open(apath, encoding="utf-8") as fh:
            atext = fh.read()
        reg = PAIR_REGISTER.get(stem, "technical")
        fb, pb, eb = score_one(btext, reg)
        fa, pa, ea = score_one(atext, reg)
        print("  %-22s %8.1f %8.1f %10s %10s" % (
            stem, fb, fa,
            "ERR" if pb is None else "%.3f" % pb,
            "ERR" if pa is None else "%.3f" % pa))
        if eb or ea:
            print("      %s" % (eb or ea))
        if pb is not None and pa is not None:
            deltas.append(pb - pa)
    if deltas:
        print()
        print("  mean detector-probability drop across %d pairs: %+.3f"
              % (len(deltas), _mean(deltas)))
        print("  (positive = the rewrite reads more human to this detector)")
    if pairs_only:
        return

    labels = lib.load_labels()
    print()
    print("Full corpus:")
    print("  %-40s %-14s %8s %10s" % ("file", "label", "floor", "det_p"))
    print("  " + "-" * 76)
    by_label = {}
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(CORPUS, rel), encoding="utf-8") as fh:
            text = fh.read()
        floor, p, err = score_one(text, meta["register"])
        print("  %-40s %-14s %8.1f %10s" % (
            rel, meta["label"], floor, "ERR" if p is None else "%.3f" % p))
        if p is not None:
            by_label.setdefault(meta["label"], []).append(p)
    print()
    print("Mean detector probability by class (this is the comparison that matters):")
    for lab in sorted(by_label):
        ps = by_label[lab]
        print("  %-16s n=%-3d mean p(AI) = %.3f" % (lab, len(ps), _mean(ps)))
    print()
    print("If mean p(AI) for 'human' is not far below 'ai' and 'ai_modern', the")
    print("detector is not separating this corpus and its verdicts here mean little.")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", action="store_true",
                    help="only score the shipped before/after example pairs")
    args = ap.parse_args(argv)
    key_var, api_key = find_api_key()
    if not api_key:
        print("skipped: no API key set.")
        print("Set one of %s to enable the external-detector path." % ", ".join(KEY_ENV_VARS))
        print("Running offline floor-score summary instead (no network calls).")
        print()
        run_offline_summary()
        return 0
    run_online(key_var, api_key, pairs_only=args.pairs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
