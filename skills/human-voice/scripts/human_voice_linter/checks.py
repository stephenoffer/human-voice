"""checks — part of human_voice_linter (split from detect_ai_prose.py)."""
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


CITATION_NEAR_RE = re.compile(
    r"\[\^?\d|\[\d+\]|\(\s*[A-Z][\w.&-]+,?\s*(?:et al\.?,?\s*)?\d{4}|\(\d{4}\)|https?://|doi:")


def _line_bounds(text, idx):
    start = text.rfind("\n", 0, idx) + 1
    end = text.find("\n", idx)
    return start, (end if end != -1 else len(text))


def _span_hit(category, lm, m, text, suggestion=None):
    """Build a Hit carrying a precise (line, col)->(end_line, end_col) span.

    Use only when `m` was matched against a text whose geometry matches the
    source file (code_stripped or the raw text); otherwise the columns would
    point at the wrong characters and a line-only Hit should be used instead.
    """
    ln, col, eln, ecol = lm.loc(m.start(), m.end())
    return Hit(category, ln, text, suggestion, col=col, end_line=eln, end_col=ecol)


def check_lexical_list(text, value, category, hits, seen_spans, lm, protected=(),
                       cite_guard=False, skip_quoted=False):
    for phrase, suggestion in as_phrase_list(value):
        rx = _phrase_regex(phrase)
        if rx is None:
            continue
        for m in rx.finditer(text):
            span = (m.start(), m.end())
            # Don't double-flag the same span across overlapping lists.
            if span in seen_spans.get(category, set()):
                continue
            # Suppress a hit that is part of a known-legitimate phrase.
            if protected and _overlaps(m.start(), m.end(), protected):
                continue
            # Vague attribution that is immediately sourced is not vague.
            if cite_guard and CITATION_NEAR_RE.search(text[m.end():m.end() + 45]):
                continue
            # Optionally skip matches on heading/blockquote lines or inside a
            # quotation (where the wording belongs to someone else).
            if skip_quoted:
                ls, le = _line_bounds(text, m.start())
                line = text[ls:le]
                if HEADING_LINE_RE.match(line) or BLOCKQUOTE_RE.match(line):
                    continue
                if text.count('"', ls, m.start()) % 2 == 1:
                    continue
            seen_spans.setdefault(category, set()).add(span)
            hits.append(_span_hit(category, lm, m, m.group(0),
                                  suggestion if suggestion else "cut"))


def check_antithesis(text, patterns, hits, lm):
    if not isinstance(patterns, list):
        return
    for pat in patterns:
        if not isinstance(pat, str) or not pat:
            continue
        try:
            rx = re.compile(pat, re.IGNORECASE)
        except re.error as exc:
            warn("skipping invalid antithesis pattern %r: %s" % (pat, exc))
            continue
        for m in rx.finditer(text):
            snippet = m.group(0)
            if len(snippet) > 70:
                snippet = snippet[:67] + "..."
            hits.append(_span_hit("antithesis", lm, m,
                                  snippet.replace("\n", " "),
                                  "drop the not-X/it's-Y framing; state it plainly"))


def check_pattern_list(text, patterns, category, suggestion, hits, lm, protected=()):
    """Run a JSON-supplied list of regexes and emit Hits under one category.

    Generalizes check_antithesis for the structural tells that live as regex
    lists in the patterns file (false agency, negative listing, dramatic
    fragmentation). Honors protected spans like the lexical checks do.
    """
    if not isinstance(patterns, list):
        return
    for pat in patterns:
        if not isinstance(pat, str) or not pat:
            continue
        try:
            rx = re.compile(pat, re.IGNORECASE)
        except re.error as exc:
            warn("skipping invalid %s pattern %r: %s" % (category, pat, exc))
            continue
        for m in rx.finditer(text):
            if protected and _overlaps(m.start(), m.end(), protected):
                continue
            snippet = m.group(0)
            if len(snippet) > 70:
                snippet = snippet[:67] + "..."
            hits.append(_span_hit(category, lm, m,
                                  snippet.replace("\n", " "), suggestion))


EM_DASH_RE = re.compile(r"\s?[—–]\s?|(?<=\w)--(?=\w)|\s--\s")


