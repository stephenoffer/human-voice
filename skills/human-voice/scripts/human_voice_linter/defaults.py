"""defaults — the single source of truth for tunable knobs.

`DEFAULTS` holds the canonical thresholds, category weights, and verdict bands.
The shipped `ai_prose_patterns.json` mirrors these values and overrides them at
runtime when present; `DEFAULTS` is the fallback used per-key when the JSON omits
or malforms a value (see resolve_weights / resolve_bands / safe_float). Keeping
one canonical table here removes the old code-vs-JSON drift. A drift guard in the
test suite asserts the JSON stays consistent with these values.
"""
from __future__ import annotations

REGISTERS = ["technical", "business", "marketing", "academic", "casual", "creative",
             "email", "release_notes", "ux_microcopy", "tutorial"]

DEFAULTS: dict = {
    # Numeric knobs read by the checks. Densities are per-1000-words; *_floor are
    # minimum acceptable values (firing below the floor); *_ratio are fractions.
    "thresholds": {
        "em_dash_per_1k_words": 1.5,
        "burstiness_cov_floor": 0.4,
        "ttr_floor": 0.38,
        "ngram_min_count": 4,
        "ngram_sizes": [2, 3],
        "bold_bullet_ratio": 0.5,
        "uniform_opener_ratio": 0.3,
        "section_rule_max": 2,
        "passive_per_1k": 45.0,
        "adverb_per_1k": 55.0,
        "nominalization_per_1k": 60.0,
        "rhetorical_per_1k": 18.0,
        "paragraph_cov_floor": 0.3,
        "list_item_cov_floor": 0.22,
        "wh_opener_ratio": 0.3,
        "wh_opener_run": 3,
        "superlative_per_1k": 12.0,
        # Modern instruction-tuned syntax. Every one of these constructions is
        # ordinary English on its own, so the thresholds sit well above the rate a
        # human writer hits by accident; the tell is the stacking, not the token.
        "cleft_per_1k": 6.0,
        "participial_tail_per_1k": 6.0,
        "clause_splice_per_1k": 8.0,
        # Over-correction guard. Above this semicolon rate WITH no dash anywhere,
        # the document has had one mark substituted for another wholesale. The
        # human maximum on this repo's corpus is 5.5.
        "semicolon_per_1k_max": 7.0,
        # Copula ("to be") as the main verb. The human maximum measured here is
        # 67.8 per 1,000 words, so the floor sits above every observed human
        # sample with margin and only catches genuinely glossary-shaped prose.
        "copula_per_1k": 78.0,
        # Assistant-shape thresholds. Detectors keyed to post-training artifacts
        # respond to markdown scaffolding density more than to word choice
        # (base models, which lack it, read as human >96% of the time), so these
        # measure how much the document looks like a chat response rather than a
        # written one. Ceilings, not floors: firing above the value.
        "headings_per_1k_words": 14.0,
        "bullet_line_ratio": 0.35,
        "bold_spans_per_1k_words": 12.0,
        # Sentence-length distribution shape. CoV alone is fooled by one long
        # outlier; these measure whether the text has real short punches and real
        # long sentences, or collapses into the 12-24 word band LLMs prefer.
        "short_sentence_ratio_floor": 0.12,
        "mid_band_ratio_max": 0.72,
        "mid_band_low": 12,
        "mid_band_high": 26,
        "short_sentence_max_words": 8,
    },
    # How the floor score is assembled. See score.score for why document-level
    # findings cannot share a per-1000-word denominator with instance findings.
    "scoring": {
        "doc_hit_points": 2.0,
        "category_cap": 15.0,
        # Runaway guard for document-level findings, mirroring category_cap for
        # instance findings: at most this many line-0 hits per category count
        # toward the score. Today no check emits more than four, so this changes
        # nothing; it stops a future check from turning one finding into ten.
        "doc_cap_per_category": 4,
        # Minimum denominator for per-1000-word instance density. See score.score:
        # a 150-word note with two hits is not "13 per 1000 words" in any sense a
        # reader would recognize, and treating it that way made short documents
        # score higher than long ones carrying the same defect more often.
        "density_floor_words": 300,
    },
    # Category weights feed the single "floor" score. Document-level findings
    # contribute weight * doc_hit_points; instance findings a per-1000-word
    # density capped at category_cap. See score.score.
    # Weights are tiered by what readers actually *cite* as an AI tell, not by
    # what a keyword scanner *matches* (the ~90k-post Reddit study found these
    # diverge: generic words like "however/thus/nuanced/comprehensive" match
    # often but are cited ~0% of the time, while structural tells dominate the
    # cited ranking). See references/cited-vs-matched.md.
    #   Tier A (>= 2.0): high-cited structural/artifact tells.
    #   Tier B (1.5):    moderate.
    #   Tier C (<= 0.5): high-match/low-cited generic diction (kept as a soft
    #                    signal, never allowed to dominate the score).
    "category_weights": {
        "filler": 1.0,
        "soft_filler": 0.5,
        "jargon": 1.0,
        "transitions": 0.5,
        "meta_commentary": 1.5,
        "chatbot_scaffold": 2.0,
        "sycophancy": 2.0,
        "hedging": 1.0,
        "puffery": 1.5,
        "vague_attribution": 1.5,
        "redundancy": 1.0,
        "cowardly_passive": 1.0,
        "self_identifying": 4.0,
        "antithesis": 2.0,
        "aidiolect": 2.0,
        "cliche_metaphor": 1.5,
        "internet_tells": 1.0,
        "significance_inflation": 1.5,
        "em_dash": 2.0,
        "bold_bullets": 2.0,
        "rule_of_three": 1.0,
        "uniform_openers": 1.0,
        "formatting": 1.0,
        "ngram_repetition": 1.0,
        "burstiness": 2.0,
        "lexical_diversity": 1.5,
        "dialect": 0.5,
        "heading_case": 0.5,
        "colon_summary": 1.0,
        "passive_voice": 0.5,
        "adverbs": 0.5,
        "rhetorical": 0.5,
        "nominalization": 0.5,
        "paragraph_uniformity": 1.5,
        "list_uniformity": 1.0,
        "circular_conclusion": 1.5,
        "parallel_structure": 1.0,
        "svo_monotony": 1.0,
        "five_paragraph_shape": 2.0,
        "hypophora": 1.0,
        "superlative_creep": 1.0,
        "name_selection": 0.5,
        "over_correction": 1.0,
        "dash_style": 0.5,
        "doubled_word": 1.0,
        "mechanics": 0.5,
        "false_agency": 1.5,
        "narrator_distance": 1.0,
        "wh_opener": 0.5,
        "vague_declarative": 1.5,
        "negative_listing": 1.0,
        "dramatic_fragmentation": 0.5,
        # Tier A. The strongest evidenced detector signal is the shape of an
        # assistant response, not its vocabulary; see references/what-detectors-see.md.
        "assistant_shape": 2.5,
        "sentence_shape": 2.0,
        # Modern syntactic signature. Tier B: each is real English used well by
        # humans, so the weights stay moderate and the checks stay count-gated.
        "cleft": 1.5,
        "participial_tail": 2.0,
        "copula_density": 1.0,
        "clause_splice": 0.5,
        "paragraph_openers": 1.5,
        "bullet_openers": 1.0,
        "noun_chain": 0.5,
    },
    # Verdict bands (upper-exclusive): score < 5 reads clean, < 15 worth a look,
    # otherwise a strong floor signal. The top band is open-ended.
    "score_bands": {
        "clean": 5.0,
        "watch": 15.0,
        "strong-tell": 1e6,
    },
}

# Convenience aliases derived from DEFAULTS (kept as module-level names for
# backward compatibility — the eval harness and tests read these directly).
DEFAULT_THRESHOLDS = DEFAULTS["thresholds"]
CATEGORY_WEIGHTS = dict(DEFAULTS["category_weights"])

# Every category the linter can emit. Used to validate register-mute config.
KNOWN_CATEGORIES = frozenset(CATEGORY_WEIGHTS)

# (label, upper) bands sorted ascending by threshold.
DEFAULT_BANDS = tuple(sorted(DEFAULTS["score_bands"].items(), key=lambda kv: kv[1]))


def threshold_default(key):
    """Canonical fallback for a threshold key (used when the JSON omits it)."""
    return DEFAULTS["thresholds"][key]


__all__ = [
    "REGISTERS",
    "DEFAULTS",
    "DEFAULT_THRESHOLDS",
    "CATEGORY_WEIGHTS",
    "KNOWN_CATEGORIES",
    "DEFAULT_BANDS",
    "threshold_default",
]
