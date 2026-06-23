"""score — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

from collections import Counter

from .defaults import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403


def muted_categories(register: str, patterns: dict) -> set:
    mutes = patterns.get("register_mutes", {})
    mutes = mutes.get(register, []) if isinstance(mutes, dict) else []
    muted_map = patterns.get("muted_checks", {})
    if not isinstance(muted_map, dict):
        muted_map = {}
    cats = set()
    for token in mutes if isinstance(mutes, list) else []:
        for c in muted_map.get(token, []) if isinstance(muted_map.get(token), list) else []:
            cats.add(c)
    return cats


def resolve_weights(patterns: dict) -> dict:
    """Category weights from the patterns file merged over the built-in defaults."""
    weights = dict(CATEGORY_WEIGHTS)
    cfg = patterns.get("category_weights") if isinstance(patterns, dict) else None
    if isinstance(cfg, dict):
        for cat, w in cfg.items():
            if cat in CATEGORY_WEIGHTS:
                try:
                    weights[cat] = float(w)
                except (TypeError, ValueError):
                    continue
    return weights


def score(hits: list, word_count: int, weights: dict | None = None) -> float:
    if weights is None:
        weights = CATEGORY_WEIGHTS
    weighted = sum(weights.get(h.category, 1.0) for h in hits)
    per_1k = (weighted / word_count * 1000) if word_count else 0.0
    return round(per_1k, 1)


def resolve_bands(patterns: dict) -> tuple:
    """(label, upper) bands sorted ascending; falls back to DEFAULT_BANDS."""
    cfg = patterns.get("score_bands") if isinstance(patterns, dict) else None
    if isinstance(cfg, dict) and cfg:
        bands = []
        for label, upper in cfg.items():
            try:
                bands.append((str(label), float(upper)))
            except (TypeError, ValueError):
                continue
        if bands:
            return tuple(sorted(bands, key=lambda b: b[1]))
    return DEFAULT_BANDS


def verdict_band(floor_score: float, bands: tuple) -> str:
    """Map a floor score to its band label (the highest band is open-ended)."""
    for label, upper in bands:
        if floor_score < upper:
            return label
    return bands[-1][0] if bands else "n/a"


def severity_of(category: str, weights: dict) -> str:
    w = weights.get(category, 1.0)
    if w >= 2.0:
        return "high"
    if w >= 1.5:
        return "medium"
    return "low"


def line_hotspots(hits: list, top: int = 5) -> list:
    counts = Counter(h.line for h in hits if h.line)
    return counts.most_common(top)


__all__ = [
    'muted_categories',
    'resolve_weights',
    'score',
    'resolve_bands',
    'verdict_band',
    'severity_of',
    'line_hotspots',
]
