"""api — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import argparse
import bisect
import functools
import json
import math
import os
import re
import sys
from collections import Counter
from .hit import *  # noqa: F401,F403
from .defaults import *  # noqa: F401,F403
from .patterns import *  # noqa: F401,F403
from .textutil import *  # noqa: F401,F403
from .checks import *  # noqa: F401,F403
from .score import *  # noqa: F401,F403
from .analyze import *  # noqa: F401,F403
from .report import *  # noqa: F401,F403


def lint(text: str, register: str = "technical", dialect: str | None = None,
         patterns: dict | None = None) -> dict:
    """Library entry point: analyze text and return the result dict.

    Mirrors the --json payload so callers can import this module instead of
    shelling out to the CLI.
    """
    if patterns is None:
        patterns = load_patterns()
    hits, report, words = analyze(text, register, dialect, patterns)
    weights = resolve_weights(patterns)
    floor = score(hits, words, weights)
    return {
        "schema_version": 1,
        "register": register,
        "dialect": dialect,
        "words": words,
        "score": floor,
        "verdict": verdict_band(floor, resolve_bands(patterns)),
        "metrics": report,
        "hits": [dict(h.as_dict(), severity=severity_of(h.category, weights)) for h in hits],
    }


__all__ = [
    'lint',
]
