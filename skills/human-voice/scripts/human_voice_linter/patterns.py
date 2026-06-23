"""patterns — part of human_voice_linter (split from detect_ai_prose.py)."""
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
from .util import *  # noqa: F401,F403


PATTERNS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ai_prose_patterns.json")


def load_patterns(path: str = PATTERNS_FILE) -> dict:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        sys.stderr.write(
            "error: pattern file not found: %s\n"
            "The linter cannot run without it. Fall back to pure judgment "
            "using references/ai-tells.md.\n" % path)
        sys.exit(2)
    except IsADirectoryError:
        sys.stderr.write("error: pattern path is a directory, not a file: %s\n" % path)
        sys.exit(2)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        sys.stderr.write("error: could not parse pattern file %s: %s\n" % (path, exc))
        sys.exit(2)
    if not isinstance(data, dict):
        sys.stderr.write("error: pattern file %s must contain a JSON object\n" % path)
        sys.exit(2)
    return data


def as_phrase_list(value) -> list:
    """Coerce a pattern value into a list of (phrase, suggestion) pairs."""
    pairs = []
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = ((v, None) for v in value)
    elif isinstance(value, str):
        items = ((value, None),)
    else:
        return pairs
    for phrase, suggestion in items:
        if not isinstance(phrase, str):
            continue
        phrase = phrase.strip()
        if not phrase:
            continue
        # Forward-compatible rich form: value may be {"suggestion": "..."}.
        if isinstance(suggestion, dict):
            suggestion = suggestion.get("suggestion")
        sug = suggestion if isinstance(suggestion, str) and suggestion.strip() else None
        pairs.append((phrase, sug))
    return pairs


def safe_float(d: dict, key: str, default: float) -> float:
    try:
        return float(d.get(key, default))
    except (TypeError, ValueError):
        return default


def safe_int_list(d: dict, key: str, default: list) -> list:
    val = d.get(key, default)
    if not isinstance(val, list):
        return list(default)
    out = []
    for n in val:
        try:
            out.append(int(n))
        except (TypeError, ValueError):
            continue
    return out or list(default)


__all__ = [
    'PATTERNS_FILE',
    'load_patterns',
    'as_phrase_list',
    'safe_float',
    'safe_int_list',
]