def _is_numeric_en_dash(text, m):
    """True when the match is an en-dash used as a number range (10–20, 2024 – 25).

    En-dashes between digits are correct typography for ranges, not the em-dash
    overuse the check targets, so they should not count.
    """
    if "–" not in m.group(0):
        return False
    i = m.start()
    while i > 0 and text[i - 1].isspace():
        i -= 1
    j = m.end()
    while j < len(text) and text[j].isspace():
        j += 1
    before = text[i - 1] if i > 0 else ""
    after = text[j] if j < len(text) else ""
    return before.isdigit() and after.isdigit()


PAIRED_DASH_RE = re.compile(r"[—–]\s?[^—–\n]{1,50}?\s?[—–]")


def check_em_dash(text, words, threshold, hits, report, lm):
    matches = [m for m in EM_DASH_RE.finditer(text) if not _is_numeric_en_dash(text, m)]
    count = len(matches)
    per_1k = (count / words * 1000) if words else 0.0
    report["em_dash_per_1k"] = round(per_1k, 1)
    report["em_dash_count"] = sum(1 for m in matches if "—" in m.group(0) or "--" in m.group(0))
    report["en_dash_count"] = sum(1 for m in matches if "–" in m.group(0))
    paired = list(PAIRED_DASH_RE.finditer(text))
    report["paired_dash_asides"] = len(paired)
    if per_1k > threshold and count >= 2:
        for m in matches[:8]:
            ctx = text[max(0, m.start() - 15):m.start() + 15].replace("\n", " ").strip()
            hits.append(Hit("em_dash", lm.line_of(m.start()), ctx,
                            "use a comma, period, or parens"))
    # Paired dash asides are a distinctive tic even below the density floor.
    elif len(paired) >= 2:
        for m in paired[:6]:
            hits.append(Hit("em_dash", lm.line_of(m.start()),
                            m.group(0).replace("\n", " ").strip(),
                            "rework the dashed aside as its own sentence or parens"))


BOLD_BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+(?:\*\*[^*\n]+\*\*|__[^_\n]+__)[ \t]*:?",
                            re.MULTILINE)
BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+\S", re.MULTILINE)


def check_bold_bullets(text, threshold, hits, report, lm):
    bullets = BULLET_RE.findall(text)
    bold = list(BOLD_BULLET_RE.finditer(text))
    report["bullets"] = len(bullets)
    report["bold_lead_bullets"] = len(bold)
    if bullets and (len(bold) / len(bullets)) >= threshold and len(bold) >= 3:
        for m in bold[:8]:
            hits.append(_span_hit("bold_bullets", lm, m,
                                  m.group(0).strip(),
                                  "convert some to prose; drop ornamental bold"))


# Triads with an optional Oxford comma, joined by "and" or "or":
# "fast, reliable, and scalable" and "fast, reliable and scalable" both match.
RULE_OF_THREE_RE = re.compile(
    r"\b([A-Za-z]+(?:ly)?)\s*,\s+([A-Za-z]+(?:ly)?)\s*,?\s+(?:and|or)\s+([A-Za-z]+(?:ly)?)\b")


def check_rule_of_three(prose_text, hits, lm):
    for m in RULE_OF_THREE_RE.finditer(prose_text):
        a, b, c = m.group(1), m.group(2), m.group(3)
        # Adjective/adverb-looking triads only; require length and -ly/-ed-ish
        # endings or short words to avoid flagging proper-noun lists.
        if not all(len(w) > 3 for w in (a, b, c)):
            continue
        # Skip proper-noun lists ("Python, Django, and Flask"): a capitalized
        # member that is NOT the sentence's first word marks a name, not an
        # adjective. The first member can be capitalized merely by position.
        if b[0].isupper() or c[0].isupper():
            continue
        hits.append(Hit("rule_of_three", lm.line_of(m.start()),
                        m.group(0), "vary to two or four, or a clause"))


def check_uniform_openers(sents, ratio_threshold, hits, report):
    openers = []
    for s in sents:
        m = WORD_RE.search(s)
        if m:
            openers.append(m.group(0).lower())
    if len(openers) < 4:
        report["opener_repeat_ratio"] = 0.0
        report["opener_entropy"] = None
        return
    counts = Counter(openers)
    # Shannon entropy of the opener distribution (low = templated openings).
    total = len(openers)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    report["opener_entropy"] = round(entropy, 2)
    word, count = counts.most_common(1)[0]
    ratio = count / total
    report["opener_repeat_ratio"] = round(ratio, 2)
    if ratio >= ratio_threshold:
        hits.append(Hit("uniform_openers", 0,
                        '%d of %d sentences open with "%s"' % (count, total, word),
                        "vary how sentences begin"))


