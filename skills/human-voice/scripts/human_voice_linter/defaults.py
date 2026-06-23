"""defaults — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations



REGISTERS = ["technical", "business", "marketing", "academic", "casual", "creative",
             "email", "release_notes", "ux_microcopy", "tutorial"]

# Hard cap so a pathological input can't hang the process. ~5M chars is far
# larger than any real document and still completes in well under a second.
CATEGORY_WEIGHTS = {
    "filler": 1.0,
    "jargon": 1.0,
    "transitions": 1.0,
    "meta_commentary": 1.5,
    "chatbot_scaffold": 2.0,
    "hedging": 1.0,
    "puffery": 1.5,
    "vague_attribution": 1.5,
    "redundancy": 1.0,
    "self_identifying": 4.0,
    "antithesis": 1.5,
    "em_dash": 2.0,
    "bold_bullets": 1.5,
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
    "dash_style": 0.5,
    "doubled_word": 1.0,
    "mechanics": 0.5,
    "false_agency": 1.5,
    "narrator_distance": 1.0,
    "wh_opener": 0.5,
    "vague_declarative": 1.5,
    "negative_listing": 1.0,
    "dramatic_fragmentation": 0.5,
}

# Every category the linter can emit. Used to validate register-mute config.
KNOWN_CATEGORIES = frozenset(CATEGORY_WEIGHTS)

# Limited to the unambiguous emoji blocks. Deliberately excludes the arrow
# (U+2190–21FF), miscellaneous-symbol (U+2600–26FF: ★ ☆ ☑ ⚙), and U+2B00–2BFF
# blocks: those hold typographic/math/rating glyphs that appear legitimately in
# technical prose and would otherwise be mis-flagged as decorative emoji.
DEFAULT_BANDS = (("clean", 5.0), ("watch", 15.0), ("strong-tell", 1e6))


__all__ = [
    'REGISTERS',
    'CATEGORY_WEIGHTS',
    'KNOWN_CATEGORIES',
    'DEFAULT_BANDS',
]
