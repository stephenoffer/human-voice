"""analyze — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

from .architecture import run_architecture_checks
from .checks import *  # noqa: F401,F403
from .defaults import *  # noqa: F401,F403
from .directives import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403
from .patterns import *  # noqa: F401,F403
from .score import *  # noqa: F401,F403
from .stylometry import report_stylometry
from .textutil import *  # noqa: F401,F403
from .util import *  # noqa: F401,F403


def analyze(text: str, register: str, dialect: str | None,
            patterns: dict) -> tuple:
    """Run every check over `text` and return (hits, report, word_count)."""
    # Normalize here too, not only in read_input: api.lint() and the eval harness
    # hand text straight to analyze, and CRLF endings alone were enough to make the
    # same file score differently through the library than through the CLI.
    text = blank_frontmatter(normalize_text(text))
    code_stripped = strip_code(text)
    metric_prose, metric_src_lines = prose_for_metrics(code_stripped,
                                                      with_line_map=True)
    sents = sentences(metric_prose)
    tokens = [w.lower() for w in WORD_RE.findall(metric_prose)]  # tokenize once
    word_count = len(tokens)
    muted = muted_categories(register, patterns)
    th = patterns.get("thresholds", {})
    if not isinstance(th, dict):
        th = {}

    # Per-register threshold multipliers. See DEFAULTS["register_thresholds"]:
    # a register that legitimately runs hot on one construction gets a wider
    # bar rather than the check switched off, so the signal above that bar is
    # still counted. Only *_per_1k-style knobs are scaled; a ratio floor is left
    # alone because doubling a floor tightens it rather than loosening it.
    rt = patterns.get("register_thresholds")
    if not isinstance(rt, dict):
        rt = DEFAULTS.get("register_thresholds", {})
    reg_mult = rt.get(register) if isinstance(rt.get(register), dict) else {}

    def thr(key):  # JSON value if present, else the canonical default
        base = safe_float(th, key, threshold_default(key))
        mult = reg_mult.get(key)
        if isinstance(mult, (int, float)) and not isinstance(mult, bool) and mult > 0:
            return base * float(mult)
        return base
    hits: list = []
    seen: dict = {}
    report: dict = {}

    # One LineMap per distinct text so each hit's line lookup is O(log n).
    lm_code = LineMap(code_stripped)
    # Report SOURCE lines, not lines of the reduced metric text.
    lm_metric = MappedLineMap(metric_prose, metric_src_lines)

    # Phrases/terms where an otherwise-flagged word is legitimate: fixed phrases
    # (context_exceptions) plus project-specific protected terms.
    protected = build_protected_spans(
        code_stripped,
        list(patterns.get("context_exceptions") or []) + list(patterns.get("protected_terms") or []))

    check_lexical_list(code_stripped, patterns.get("filler"), "filler", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("soft_filler"), "soft_filler", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("jargon"), "jargon", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("overused_transitions"), "transitions", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("meta_commentary"), "meta_commentary", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("chatbot_scaffold"), "chatbot_scaffold", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("sycophancy"), "sycophancy", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("aidiolect"), "aidiolect", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("cliche_metaphor"), "cliche_metaphor", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("internet_tells"), "internet_tells", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("significance_inflation"), "significance_inflation", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("hedging"), "hedging", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("puffery"), "puffery", hits, seen, lm_code, protected)
    check_lexical_list(code_stripped, patterns.get("vague_attribution"), "vague_attribution", hits, seen, lm_code, protected, cite_guard=True)
    check_lexical_list(code_stripped, patterns.get("redundancy"), "redundancy", hits, seen, lm_code, protected, skip_quoted=True)
    check_lexical_list(code_stripped, patterns.get("cowardly_passive"), "cowardly_passive", hits, seen, lm_code, protected)
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

    check_em_dash(metric_prose, word_count, thr("em_dash_per_1k_words"), hits, report, lm_metric)
    # Markdown-shape checks run on the CODE-STRIPPED text, not the raw source. A
    # `# comment` in a fenced bash block is not a heading and `- **Flag**: ...` in a
    # quoted markdown sample is not a bold bullet; counting them flagged READMEs and
    # style guides for showing the anti-pattern they warn against. strip_code keeps
    # line geometry, so reported line numbers still line up with the file.
    check_bold_bullets(code_stripped, thr("bold_bullet_ratio"), hits, report, lm_code)
    check_rule_of_three(metric_prose, hits, lm_metric)
    check_uniform_openers(sents, thr("uniform_opener_ratio"), hits, report)
    check_wh_openers(sents, thr("wh_opener_ratio"), int(thr("wh_opener_run")), hits, report)
    check_formatting(code_stripped, thr("section_rule_max"), hits, report, lm_code)
    check_burstiness(sents, thr("burstiness_cov_floor"), hits, report)
    check_lexical_diversity(metric_prose, thr("ttr_floor"), hits, report)
    check_ngram_repetition(metric_prose, safe_int_list(th, "ngram_sizes", threshold_default("ngram_sizes")),
                           int(thr("ngram_min_count")), hits, lm_metric)
    check_heading_case(code_stripped, hits, lm_code)
    check_heading_structure(code_stripped, hits, report, lm_code)
    # Precision checks: residue rather than style. Run on the metric prose so a
    # document that *documents* these strings in backticks (this repo's own
    # references do) is not flagged for naming them.
    check_llm_artifact(code_stripped, hits, lm_code)
    check_quote_style(metric_prose, hits, report, lm_metric)

    # Density / structural checks. Conservative thresholds keep clean human prose
    # clean; several are muted by register (see register_mutes).
    check_colon_summary(metric_prose, hits, report, lm_metric)
    check_passive_voice(metric_prose, word_count, thr("passive_per_1k"), hits, report)
    check_adverbs(tokens, word_count, thr("adverb_per_1k"), hits, report)
    check_nominalizations(metric_prose, word_count, thr("nominalization_per_1k"), hits, report)
    check_rhetorical(sents, word_count, thr("rhetorical_per_1k"), hits, report)
    check_paragraph_uniformity(code_stripped, thr("paragraph_cov_floor"), hits, report)
    check_list_uniformity(code_stripped, thr("list_item_cov_floor"), hits, report)
    check_circular_conclusion(code_stripped, hits, report)
    check_parallel_structure(sents, hits, report)
    check_five_paragraph_shape(code_stripped, hits, report)
    check_hypophora(sents, hits, report)
    check_superlative_creep(metric_prose, word_count, thr("superlative_per_1k"), hits, report)
    check_svo_monotony(sents, hits, report)
    check_name_selection(code_stripped, hits, report)
    # Modern instruction-tuned signature: syntactic, not lexical. All count-gated.
    check_cleft(metric_prose, word_count, thr("cleft_per_1k"), hits, report, lm_metric)
    check_participial_tail(metric_prose, word_count, thr("participial_tail_per_1k"),
                           hits, report, lm_metric)
    check_copula_density(sents, word_count, thr("copula_per_1k"), hits, report)
    check_comma_splice_chain(metric_prose, word_count, thr("clause_splice_per_1k"),
                             hits, report, lm_metric)
    check_copula_avoidance(metric_prose, word_count, thr("copula_avoidance_per_1k"),
                           hits, report, lm_metric)
    check_paragraph_openers(code_stripped, hits, report)
    check_bullet_openers(code_stripped, hits, report)
    check_noun_chains(metric_prose, hits, report, lm_metric)
    check_over_correction(metric_prose, hits, report)
    check_punctuation_substitution(metric_prose, word_count,
                                   thr("semicolon_per_1k_max"), hits, report)
    # Detector-aligned shape checks: the markdown/assistant signature and the
    # sentence-length distribution. Both are document-level.
    check_assistant_shape(code_stripped, word_count, thr("headings_per_1k_words"),
                          thr("bullet_line_ratio"), thr("bold_spans_per_1k_words"),
                          hits, report, raw_text=text)
    check_sentence_shape(sents, int(thr("short_sentence_max_words")),
                         thr("short_sentence_ratio_floor"), int(thr("mid_band_low")),
                         int(thr("mid_band_high")), thr("mid_band_ratio_max"),
                         hits, report)
    # Content architecture: restated points, section balance, and technical depth
    # held level across sections. Reads the section tree, so it needs the source
    # text as well as the code-stripped copy (fenced code counts as depth).
    run_architecture_checks(text, code_stripped, word_count, thr, hits, report)
    adj_prose = prose_for_adjacency(text)
    lm_adj = LineMap(adj_prose)
    check_dash_style(adj_prose, hits, report, lm_adj)
    check_doubled_words(adj_prose, hits, report, lm_adj)
    check_mechanics(adj_prose, hits, report, lm_adj)
    report_punctuation_profile(metric_prose, word_count, report)
    # Reported, not scored: what vacuous prose lacks rather than what it contains.
    report_specificity(metric_prose, sents, word_count, report)
    # Reported, never scored -- scoring it reproduces the ESL bias this skill
    # exists to argue against. See report_contraction_rate's docstring.
    report_contraction_rate(metric_prose, word_count, report)
    # Burrows's Delta against the committed human function-word profile. Also
    # unscored, and read in the opposite direction from the obvious one: see
    # stylometry.py. A missing or malformed profile leaves the key absent.
    report_stylometry(metric_prose, report)

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
