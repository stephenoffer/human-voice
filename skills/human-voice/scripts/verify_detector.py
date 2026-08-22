#!/usr/bin/env python3
"""Verification gate: does this text still read as AI to a real detector?

The linter is a floor. It computes no perplexity and runs no model, so a document
can score 0.0 on it and still be flagged. This closes that loop: it asks an actual
detector and exits non-zero while the text is still flagged, so the rewrite has a
hard stopping condition instead of a judgment call.

    export GPTZERO_API_KEY=...            # or ORIGINALITY / SAPLING / WINSTON
    python3 verify_detector.py draft.md               # exit 1 while flagged
    python3 verify_detector.py --max-p-ai 0.05 d.md   # stricter gate
    python3 verify_detector.py --json draft.md
    python3 verify_detector.py --before old.md draft.md   # show the movement
    cat draft.md | python3 verify_detector.py -

With no API key set it exits 2 and says so, rather than reporting a pass it did not
earn. Nothing is sent anywhere until a key is configured; there is no default
endpoint and no telemetry.

Calibrate the detector before you believe it. Run it on a few pieces you know a
person wrote. In this repo's own panel of open detectors, one labels 34 of 34
hand-written human files as AI at p(AI)=1.000: it will flag your rewrite forever
while telling you nothing. A detector that cannot pass human text is not a target
worth chasing, and `eval/detector_local.py` excludes such models automatically.

Detector verdicts are evidence, not truth. GPT detectors misclassify non-native
English writing as machine-generated (Liang et al. 2023, Patterns), so a "clear"
does not certify authorship and a "flagged" does not refute it. Use this to catch a
rewrite that did not go far enough. Do not use it to grind prose into something
that scores well and reads badly: the tools that do that are detected precisely
because of the damage (see references/what-detectors-see.md).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from human_voice_linter import api as hv_api  # noqa: E402
from human_voice_linter import detector as D  # noqa: E402

EXIT_CLEAR = 0
EXIT_FLAGGED = 1
EXIT_UNAVAILABLE = 2


def read_target(target):
    if target == "-":
        return sys.stdin.read()
    with open(target, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Exit: 0 clear, 1 still flagged, 2 no detector configured.")
    ap.add_argument("target", help="file to verify, or - for stdin")
    ap.add_argument("--before", metavar="FILE",
                    help="also probe this earlier draft and report the movement")
    ap.add_argument("--max-p-ai", type=float, default=D.DEFAULT_MAX_P_AI,
                    help="gate threshold on p(AI) (default %(default)s)")
    ap.add_argument("--register", default="technical",
                    help="register for the floor score shown alongside")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)

    key_var, api_key = D.find_api_key()
    text = read_target(args.target)
    floor = hv_api.lint(text, register=args.register)

    if not api_key:
        msg = ("no detector configured: set one of %s to run the verification gate"
               % ", ".join(D.KEY_ENV_VARS))
        if args.json:
            json.dump({"status": "unavailable", "reason": msg,
                       "floor_score": floor["score"], "floor_verdict": floor["verdict"]},
                      sys.stdout, indent=2)
            print()
        else:
            print("verification: UNAVAILABLE")
            print("  %s" % msg)
            print("  floor score %.1f [%s] — the linter ran, but it is a floor and"
                  % (floor["score"], floor["verdict"]))
            print("  cannot stand in for a detector. Report this gate as not run.")
        return EXIT_UNAVAILABLE

    result = {"detector": D.DETECTORS[key_var]["name"], "max_p_ai": args.max_p_ai,
              "floor_score": floor["score"], "floor_verdict": floor["verdict"]}
    try:
        p_ai = D.probe(text, api_key, key_var, timeout=args.timeout)
    except Exception as exc:
        result.update(status="error", reason="%s: %s" % (type(exc).__name__, exc))
        if args.json:
            json.dump(result, sys.stdout, indent=2)
            print()
        else:
            print("verification: ERROR")
            print("  %s" % result["reason"])
            print("  Treat this as NOT verified. Do not report a pass.")
        return EXIT_UNAVAILABLE

    label, clear = D.verdict(p_ai, args.max_p_ai)
    result.update(status=label, p_ai=round(p_ai, 4))

    if args.before:
        try:
            p_before = D.probe(read_target(args.before), api_key, key_var,
                               timeout=args.timeout)
            result["p_ai_before"] = round(p_before, 4)
            result["delta"] = round(p_before - p_ai, 4)
        except Exception as exc:
            result["before_error"] = "%s: %s" % (type(exc).__name__, exc)

    if args.json:
        json.dump(result, sys.stdout, indent=2)
        print()
    else:
        print("verification: %s   (%s)" % (label.upper(), result["detector"]))
        print("  p(AI) = %.3f    gate = below %.2f" % (p_ai, args.max_p_ai))
        if "delta" in result:
            print("  before = %.3f  ->  after = %.3f   (%+.3f)"
                  % (result["p_ai_before"], p_ai, -result["delta"]))
        print("  linter floor: %.1f [%s]" % (floor["score"], floor["verdict"]))
        if clear:
            print("  Clear at this threshold, against this detector. That is not a")
            print("  guarantee against a different one, and detectors carry real")
            print("  false-positive rates in both directions.")
        else:
            print("  Still flagged, so the pass is not finished. Go back to the")
            print("  rewrite in priority order: shape first (headings, bullet ratio,")
            print("  bold density, the recap section), then the sentence-length")
            print("  distribution, then real specificity from the author-material")
            print("  intake. Each loop must leave the writing better.")
            print("  Do NOT reach for synonym mangling, Unicode homoglyphs,")
            print("  zero-width characters, or injected typos. Detectors catch those")
            print("  by the damage they leave, so they lose on their own terms.")
            print("  If two passes cannot move this without hurting the prose, stop")
            print("  and report the residual instead of grinding.")
    return EXIT_CLEAR if clear else EXIT_FLAGGED


if __name__ == "__main__":
    sys.exit(main())
