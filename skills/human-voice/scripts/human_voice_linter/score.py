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
    'resolve_scoring',
    'muted_categories',
    'resolve_weights',
    'score',
    'resolve_bands',
    'verdict_band',
    'severity_of',
    'line_hotspots',
]