WH_OPENERS = frozenset(("what", "when", "where", "which", "who", "why", "how"))


def check_wh_openers(sents, ratio_threshold, run, hits, report):
    """Flag the Wh-opener crutch: many sentences opening with what/when/why/...

    A specific sub-case of uniform openers ("What makes this hard is...",
    "Why does this matter?"). Fires on either a high overall ratio or a run of
    consecutive Wh-openers, so a short passage that stacks three of them is
    caught even when the document-wide ratio is diluted.
    """
    firsts = []
    for s in sents:
        m = WORD_RE.search(s)
        firsts.append(m.group(0).lower() if m else None)
    wh_flags = [f in WH_OPENERS for f in firsts]
    total = sum(1 for f in firsts if f is not None)
    count = sum(wh_flags)
    report["wh_opener_count"] = count
    if total < 4:
        return
    ratio = count / total
    report["wh_opener_ratio"] = round(ratio, 2)
    streak = 0
    max_streak = 0
    for flag in wh_flags:
        streak = streak + 1 if flag else 0
        max_streak = max(max_streak, streak)
    if ratio >= ratio_threshold or max_streak >= run:
        hits.append(Hit("wh_opener", 0,
                        "%d of %d sentences open with a Wh- word (run of %d)"
                        % (count, total, max_streak),
                        "lead with the subject; name the specific thing, not 'What makes this...'"))


def check_formatting(text, max_rules, hits, report, lm):
    max_rules = int(max_rules)
    emojis = EMOJI_RE.findall(text)
    report["emoji"] = len(emojis)
    if emojis:
        m = EMOJI_RE.search(text)
        hits.append(_span_hit("formatting", lm, m,
                              "emoji (%d)" % len(emojis), "remove decorative emoji"))
    rules = list(SECTION_RULE_MULTILINE_RE.finditer(text))
    report["section_rules"] = len(rules)
    if len(rules) > max_rules:
        for m in rules[max_rules:max_rules + 6]:
            hits.append(_span_hit("formatting", lm, m,
                                  "horizontal rule", "drop rules between every section"))


def check_burstiness(sents, floor, hits, report):
    lengths = [n for n in (len(WORD_RE.findall(s)) for s in sents) if n > 0]
    if len(lengths) < 5:
        report["burstiness_cov"] = None
        report["mean_sentence_len"] = round(sum(lengths) / len(lengths), 1) if lengths else 0
        return
    mean = sum(lengths) / len(lengths)
    if mean <= 0:
        report["burstiness_cov"] = None
        report["mean_sentence_len"] = 0
        return
    var = sum((n - mean) ** 2 for n in lengths) / len(lengths)
    cov = math.sqrt(var) / mean
    report["burstiness_cov"] = round(cov, 2)
    report["mean_sentence_len"] = round(mean, 1)
    if cov < floor:
        hits.append(Hit("burstiness", 0,
                        "sentence-length CoV %.2f (floor %.2f)" % (cov, floor),
                        "mix short punches with long sentences"))


def _yules_k(words):
    """Yule's K — vocabulary richness, robust to text length (lower = richer)."""
    n = len(words)
    if n < 2:
        return None
    freqs = Counter(words)
    spectrum = Counter(freqs.values())  # how many words occur m times
    inner = sum(vm * (m * m) for m, vm in spectrum.items())
    return round(1e4 * (inner - n) / (n * n), 1)


def check_lexical_diversity(prose_text, floor, hits, report):
    words = [w.lower() for w in WORD_RE.findall(prose_text)]
    if len(words) < 50:
        report["ttr"] = None
        report["yules_k"] = None
        return
    window = 50
    # Moving-average TTR (MATTR): overlapping windows for a smoother estimate.
    # Fall back to non-overlapping stride on very large inputs to bound cost.
    stride = 1 if len(words) <= 50000 else window
    ratios = []
    for i in range(0, len(words) - window + 1, stride):
        ratios.append(len(set(words[i:i + window])) / window)
    ttr = (sum(ratios) / len(ratios)) if ratios else (len(set(words)) / len(words))
    report["ttr"] = round(ttr, 2)
    report["yules_k"] = _yules_k(words)
    if ttr < floor:
        hits.append(Hit("lexical_diversity", 0,
                        "type-token ratio %.2f (floor %.2f)" % (ttr, floor),
                        "vary word choice; avoid repeating concept terms verbatim"))


