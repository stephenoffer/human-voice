"""floor — the single length-stable "floor" score."""
from __future__ import annotations

from ..config.defaults import CATEGORY_WEIGHTS, DEFAULTS


def score(hits: list, word_count: int, weights: dict | None = None,
          doc_points: float | None = None, category_cap: float | None = None,
          doc_cap_per_category: int | None = None) -> float:
    """Length-stable floor score.

    Two kinds of finding cannot share one denominator. An *instance* tell (a
    filler word, an em-dash) recurs with length, so it belongs in a per-1000-word
    density. A *document* tell (flat burstiness, even paragraphs, an assistant
    heading shape) fires at most once no matter how long the text is, so dividing
    it by word count made the same defect worth 13 points in a 150-word note and
    1 point in a 2000-word report. Document findings (``Hit.line == 0``) now
    contribute fixed points; only instance findings are normalized by length.

    Each category's density contribution is also capped, so one runaway check
    (n-gram repetition on a long, repetitive document could emit hundreds of
    hits) can no longer swamp every other signal. Document findings get the same
    protection through `doc_cap_per_category`: a check that emits one line-0 hit
    per example -- superlative_creep used to emit six -- would otherwise be worth
    six times doc_points for what is really one finding.
    """
    if weights is None:
        weights = CATEGORY_WEIGHTS
    if doc_points is None:
        doc_points = DEFAULTS["scoring"]["doc_hit_points"]
    if category_cap is None:
        category_cap = DEFAULTS["scoring"]["category_cap"]
    if doc_cap_per_category is None:
        doc_cap_per_category = int(DEFAULTS["scoring"]["doc_cap_per_category"])
    per_category: dict = {}
    doc_counts: dict = {}
    doc_weight = 0.0
    for h in hits:
        w = weights.get(h.category, 1.0)
        if getattr(h, "line", None) == 0:
            n = doc_counts.get(h.category, 0)
            if n >= doc_cap_per_category:
                continue
            doc_counts[h.category] = n + 1
            doc_weight += w
        else:
            per_category[h.category] = per_category.get(h.category, 0.0) + w
    # Floor the denominator. Below a few hundred words a per-1000-word rate is an
    # extrapolation rather than a measurement: two em-dashes in a 220-word email
    # scored as "9 per 1000 words" and drove the category straight into its cap,
    # so a normal human note outscored a 2000-word document with ten of them. The
    # floor makes a short text's score proportional to what is actually in it.
    denominator = max(word_count, DEFAULTS["scoring"]["density_floor_words"])
    per_1k = 0.0
    if word_count:
        for weighted in per_category.values():
            per_1k += min(weighted / denominator * 1000.0, category_cap)
    return round(per_1k + doc_weight * doc_points, 1)


def resolve_scoring(patterns: dict) -> tuple:
    """(doc_hit_points, category_cap, doc_cap_per_category) over the defaults."""
    base = DEFAULTS["scoring"]
    cfg = patterns.get("scoring") if isinstance(patterns, dict) else None
    out = []
    for key in ("doc_hit_points", "category_cap", "doc_cap_per_category"):
        val = base[key]
        if isinstance(cfg, dict) and key in cfg:
            try:
                val = float(cfg[key])
            except (TypeError, ValueError):
                val = base[key]
        out.append(val)
    return tuple(out)


__all__ = ["score", "resolve_scoring"]
