"""analyze — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import argparse
import bisect
import functools
import json
import math
import os
import re
import sys
from collections import Counter
from .util import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403
from .defaults import *  # noqa: F401,F403
from .textutil import *  # noqa: F401,F403
from .patterns import *  # noqa: F401,F403
from .checks import *  # noqa: F401,F403
from .score import *  # noqa: F401,F403
from .directives import *  # noqa: F401,F403


def analyze(text: str, register: str, dialect: str | None,
            patterns: dict) -> tuple:
    """Run every check over `text` and return (hits, report, word_count)."""
    text = blank_frontmatter(text)
    code_stripped = strip_code(text)
    metric_prose = prose_for_metrics(code_stripped)
    sents = sentences(metric_prose)
    tokens = [w.lower() for w in WORD_RE.findall(metric_prose)]  # tokenize once
    word_count = len(tokens)
    muted = muted_categories(register, patterns)
    th = patterns.get("thresholds", {})
    if not isinstance(th, dict):
        th = {}
    hits = []
    seen = {}
    report = {}

    # One LineMap per distinct text so each hit's line lookup is O(log n).
    lm_code = LineMap(code_stripped)
    lm_metric = LineMap(metric_prose)
    lm_raw = LineMap(text)

    # Phrases/terms where an otherwise-flagged word is legitimate: fixed phrases
    # (context_exceptions) plus project-specific protected terms.
    protected = build_protected_spans(
        code_stripped,
        list(patterns.get("context_exceptions") or []) + list(patterns.get("protected_terms") or []))

    check_lexical_list(code_stripped, patterns.get("filler"), "filler", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("jargon"), "jargon", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("overused_transitions"), "transitions", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("meta_commentary"), "meta_commentary", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("chatbot_scaffold"), "chatbot_scaffold", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("hedging"), "hedging", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("puffery"), "puffery", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("vague_attribution"), "vague_attribution", hits, seen, lm_code, protected, cite_guard=True)
    check_lexical_list(code_stripped, patterns.get("redundancy"), "redundancy", hits, seen, lm_code, protected, skip_quoted=True)
    check_lexical_list(code_stripped, patterns.get("self_identifying"), "self_identifying", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("narrator_distance"), "narrator_distance", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("vague_declarative"), "vague_declarative", hits, seen, lm_code, protected)
    check_antithesis(code_stripped, patterns.get("antithesis_patterns"), hits, lm_code)
    check_pattern_list(code_stripped, patterns.get("false_agency_patterns"), "false_agency",
                       "name the human actor (or use 'you'); don't invent one", hits, lm_code, protected)
    check_pattern_list(code_stripped, patterns.get("negative_listing_patterns"), "negative_listing",
                       "state the final answer; cut the list of what it isn't", hits, lm_code, protected)
    check_pattern_list(code_stripped, patterns.get("dramatic_fragmentation_patterns"), "dramatic_fragmentation",
                       "use complete sentences; trust the content over the staccato", hits, lm_code, protected)

    check_em_dash(metric_prose, word_count, safe_float(th, "em_dash_per_1k_words", threshold_default("em_dash_per_1k_words")), hits, report, lm_metric)
    check_bold_bullets(text, safe_float(th, "bold_bullet_ratio", threshold_default("bold_bullet_ratio")), hits, report, lm_raw)
    check_rule_of_three(metric_prose, hits, lm_metric)
    check_uniform_openers(sents, safe_float(th, "uniform_opener_ratio", threshold_default("uniform_opener_ratio")), hits, report)
    check_wh_openers(sents, safe_float(th, "wh_opener_ratio", threshold_default("wh_opener_ratio")),
                     int(safe_float(th, "wh_opener_run", threshold_default("wh_opener_run"))), hits, report)
    check_formatting(text, safe_float(th, "section_rule_max", threshold_default("section_rule_max")), hits, report, lm_raw)
    check_burstiness(sents, safe_float(th, "burstiness_cov_floor", threshold_default("burstiness_cov_floor")), hits, report)
    check_lexical_diversity(metric_prose, safe_float(th, "ttr_floor", threshold_default("ttr_floor")), hits, report)
    check_ngram_repetition(metric_prose, safe_int_list(th, "ngram_sizes", threshold_default("ngram_sizes")),
                           int(safe_float(th, "ngram_min_count", threshold_default("ngram_min_count"))), hits)
    check_heading_case(text, hits, lm_raw)

    # Density / structural checks (Phase 2). Conservative thresholds keep clean
    # human prose clean; several are muted by register (see register_mutes).
    check_colon_summary(metric_prose, hits, report, lm_metric)
    check_passive_voice(metric_prose, word_count, safe_float(th, "passive_per_1k", threshold_default("passive_per_1k")), hits, report)
    check_adverbs(tokens, word_count, safe_float(th, "adverb_per_1k", threshold_default("adverb_per_1k")), hits, report)
    check_nominalizations(metric_prose, word_count, safe_float(th, "nominalization_per_1k", threshold_default("nominalization_per_1k")), hits, report)
    check_rhetorical(sents, word_count, safe_float(th, "rhetorical_per_1k", threshold_default("rhetorical_per_1k")), hits, report)
    check_paragraph_uniformity(code_stripped, safe_float(th, "paragraph_cov_floor", threshold_default("paragraph_cov_floor")), hits, report)
    check_list_uniformity(code_stripped, safe_float(th, "list_item_cov_floor", threshold_default("list_item_cov_floor")), hits, report)
    check_circular_conclusion(code_stripped, hits, report)
    check_parallel_structure(sents, hits, report)
    adj_prose = prose_for_adjacency(text)
    lm_adj = LineMap(adj_prose)
    check_dash_style(adj_prose, hits, report, lm_adj)
    check_doubled_words(adj_prose, hits, report, lm_adj)
    check_mechanics(adj_prose, hits, report, lm_adj)
    report_punctuation_profile(metric_prose, word_count, report)

    if dialect:
        dmap = patterns.get("dialect", {})
        dmap = dmap.get(dialect, {}) if isinstance(dmap, dict) else {}
        check_dialect(code_stripped, dmap, hits, lm_code)

    hits = [h for h in hits if h.category not in muted]
    # Inline ignore directives (HTML comments) suppress specific lines/categories.
    ignored = parse_directives(text)
    if ignored:
        hits = [h for h in hits if not directive_suppresses(h, ignored)]
    report["word_count"] = word_count
    report["sentence_count"] = len(sents)
    return hits, report, word_count


# Default verdict bands (upper-exclusive): score < 5 reads clean, < 15 worth a
# look, otherwise a strong floor signal. The top band is open-ended (large
# threshold). Overridable via patterns["score_bands"].


__all__ = [
    'analyze',
]