STOPWORDS = set("the a an of to in and or is are was were be been being it its "
                "this that these those for on with as at by from we you they i "
                "he she but not so if then than into over under can will would "
                "should could may might do does did has have had our your their "
                "about which who whom there here when where how what why".split())


def check_ngram_repetition(prose_text, sizes, min_count, hits):
    words = [w.lower() for w in WORD_RE.findall(prose_text)]
    for n in sizes:
        if n < 2 or len(words) < n:
            continue
        grams = Counter()
        for i in range(len(words) - n + 1):
            gram = tuple(words[i:i + n])
            if all(w in STOPWORDS for w in gram):
                continue
            grams[gram] += 1
        for gram, count in grams.most_common():
            if count >= min_count:
                hits.append(Hit("ngram_repetition", 0,
                                '"%s" x%d' % (" ".join(gram), count),
                                "rephrase repeated %d-grams" % n))
            else:
                break  # most_common is descending; nothing further qualifies


def _is_identifier_context(text, start, end):
    """True when a match sits in a code identifier rather than prose.

    Skips dialect hits on tokens like `optimizer`, `Color.RED`, `analyse()`, or
    SCREAMING_CASE constants, where the spelling is a fixed API name, not drift.
    """
    word = text[start:end]
    if word.isupper() and len(word) > 1:
        return True
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    return before in "_.$" or after in "_.("


def check_dialect(text, dialect_map, hits, lm):
    if not isinstance(dialect_map, dict):
        return
    for wrong, right in dialect_map.items():
        if not isinstance(wrong, str) or not wrong:
            continue
        rx = _word_regex(wrong)
        if rx is None:
            continue
        for m in rx.finditer(text):
            if _is_identifier_context(text, m.start(), m.end()):
                continue
            sug = ("use '%s' for consistent dialect" % right
                   if isinstance(right, str) else "spelling drift")
            hits.append(_span_hit("dialect", lm, m, m.group(0), sug))


HEADING_RE = re.compile(r"^[ \t]*(#{1,6})[ \t]+(.+?)[ \t]*#*$", re.MULTILINE)


def check_heading_case(text, hits, lm):
    styles = []
    spans = []
    for m in HEADING_RE.finditer(text):
        title = m.group(2).strip()
        words = [w for w in title.split() if any(ch.isalpha() for ch in w)]
        if len(words) < 2:
            continue
        caps = sum(1 for w in words if w[0].isupper())
        style = "title" if caps >= max(2, len(words) - 1) else "sentence"
        styles.append(style)
        spans.append((m.start(), title))
    if len(set(styles)) > 1:
        majority = Counter(styles).most_common(1)[0][0]
        for (start, title), style in zip(spans, styles):
            if style != majority:
                hits.append(Hit("heading_case", lm.line_of(start), title,
                                "match the dominant heading case (%s)" % majority))


# ---------------------------------------------------------------------------
# Density / structural checks (Phase 2)
# ---------------------------------------------------------------------------

# Passive voice: a "to be" form (optionally with an adverb) + a past participle.
# Deliberately conservative — flagged only when density is high, since some
# passive is normal and necessary.
PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|got|gets)\s+(?:\w+ly\s+)?"
    r"(?:\w+ed|written|made|done|given|taken|seen|known|built|held|kept|sent|"
    r"shown|told|found|put|set|read|lost|won|paid|met|drawn|grown|chosen)\b",
    re.IGNORECASE)
ADVERB_RE = re.compile(r"\b\w{3,}ly\b")
NOMINALIZATION_RE = re.compile(r"\b\w{4,}(?:tion|ment|ance|ence|ity|ization|isation)s?\b",
                               re.IGNORECASE)
