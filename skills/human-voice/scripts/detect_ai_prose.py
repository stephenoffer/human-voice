#!/usr/bin/env python3
"""Detect surface features that correlate with AI-written prose.

This is the deterministic *floor* of the human-voice skill: cheap, regex-able
tells (filler diction, em-dash overuse, bold-bullet listicles, rule-of-three,
low burstiness, n-gram repetition, low lexical diversity). It does NOT compute
perplexity or log-prob curvature the way GPTZero or DetectGPT do — it catches
the surface features that *correlate* with what those detectors measure. No
detector is ground truth; the real test is a skeptical human read.

Pure standard library. No third-party dependencies. Designed to never crash on
hostile input: bad encodings, binary files, malformed pattern files, and
adversarial Markdown all degrade gracefully rather than raising.

Usage:
    detect_ai_prose.py <file>
    detect_ai_prose.py -                      # read stdin
    detect_ai_prose.py --register marketing <file>
    detect_ai_prose.py --dialect american <file>
    detect_ai_prose.py --json <file>
"""

import os
import sys

# The implementation lives in the human_voice_linter package alongside this
# file. This shim is kept at this exact path because the README, Makefile,
# CI, SKILL.md, and the eval harness all invoke/import it directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from human_voice_linter import *  # noqa: E402,F401,F403
from human_voice_linter import main  # noqa: E402


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        os._exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
