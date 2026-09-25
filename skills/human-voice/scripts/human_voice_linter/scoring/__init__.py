"""scoring — turning hits into one floor score and a verdict.

    floor    score() and the scoring knobs
    weights  per-category weights and severity
    bands    verdict bands
"""
from __future__ import annotations

from .bands import resolve_bands, verdict_band
from .floor import resolve_scoring, score
from .weights import resolve_weights, severity_of

__all__ = [
    "resolve_bands",
    "verdict_band",
    "resolve_scoring",
    "score",
    "resolve_weights",
    "severity_of",
]