COLON_SUMMARY_RE = re.compile(
    r"\b(?:the\s+)?(?:key|answer|takeaway|bottom line|point|truth|reality|catch|"
    r"problem|reason|result|upshot|short of it)\s+(?:here\s+)?is:\s*\S",
    re.IGNORECASE)


def _density_hit(category, count, words, threshold, hits, report, metric_key,
                 example, suggestion, min_words=150):
    per_1k = (count / words * 1000) if words else 0.0
    report[metric_key] = round(per_1k, 1)
    if words >= min_words and per_1k > threshold and count >= 3:
        hits.append(Hit(category, 0,
                        "%s: %.0f / 1k words (floor %.0f)" % (example, per_1k, threshold),
                        suggestion))


def check_passive_voice(prose_text, words, threshold, hits, report):
    count = len(PASSIVE_RE.findall(prose_text))
    _density_hit("passive_voice", count, words, threshold, hits, report,
                 "passive_per_1k", "passive constructions",
                 "prefer the active voice where the actor matters")


def check_adverbs(tokens, words, threshold, hits, report):
    count = sum(1 for t in tokens if len(t) > 3 and t.endswith("ly"))
    _density_hit("adverbs", count, words, threshold, hits, report,
                 "adverb_per_1k", "-ly adverbs",
                 "cut weak adverbs; pick a stronger verb or adjective")


def check_nominalizations(prose_text, words, threshold, hits, report):
    count = len(NOMINALIZATION_RE.findall(prose_text))
    _density_hit("nominalization", count, words, threshold, hits, report,
                 "nominalization_per_1k", "nominalizations",
                 "turn -tion/-ment nouns back into verbs")


def check_rhetorical(sents, words, threshold, hits, report):
    count = sum(1 for s in sents if s.rstrip().endswith("?"))
    _density_hit("rhetorical", count, words, threshold, hits, report,
                 "rhetorical_per_1k", "rhetorical questions",
                 "answer the question or cut it")


def check_colon_summary(prose_text, hits, report, lm):
    matches = list(COLON_SUMMARY_RE.finditer(prose_text))
    report["colon_summary"] = len(matches)
    if len(matches) >= 3:
        for m in matches[:6]:
            hits.append(Hit("colon_summary", lm.line_of(m.start()),
                            m.group(0).strip().replace("\n", " "),
                            "vary the lead-in; not every point needs 'X is: ...'"))


def report_punctuation_profile(prose_text, words, report):
    """Per-1k-word punctuation counts (report-only; a stylometric signal)."""
    if not words:
        return
    for key, ch in (("semicolon", ";"), ("colon", ":"), ("question", "?"),
                    ("exclaim", "!")):
        report["%s_per_1k" % key] = round(prose_text.count(ch) / words * 1000, 1)
    report["paren_per_1k"] = round(prose_text.count("(") / words * 1000, 1)


def paragraphs_of(code_stripped):
    """Word counts of prose paragraphs (blank-line separated, non-structural)."""
    counts = []
    for block in re.split(r"\n[ \t]*\n", code_stripped):
        lines = []
        for ln in block.split("\n"):
            if (HEADING_LINE_RE.match(ln) or SETEXT_RE.match(ln) or SECTION_RULE_RE.match(ln)
                    or TABLE_ROW_RE.match(ln) or LIST_MARKER_RE.match(ln)):
                continue
            lines.append(ln)
        text = strip_inline_markup(" ".join(lines))
        n = len(WORD_RE.findall(text))
        if n > 0:
            counts.append(n)
    return counts


def _cov(values):
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean <= 0:
        return None
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var) / mean


def check_paragraph_uniformity(code_stripped, floor, hits, report, min_paras=4):
    counts = paragraphs_of(code_stripped)
    cov = _cov(counts)
    report["paragraph_len_cov"] = round(cov, 2) if cov is not None else None
    if len(counts) >= min_paras and cov is not None and cov < floor:
        hits.append(Hit("paragraph_uniformity", 0,
                        "paragraph-length CoV %.2f (floor %.2f)" % (cov, floor),
                        "vary paragraph length; AI drafts are suspiciously even"))


