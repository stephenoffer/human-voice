"""text — turning a markdown source into the views the checks measure.

    markdown  normalization, the markdown line grammar, code and markup stripping
    prose     metric prose, adjacency prose, paragraphs, list items
    tokens    words, stopwords, sentence segmentation
    linemap   offset -> source line lookups
    phrases   compiled phrase-list matchers and protected spans
    dashes    dash patterns shared by the checks and the autofixer
    stats     rates, coefficient of variation, runs
"""
from __future__ import annotations

from .dashes import EM_DASH_RE, PAIRED_DASH_RE, is_numeric_en_dash, pause_dashes
from .linemap import LineMap, MappedLineMap, line_of
from .markdown import (
    BARE_URL_RE,
    BLOCKQUOTE_RE,
    CODE_FENCE_RE,
    CONTROL_CHARS_RE,
    EMOJI_RE,
    EMPHASIS_RE,
    FOOTNOTE_DEF_RE,
    FOOTNOTE_REF_RE,
    HEADING_LINE_RE,
    HTML_TAG_RE,
    INLINE_CODE_RE,
    LINK_RE,
    LIST_MARKER_RE,
    SECTION_RULE_MULTILINE_RE,
    SECTION_RULE_RE,
    SETEXT_RE,
    TABLE_ROW_RE,
    TABLE_SEP_RE,
    UNDERSCORE_EMPHASIS_RE,
    blank_frontmatter,
    is_structural_line,
    normalize_text,
    strip_code,
    strip_inline_markup,
)
from .phrases import build_protected_spans, compile_phrase_matchers, norm_phrase, overlaps, phrase_regex
from .prose import list_items, prose_for_adjacency, prose_for_metrics, prose_paragraphs
from .stats import cov, longest_run, per_1k, rounded
from .tokens import (
    ABBREV_RE,
    ABBREVIATIONS,
    SENTENCE_SPLIT_RE,
    STOPWORDS,
    WORD_RE,
    first_word,
    first_words,
    sentences,
    word_lengths,
)

__all__ = [
    "EM_DASH_RE", "PAIRED_DASH_RE", "is_numeric_en_dash", "pause_dashes",
    "LineMap", "MappedLineMap", "line_of",
    "BARE_URL_RE", "BLOCKQUOTE_RE", "CODE_FENCE_RE", "CONTROL_CHARS_RE", "EMOJI_RE",
    "EMPHASIS_RE", "FOOTNOTE_DEF_RE", "FOOTNOTE_REF_RE", "HEADING_LINE_RE",
    "HTML_TAG_RE", "INLINE_CODE_RE", "LINK_RE", "LIST_MARKER_RE",
    "SECTION_RULE_MULTILINE_RE", "SECTION_RULE_RE", "SETEXT_RE", "TABLE_ROW_RE",
    "TABLE_SEP_RE", "UNDERSCORE_EMPHASIS_RE",
    "blank_frontmatter", "is_structural_line", "normalize_text", "strip_code",
    "strip_inline_markup",
    "build_protected_spans", "compile_phrase_matchers", "norm_phrase", "overlaps",
    "phrase_regex",
    "list_items", "prose_for_adjacency", "prose_for_metrics", "prose_paragraphs",
    "cov", "longest_run", "per_1k", "rounded",
    "ABBREV_RE", "ABBREVIATIONS", "SENTENCE_SPLIT_RE", "STOPWORDS", "WORD_RE",
    "first_word", "first_words", "sentences", "word_lengths",
]
