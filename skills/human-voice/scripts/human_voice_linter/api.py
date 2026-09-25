"""api — the library entry point."""
from __future__ import annotations

from .config.patterns import load_patterns
from .engine import analyze
from .reporting.payload import build_payload
from .scoring.bands import resolve_bands
from .scoring.floor import score
from .scoring.weights import resolve_weights


def lint(text: str, register: str = "technical", dialect: str | None = None,
         patterns: dict | None = None) -> dict:
    """Analyze text and return the result dict.

    Mirrors the --json payload so callers can import this module instead of
    shelling out to the CLI.
    """
    if patterns is None:
        patterns = load_patterns()
    hits, report, words = analyze(text, register, dialect, patterns)
    weights = resolve_weights(patterns)
    floor = score(hits, words, weights)
    return build_payload(hits, report, words, floor, register=register, dialect=dialect,
                         weights=weights, bands=resolve_bands(patterns))


__all__ = ["lint"]