def check_list_uniformity(code_stripped, floor, hits, report, min_items=4):
    counts = []
    for ln in code_stripped.split("\n"):
        if LIST_MARKER_RE.match(ln):
            item = strip_inline_markup(LIST_MARKER_RE.sub("", ln))
            n = len(WORD_RE.findall(item))
            if n > 0:
                counts.append(n)
    cov = _cov(counts)
    report["list_item_cov"] = round(cov, 2) if cov is not None else None
    if len(counts) >= min_items and cov is not None and cov < floor:
        hits.append(Hit("list_uniformity", 0,
                        "list-item-length CoV %.2f (floor %.2f)" % (cov, floor),
                        "uniform list items read as generated; vary or convert to prose"))


def check_circular_conclusion(code_stripped, hits, report, min_paras=3, overlap=0.5):
    counts = []
    paras = [p for p in re.split(r"\n[ \t]*\n", code_stripped) if p.strip()]
    prose = []
    for block in paras:
        lines = [ln for ln in block.split("\n")
                 if not (HEADING_LINE_RE.match(ln) or SECTION_RULE_RE.match(ln)
                         or TABLE_ROW_RE.match(ln))]
        text = strip_inline_markup(" ".join(lines))
        if WORD_RE.findall(text):
            prose.append([w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS])
    if len(prose) < min_paras:
        return
    first, last = set(prose[0]), set(prose[-1])
    if not first or not last:
        return
    jacc = len(first & last) / len(first | last)
    if jacc >= overlap:
        hits.append(Hit("circular_conclusion", 0,
                        "closing paragraph repeats the opening (overlap %.2f)" % jacc,
                        "end on the last real point; cut the recap"))


def check_parallel_structure(sents, hits, report, run=3):
    """Flag >= `run` consecutive sentences sharing their first two words."""
    def head(s):
        ws = WORD_RE.findall(s.lower())
        return tuple(ws[:2]) if len(ws) >= 2 else None
    streak = 1
    flagged = 0
    for i in range(1, len(sents)):
        if head(sents[i]) is not None and head(sents[i]) == head(sents[i - 1]):
            streak += 1
            if streak == run:
                h = head(sents[i])
                hits.append(Hit("parallel_structure", 0,
                                '%d+ sentences in a row open "%s ..."' % (run, " ".join(h)),
                                "vary sentence openings and structure"))
                flagged += 1
        else:
            streak = 1


# ---------------------------------------------------------------------------
# Dash style, doubled words, and punctuation mechanics (grammar/formatting)
# ---------------------------------------------------------------------------

# ASCII double-hyphen used as a dash ("draft--like this" or "spaced -- like so").
ASCII_DASH_RE = re.compile(r"(?<=\w)--(?=\w)|\s--\s")
# An em-dash that hugs its words on both sides (no spaces): "word—word".
EM_TIGHT_RE = re.compile(r"\w—\w")
# An em-dash spaced on both sides: "word — word".
EM_SPACED_RE = re.compile(r"\w\s—\s\w")
# Spaced hyphen standing in for a dash between lowercase words: "this - that".
SPACED_HYPHEN_DASH_RE = re.compile(r"(?<=[a-z]) - (?=[a-z])")


def check_dash_style(prose_text, hits, report, lm):
    """Dash *correctness and consistency*, distinct from em-dash density.

    Flags ASCII `--` standing in for a real dash, a spaced hyphen used as a
    dash, and a document that mixes spaced and unspaced em-dashes.
    """
    ascii_dd = list(ASCII_DASH_RE.finditer(prose_text))
    spaced_hyphen = list(SPACED_HYPHEN_DASH_RE.finditer(prose_text))
    tight = len(EM_TIGHT_RE.findall(prose_text))
    spaced = len(EM_SPACED_RE.findall(prose_text))
    report["dash_ascii_double"] = len(ascii_dd)
    report["dash_spaced_hyphen"] = len(spaced_hyphen)
    report["em_dash_spacing_mixed"] = bool(tight and spaced)
    for m in ascii_dd[:6]:
        hits.append(Hit("dash_style", lm.line_of(m.start()),
                        m.group(0).strip() or "--",
                        "use an em-dash (—) or rework; '--' reads as raw markup"))
    for m in spaced_hyphen[:6]:
        ctx = prose_text[max(0, m.start() - 8):m.end() + 8].replace("\n", " ").strip()
        hits.append(Hit("dash_style", lm.line_of(m.start()), ctx,
                        "a spaced hyphen isn't a dash; use a comma, period, or em-dash"))
    if tight and spaced:
        hits.append(Hit("dash_style", 0,
                        "em-dash spacing is inconsistent (both word—word and word — word)",
                        "pick one em-dash spacing convention and hold it"))


