"""checks — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import math
import re
from collections import Counter

from .defaults import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403
from .patterns import *  # noqa: F401,F403
from .textutil import *  # noqa: F401,F403
from .util import *  # noqa: F401,F403

CITATION_NEAR_RE = re.compile(
    r"\[\^?\d|\[\d+\]|\(\s*[A-Z][\w.&-]+,?\s*(?:et al\.?,?\s*)?\d{4}|\(\d{4}\)|https?://|doi:")


# How many instance findings a single check will emit. This bounds memory and
# output on a hostile input; it is NOT a display limit. It used to be 6 or 8,
# inlined per check, and that silently capped the SCORE too: a 5,000-word document
# with fifty em-dashes emitted eight hits and scored the same as one with eight,
# because the density is computed from the hits the check produced. Display
# truncation belongs in the report layer, which already says "... and N more".
MAX_INSTANCE_HITS = 200

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
    """Flag every phrase from one pattern list, in ONE pass per boundary bucket.

    This used to compile and run a separate `\bphrase\b` regex per entry. With a
    thousand-plus entries in the pattern file that was 66% of total analysis time:
    a 36,000-word document meant twelve hundred full scans of the text. The
    phrases are alternated into a handful of combined regexes instead, and each
    match is mapped back to its suggestion by normalizing the matched text the
    same way `_phrase_regex` normalizes the phrase.

    One deliberate behavior change comes with it: where two phrases in the SAME
    list overlap at the same position, the alternation picks the longer one rather
    than emitting both. That is what a reader would call one finding.
    """
    pairs = as_phrase_list(value)
    if not pairs:
        return
    lookup = {}
    for phrase, suggestion in pairs:
        lookup.setdefault(_norm_phrase(phrase), suggestion)
    found = seen_spans.setdefault(category, set())
    # Collect from every chunk first, then take the longest match at each position
    # and drop anything overlapping it. Two entries in one list that cover the same
    # words ("it's worth noting" and "worth noting that") are one finding, not two,
    # and this is also what keeps chunked alternations from re-introducing the
    # double count across chunk boundaries.
    matches = []
    for rx in compile_phrase_matchers([p for p, _ in pairs]):
        matches.extend(rx.finditer(text))
    matches.sort(key=lambda m: (m.start(), -(m.end() - m.start())))
    kept = []
    last_end = -1
    for m in matches:
        if m.start() < last_end:
            continue
        kept.append(m)
        last_end = m.end()
    for m in kept:
        span = (m.start(), m.end())
        # Don't double-flag the same span across overlapping lists.
        if span in found:
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
        found.add(span)
        suggestion = lookup.get(_norm_phrase(m.group(0)))
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


# Real dashes only. ASCII `--` belongs to `dash_style`, which owns the "that is
# raw markup, not a dash" finding; counting it here too made one double-hyphen
# worth two hits in two categories, and a document written in the old
# `name -- description` docstring style scored twice for one convention.
EM_DASH_RE = re.compile(r"\s?[—–]\s?")


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
    # Three, not two. Two em-dashes is what a person who likes em-dashes writes in
    # an email; the tell is the dash becoming the default connector. The paired
    # aside below still fires at two, because "— like this —" is a distinct tic
    # rather than a rate.
    if per_1k > threshold and count >= 3:
        for m in matches[:MAX_INSTANCE_HITS]:
            ctx = text[max(0, m.start() - 15):m.start() + 15].replace("\n", " ").strip()
            hits.append(Hit("em_dash", lm.line_of(m.start()), ctx,
                            "use a comma, period, or parens"))
    # Paired dash asides are a distinctive tic even below the density floor.
    elif len(paired) >= 2:
        for m in paired[:MAX_INSTANCE_HITS]:
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
        for m in bold[:MAX_INSTANCE_HITS]:
            hits.append(_span_hit("bold_bullets", lm, m,
                                  m.group(0).strip(),
                                  "convert some to prose; drop ornamental bold"))


def _distinct_by_text(matches):
    """First occurrence of each distinct matched phrase, order preserved.

    Used where the tell is a HABIT rather than a count: repeating one phrase is
    terminology consistency (principle 6), and charging for every copy of it turns
    a virtue into a finding.
    """
    seen = set()
    out = []
    for m in matches:
        key = " ".join(m.group(0).lower().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


# Triads with an optional Oxford comma, joined by "and" or "or":
# "fast, reliable, and scalable" and "fast, reliable and scalable" both match.
RULE_OF_THREE_RE = re.compile(
    r"\b([A-Za-z]+)\s*,\s+([A-Za-z]+)\s*,?\s+(?:and|or)\s+([A-Za-z]+)\b")

# Noun-PHRASE triads the single-word pattern misses ("encryption at rest,
# row-level access control, and audit logging"). Members are 1-3 words; at least
# one must be multi-word (a single-word triad is already handled above).
NOUN_TRIAD_RE = re.compile(
    r"\b([A-Za-z][\w-]*(?:\s+[\w-]+){0,2}),\s+([A-Za-z][\w-]*(?:\s+[\w-]+){0,2}),"
    r"\s+and\s+([A-Za-z][\w-]*(?:\s+[\w-]+){0,2})\b")


# Words that mark a triad member as a CLAUSE rather than a noun phrase. The
# noun-triad pattern cannot tell "encryption at rest, row-level access control,
# and audit logging" (a real triad) from "you paste code into a notebook, the
# kernel dies, and the last save is gone" (a sentence with three clauses in it),
# and flagging the second told a writer to break a sentence that was already fine.
_CLAUSE_PRONOUNS = frozenset((
    "it", "he", "she", "they", "we", "you", "i", "who", "which", "that"))
_CLAUSE_VERBS = frozenset((
    "is", "are", "was", "were", "be", "been", "am", "has", "have", "had",
    "do", "does", "did", "will", "would", "can", "could", "should", "may",
    "might", "must", "gets", "goes", "comes", "makes", "takes", "runs",
    "starts", "stops", "dies", "fails", "works", "means", "keeps", "leaves"))
# A member that OPENS with one of these is a phrase fragment captured out of a
# longer clause, not a list item.
_MEMBER_BAD_START = frozenset((
    "into", "onto", "from", "with", "for", "of", "to", "in", "on", "at", "by",
    "as", "than", "when", "while", "because", "if", "so", "but", "and", "or",
    "after", "before", "since", "though", "although", "unless", "until"))


def _is_noun_phrase(member):
    """Rough test: does this triad member read as a noun phrase, not a clause?"""
    words = [w.lower() for w in WORD_RE.findall(member)]
    if not words:
        return False
    if words[0] in _MEMBER_BAD_START:
        return False
    return not any(w in _CLAUSE_PRONOUNS or w in _CLAUSE_VERBS for w in words)


# A triad member that is really a function word swept up by the pattern: "a field
# that, directly or indirectly, holds ..." is not a list of three.
_TRIAD_STOP_MEMBERS = frozenset((
    "that", "this", "these", "those", "which", "what", "when", "where", "while",
    "then", "than", "with", "from", "into", "onto", "over", "under", "after",
    "before", "because", "unless", "until", "since", "though", "although",
    "here", "there", "they", "them", "their", "your", "ours", "have", "been",
    "were", "will", "would", "could", "should", "does", "done", "such", "some",
    "each", "both", "also", "only", "just", "even", "well", "more", "most",
    "less", "least", "very", "much", "many", "same", "other", "another"))


def check_rule_of_three(prose_text, hits, lm, min_single_word=2):
    """Triads, single-word and noun-phrase, both gated on repetition.

    A tricolon is a rhetorical figure, and principle 2 says explicitly that one is
    fine. What marks machine prose is the REFLEX: reaching for three whenever a
    list appears. Both halves of this check now need two instances in a document,
    so "tuples, lists, and dicts" (a real enumeration of exactly three things) does
    not get told to become two or four.
    """
    single = []
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
        if any(w.lower() in _TRIAD_STOP_MEMBERS for w in (a, b, c)):
            continue
        single.append(m)
    # DISTINCT triads. One boilerplate phrase repeated across twenty API
    # docstrings ("string, bytes, or bytearray") is one habit, not twenty, and
    # counting each copy put a reference manual straight into the category cap.
    # Terminology consistency is what principle 6 asks for; penalizing it is
    # exactly backwards.
    single = _distinct_by_text(single)
    if len(single) >= min_single_word:
        for m in single[:MAX_INSTANCE_HITS]:
            hits.append(Hit("rule_of_three", lm.line_of(m.start()),
                            m.group(0), "vary to two or four, or a clause"))
    # Noun-phrase triads: the reflexive STACKING is the tell, so only flag when a
    # document has 2+ of them; a single legitimate enumeration is left alone.
    np_hits = []
    for m in NOUN_TRIAD_RE.finditer(prose_text):
        members = (m.group(1), m.group(2), m.group(3))
        if not any(len(x.split()) > 1 for x in members):
            continue  # all single-word -> already covered above
        # A clause list is not a rule-of-three triad. See _is_noun_phrase.
        if not all(_is_noun_phrase(x) for x in members):
            continue
        # Proper-noun list guard (members 2/3; member 1 may be capitalized by
        # sentence position): "Slack, Google Drive, and GitHub" is a real list.
        if members[1][0].isupper() or members[2][0].isupper():
            continue
        np_hits.append(m)
    np_hits = _distinct_by_text(np_hits)
    if len(np_hits) >= 2:
        for m in np_hits[:MAX_INSTANCE_HITS]:
            snippet = m.group(0)
            hits.append(Hit("rule_of_three", lm.line_of(m.start()),
                            (snippet[:60] + "...") if len(snippet) > 63 else snippet,
                            "break the triad: two items, four, or a clause"))


# The words English sentences start with by default. A third of sentences opening
# "The" or "We" is what ordinary prose looks like -- measured on this corpus, human
# and AI files overlap completely in the 0.30-0.45 band for these words, so firing
# there produced false positives and no separation. A repeated DISTINCTIVE opener
# ("However", "Additionally", "By") is a real templating signal at a much lower
# rate, and svo_monotony already covers long subject-initial runs.
COMMON_OPENERS = frozenset((
    "the", "a", "an", "i", "we", "it", "this", "that", "they", "you", "he",
    "she", "there", "our", "my", "these", "those", "his", "her", "its", "their"))
COMMON_OPENER_RATIO = 0.45
COMMON_OPENER_MIN = 5


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
    if word in COMMON_OPENERS:
        fires = ratio >= COMMON_OPENER_RATIO and count >= COMMON_OPENER_MIN
    else:
        fires = ratio >= ratio_threshold
    if fires:
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
    ratio = (count / total) if total else 0.0
    report["wh_opener_ratio"] = round(ratio, 2)
    if total < 4:
        return
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
    # A run of dashes directly under a non-blank line is a setext heading
    # underline, not a rule between sections. Counting those flagged every
    # docstring and every doc that underlines its headings.
    rules = []
    for m in SECTION_RULE_MULTILINE_RE.finditer(text):
        prev_end = text.rfind("\n", 0, m.start())
        prev_start = text.rfind("\n", 0, prev_end) + 1 if prev_end > 0 else 0
        if prev_end > 0 and text[prev_start:prev_end].strip():
            continue
        rules.append(m)
    report["section_rules"] = len(rules)
    if len(rules) > max_rules:
        for m in rules[max_rules:max_rules + MAX_INSTANCE_HITS]:
            hits.append(_span_hit("formatting", lm, m,
                                  "horizontal rule", "drop rules between every section"))


def check_burstiness(sents, floor, hits, report, min_sents=8):
    """Coefficient of variation of sentence length.

    Needs at least `min_sents` sentences. At five, the CoV is dominated by
    sampling noise: a seven-sentence human abstract measured 0.33 and got flagged
    for "flat rhythm" while every AI file that actually fires has ten or more
    sentences. Raising the floor removed a false positive and cost no recall.
    """
    lengths = [n for n in (len(WORD_RE.findall(s)) for s in sents) if n > 0]
    if len(lengths) < min_sents:
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


def check_ngram_repetition(prose_text, sizes, min_count, hits, lm=None, max_report=8,
                           per_words=400):
    """Repeated n-grams, reported at the first occurrence and capped.

    This is an *instance* check, not a document one: a long repetitive text has
    genuinely more of them. It used to emit unbounded positionless hits, which
    both hid the location from the reader and let one category swamp the score on
    a long document (hundreds of hits on an 800-word input). Each finding now
    carries the line of its first occurrence, and the count is capped the same way
    every other instance check caps its examples.
    """
    # Count n-grams WITHIN sentences. Sliding a window over the whole token stream
    # manufactured phrases that straddle a full stop -- "...to the client. The
    # client retries..." yielded the trigram "client the client" -- which is an
    # artifact of the window, not a repetition anybody wrote.
    per_sentence = [[w.lower() for w in WORD_RE.findall(sent)]
                    for sent in sentences(prose_text)]
    if not per_sentence:
        per_sentence = [[w.lower() for w in WORD_RE.findall(prose_text)]]
    total_words = sum(len(ws) for ws in per_sentence)
    # Repetition is a RATE. A bigram appearing four times is a tic in a 300-word
    # note and unremarkable in a 4,000-word reference, where the same four
    # occurrences are terminology consistency (principle 6). Scale the floor with
    # length instead of holding one absolute count for every document.
    min_count = max(min_count, 3 + total_words // per_words)
    found = []
    for n in sizes:
        if n < 2 or total_words < n:
            continue
        # A repeated n-gram is only a tell when it repeats *content*. Requiring
        # two content words keeps the check off "the text", "the skill", "the
        # rewrite" -- article-plus-defined-term pairs that are precisely the
        # terminology consistency principle 6 tells you to hold. Flagging them
        # pushed writers toward rotating synonyms, which is the opposite of the
        # guidance and a tell in its own right.
        min_content = 2
        grams = Counter()
        for words in per_sentence:
            for i in range(len(words) - n + 1):
                gram = tuple(words[i:i + n])
                # A single letter is not a content word. "e.g." tokenizes to
                # ("e", "g"), which passed the two-content-word test and made
                # every document that abbreviates read as repetitive.
                if sum(1 for w in gram
                       if len(w) > 2 and w not in STOPWORDS) < min_content:
                    continue
                grams[gram] += 1
        for gram, count in grams.most_common():
            if count < min_count:
                break  # most_common is descending; nothing further qualifies
            found.append((count, n, gram))
    found.sort(key=lambda t: (-t[0], t[1], t[2]))
    for count, n, gram in found[:max_report]:
        phrase = " ".join(gram)
        line = 0
        if lm is not None:
            # Tokens are joined by single spaces, but the source may separate them
            # with a newline or runs of whitespace, so a literal find() misses.
            m = re.search(r"\s+".join(re.escape(w) for w in gram),
                          prose_text, re.IGNORECASE)
            if m:
                line = lm.line_of(m.start())
        hits.append(Hit("ngram_repetition", line,
                        '"%s" x%d' % (phrase, count),
                        "rephrase repeated %d-grams" % n))


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
    if before in "_$" or after in "_(":
        return True
    # `obj.method` / `pkg.name` is attribute access; `we optimise.` is a sentence.
    # Requiring an identifier character on the far side of the dot keeps the check
    # from silently skipping every word that ends a sentence.
    if before == "." and start >= 2 and (text[start - 2].isalnum() or text[start - 2] == "_"):
        return True
    if after == "." and end + 1 < len(text) and (text[end + 1].isalnum() or text[end + 1] == "_"):
        return True
    return False


def check_dialect(text, dialect_map, hits, lm):
    """Spelling drift against the chosen dialect, in one pass over the text.

    Sixty separate `\bword\b` scans became one alternation for the same reason
    check_lexical_list did: the cost is a full pass per pattern, and a long
    document pays it once per word in the map.
    """
    if not isinstance(dialect_map, dict):
        return
    words = [w for w in dialect_map if isinstance(w, str) and w]
    if not words:
        return
    lower = {w.lower(): dialect_map[w] for w in words}
    for rx in compile_phrase_matchers(words):
        for m in rx.finditer(text):
            if _is_identifier_context(text, m.start(), m.end()):
                continue
            right = lower.get(_norm_phrase(m.group(0)))
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
        for m in matches[:MAX_INSTANCE_HITS]:
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
    paras = [p for p in re.split(r"\n[ \t]*\n", code_stripped) if p.strip()]
    prose = []
    for block in paras:
        lines = [ln for ln in block.split("\n")
                 if not (HEADING_LINE_RE.match(ln) or SECTION_RULE_RE.match(ln)
                         or TABLE_ROW_RE.match(ln))]
        text = strip_inline_markup(" ".join(lines))
        if WORD_RE.findall(text):
            prose.append([w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS])
    report["prose_blocks"] = len(prose)
    if len(prose) < min_paras:
        report["conclusion_overlap"] = None
        return
    first, last = set(prose[0]), set(prose[-1])
    if not first or not last:
        report["conclusion_overlap"] = None
        return
    jacc = len(first & last) / len(first | last)
    report["conclusion_overlap"] = round(jacc, 2)
    if jacc >= overlap:
        hits.append(Hit("circular_conclusion", 0,
                        "closing paragraph repeats the opening (overlap %.2f)" % jacc,
                        "end on the last real point; cut the recap"))


def check_parallel_structure(sents, hits, report, run=3):
    """Flag runs of >= `run` consecutive sentences sharing their first two words.

    Reports the run's ACTUAL length, not the threshold. The old version fired the
    instant a streak reached `run` and then went quiet, so five sentences opening
    "The system ..." and three of them read identically in the report -- the
    writer could not tell a borderline case from a severe one.
    """
    def head(s):
        ws = WORD_RE.findall(s.lower())
        return tuple(ws[:2]) if len(ws) >= 2 else None
    heads = [head(s) for s in sents]
    runs = []
    i = 0
    while i < len(heads):
        if heads[i] is None:
            i += 1
            continue
        j = i + 1
        while j < len(heads) and heads[j] == heads[i]:
            j += 1
        if j - i >= run:
            runs.append((j - i, heads[i]))
        i = j
    report["parallel_runs"] = len(runs)
    report["longest_parallel_run"] = max((n for n, _ in runs), default=0)
    for length, h in runs[:4]:
        hits.append(Hit("parallel_structure", 0,
                        '%d sentences in a row open "%s ..."' % (length, " ".join(h)),
                        "vary sentence openings and structure"))


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


# Above this many occurrences of one dash convention, the finding is the
# convention rather than the instances, and it is reported once.
DASH_STYLE_INSTANCE_MAX = 5


def _dash_findings(matches, label, suggestion, prose_text, hits, lm):
    if not matches:
        return
    if len(matches) <= DASH_STYLE_INSTANCE_MAX:
        for m in matches:
            ctx = prose_text[max(0, m.start() - 8):m.end() + 8].replace("\n", " ").strip()
            hits.append(Hit("dash_style", lm.line_of(m.start()), ctx or label, suggestion))
        return
    lines = ", ".join("L%d" % lm.line_of(m.start()) for m in matches[:6])
    hits.append(Hit("dash_style", 0,
                    "%d occurrences of %s (first at %s)" % (len(matches), label, lines),
                    suggestion + "; this is one find-and-replace, not %d edits"
                    % len(matches)))


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
    # A handful of stray `--` is a per-line finding a writer fixes one at a time.
    # A hundred of them is one house style and one find-and-replace, so report it
    # once rather than charging for every occurrence: a reference manual written in
    # the `name -- description` convention was otherwise pinned at the category cap
    # by a single stylistic decision.
    _dash_findings(ascii_dd, "--", "use an em-dash (—) or rework; '--' reads as raw markup",
                   prose_text, hits, lm)
    _dash_findings(spaced_hyphen, "a spaced hyphen used as a dash",
                   "a spaced hyphen isn't a dash; use a comma, period, or em-dash",
                   prose_text, hits, lm)
    if tight and spaced:
        hits.append(Hit("dash_style", 0,
                        "em-dash spacing is inconsistent (both word—word and word — word)",
                        "pick one em-dash spacing convention and hold it"))


# Consecutive identical words ("the the"), case-insensitive. The gap is spaces
# or tabs only (no newline), so a word ending one line/heading and the same word
# opening the next (e.g. "...use it" / "It does...") is not a false doubling.
# Excludes words that legitimately repeat ("had had", "that that").
# The gap is ONE space or tab. A doubled word is a typing slip and it leaves a
# single space; three or more spaces is column alignment, and matching it flagged
# every two-column reference table ("match     Match a regular expression").
DOUBLED_WORD_RE = re.compile(r"\b([A-Za-z]{2,})\b[ \t]{1,2}\1\b", re.IGNORECASE)
DOUBLE_OK = {"that", "had", "ha", "no", "so", "very", "really", "blah", "yeah",
             "ok", "bye", "din", "tut", "hear", "now"}


def check_doubled_words(prose_text, hits, report, lm):
    matches = []
    for m in DOUBLED_WORD_RE.finditer(prose_text):
        if m.group(1).lower() in DOUBLE_OK:
            continue
        matches.append(m)
    report["doubled_words"] = len(matches)
    for m in matches[:MAX_INSTANCE_HITS]:
        hits.append(Hit("doubled_word", lm.line_of(m.start()),
                        m.group(0).replace("\n", " "),
                        "remove the duplicated word"))


# Space before sentence punctuation: "word ," / "word ;" / "word ?".
# `word :` is a mechanical error; `plus one :-)` is a smiley and `see :func:`x``
# is a role marker. Require the punctuation NOT to be the head of an emoticon or a
# reStructuredText role.
SPACE_BEFORE_PUNCT_RE = re.compile(r"\w[ \t]+([,;:!?])(?![-)(|/\\DPpO0<>*^]|\w+:)")
# Repeated terminal punctuation: "!!", "??", or 3+ mixed ("?!?"). A lone "?!"
# (one of each) is left alone as a legitimate interrobang.
MULTI_PUNCT_RE = re.compile(r"!{2,}|\?{2,}|[!?]{3,}")


def check_mechanics(prose_text, hits, report, lm):
    space_before = list(SPACE_BEFORE_PUNCT_RE.finditer(prose_text))
    multi_punct = list(MULTI_PUNCT_RE.finditer(prose_text))
    report["space_before_punct"] = len(space_before)
    report["multi_terminal_punct"] = len(multi_punct)
    for m in space_before[:MAX_INSTANCE_HITS]:
        ctx = prose_text[max(0, m.start() - 6):m.end() + 4].replace("\n", " ").strip()
        hits.append(Hit("mechanics", lm.line_of(m.start()), ctx,
                        "no space before '%s'" % m.group(1)))
    for m in multi_punct[:MAX_INSTANCE_HITS]:
        hits.append(Hit("mechanics", lm.line_of(m.start()), m.group(0),
                        "one punctuation mark is enough"))


# ---------------------------------------------------------------------------
# Structure, rhetoric, and over-correction checks (v0.4)
# ---------------------------------------------------------------------------


def _prose_paragraph_texts(code_stripped):
    """Prose paragraphs as plain strings (structural lines stripped out)."""
    out = []
    for block in re.split(r"\n[ \t]*\n", code_stripped):
        lines = []
        for ln in block.split("\n"):
            if (HEADING_LINE_RE.match(ln) or SETEXT_RE.match(ln) or SECTION_RULE_RE.match(ln)
                    or TABLE_ROW_RE.match(ln) or LIST_MARKER_RE.match(ln)):
                continue
            lines.append(ln)
        text = strip_inline_markup(" ".join(lines)).strip()
        if WORD_RE.findall(text):
            out.append(text)
    return out


CONCLUSION_OPENER_RE = re.compile(
    r"^\s*(?:in conclusion|in summary|to sum up|to summarize|to summarise|"
    r"in closing|all in all|in short|to conclude|overall,|ultimately,)\b",
    re.IGNORECASE)


def check_five_paragraph_shape(code_stripped, hits, report):
    """The intro / three-body / 'in conclusion' wrap-up essay mold.

    A doc-level structural tell readers cite often (the five-paragraph shape).
    Fires only when a multi-paragraph piece closes on an explicit conclusion
    marker, so a normal essay that simply ends is left alone.
    """
    paras = _prose_paragraph_texts(code_stripped)
    report["prose_paragraphs"] = len(paras)
    # The upper bound was 9, which let a 12-paragraph report close on "In
    # conclusion, ..." unflagged -- the recap is the tell, and it does not stop
    # being one because the piece is long. Only the floor is a real constraint:
    # a three-paragraph note has no essay shape to critique.
    if len(paras) < 4:
        return
    if CONCLUSION_OPENER_RE.match(paras[-1]):
        hits.append(Hit("five_paragraph_shape", 0,
                        "%d-paragraph essay closing on a conclusion wrap-up" % len(paras),
                        "let the structure follow the argument; end on the last real point, not a recap"))


HYPOPHORA_ANSWER_RE = re.compile(
    r"^\s*(?:because|the answer|it'?s\b|its\b|simple\.|yes\b|no\b|turns out|"
    r"here'?s why|that'?s because|the reason|short answer)\b",
    re.IGNORECASE)


def check_hypophora(sents, hits, report):
    """Ask-then-immediately-answer ('Why does this matter? Because ...').

    Distinct from a bare rhetorical question: the next sentence supplies the
    answer. One is fine; a run of them is the LinkedIn-explainer cadence.
    """
    count = 0
    for i in range(len(sents) - 1):
        if sents[i].rstrip().endswith("?") and HYPOPHORA_ANSWER_RE.match(sents[i + 1]):
            count += 1
    report["hypophora"] = count
    if count >= 2:
        hits.append(Hit("hypophora", 0,
                        "%d question-then-answer beats" % count,
                        "ask fewer rhetorical questions; just state the point"))


# Absolute/superlative claims. Kept distinct from the filler lists to limit
# double-counting; the check only fires when the claim is NOT backed by a
# nearby number, since "the best (by 12%)" is an earned superlative.
SUPERLATIVE_RE = re.compile(
    r"\b(?:the\s+)?(?:most|best|worst|greatest|finest|biggest|largest|fastest|"
    r"ultimate|perfect|unprecedented|unparalleled|unmatched|premier|foremost|"
    r"world-?class|game-?changing|the only|never before|second to none)\b",
    re.IGNORECASE)
_NUMBER_NEAR_RE = re.compile(r"\d")


def check_superlative_creep(prose_text, words, threshold, hits, report, min_words=150):
    matches = list(SUPERLATIVE_RE.finditer(prose_text))
    unbacked = [m for m in matches
                if not _NUMBER_NEAR_RE.search(prose_text[m.end():m.end() + 40])]
    count = len(unbacked)
    per_1k = (count / words * 1000) if words else 0.0
    report["superlative_per_1k"] = round(per_1k, 1)
    if words >= min_words and per_1k > threshold and count >= 3:
        # ONE document finding, not one per example. Emitting six line-0 hits made
        # a single density signal worth six times doc_hit_points -- more than any
        # structural tell -- and gave the writer no line to go to. The examples ride
        # along in the text instead.
        examples = ", ".join(sorted({m.group(0).strip().lower() for m in unbacked})[:5])
        hits.append(Hit("superlative_creep", 0,
                        "unbacked superlatives: %.0f / 1k words (floor %.0f): %s"
                        % (per_1k, threshold, examples),
                        "match the claim to evidence; cut the superlative or give the number"))


# Subject-class openers: the canonical Subject-Verb-Object lead. A long run of
# them is the flat, even cadence a scanner can't see in any single sentence.
SUBJECT_OPENERS = frozenset((
    "the", "this", "that", "these", "those", "it", "we", "you", "they", "i",
    "a", "an", "our", "their", "his", "her", "its", "he", "she"))


def check_svo_monotony(sents, hits, report, run=6, min_sents=8):
    """Flag a long *consecutive run* of subject-initial sentences.

    Subject-Verb-Object is English's default order, so most prose is majority
    subject-initial; an overall-share test would false-positive on careful human
    writing (and on ESL prose especially). The discriminating signal is a long
    unbroken run with no question, fragment, fronted adverbial, or transition to
    break it. Conservative on purpose; burstiness and uniform_openers cover the
    rest.
    """
    flags = []
    for s in sents:
        m = WORD_RE.search(s)
        flags.append(bool(m) and m.group(0).lower() in SUBJECT_OPENERS)
    streak = max_streak = 0
    for f in flags:
        streak = streak + 1 if f else 0
        max_streak = max(max_streak, streak)
    report["subject_opener_run"] = max_streak
    if len(sents) < min_sents:
        return
    if max_streak >= run:
        hits.append(Hit("svo_monotony", 0,
                        "%d sentences in a row open with a subject (Subject-Verb-Object lead)"
                        % max_streak,
                        "break the run: lead with a clause, a question, or a fronted adverbial"))


# Default AI character names and reflexive honorifics (fiction/creative tell).
DEFAULT_NAME_RE = re.compile(r"\b(Emily|Sarah|Michael|Jacob|Elena|Maya)\b")
DR_TITLE_RE = re.compile(r"\bDr\.\s+[A-Z]")


def check_name_selection(text, hits, report):
    names = Counter(m.group(1) for m in DEFAULT_NAME_RE.finditer(text))
    dr = len(DR_TITLE_RE.findall(text))
    report["default_names"] = sum(names.values())
    report["dr_titles"] = dr
    top = names.most_common(1)
    if top and top[0][1] >= 2:
        hits.append(Hit("name_selection", 0,
                        '"%s" used %d times (AI defaults to a few stock names)' % top[0],
                        "pick names that fit the era, region, and class of your characters"))
    if dr >= 3:
        hits.append(Hit("name_selection", 0, "%d 'Dr.' honorifics" % dr,
                        "AI over-titles; use first names or nicknames after introduction"))


# The "anti-AI costume": performed casualness that is itself a tell.
COSTUME_SLANG_RE = re.compile(r"\b(?:lol|lmao|idk|tbh|ngl|imo|fr|smh|iirc)\b", re.IGNORECASE)
SENTENCE_START_RE = re.compile(r"(?:^|[.!?]\s+)([A-Za-z])")


def check_punctuation_substitution(prose_text, words, semicolon_max, hits, report,
                                   min_words=150):
    """The humanizer's own fingerprint: every em-dash swapped for one other mark.

    Principle 2 says the em-dash fix has to VARY the replacement, and this is the
    check that holds the tool to it. A writer who reaches for semicolons also
    reaches for dashes; a document with an unusual semicolon rate and not one dash
    has been through a mechanical pass, and the flat substitution is a fresh
    uniform signature in place of the old one. Measured on this repo's corpus the
    human maximum is 5.5 semicolons per 1,000 words, and three of the shipped
    rewrites were over it before this check existed.
    """
    if not words:
        return
    semis = prose_text.count(";")
    per_1k = semis / words * 1000.0
    dashes = len([m for m in EM_DASH_RE.finditer(prose_text)
                  if not _is_numeric_en_dash(prose_text, m)])
    report["semicolon_per_1k"] = round(per_1k, 1)
    if words >= min_words and per_1k > semicolon_max and semis >= 3 and dashes == 0:
        hits.append(Hit("over_correction", 0,
                        "%.0f semicolons / 1k words and no dashes at all"
                        % per_1k,
                        "vary the replacement mark: a comma here, a period there, "
                        "parentheses elsewhere. One substitute everywhere is a new "
                        "uniform signature"))


def check_over_correction(prose_text, hits, report):
    """Detect over-correction into the anti-AI costume.

    Forced all-lowercase sentence starts and sprinkled chat slang read as a
    *performed* humanness. A new class so the linter never rewards swapping one
    costume for another. Muted in casual/creative where the voice is native.
    """
    starts = SENTENCE_START_RE.findall(prose_text)
    slang = len(COSTUME_SLANG_RE.findall(prose_text))
    report["costume_slang"] = slang
    if len(starts) >= 6:
        lower = sum(1 for c in starts if c.islower())
        share = lower / len(starts)
        report["lowercase_sentence_share"] = round(share, 2)
        if share >= 0.5:
            hits.append(Hit("over_correction", 0,
                            "%d%% of sentences start lowercase" % round(share * 100),
                            "forced lowercase is its own tell; write in a real register, not the anti-AI costume"))
    if slang >= 3:
        hits.append(Hit("over_correction", 0,
                        "%d chat-slang markers (lol/idk/tbh/...)" % slang,
                        "sprinkled slang reads as performed casualness; drop it or commit to the register"))



# ---------------------------------------------------------------------------
# Detector-aligned shape checks (v0.5)
#
# The strongest published evidence about what trained detectors respond to is
# that they track *post-training* artifacts rather than "machine-ness": base
# models, which never went through instruction tuning, are classified human at
# >96%, while their instruction-tuned siblings are caught. The artifacts named
# are response length conventions, markdown formatting preference (headings,
# lists, bolded runs), and assistant-style structural conventions. Word choice
# is downstream of all of that. These two checks measure the shape directly.
# See references/what-detectors-see.md.
# ---------------------------------------------------------------------------

BOLD_SPAN_RE = re.compile(r"\*\*[^*\n]{1,80}\*\*|__[^_\n]{1,80}__")

# Section titles that mark an answer wrapping itself up for the reader. A human
# report has a conclusion; an assistant response almost always does.
SUMMARY_HEADING_RE = re.compile(
    r"^[ \t]*#{1,6}[ \t]+(?:in\s+)?(?:conclusion|summary|in\s+summary|takeaways?|"
    r"key\s+takeaways?|final\s+thoughts?|tl;?dr|wrapping\s+up|closing\s+thoughts?|"
    r"the\s+bottom\s+line|next\s+steps)\b",
    re.IGNORECASE | re.MULTILINE)


def check_assistant_shape(text, word_count, headings_per_1k, bullet_ratio_max,
                          bold_per_1k, hits, report, raw_text=None):
    """Markdown scaffolding density: does this read as a written document or as a
    chat answer? Density-based, so a README's headings are fine and a heading
    every sixty words is not.

    `text` must be code-stripped: a `# comment` inside a fenced bash block is not
    a heading, `- **Flag**: ...` inside a quoted markdown sample is not a bold
    bullet, and counting them flagged style guides for demonstrating the very
    anti-pattern they warn against. `raw_text` (the pre-strip source) supplies the
    content-line denominator, so a code-heavy page is not judged as if the code
    were not there.
    """
    heading_lines = [ln for ln in text.splitlines() if HEADING_LINE_RE.match(ln)]
    denominator_src = raw_text if raw_text is not None else text
    content_lines = [ln for ln in denominator_src.splitlines() if ln.strip()]
    bullet_lines = [ln for ln in text.splitlines() if LIST_MARKER_RE.match(ln)]
    bold_spans = BOLD_SPAN_RE.findall(text)

    h_per_1k = (len(heading_lines) / word_count * 1000.0) if word_count else 0.0
    b_ratio = (len(bullet_lines) / len(content_lines)) if content_lines else 0.0
    bold_1k = (len(bold_spans) / word_count * 1000.0) if word_count else 0.0
    report["headings"] = len(heading_lines)
    report["headings_per_1k"] = round(h_per_1k, 1)
    report["bullet_line_ratio"] = round(b_ratio, 2)
    report["bold_spans"] = len(bold_spans)
    report["bold_spans_per_1k"] = round(bold_1k, 1)

    if word_count < 120:  # too short for a density to mean anything
        return
    if h_per_1k > headings_per_1k and len(heading_lines) >= 3:
        hits.append(Hit("assistant_shape", 0,
                        "a heading every %d words (%d headings / %d words)"
                        % (int(word_count / max(1, len(heading_lines))),
                           len(heading_lines), word_count),
                        "let paragraphs carry the structure; keep headings for real sections"))
    if b_ratio > bullet_ratio_max and len(bullet_lines) >= 5:
        hits.append(Hit("assistant_shape", 0,
                        "%.0f%% of content lines are list items" % (b_ratio * 100),
                        "turn the bulleted answer back into paragraphs"))
    if bold_1k > bold_per_1k and len(bold_spans) >= 4:
        hits.append(Hit("assistant_shape", 0,
                        "%d bold spans in %d words" % (len(bold_spans), word_count),
                        "drop emphasis that is decorating rather than distinguishing"))
    # The tell is a document that WRAPS ITSELF UP, so the recap heading has to be
    # the last one. A "Next steps" section in the middle of a project doc is a
    # section, not a chat answer signing off, and flagging it was wrong.
    summary = None
    for m in SUMMARY_HEADING_RE.finditer(text):
        summary = m
    if summary and len(heading_lines) >= 2:
        later = [ln for ln in text[summary.end():].splitlines()
                 if HEADING_LINE_RE.match(ln)]
        if not later:
            hits.append(Hit("assistant_shape", 0,
                            "closes with a %r section"
                            % summary.group(0).strip().lstrip("# ").strip(),
                            "end on the last real point; drop the recap section"))


def check_sentence_shape(sents, short_max, short_floor, mid_low, mid_high,
                         mid_max, hits, report, min_sents=8):
    """Sentence-length *distribution*, not just its coefficient of variation.

    Human prose reaches: it drops three-word sentences and runs forty-word ones.
    LLM prose collapses toward the middle. CoV misses this because a single long
    sentence inflates it while the rest stay uniform, so measure the tails
    directly."""
    lengths = [n for n in (len(WORD_RE.findall(s)) for s in sents) if n > 0]
    if len(lengths) < min_sents:
        report["short_sentence_ratio"] = None
        report["mid_band_ratio"] = None
        return
    n = len(lengths)
    short = sum(1 for x in lengths if x <= short_max) / n
    mid = sum(1 for x in lengths if mid_low <= x <= mid_high) / n
    report["short_sentence_ratio"] = round(short, 2)
    report["mid_band_ratio"] = round(mid, 2)
    report["longest_sentence"] = max(lengths)
    report["shortest_sentence"] = min(lengths)
    if short < short_floor:
        hits.append(Hit("sentence_shape", 0,
                        "only %.0f%% of sentences are <=%d words (floor %.0f%%)"
                        % (short * 100, short_max, short_floor * 100),
                        "cut in a short sentence. Like this one."))
    if mid > mid_max:
        hits.append(Hit("sentence_shape", 0,
                        "%.0f%% of sentences sit in the %d-%d word band"
                        % (mid * 100, mid_low, mid_high),
                        "push sentences out of the middle: some very short, some long"))


# Checkable specifics: numbers, dates, units, and proper nouns that are not just a
# sentence-initial capital. Reported, never scored. See report_specificity.
SPECIFIC_NUM_RE = re.compile(r"\b\d[\d,.:]*\b|\b\d+\s?%")
CAPWORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def report_specificity(prose_text, sents, words, report):
    """How many checkable specifics per 100 words. A METRIC, not a tell.

    Vacuity is the tell this skill calls highest and no regex can see. This does not
    see it either, but it measures the thing vacuous prose reliably lacks: numbers,
    dates, and named entities a reader could go and check.

    Deliberately NOT scored. Measured on this corpus the medians separate (human 3.0
    per 100 words, realistic-AI 0.6) and the ranges overlap completely: plenty of
    good human writing, fiction especially, contains no number and no proper noun at
    all. Scoring it would flag exactly the careful and creative writers detectors
    already mistreat. What it is good for is prompting the author-material intake:
    near-zero means the draft has nothing checkable in it, so cutting tells will
    leave clean, generic, unowned prose unless real material comes from somewhere.
    """
    nums = SPECIFIC_NUM_RE.findall(prose_text)
    proper = 0
    for sent in sents:
        toks = re.findall(r"\S+", sent)
        for tok in toks[1:]:          # skip the sentence-initial capital
            w = CAPWORD_RE.match(re.sub(r"^[^A-Za-z]+", "", tok))
            if w:
                text = w.group(0)
                if text[:1].isupper() and not text.isupper():
                    proper += 1
    per_100 = ((len(nums) + proper) / words * 100) if words else 0.0
    report["numbers"] = len(nums)
    report["proper_nouns"] = proper
    report["specifics_per_100"] = round(per_100, 2)
    # A single flag the rewrite procedure can branch on.
    report["specifics_thin"] = bool(words >= 120 and per_100 < 0.5)


# ---------------------------------------------------------------------------
# Modern instruction-tuned signature (v0.6)
#
# The lexical lists catch 2023-era slop ("delve", "tapestry", "in today's
# fast-paced world"). A current model does not write that way; it writes clean,
# well-organized prose whose tells are SYNTACTIC. Four constructions carry most of
# it, and all four are ordinary English in isolation -- a person uses each of them
# -- so every check here is count-gated and fires on the STACKING, never on one
# instance. Each also reports a metric so a writer can see the trend before it
# trips.
# ---------------------------------------------------------------------------

# Wh-cleft ("What matters is X", "All you need is Y"): the sentence delays its
# subject to stage the point. One is rhetoric; four in a page is a cadence.
# Anchored at a clause boundary, not only a sentence boundary. Restricting this
# to sentence-initial "What" missed the commonest form in narrative prose --
# "But standing in the hallway, what she felt was mostly the practical weight"
# -- which is the same construction one clause later. Comma-anchored matches
# require the lowercase form so a mid-sentence proper "What" (a quoted question)
# does not count.
WH_CLEFT_RE = re.compile(
    r"(?:^|(?<=[.!?])\s+|(?<=[:;])\s+)(?:What|All)\s+[^.?!\n]{3,60}?\s(?:is|was|are|were)\b"
    r"|(?<=,)\s+(?:what|all)\s+[^.?!\n]{3,60}?\s(?:is|was|are|were)\b")
# Reversed wh-cleft ("The reason this works is that...", "The thing about X is").
# Anchored to a sentence start, because mid-sentence the same words are ordinary
# ("we fixed the problem and the answer was obvious" is not a cleft), and the gap
# refuses to cross a subordinator so "the problem looks like X when it is Y" no
# longer matches. The second alternative covers the zero-gap form, which is only a
# cleft when it continues with "that" or "not".
_CLEFT_HEADS = (r"thing|reason|problem|point|question|part|issue|trick|catch|"
                r"difference|answer|upshot|kicker|takeaway|challenge|surprise|"
                r"story|truth")
# Clause-start anchors. A reverse cleft can open a sentence or follow a comma or a
# coordinator ("..., and the reason my estimate was low is that ..."). Every
# alternative is fixed-width, which Python's lookbehind requires.
_CLAUSE_START = (r"(?:^|(?<=[.!?;:])\s|(?<=\n)|(?<=,\s)|(?<=\band\s)"
                 r"|(?<=\bbut\s)|(?<=\bso\s))")
REVERSE_CLEFT_RE = re.compile(
    _CLAUSE_START + r"the\s+(?:[\w-]+\s+){0,2}?(?:" + _CLEFT_HEADS + r")\b"
    r"(?:\s+(?!when\b|because\b|if\b|while\b|although\b|unless\b|so\b|but\b"
    r"|and\b|or\b)[\w'-]+){1,5}\s+(?:is|was)\b"
    r"|" + _CLAUSE_START + r"the\s+(?:[\w-]+\s+){0,2}?(?:" + _CLEFT_HEADS +
    r")\s+(?:is|was)\s+(?:that|not)\b",
    re.IGNORECASE)
# It-cleft ("It is the second call that fails").
IT_CLEFT_RE = re.compile(
    r"\bit\s+(?:is|was|isn'?t|wasn'?t)\s+(?:not\s+)?(?:the\s+|a\s+|an\s+)?"
    r"[\w'-]+(?:\s+[\w'-]+){0,3}\s+that\b",
    re.IGNORECASE)


def check_cleft(prose_text, words, threshold, hits, report, lm, min_count=3,
                min_words=120):
    """Cleft-construction stacking: What-X-is-Y / The-reason-is / It-is-X-that.

    A cleft front-loads emphasis by deferring the real subject. Every one of these
    is grammatical and useful, and careful human writers reach for them, so a lone
    cleft means nothing -- the human corpus has them too. What separates
    instruction-tuned prose is the RATE: the construction becomes the default way
    a point gets introduced, several times a page, because it reliably reads as
    thoughtful. Gated on both an absolute count and a per-1k density so a short
    note with two clefts stays clean.
    """
    matches = []
    for rx in (WH_CLEFT_RE, REVERSE_CLEFT_RE, IT_CLEFT_RE):
        matches.extend(rx.finditer(prose_text))
    matches.sort(key=lambda m: m.start())
    # Overlapping alternatives (a reverse cleft inside a wh-cleft) count once.
    deduped = []
    for m in matches:
        if deduped and m.start() < deduped[-1].end():
            continue
        deduped.append(m)
    count = len(deduped)
    per_1k = (count / words * 1000) if words else 0.0
    report["cleft_count"] = count
    report["cleft_per_1k"] = round(per_1k, 1)
    if words < min_words or count < min_count or per_1k <= threshold:
        return
    for m in deduped[:MAX_INSTANCE_HITS]:
        snippet = m.group(0).strip().replace("\n", " ")
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        hits.append(Hit("cleft", lm.line_of(m.start()), snippet,
                        "put the subject first: say the thing instead of staging it"))


# Resultative participial tail: a comma followed by an -ing verb that explains the
# consequence of the main clause. LLM prose appends one to sentence after sentence
# because it manufactures a sense of consequence for free.
#
# Abstract, resultative participles only. "turning", "letting", "leaving" and
# "freeing" were in this list and are ordinary narrative motion (", turning toward
# the door"), which would have made the check fire on fiction for doing the thing
# fiction does. What stays is the consequence-clause vocabulary: verbs that assert
# an effect rather than describe an action.
PARTICIPIAL_TAIL_RE = re.compile(
    r",\s+(?:making|allowing|enabling|ensuring|helping|giving|providing|creating|"
    r"offering|delivering|driving|reducing|improving|increasing|"
    r"reflecting|highlighting|underscoring|demonstrating|showcasing|emphasizing|"
    r"emphasising|reinforcing|meaning|resulting|leading|"
    r"saving|boosting|streamlining|unlocking|empowering|positioning|paving)\s+\w",
    re.IGNORECASE)


def check_participial_tail(prose_text, words, threshold, hits, report, lm,
                           min_count=3, min_words=120):
    """The ", making it easier to..." tail, counted as a rate.

    One resultative participle is fine English. Three or four in a page is the
    single most repeatable syntactic habit of instruction-tuned prose: every
    sentence is given a consequence clause so it sounds like it earned a payoff,
    whether or not one follows from it. Because the tail is grammatically
    subordinate, it also lets a claim slide past unexamined, which is why cutting
    it usually improves the argument and not just the rhythm.
    """
    matches = list(PARTICIPIAL_TAIL_RE.finditer(prose_text))
    count = len(matches)
    per_1k = (count / words * 1000) if words else 0.0
    report["participial_tail_count"] = count
    report["participial_tail_per_1k"] = round(per_1k, 1)
    if words < min_words or count < min_count or per_1k <= threshold:
        return
    for m in matches[:MAX_INSTANCE_HITS]:
        ctx = prose_text[max(0, m.start() - 24):m.end() + 12].replace("\n", " ").strip()
        hits.append(Hit("participial_tail", lm.line_of(m.start()), ctx,
                        "split it: state the consequence as its own sentence, or drop it"))


# Copula ("to be") as the main verb. Counted per sentence, not per document,
# because the tell is a paragraph where nothing happens -- everything simply IS.
COPULA_RE = re.compile(r"\b(?:is|are|was|were|be|been|being|isn'?t|aren'?t|"
                       r"wasn'?t|weren'?t)\b", re.IGNORECASE)


def check_copula_density(sents, words, threshold, hits, report, min_words=150):
    """How much of the prose leans on 'to be' instead of a verb that does work.

    Reported always, flagged only well above the human range. High copula density
    is what makes a passage feel like a definition list read aloud: X is Y, Y is
    important, the result is Z. It correlates with vacuity, which is the tell this
    skill ranks highest and no regex can see directly.
    """
    per_sentence = [len(COPULA_RE.findall(s)) for s in sents]
    count = sum(per_sentence)
    per_1k = (count / words * 1000) if words else 0.0
    report["copula_per_1k"] = round(per_1k, 1)
    report["copula_stacked_sentences"] = sum(1 for n in per_sentence if n >= 3)
    if words >= min_words and per_1k > threshold and count >= 8:
        hits.append(Hit("copula_density", 0,
                        "'to be' as the main verb: %.0f / 1k words (floor %.0f)"
                        % (per_1k, threshold),
                        "give the sentences real verbs; 'X is Y' twice a paragraph reads as a glossary"))


# Two independent clauses welded with ", and" / ", but" where a period belongs.
# The give-away shape is a comma, a coordinator, and a fresh pronoun subject.
SPLICE_RE = re.compile(
    r",\s+(?:and|but|so|yet)\s+(?:it|this|that|they|we|you|he|she|there)\s+"
    r"(?:is|was|are|were|has|have|had|will|can|could|would|does|did|do|"
    r"means?|makes?|becomes?|gives?|takes?|works?|helps?)\b",
    re.IGNORECASE)


def check_comma_splice_chain(prose_text, words, threshold, hits, report, lm,
                             min_count=4, min_words=150):
    """Repeated ', and it is ...' clause-welding.

    Chaining two full clauses with a comma plus a coordinator is correct English
    and every writer does it. Doing it four or five times a page flattens the
    prose into one continuous middle-length line, which is the same defect
    burstiness measures from the other side. Count-gated hard, and low-weighted,
    because the construction itself is innocent.
    """
    matches = list(SPLICE_RE.finditer(prose_text))
    count = len(matches)
    per_1k = (count / words * 1000) if words else 0.0
    report["clause_splice_count"] = count
    report["clause_splice_per_1k"] = round(per_1k, 1)
    if words < min_words or count < min_count or per_1k <= threshold:
        return
    for m in matches[:MAX_INSTANCE_HITS]:
        ctx = prose_text[max(0, m.start() - 20):m.end() + 6].replace("\n", " ").strip()
        hits.append(Hit("clause_splice", lm.line_of(m.start()), ctx,
                        "end the sentence and start a new one; the comma is doing a period's job"))


def _first_words(text, n=2):
    ws = WORD_RE.findall(text.lower())
    return tuple(ws[:n]) if len(ws) >= n else (tuple(ws) if ws else None)


def check_paragraph_openers(code_stripped, hits, report, min_paras=5,
                            repeat_ratio=0.4):
    """Paragraphs that all open with the same PHRASE.

    `uniform_openers` measures sentences and misses this: a draft can vary inside
    a paragraph and still start every paragraph the same way. Paragraph openings
    are what a reader skims, so repetition there is disproportionately visible.

    Keyed on the first TWO words, not the first one. "The" is the most common word
    in English and three paragraphs starting with it says nothing -- that version
    of the check flagged a human business proposal whose paragraphs opened "The
    math:", "The real win", "The warehouse". Two words separate a shared article
    from a shared opening move.
    """
    paras = _prose_paragraph_texts(code_stripped)
    openers = [w for w in (_first_words(p, 2) for p in paras) if w and len(w) == 2]
    report["paragraph_count"] = len(paras)
    if len(openers) < min_paras:
        report["paragraph_opener_repeat"] = None
        return
    phrase, count = Counter(openers).most_common(1)[0]
    ratio = count / len(openers)
    report["paragraph_opener_repeat"] = round(ratio, 2)
    if ratio >= repeat_ratio and count >= 3:
        hits.append(Hit("paragraph_openers", 0,
                        '%d of %d paragraphs open with "%s"'
                        % (count, len(openers), " ".join(phrase)),
                        "vary how paragraphs begin; readers skim the first words of each"))


def check_bullet_openers(code_stripped, hits, report, min_items=4,
                         repeat_ratio=0.6):
    """List items that all open with the same word or the same part of speech.

    Templated bullets ("Improve...", "Reduce...", "Increase...") are the list-level
    version of parallel structure: the shape is filled in rather than written. A
    deliberately parallel list is a real technique, so this needs a clear majority
    and at least four items before it says anything.
    """
    items = []
    for ln in code_stripped.split("\n"):
        if LIST_MARKER_RE.match(ln):
            body = strip_inline_markup(LIST_MARKER_RE.sub("", ln)).strip()
            if WORD_RE.findall(body):
                items.append(body)
    if len(items) < min_items:
        report["bullet_opener_repeat"] = None
        return
    firsts = [WORD_RE.findall(i.lower())[0] for i in items]
    word, count = Counter(firsts).most_common(1)[0]
    ratio = count / len(firsts)
    report["bullet_opener_repeat"] = round(ratio, 2)
    gerunds = sum(1 for f in firsts if f.endswith("ing") and len(f) > 5)
    if ratio >= repeat_ratio and count >= 3:
        hits.append(Hit("bullet_openers", 0,
                        '%d of %d list items open with "%s"' % (count, len(firsts), word),
                        "vary the item openings, or fold the list into a sentence"))
    elif len(firsts) >= min_items and gerunds / len(firsts) >= 0.75:
        hits.append(Hit("bullet_openers", 0,
                        "%d of %d list items open with an -ing verb"
                        % (gerunds, len(firsts)),
                        "a list of gerunds reads as generated; use varied phrasing"))


# Nominal chain: "the reduction of the complexity of the interface". Three or more
# "of the" links in one sentence is a noun pile-up rather than a sentence.
OF_CHAIN_RE = re.compile(r"\b(?:of|for|in|to)\s+the\s+[\w-]+\s+"
                         r"(?:of|for|in)\s+the\s+[\w-]+\s+(?:of|for|in)\s+the\b",
                         re.IGNORECASE)


def check_noun_chains(prose_text, hits, report, lm, min_count=2):
    """Stacked prepositional-noun chains ('the X of the Y of the Z')."""
    matches = list(OF_CHAIN_RE.finditer(prose_text))
    report["noun_chains"] = len(matches)
    if len(matches) < min_count:
        return
    for m in matches[:MAX_INSTANCE_HITS]:
        hits.append(Hit("noun_chain", lm.line_of(m.start()),
                        m.group(0).replace("\n", " "),
                        "unstack the nouns: make one of them the verb"))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Paste artifacts: residue a model left in its own output.
#
# Every string here is a citation marker, tool-call wrapper, or unfilled template
# slot that appears only because text came out of a chat product and went into a
# document unread. Unlike every other check in this file, these are not stylistic
# tendencies with a human range -- no writer types "oaicite" -- so one instance is
# a finding rather than a whisper, and the category carries the weight to say so.
# Catalogued by Wikipedia's WikiProject AI Cleanup across ChatGPT, Gemini, Grok,
# DeepSeek and Perplexity output; see references/competitive-landscape.md.
LLM_ARTIFACT_RES = (
    (re.compile(r"\b(?:oaicite|contentReference|attributableIndex|citeturn\w*)\b"),
     "ChatGPT citation residue: delete it"),
    (re.compile(r"\bturn\d+(?:search|news|view|image)\d+\b"),
     "ChatGPT tool-call residue: delete it"),
    (re.compile(r"\[cite:\s*\d+\s*\]|\[span_\d+\]\(start_span\)|\(end_span\)"),
     "Gemini citation residue: delete it"),
    (re.compile(r"\bgrok_(?:card|render_citation_card_json)\b"),
     "Grok render residue: delete it"),
    (re.compile(r"\b(?:ppl-ai-file-upload|attached_file:)"),
     "Perplexity upload residue: delete it"),
    (re.compile(r":::writing\b"),
     "model block marker: delete it"),
    (re.compile(r"utm_source=(?:chatgpt|openai|perplexity)[\w.]*", re.I),
     "tracking parameter added by the chat product: strip it from the URL"),
    (re.compile(r"【[^】]{0,80}】"),
     "lenticular-bracket citation residue: delete it"),
    # Template slots only. A bare "[X]" or "[X, Y]" is mathematical and
    # generic-parameter notation in real technical writing -- the Python stdlib
    # docs in eval/human_baseline.py carry eleven of them -- so the pattern
    # requires a form no equation produces: an explicit verb, a possessive, or a
    # two-word slot name.
    (re.compile(r"\[(?:INSERT[\w ]*|Insert\s+\w+|Your\s+\w+"
                r"|(?:Company|Client|Product|Customer|Recipient|Sender|Full)\s+Name"
                r"|Name\s+of\s+\w+|PLACEHOLDER\w*)[^\]\n]{0,40}\]"),
     "unfilled template placeholder: fill it or cut the sentence"),
)

# Placeholders this skill deliberately emits (anti-hallucination protocol step 5)
# are the author's to resolve, not residue to flag.
_SANCTIONED_PLACEHOLDER = re.compile(
    r"\[(?:SOURCE NEEDED|VERIFY|FIGURE\?|TODO|CITATION NEEDED)\]", re.I)


_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def check_llm_artifact(text, hits, lm):
    """Flag chat-product residue and unfilled placeholders. Precision check.

    Runs on the code-stripped source rather than the reduced metric prose,
    because two of these live inside a URL (`utm_source=chatgpt.com`) and the
    metric text drops link targets. Backticked spans are skipped by hand instead,
    so a document that *names* these strings -- this repo's own reference pages do
    -- is not flagged for documenting them.
    """
    skip = [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(text)]
    for rx, suggestion in LLM_ARTIFACT_RES:
        for m in rx.finditer(text):
            frag = m.group(0)
            if _SANCTIONED_PLACEHOLDER.fullmatch(frag):
                continue
            if any(a <= m.start() < b for a, b in skip):
                continue
            hits.append(_span_hit("llm_artifact", lm, m, frag.strip(), suggestion))
            if len(hits) > MAX_INSTANCE_HITS * 4:
                return


# Copula avoidance: the elaborate substitute for "is". Present-tense third person
# only, because "represented" and "featured" in a past-tense narrative are doing
# ordinary work. "Serves as" and its family are the constructions the Wikipedia
# AI-Cleanup corpus found rising as "is"/"are" fell.
COPULA_AVOID_RE = re.compile(
    r"\b(?:serves?|stands?|functions?|operates?|acts?)\s+as\b"
    r"|\b(?:represents|embodies|exemplifies|encompasses|constitutes)\b"
    r"|\b(?:boasts|features|offers|maintains|possesses)\s+(?:a|an|the|its|several|numerous|\d)",
    re.IGNORECASE)


def check_copula_avoidance(prose_text, words, threshold, hits, report, lm,
                           min_count=3, min_words=150):
    """The mirror of copula_density: reaching past 'is' on every definition.

    One "serves as" is unremarkable. A document where nothing is allowed to
    simply BE anything -- where each subject instead stands as, represents,
    embodies or boasts -- has the register of a press release written to fill a
    length, and it is the construction that replaced plain copulas in
    post-2022 encyclopedic text. Count- and density-gated like every other
    syntactic check here, because each phrase on its own is fine English.
    """
    matches = list(COPULA_AVOID_RE.finditer(prose_text))
    count = len(matches)
    per_1k = (count / words * 1000) if words else 0.0
    report["copula_avoidance_count"] = count
    report["copula_avoidance_per_1k"] = round(per_1k, 1)
    if words < min_words or count < min_count or per_1k <= threshold:
        return
    for m in matches[:MAX_INSTANCE_HITS]:
        hits.append(Hit("copula_avoidance", lm.line_of(m.start()), m.group(0).strip(),
                        "use the plain copula, or a verb that does real work"))


_HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$", re.M)
_LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


def check_heading_structure(code_stripped, hits, report, lm):
    """Markdown scaffolding a person does not produce by hand.

    Four distinct faults, all of them artifacts of a model emitting an outline
    rather than a writer building a document: heading levels that skip a rung
    (## straight to ####), more than one H1 in a single file, a heading whose
    entire body is the next heading, and a heading that runs straight into a
    bullet list with no sentence in between. Each is individually minor; the
    reason to score them is that a document with several has been assembled, not
    written. Catalogued by Wikipedia's AI-Cleanup project as markup signs.
    """
    headings = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING_RE.finditer(code_stripped)]
    report["heading_count"] = len(headings)
    if len(headings) < 2:
        return
    h1s = [h for h in headings if h[1] == 1]
    if len(h1s) > 1:
        hits.append(Hit("heading_structure", lm.line_of(h1s[1][0]),
                        "%d level-1 headings in one document" % len(h1s),
                        "one H1 per document; demote the rest"))
    prev_level = headings[0][1]
    for start, level, title in headings[1:]:
        if level > prev_level + 1:
            hits.append(Hit("heading_structure", lm.line_of(start),
                            "heading level jumps %d -> %d at %r" % (prev_level, level, title[:40]),
                            "use the next level down; do not skip a rung"))
        prev_level = level
    lines = code_stripped.split("\n")
    heading_lines = {}
    for m in _HEADING_RE.finditer(code_stripped):
        heading_lines[code_stripped.count("\n", 0, m.start())] = m.group(2)
    for idx, title in sorted(heading_lines.items()):
        nxt = None
        for j in range(idx + 1, min(idx + 4, len(lines))):
            if lines[j].strip():
                nxt = (j, lines[j])
                break
        if not nxt:
            continue
        j, body = nxt
        if j in heading_lines:
            hits.append(Hit("heading_structure", idx + 1,
                            "heading %r contains only another heading" % title[:40],
                            "merge the two, or write the section"))
        elif _LIST_LINE_RE.match(body):
            hits.append(Hit("heading_structure", idx + 1,
                            "heading %r runs straight into a list" % title[:40],
                            "put a sentence between the heading and the list"))


_CURLY_RE = re.compile(r"[‘’“”]")
_STRAIGHT_QUOTE_RE = re.compile(r"(?<![\w=])[\"'](?=\w)|(?<=\w)[\"'](?![\w=])")


def check_quote_style(prose_text, hits, report, lm):
    """Straight and curly quotes mixed in one document.

    Either convention is fine held consistently, and a word processor produces
    curly quotes throughout. A document carrying BOTH usually has a seam in it:
    text that came out of a chat product (which emits curly) pasted beside text
    someone typed (straight). Same logic as the dialect and heading-case checks
    -- the tell is the inconsistency, not either style.
    """
    curly = list(_CURLY_RE.finditer(prose_text))
    straight = list(_STRAIGHT_QUOTE_RE.finditer(prose_text))
    report["curly_quotes"] = len(curly)
    report["straight_quotes"] = len(straight)
    if not curly or not straight:
        return
    total = len(curly) + len(straight)
    minority = curly if len(curly) <= len(straight) else straight
    # A seam is a lopsided mix in a document with enough quotes to judge. Two of
    # each is a document that quotes code beside quoted speech, not a paste.
    if total < 6 or len(minority) * 4 > total:
        return
    for m in minority[:6]:
        hits.append(Hit("quote_style", lm.line_of(m.start()), m.group(0),
                        "hold one quote convention through the document"))


CONTRACTION_RE = re.compile(r"\b\w+['’](?:t|s|re|ve|ll|d|m)\b", re.IGNORECASE)


def report_contraction_rate(prose_text, words, report):
    """Reported, never scored. See references/competitive-landscape.md.

    Contraction rate is the single most discriminative surface feature in the
    published humanizer literature (AI ~0.00 per chunk against ~0.17 for human)
    and it is measured here for the writer's benefit: marketing copy with zero
    contractions reads stiff, and that is worth knowing. It is deliberately NOT
    a scored category. On this repo's own corpus a contraction-absence check
    gated to the conversational registers fires on four of the ten ESL/formal
    files -- careful non-native writers who use no contractions and are human.
    Scoring it would reproduce exactly the bias Liang et al. (2023) measured in
    commercial detectors, in a tool whose whole argument is that those detectors
    are wrong about that population.
    """
    count = len(CONTRACTION_RE.findall(prose_text))
    report["contractions"] = count
    report["contractions_per_1k"] = round((count / words * 1000) if words else 0.0, 1)


__all__ = [
    'CITATION_NEAR_RE',
    'MAX_INSTANCE_HITS',
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
    '_distinct_by_text',
    '_TRIAD_STOP_MEMBERS',
    'RULE_OF_THREE_RE',
    'NOUN_TRIAD_RE',
    '_CLAUSE_PRONOUNS',
    '_CLAUSE_VERBS',
    '_MEMBER_BAD_START',
    '_is_noun_phrase',
    'check_rule_of_three',
    'COMMON_OPENERS',
    'COMMON_OPENER_RATIO',
    'COMMON_OPENER_MIN',
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
    'DASH_STYLE_INSTANCE_MAX',
    '_dash_findings',
    'check_dash_style',
    'DOUBLED_WORD_RE',
    'DOUBLE_OK',
    'check_doubled_words',
    'SPACE_BEFORE_PUNCT_RE',
    'MULTI_PUNCT_RE',
    'check_mechanics',
    '_prose_paragraph_texts',
    'CONCLUSION_OPENER_RE',
    'check_five_paragraph_shape',
    'HYPOPHORA_ANSWER_RE',
    'check_hypophora',
    'SUPERLATIVE_RE',
    'check_superlative_creep',
    'SUBJECT_OPENERS',
    'check_svo_monotony',
    'DEFAULT_NAME_RE',
    'DR_TITLE_RE',
    'check_name_selection',
    'COSTUME_SLANG_RE',
    'SENTENCE_START_RE',
    'check_punctuation_substitution',
    'check_over_correction',
    'BOLD_SPAN_RE',
    'SUMMARY_HEADING_RE',
    'check_assistant_shape',
    'check_sentence_shape',
    'SPECIFIC_NUM_RE',
    'CAPWORD_RE',
    'report_specificity',
    'WH_CLEFT_RE',
    '_CLEFT_HEADS',
    '_CLAUSE_START',
    'REVERSE_CLEFT_RE',
    'IT_CLEFT_RE',
    'check_cleft',
    'PARTICIPIAL_TAIL_RE',
    'check_participial_tail',
    'LLM_ARTIFACT_RES',
    'check_llm_artifact',
    'COPULA_AVOID_RE',
    'check_copula_avoidance',
    'check_heading_structure',
    'check_quote_style',
    'CONTRACTION_RE',
    'report_contraction_rate',
    'COPULA_RE',
    'check_copula_density',
    'SPLICE_RE',
    'check_comma_splice_chain',
    '_first_words',
    'check_paragraph_openers',
    'check_bullet_openers',
    'OF_CHAIN_RE',
    'check_noun_chains',
]
