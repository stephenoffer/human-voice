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

2. Implement `call_detector(text, api_key) -> float` below. It must return a
   single "probability this text is AI" in [0.0, 1.0]. For GPTZero that is the
   `documents[0].completely_generated_prob` field of the POST /v2/predict/text
   response. Use only the standard library (urllib.request) so this file keeps
   its zero-dependency promise, or import `requests` if your project already
   has it.

       import urllib.request, json
       req = urllib.request.Request(
           "https://api.gptzero.me/v2/predict/text",
           data=json.dumps({"document": text}).encode(),
           headers={"x-api-key": api_key, "Content-Type": "application/json"},
           method="POST")
       with urllib.request.urlopen(req, timeout=30) as resp:
           payload = json.load(resp)
       return float(payload["documents"][0]["completely_generated_prob"])

3. Run before/after pairs. This harness looks for pairs in the corpus by
   convention: an AI file `ai/aNN_*.md` is the "before"; if a matching human
   rewrite exists you can compare. By default it simply scores every corpus
   file through the detector and prints the detector score next to the linter
   floor score, so you can see whether the two agree.

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

# Recognized API-key env vars. The first one set selects the detector.
KEY_ENV_VARS = ("GPTZERO_API_KEY", "ORIGINALITY_API_KEY", "SAPLING_API_KEY",
                "AI_DETECTOR_API_KEY")


def find_api_key():
    for var in KEY_ENV_VARS:
        val = os.environ.get(var)
        if val:
            return var, val
    return None, None


def call_detector(text, api_key):
    """Return P(text is AI) in [0,1] from a real external detector.

    Intentionally unimplemented. Fill this in following the docstring above to
    enable the online path. Until then the harness will refuse to pretend it
    has a working detector.
    """
    raise NotImplementedError(
        "call_detector is a stub. Wire a real detector per the module docstring "
        "before using the online path.")


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


def run_online(key_var, api_key):
    dap = lib.load_detector()
    patterns = lib.load_patterns(dap)
    labels = lib.load_labels()
    print("Online path: using %s. Calling external detector per file." % key_var)
    print("(External detectors are biased; treat scores as evidence, not truth.)")
    print()
    print("  %-38s %-6s %8s %12s" % ("file", "label", "floor", "detector_p"))
    print("  " + "-" * 70)
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(CORPUS, rel), encoding="utf-8") as fh:
            text = fh.read()
        res = dap.lint(text, register=meta["register"], dialect=None, patterns=patterns)
        try:
            p = call_detector(text, api_key)
            pstr = "%.3f" % p
        except NotImplementedError as exc:
            print()
            print("error: %s" % exc)
            print("Falling back to the offline summary.")
            return run_offline_summary()
        except Exception as exc:  # network/parse errors must never crash the harness
            pstr = "ERR(%s)" % type(exc).__name__
        print("  %-38s %-6s %8.1f %12s" % (rel, meta["label"], res["score"], pstr))


def main():
    key_var, api_key = find_api_key()
    if not api_key:
        print("skipped: no API key set.")
        print("Set one of %s to enable the external-detector path." % ", ".join(KEY_ENV_VARS))
        print("Running offline floor-score summary instead (no network calls).")
        print()
        run_offline_summary()
        return 0
    run_online(key_var, api_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