# Consecutive identical words ("the the"), case-insensitive. The gap is spaces
# or tabs only (no newline), so a word ending one line/heading and the same word
# opening the next (e.g. "...use it" / "It does...") is not a false doubling.
# Excludes words that legitimately repeat ("had had", "that that").
DOUBLED_WORD_RE = re.compile(r"\b([A-Za-z]{2,})\b[ \t]+\1\b", re.IGNORECASE)
DOUBLE_OK = {"that", "had", "ha", "no", "so", "very", "really", "blah", "yeah",
             "ok", "bye", "din", "tut", "hear", "now"}


def check_doubled_words(prose_text, hits, report, lm):
    matches = []
    for m in DOUBLED_WORD_RE.finditer(prose_text):
        if m.group(1).lower() in DOUBLE_OK:
            continue
        matches.append(m)
    report["doubled_words"] = len(matches)
    for m in matches[:8]:
        hits.append(Hit("doubled_word", lm.line_of(m.start()),
                        m.group(0).replace("\n", " "),
                        "remove the duplicated word"))


# Space before sentence punctuation: "word ," / "word ;" / "word ?".
SPACE_BEFORE_PUNCT_RE = re.compile(r"\w[ \t]+([,;:!?])")
# Repeated terminal punctuation: "!!", "??", or 3+ mixed ("?!?"). A lone "?!"
# (one of each) is left alone as a legitimate interrobang.
MULTI_PUNCT_RE = re.compile(r"!{2,}|\?{2,}|[!?]{3,}")


def check_mechanics(prose_text, hits, report, lm):
    space_before = list(SPACE_BEFORE_PUNCT_RE.finditer(prose_text))
    multi_punct = list(MULTI_PUNCT_RE.finditer(prose_text))
    report["space_before_punct"] = len(space_before)
    report["multi_terminal_punct"] = len(multi_punct)
    for m in space_before[:6]:
        ctx = prose_text[max(0, m.start() - 6):m.end() + 4].replace("\n", " ").strip()
        hits.append(Hit("mechanics", lm.line_of(m.start()), ctx,
                        "no space before '%s'" % m.group(1)))
    for m in multi_punct[:6]:
        hits.append(Hit("mechanics", lm.line_of(m.start()), m.group(0),
                        "one punctuation mark is enough"))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


__all__ = [
    'CITATION_NEAR_RE',
    '_line_bounds',
    'check_lexical_list',
    'check_antithesis',
    'check_pattern_list',
    'EM_DASH_RE',
    '_is_numeric_en_dash',
    'PAIRED_DASH_RE',
    'check_em_dash',
    'BOLD_BULLET_RE',
    'BULLET_RE',
    'check_bold_bullets',
    'RULE_OF_THREE_RE',
    'check_rule_of_three',
    'check_uniform_openers',
    'WH_OPENERS',
    'check_wh_openers',
    'check_formatting',
    'check_burstiness',
    '_yules_k',
    'check_lexical_diversity',
    'STOPWORDS',
    'check_ngram_repetition',
    '_is_identifier_context',
    'check_dialect',
    'HEADING_RE',
    'check_heading_case',
    'PASSIVE_RE',
    'ADVERB_RE',
    'NOMINALIZATION_RE',
    'COLON_SUMMARY_RE',
    '_density_hit',
    'check_passive_voice',
    'check_adverbs',
    'check_nominalizations',
    'check_rhetorical',
    'check_colon_summary',
    'report_punctuation_profile',
    'paragraphs_of',
    '_cov',
    'check_paragraph_uniformity',
    'check_list_uniformity',
    'check_circular_conclusion',
    'check_parallel_structure',
    'ASCII_DASH_RE',
    'EM_TIGHT_RE',
    'EM_SPACED_RE',
    'SPACED_HYPHEN_DASH_RE',
    'check_dash_style',
    'DOUBLED_WORD_RE',
    'DOUBLE_OK',
    'check_doubled_words',
    'SPACE_BEFORE_PUNCT_RE',
    'MULTI_PUNCT_RE',
    'check_mechanics',
]
