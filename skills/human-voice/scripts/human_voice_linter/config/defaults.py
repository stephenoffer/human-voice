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
        # Trigrams only. A repeated two-word phrase is almost always a term of art
        # ("event loop", "type variables"), and holding a term steady is principle 6.
        # Bigrams were 49% of all false-positive points on the stdlib docstring
        # sweep and moved no eval metric at all when removed.
        "ngram_sizes": [3],
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
        # Copula AVOIDANCE, the mirror image of copula_per_1k. Where 2023-era
        # prose over-used "is", current models reach for an elaborate substitute
        # ("serves as", "stands as", "represents", "boasts") to dodge it; the
        # Wikipedia AI-Cleanup corpus measured a >10% drop in "is"/"are" after
        # 2022 alongside a rise in these. Measured on this repo's corpus: 0.8
        # per 1k in the human class (max 7.0), 4.0 in the caricature class, so
        # the bar sits above every human sample measured here.
        "copula_avoidance_per_1k": 8.0,
        # Content architecture: what the document spends its words on. Calibrated
        # on 311 long human READMEs and manuals (see eval/structure_eval.py): at
        # these values restatement and depth_drift each fired on one of them and
        # section_balance on none.
        #   restatement: a sentence or list item whose stemmed content words
        #   overlap an earlier one in another section at this Jaccard or more.
        #   Needs min_pairs pairs AND per_1k pairs per 1,000 words, so a long
        #   manual that repeats one note is not a short design doc that says
        #   four things twice.
        "restatement_jaccard": 0.5,
        "restatement_min_pairs": 2,
        "restatement_per_1k": 2.5,
        #   section_balance: hollow stubs under this many words; section-length
        #   CoV below the even floor across five or more real sections; framing
        #   sections (overview, background, summary) above this share of words.
        "section_stub_words": 30,
        "section_even_cov_floor": 0.15,
        "framing_share_max": 0.35,
        #   depth_drift: checkable technical markers per 100 words. A section at
        #   or under `hollow` beside one at or over `dense`; beginner explanations
        #   in a document at or over `expert`.
        "depth_dense_per_100": 5.0,
        "depth_hollow_per_100": 0.5,
        "depth_expert_per_100": 4.0,
    },
    # Per-register threshold multipliers. A register that legitimately runs hot
    # on one construction used to be handled by MUTING the check outright, which
    # threw away the signal along with the false positives: creative prose with
    # `cleft_ok` muted meant a fiction sample could stack ten clefts per 1,000
    # words and score zero, and two of the three files the floor missed on the
    # modern-AI class were exactly that. A multiplier says "fiction tolerates
    # twice the rate" instead of "fiction is exempt", which is what the corpus
    # actually shows: the human creative samples here carry zero clefts.
    "register_thresholds": {
        "creative": {"cleft_per_1k": 1.3, "clause_splice_per_1k": 1.6},
        "academic": {"passive_per_1k": 1.5, "nominalization_per_1k": 1.4},
        "casual": {"clause_splice_per_1k": 1.4},
        # A tutorial explains the basics to a reader it also hands commands to;
        # that is the genre, so the expert bar for explainer whiplash doubles.
        "tutorial": {"depth_expert_per_100": 2.0},
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
        # Tier A, and the highest-precision check in the file. These are strings
        # no writer types: citation and tool-call residue left in pasted model
        # output (oaicite, turn0search0, [cite: 1], grok_render_citation_card_json)
        # and unfilled template placeholders ("[Your Name]"). One hit is proof,
        # not a whisper, so the weight matches self_identifying.
        "llm_artifact": 4.0,
        # The copula-avoidance mirror of copula_density (see thresholds).
        "copula_avoidance": 1.0,
        # Markdown scaffolding a person does not produce by hand: skipped heading
        # levels, several H1s in one document, a heading whose entire body is
        # another heading, a heading followed straight into a bullet list with no
        # sentence between them.
        "heading_structure": 1.0,
        # Straight and curly quotes mixed in one document: the seam where model
        # output (curly) was pasted into hand-written text (straight).
        "quote_style": 0.5,
        # Content architecture (architecture.py). Tier B: restatement and section
        # balance are what an editor marks first on an agent-written report, and
        # depth_drift is the looser proxy, so it weighs least.
        "restatement": 1.5,
        "section_balance": 1.5,
        "depth_drift": 1.0,
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
