"""project — .humanvoicerc discovery and the overrides layered on the pattern file."""
from __future__ import annotations

import json
import os

from ..core.log import warn

CONFIG_NAME = ".humanvoicerc"


def apply_threshold_overrides(patterns, overrides):
    """Apply `--threshold key=value` overrides on top of the loaded patterns."""
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


__all__ = [
    "CONFIG_NAME",
    "apply_threshold_overrides",
    "find_project_config",
    "merge_config",
]
