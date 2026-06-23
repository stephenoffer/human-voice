"""config — part of human_voice_linter (split from detect_ai_prose.py)."""
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
from .patterns import *  # noqa: F401,F403
from .defaults import *  # noqa: F401,F403


def apply_threshold_overrides(patterns, overrides):
    if not overrides:
        return patterns
    th = dict(patterns.get("thresholds", {})) if isinstance(patterns.get("thresholds"), dict) else {}
    for ov in overrides:
        if "=" not in ov:
            warn("ignoring malformed --threshold %r (want key=value)" % ov)
            continue
        k, v = ov.split("=", 1)
        try:
            th[k.strip()] = float(v)
        except ValueError:
            warn("ignoring non-numeric --threshold %r" % ov)
    patterns = dict(patterns)
    patterns["thresholds"] = th
    return patterns


CONFIG_NAME = ".humanvoicerc"


def find_project_config(start):
    """Walk up from `start` looking for a .humanvoicerc JSON file."""
    try:
        d = os.path.dirname(os.path.abspath(start)) if start and start != "-" else os.getcwd()
    except OSError:
        return None
    seen = set()
    while d and d not in seen:
        seen.add(d)
        candidate = os.path.join(d, CONFIG_NAME)
        if os.path.isfile(candidate):
            try:
                with open(candidate, encoding="utf-8", errors="replace") as fh:
                    cfg = json.load(fh)
                if isinstance(cfg, dict):
                    return cfg
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                warn("ignoring unreadable %s: %s" % (candidate, exc))
                return None
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def merge_config(patterns, cfg):
    """Merge a .humanvoicerc dict into the loaded patterns (project overrides)."""
    if not isinstance(cfg, dict):
        return patterns
    patterns = dict(patterns)
    if isinstance(cfg.get("thresholds"), dict):
        th = dict(patterns.get("thresholds", {}) if isinstance(patterns.get("thresholds"), dict) else {})
        th.update(cfg["thresholds"])
        patterns["thresholds"] = th
    if isinstance(cfg.get("category_weights"), dict):
        cw = dict(patterns.get("category_weights", {}) if isinstance(patterns.get("category_weights"), dict) else {})
        cw.update(cfg["category_weights"])
        patterns["category_weights"] = cw
    if isinstance(cfg.get("score_bands"), dict):
        patterns["score_bands"] = cfg["score_bands"]
    for listkey in ("protected_terms", "context_exceptions"):
        if isinstance(cfg.get(listkey), list):
            patterns[listkey] = list(patterns.get(listkey) or []) + list(cfg[listkey])
    return patterns


def collect_targets(inputs, recursive):
    """Expand inputs into a flat list of file paths (or '-'), walking dirs."""
    targets = []
    for inp in inputs:
        if inp == "-":
            targets.append(inp)
        elif os.path.isdir(inp):
            for root, _dirs, files in os.walk(inp):
                for fn in sorted(files):
                    if fn.endswith((".md", ".markdown", ".txt")):
                        targets.append(os.path.join(root, fn))
                if not recursive:
                    break
        else:
            targets.append(inp)
    return targets


__all__ = [
    'apply_threshold_overrides',
    'CONFIG_NAME',
    'find_project_config',
    'merge_config',
    'collect_targets',
]
