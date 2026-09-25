"""bands — mapping a floor score to its verdict label."""
from __future__ import annotations

from ..config.defaults import DEFAULT_BANDS


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


__all__ = ["resolve_bands", "verdict_band"]
