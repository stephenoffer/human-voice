"""stats — the few numeric summaries several checks share."""
from __future__ import annotations

import math


def per_1k(count, words):
    """`count` per 1,000 words, or 0.0 for an empty document."""
    return (count / words * 1000) if words else 0.0


def cov(values):
    """Coefficient of variation, or None when it is undefined."""
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean <= 0:
        return None
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var) / mean


def longest_run(flags):
    """Length of the longest run of truthy values."""
    streak = best = 0
    for flag in flags:
        streak = streak + 1 if flag else 0
        best = max(best, streak)
    return best


def rounded(value, digits=2):
    return round(value, digits) if value is not None else None


__all__ = ["per_1k", "cov", "longest_run", "rounded"]
