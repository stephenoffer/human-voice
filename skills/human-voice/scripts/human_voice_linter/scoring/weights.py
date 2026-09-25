"""weights — per-category weights and the severity each implies."""
from __future__ import annotations

from ..config.defaults import CATEGORY_WEIGHTS


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


def severity_of(category: str, weights: dict) -> str:
    w = weights.get(category, 1.0)
    if w >= 2.0:
        return "high"
    if w >= 1.5:
        return "medium"
    return "low"


__all__ = ["resolve_weights", "severity_of"]
