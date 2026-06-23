#!/usr/bin/env python3
"""Detect surface features that correlate with AI-written prose.

This is the deterministic *floor* of the human-voice skill: cheap, regex-able
tells (filler diction, em-dash overuse, bold-bullet listicles, rule-of-three,
low burstiness, n-gram repetition, low lexical diversity). It does NOT compute
perplexity or log-prob curvature the way GPTZero or DetectGPT do — it catches
the surface features that *correlate* with what those detectors measure. No
detector is ground truth; the real test is a skeptical human read.

Pure standard library. No third-party dependencies. Designed to never crash on
hostile input: bad encodings, binary files, malformed pattern files, and
adversarial Markdown all degrade gracefully rather than raising.

Usage:
    detect_ai_prose.py <file>
    detect_ai_prose.py -                      # read stdin
    detect_ai_prose.py --register marketing <file>
    detect_ai_prose.py --dialect american <file>
    detect_ai_prose.py --json <file>
"""

import argparse
import bisect
import functools
import json
import math
import os
import re
import sys
from collections import Counter

PATTERNS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "ai_prose_patterns.json")

REGISTERS = ["technical", "business", "marketing", "academic", "casual", "creative",
             "email", "release_notes", "ux_microcopy", "tutorial"]

# Hard cap so a pathological input can't hang the process. ~5M chars is far
# larger than any real document and still completes in well under a second.
MAX_CHARS = 5_000_000

# Category weights feed the single "floor" score (tells per 1000 words).
# Structure and substance-adjacent tells weigh more than lone diction hits.
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
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols, pictographs, emoticons, transport, supplemental
    "\U00002700-\U000027BF"   # dingbats (✂ ✅ ✨ ❌ ❤)
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U0000FE0F"              # emoji variation selector
    "]"
)


def warn(msg):
    sys.stderr.write("warning: %s\n" % msg)


class Hit:
    __slots__ = ("category", "line", "text", "suggestion")

    def __init__(self, category, line, text, suggestion=None):
        self.category = category
        self.line = line
        self.text = text
        self.suggestion = suggestion

    def as_dict(self):
        d = {"category": self.category, "line": self.line, "text": self.text}
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


# ---------------------------------------------------------------------------
# Loading / input (never raises on bad data; exits 2 only when truly unusable)
# ---------------------------------------------------------------------------

def load_patterns(path=PATTERNS_FILE):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        sys.stderr.write(
            "error: pattern file not found: %s\n"
            "The linter cannot run without it. Fall back to pure judgment "
            "using references/ai-tells.md.\n" % path)
        sys.exit(2)
    except IsADirectoryError:
        sys.stderr.write("error: pattern path is a directory, not a file: %s\n" % path)
        sys.exit(2)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        sys.stderr.write("error: could not parse pattern file %s: %s\n" % (path, exc))
        sys.exit(2)
    if not isinstance(data, dict):
        sys.stderr.write("error: pattern file %s must contain a JSON object\n" % path)
        sys.exit(2)
    return data


def read_input(target):
    if target == "-":
        try:
            raw = sys.stdin.buffer.read()
        except (AttributeError, OSError):
            raw = sys.stdin.read().encode("utf-8", "replace")
        text = raw.decode("utf-8", "replace")
    else:
        if os.path.isdir(target):
            sys.stderr.write("error: input is a directory, not a file: %s\n" % target)
            sys.exit(2)
        try:
            with open(target, "rb") as fh:
                raw = fh.read()
        except (FileNotFoundError, IsADirectoryError, PermissionError, OSError) as exc:
            sys.stderr.write("error: could not read input %s: %s\n" % (target, exc))
            sys.exit(2)
        text = raw.decode("utf-8", "replace")
    if len(text) > MAX_CHARS:
        warn("input truncated to %d chars (was %d)" % (MAX_CHARS, len(text)))
        text = text[:MAX_CHARS]
    # Normalize line endings and strip the BOM so offsets and line numbers are stable.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("﻿"):
        text = text[1:]
    # Drop NULs and other control chars (except tab/newline) that creep in from
    # binary files; they break word/sentence heuristics and terminal output.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text


def blank_frontmatter(text):
    """Blank a leading YAML/TOML front-matter block (keeping line geometry).

    Front-matter delimiters (`---`) are otherwise counted as horizontal rules
    and the key/value lines are scored as prose.
    """
    if not (text.startswith("---\n") or text.startswith("+++\n")):
        return text
    fence = text[:3]
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i].strip() in (fence, "---", "..."):
            for j in range(i + 1):
                lines[j] = ""
            return "\n".join(lines)
    return text  # no closing fence: treat as ordinary content


def as_phrase_list(value):
    """Coerce a pattern value into a list of (phrase, suggestion) pairs."""
    pairs = []
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = ((v, None) for v in value)
    elif isinstance(value, str):
        items = ((value, None),)
    else:
        return pairs
    for phrase, suggestion in items:
        if not isinstance(phrase, str):
            continue
        phrase = phrase.strip()
        if not phrase:
            continue
        # Forward-compatible rich form: value may be {"suggestion": "..."}.
        if isinstance(suggestion, dict):
            suggestion = suggestion.get("suggestion")
        sug = suggestion if isinstance(suggestion, str) and suggestion.strip() else None
        pairs.append((phrase, sug))
    return pairs


def safe_float(d, key, default):
    try:
        return float(d.get(key, default))
    except (TypeError, ValueError):
        return default


def safe_int_list(d, key, default):
    val = d.get(key, default)
    if not isinstance(val, list):
        return list(default)
    out = []
    for n in val:
        try:
            out.append(int(n))
        except (TypeError, ValueError):
            continue
    return out or list(default)


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

# Fenced code: ``` or ~~~ (3+), with optional info string, possibly unterminated.
CODE_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?(?:\n([\s\S]*?))?(?:\n[ \t]*\1[ \t]*$|\Z)",
                           re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])["\')\]”’]?\s+(?=[A-Z0-9"\'(“])')

ABBREVIATIONS = {
    "e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "prof", "sr", "jr",
    "st", "inc", "ltd", "co", "corp", "fig", "al", "approx", "dept", "est",
    "u.s", "u.k", "ph.d", "no", "vol", "ch", "pp", "ca", "cf",
}

# One alternation for all abbreviations (longest first), built once. Replaces a
# per-abbreviation re.sub loop with a single pass over the text.
ABBREV_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(a) for a in sorted(ABBREVIATIONS, key=len, reverse=True))
    + r")\.", re.IGNORECASE)

LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
BARE_URL_RE = re.compile(r"(?:https?|ftp)://\S+|www\.\S+")
FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]]+\]")
HTML_TAG_RE = re.compile(r"<[^>\n]+>")
EMPHASIS_RE = re.compile(r"(\*\*\*|\*\*|\*|___|__|_|~~)")
HEADING_LINE_RE = re.compile(r"^[ \t]*#{1,6}[ \t]+")
SETEXT_RE = re.compile(r"^[ \t]*(=+|-+)[ \t]*$")
LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")
BLOCKQUOTE_RE = re.compile(r"^[ \t]*>+[ \t]?")
TABLE_ROW_RE = re.compile(r"^[ \t]*\|.*\|?[ \t]*$")
TABLE_SEP_RE = re.compile(r"^[ \t]*\|?[\s:|-]*[-:][\s:|-]*\|?[ \t]*$")
SECTION_RULE_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$")
SECTION_RULE_MULTILINE_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.MULTILINE)


def strip_code(text):
    """Replace fenced and inline code with newline-preserving blanks.

    Keeps the character/line geometry so reported line numbers still line up
    with the original file.
    """
    def fence_sub(m):
        return "\n" * m.group(0).count("\n")
    text = CODE_FENCE_RE.sub(fence_sub, text)
    text = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)
    return text


def line_of(text, index):
    return text.count("\n", 0, index) + 1


class LineMap:
    """Precomputed newline offsets for O(log n) line lookups.

    `line_of` is called once per hit; on a large document with many hits the
    naive str.count from offset 0 is quadratic. Build one of these per text and
    bisect each index instead.
    """

    __slots__ = ("offsets",)

    def __init__(self, text):
        push = self.offsets = []
        start = 0
        while True:
            nl = text.find("\n", start)
            if nl < 0:
                break
            push.append(nl)
            start = nl + 1

    def line_of(self, index):
        return bisect.bisect_left(self.offsets, index) + 1


def strip_inline_markup(line):
    line = LINK_RE.sub(r"\1", line)        # links/images -> anchor text only
    line = BARE_URL_RE.sub(" ", line)      # drop bare URLs
    line = FOOTNOTE_REF_RE.sub(" ", line)
    line = HTML_TAG_RE.sub(" ", line)
    line = EMPHASIS_RE.sub("", line)       # drop emphasis markers, keep words
    return line


def prose_for_metrics(code_stripped):
    """Markdown-normalized text for sentence/burstiness/diversity metrics.

    Drops headings, table rows, rules, and footnote definitions; strips list,
    blockquote, and inline markup; terminates list items so they count as their
    own sentence; and joins soft-wrapped paragraph lines.
    """
    out_paras = []
    cur = []
    for raw in code_stripped.split("\n"):
        line = raw
        if (not line.strip() or HEADING_LINE_RE.match(line) or SETEXT_RE.match(line)
                or SECTION_RULE_RE.match(line) or TABLE_SEP_RE.match(line)
                or TABLE_ROW_RE.match(line) or re.match(r"^[ \t]*\[\^[^\]]+\]:", line)):
            if cur:
                out_paras.append(" ".join(cur))
                cur = []
            continue
        is_item = bool(LIST_MARKER_RE.match(line))
        line = BLOCKQUOTE_RE.sub("", line)
        line = LIST_MARKER_RE.sub("", line)
        line = strip_inline_markup(line).strip()
        if not line:
            continue
        if is_item:
            if cur:
                out_paras.append(" ".join(cur))
                cur = []
            if line[-1] not in ".!?":
                line += "."
            out_paras.append(line)
        else:
            cur.append(line)
    if cur:
        out_paras.append(" ".join(cur))
    return "\n".join(out_paras)


def prose_for_adjacency(text):
    """Text for adjacency checks (dashes, doubled words, punctuation spacing).

    Unlike `strip_code`, which blanks code with equal-length spaces to preserve
    geometry, this replaces each stripped span (inline code, URLs, footnotes)
    with a single placeholder word. That keeps a stripped token from leaving a
    phantom gap — `` of `--flag`, `` must read as `of x,` (no space before the
    comma), not `of      ,`. Newlines are preserved so line numbers still line
    up; only within-line columns shift.
    """
    text = CODE_FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    out = []
    for raw in text.split("\n"):
        line = HEADING_LINE_RE.sub("", raw)
        line = BLOCKQUOTE_RE.sub("", line)
        line = LIST_MARKER_RE.sub("", line)
        line = INLINE_CODE_RE.sub("x", line)
        line = LINK_RE.sub(r"\1", line)
        line = BARE_URL_RE.sub("x", line)
        line = FOOTNOTE_REF_RE.sub("x", line)
        line = HTML_TAG_RE.sub("", line)
        line = EMPHASIS_RE.sub("", line)
        out.append(line)
    return "\n".join(out)


def sentences(prose):
    if not prose.strip():
        return []
    protected = re.sub(r"(\d)\.(\d)", lambda m: m.group(1) + "\x00" + m.group(2), prose)
    protected = re.sub(r"\.\.\.+", lambda m: "\x00" * len(m.group(0)), protected)
    protected = re.sub(r"\b(?:[A-Za-z]\.){2,}",
                       lambda m: m.group(0).replace(".", "\x00"), protected)
    # Protect abbreviation-final periods in one pass (e.g. -> e.g\x00).
    protected = ABBREV_RE.sub(lambda m: m.group(0)[:-1] + "\x00", protected)
    parts = SENTENCE_SPLIT_RE.split(protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _phrase_regex(phrase):
    body = re.escape(phrase).replace(r"\ ", r"\s+")
    # Use boundaries only where the edge is a word char, so phrases starting or
    # ending in punctuation still match.
    left = r"\b" if phrase[:1].isalnum() else ""
    right = r"\b" if phrase[-1:].isalnum() else ""
    try:
        return re.compile(left + body + right, re.IGNORECASE)
    except re.error:
        return None


@functools.lru_cache(maxsize=None)
def _word_regex(word):
    """Cached \\bword\\b matcher (case-insensitive) for dialect checks."""
    try:
        return re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    except re.error:
        return None


def _overlaps(start, end, spans):
    """True if [start, end) overlaps any (s, e) in spans (small list, linear)."""
    for s, e in spans:
        if start < e and s < end:
            return True
    return False


def build_protected_spans(text, exceptions):
    """Character ranges where a lexical word is a known legitimate use.

    Driven by the `context_exceptions` patterns key — e.g. "test harness" or
    "vital signs" protect "harness"/"vital" from being flagged as filler. These
    are whole-phrase matches; any lexical hit landing inside one is suppressed.
    """
    spans = []
    for phrase in exceptions or ():
        if not isinstance(phrase, str) or not phrase.strip():
            continue
        rx = _phrase_regex(phrase.strip())
        if rx is None:
            continue
        for m in rx.finditer(text):
            spans.append((m.start(), m.end()))
    return spans


# A citation/source token appearing just after a phrase ("studies suggest [1]",
# "studies show (Smith 2024)") means the attribution is NOT vague.
CITATION_NEAR_RE = re.compile(
    r"\[\^?\d|\[\d+\]|\(\s*[A-Z][\w.&-]+,?\s*(?:et al\.?,?\s*)?\d{4}|\(\d{4}\)|https?://|doi:")


def _line_bounds(text, idx):
    start = text.rfind("\n", 0, idx) + 1
    end = text.find("\n", idx)
    return start, (end if end != -1 else len(text))


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
            hits.append(Hit(category, lm.line_of(m.start()), m.group(0),
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
            hits.append(Hit("antithesis", lm.line_of(m.start()),
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
            hits.append(Hit(category, lm.line_of(m.start()),
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
            hits.append(Hit("bold_bullets", lm.line_of(m.start()),
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
        hits.append(Hit("formatting", lm.line_of(m.start()),
                        "emoji (%d)" % len(emojis), "remove decorative emoji"))
    rules = list(SECTION_RULE_MULTILINE_RE.finditer(text))
    report["section_rules"] = len(rules)
    if len(rules) > max_rules:
        for m in rules[max_rules:max_rules + 6]:
            hits.append(Hit("formatting", lm.line_of(m.start()),
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
            hits.append(Hit("dialect", lm.line_of(m.start()), m.group(0), sug))


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

def muted_categories(register, patterns):
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


def analyze(text, register, dialect, patterns):
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

    check_em_dash(metric_prose, word_count, safe_float(th, "em_dash_per_1k_words", 6.0), hits, report, lm_metric)
    check_bold_bullets(text, safe_float(th, "bold_bullet_ratio", 0.5), hits, report, lm_raw)
    check_rule_of_three(metric_prose, hits, lm_metric)
    check_uniform_openers(sents, safe_float(th, "uniform_opener_ratio", 0.3), hits, report)
    check_wh_openers(sents, safe_float(th, "wh_opener_ratio", 0.30),
                     int(safe_float(th, "wh_opener_run", 3)), hits, report)
    check_formatting(text, safe_float(th, "section_rule_max", 2), hits, report, lm_raw)
    check_burstiness(sents, safe_float(th, "burstiness_cov_floor", 0.45), hits, report)
    check_lexical_diversity(metric_prose, safe_float(th, "ttr_floor", 0.40), hits, report)
    check_ngram_repetition(metric_prose, safe_int_list(th, "ngram_sizes", [2, 3]),
                           int(safe_float(th, "ngram_min_count", 3)), hits)
    check_heading_case(text, hits, lm_raw)

    # Density / structural checks (Phase 2). Conservative thresholds keep clean
    # human prose clean; several are muted by register (see register_mutes).
    check_colon_summary(metric_prose, hits, report, lm_metric)
    check_passive_voice(metric_prose, word_count, safe_float(th, "passive_per_1k", 45.0), hits, report)
    check_adverbs(tokens, word_count, safe_float(th, "adverb_per_1k", 55.0), hits, report)
    check_nominalizations(metric_prose, word_count, safe_float(th, "nominalization_per_1k", 60.0), hits, report)
    check_rhetorical(sents, word_count, safe_float(th, "rhetorical_per_1k", 18.0), hits, report)
    check_paragraph_uniformity(code_stripped, safe_float(th, "paragraph_cov_floor", 0.30), hits, report)
    check_list_uniformity(code_stripped, safe_float(th, "list_item_cov_floor", 0.22), hits, report)
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
    report["word_count"] = word_count
    report["sentence_count"] = len(sents)
    return hits, report, word_count


# Default verdict bands (upper-exclusive): score < 5 reads clean, < 15 worth a
# look, otherwise a strong floor signal. The top band is open-ended (large
# threshold). Overridable via patterns["score_bands"].
DEFAULT_BANDS = (("clean", 5.0), ("watch", 15.0), ("strong-tell", 1e6))


def resolve_weights(patterns):
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


def score(hits, word_count, weights=None):
    if weights is None:
        weights = CATEGORY_WEIGHTS
    weighted = sum(weights.get(h.category, 1.0) for h in hits)
    per_1k = (weighted / word_count * 1000) if word_count else 0.0
    return round(per_1k, 1)


def resolve_bands(patterns):
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


def verdict_band(floor_score, bands):
    """Map a floor score to its band label (the highest band is open-ended)."""
    for label, upper in bands:
        if floor_score < upper:
            return label
    return bands[-1][0] if bands else "n/a"


def render_text(target, register, dialect, hits, report, word_count, floor_score,
                band="n/a", max_examples=6):
    by_cat = {}
    for h in hits:
        by_cat.setdefault(h.category, []).append(h)

    out = []
    out.append("AI-prose floor report — %s" % target)
    out.append("register: %s%s   words: %d" % (
        register, ("   dialect: " + dialect) if dialect else "", word_count))
    out.append("score: %.1f weighted tells / 1k words  [%s]  (lower is better; a FLOOR, not proof)"
               % (floor_score, band))
    bcov = report.get("burstiness_cov")
    out.append("burstiness CoV: %s   TTR: %s   em-dash/1k: %s   mean sentence: %s words" % (
        bcov if bcov is not None else "n/a",
        report.get("ttr", "n/a"),
        report.get("em_dash_per_1k", "n/a"),
        report.get("mean_sentence_len", "n/a")))
    out.append("")
    if word_count == 0:
        out.append("No prose found (empty, code-only, or non-text input). Nothing to score.")
        return "\n".join(out)
    if not hits:
        out.append("No surface tells flagged. Now do the skeptical human read — the")
        out.append("linter cannot see vacuity, weak stance, or fabrication.")
        return "\n".join(out)

    out.append("Tells by category (%d total):" % len(hits))
    for cat in sorted(by_cat, key=lambda c: (-len(by_cat[c]), c)):
        items = by_cat[cat]
        out.append("  %-20s %d" % (cat, len(items)))
        for h in items[:max_examples]:
            loc = ("L%d: " % h.line) if h.line else ""
            sug = ("  -> %s" % h.suggestion) if h.suggestion else ""
            out.append("      %s%s%s" % (loc, h.text, sug))
        if len(items) > max_examples:
            out.append("      ... and %d more" % (len(items) - max_examples))
    hotspots = line_hotspots(hits)
    if len(hotspots) > 1 and hotspots[0][1] > 1:
        spots = ", ".join("L%d (%d)" % (ln, n) for ln, n in hotspots if n > 1)
        if spots:
            out.append("")
            out.append("Hotspot lines: %s" % spots)
    out.append("")
    out.append("Floor only. The linter cannot see vacuity, weak stance, terminology")
    out.append("drift, or fabrication. A skeptical human read is the real test.")
    return "\n".join(out)


def severity_of(category, weights):
    w = weights.get(category, 1.0)
    if w >= 2.0:
        return "high"
    if w >= 1.5:
        return "medium"
    return "low"


def line_hotspots(hits, top=5):
    counts = Counter(h.line for h in hits if h.line)
    return counts.most_common(top)


def lint(text, register="technical", dialect=None, patterns=None):
    """Library entry point: analyze text and return the result dict.

    Mirrors the --json payload so callers can import this module instead of
    shelling out to the CLI.
    """
    if patterns is None:
        patterns = load_patterns()
    hits, report, words = analyze(text, register, dialect, patterns)
    weights = resolve_weights(patterns)
    floor = score(hits, words, weights)
    return {
        "schema_version": 1,
        "register": register,
        "dialect": dialect,
        "words": words,
        "score": floor,
        "verdict": verdict_band(floor, resolve_bands(patterns)),
        "metrics": report,
        "hits": [dict(h.as_dict(), severity=severity_of(h.category, weights)) for h in hits],
    }


def _match_case(original, replacement):
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


# Only 1:1 lexical swaps with a concrete replacement are auto-fixable. "cut"
# suggestions and structural tells need human judgment and are never auto-applied.
SAFE_FIX_KEYS = ("filler", "jargon", "redundancy")

# Registers where decorative emoji can be legitimate (casual/social copy), so the
# autofixer leaves them alone; everywhere else it strips them.
EMOJI_KEEP_REGISTERS = frozenset({"creative", "casual"})
# The em-dash is the creative writer's native tool, so dash normalization is
# skipped there; in every other register the autofixer replaces it.
DASH_KEEP_REGISTERS = frozenset({"creative"})

# An emoji run plus the inline whitespace hugging it, collapsed in one edit so
# stripping never leaves a doubled or dangling space. (`[ \t]` only, never a
# newline, so line geometry is preserved.)
AUTOFIX_EMOJI_RE = re.compile(r"[ \t]*" + EMOJI_RE.pattern + r"+[ \t]*")

# Dash-as-pause constructs the autofixer rewrites to a comma. Each alternative
# keeps the surrounding inline spaces in the match so they collapse cleanly:
#   em-dash (tight or spaced), en-dash (range guard applied below),
#   ASCII `--`, and a spaced hyphen between lowercase words.
AUTOFIX_DASH_RE = re.compile(
    r"[ \t]*—[ \t]*|[ \t]*–[ \t]*|(?<=\w)[ \t]*--[ \t]*(?=\w)|[ \t]--[ \t]"
    r"|(?<=[a-z]) - (?=[a-z])")


def _emoji_edits(cs, register):
    """(start, end, replacement) edits that strip decorative emoji from `cs`."""
    if register in EMOJI_KEEP_REGISTERS:
        return []
    edits = []
    for m in AUTOFIX_EMOJI_RE.finditer(cs):
        before = cs[m.start() - 1] if m.start() > 0 else ""
        after = cs[m.end()] if m.end() < len(cs) else ""
        # Keep one space only when the emoji sat between two words; otherwise the
        # emoji (and its padding) goes entirely.
        flanked = bool(before) and not before.isspace() and bool(after) and not after.isspace()
        edits.append((m.start(), m.end(), " " if flanked else ""))
    return edits


def _dash_edits(cs, register):
    """(start, end, replacement) edits that rewrite dash-as-pause marks to commas.

    Numeric en-dash ranges (10–20, 2024 – 25) are preserved; compound hyphens
    (well-known) are never matched.
    """
    if register in DASH_KEEP_REGISTERS:
        return []
    edits = []
    for m in AUTOFIX_DASH_RE.finditer(cs):
        if "–" in m.group(0) and _is_numeric_en_dash(cs, m):
            continue
        after = cs[m.end()] if m.end() < len(cs) else ""
        # A comma needs no trailing space at end-of-line / end-of-text.
        rep = ", " if (after and after != "\n") else ","
        edits.append((m.start(), m.end(), rep))
    return edits


def _mask_code(text):
    """Blank fenced and inline code with EQUAL-LENGTH filler (spaces, newlines
    kept in place). Unlike strip_code -- which collapses a fence to bare newlines
    -- this preserves exact character offsets, so a match found in the mask
    splices back into the original text correctly even after a code block."""
    def fence_sub(m):
        return "".join("\n" if c == "\n" else " " for c in m.group(0))
    masked = CODE_FENCE_RE.sub(fence_sub, text)
    masked = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), masked)
    return masked


def _apply_edits(text, edits):
    """Splice (start, end, replacement) edits into `text`; keep the leftmost on
    overlap. Returns (new_text, applied_count). Offsets index `_mask_code(text)`,
    which shares geometry with `text`, so code is never modified."""
    edits.sort(key=lambda e: e[0])
    out, pos, last, applied = [], 0, -1, 0
    for s, e, rep in edits:
        if s < last:
            continue
        out.append(text[pos:s])
        out.append(rep)
        pos, last, applied = e, e, applied + 1
    out.append(text[pos:])
    return "".join(out), applied


def _swap_edits(cs, patterns):
    """(start, end, replacement) edits for unambiguous 1:1 lexical swaps."""
    edits = []
    for key in SAFE_FIX_KEYS:
        for phrase, suggestion in as_phrase_list(patterns.get(key)):
            if not suggestion or suggestion == "cut":
                continue
            rx = _phrase_regex(phrase)
            if rx is None:
                continue
            for m in rx.finditer(cs):
                edits.append((m.start(), m.end(), _match_case(m.group(0), suggestion)))
    return edits


def autofix(text, patterns, register="technical"):
    """Apply deterministic fixes. Returns (new_text, swaps, emoji, dashes).

    Three classes of edit, all unambiguous enough to apply without human
    judgment: 1:1 lexical swaps (filler/jargon/redundancy), decorative-emoji
    removal, and dash-as-pause -> comma normalization. Emoji and dash fixes are
    register-gated (kept in creative; emoji also kept in casual).

    Applied as three sequential passes rather than one merged edit list: emoji
    and dash constructs share the whitespace between them, so merging would let
    one edit swallow the space the next one needs. Each pass re-derives
    _mask_code(text) so code is never touched.
    """
    text, swaps = _apply_edits(text, _swap_edits(_mask_code(text), patterns))
    text, emoji = _apply_edits(text, _emoji_edits(_mask_code(text), register))
    text, dashes = _apply_edits(text, _dash_edits(_mask_code(text), register))
    return text, swaps, emoji, dashes


def apply_threshold_overrides(patterns, overrides):
    if not overrides:
        return patterns
    th = dict(patterns.get("thresholds", {})) if isinstance(patterns.get("thresholds"), dict) else {}
    for ov in overrides:
        if "=" not in ov:
            warn("ignoring malformed --threshold %r (want key=value)" % ov)
            continue
        k, v = ov.split("=", 1)
        try:
            th[k.strip()] = float(v)
        except ValueError:
            warn("ignoring non-numeric --threshold %r" % ov)
    patterns = dict(patterns)
    patterns["thresholds"] = th
    return patterns


def filter_hits(hits, enable, disable):
    if enable:
        hits = [h for h in hits if h.category in enable]
    if disable:
        hits = [h for h in hits if h.category not in disable]
    return hits


def render_sarif(results):
    """Minimal SARIF 2.1.0 doc so hits surface inline in code-scanning UIs."""
    sarif_results = []
    rules = {}
    for res in results:
        for h in res["hits"]:
            cat = h["category"]
            rules.setdefault(cat, {"id": cat, "name": cat,
                                   "shortDescription": {"text": "AI-prose tell: %s" % cat}})
            sarif_results.append({
                "ruleId": cat,
                "level": {"high": "error", "medium": "warning", "low": "note"}.get(
                    h.get("severity", "low"), "note"),
                "message": {"text": "%s%s" % (
                    h["text"], "  -> " + h["suggestion"] if h.get("suggestion") else "")},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": res["input"]},
                    "region": {"startLine": max(1, h.get("line") or 1)}}}],
            })
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {"driver": {"name": "detect_ai_prose", "rules": list(rules.values())}},
            "results": sarif_results,
        }],
    }


CONFIG_NAME = ".humanvoicerc"


def find_project_config(start):
    """Walk up from `start` looking for a .humanvoicerc JSON file."""
    try:
        d = os.path.dirname(os.path.abspath(start)) if start and start != "-" else os.getcwd()
    except OSError:
        return None
    seen = set()
    while d and d not in seen:
        seen.add(d)
        candidate = os.path.join(d, CONFIG_NAME)
        if os.path.isfile(candidate):
            try:
                with open(candidate, encoding="utf-8", errors="replace") as fh:
                    cfg = json.load(fh)
                if isinstance(cfg, dict):
                    return cfg
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                warn("ignoring unreadable %s: %s" % (candidate, exc))
                return None
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def merge_config(patterns, cfg):
    """Merge a .humanvoicerc dict into the loaded patterns (project overrides)."""
    if not isinstance(cfg, dict):
        return patterns
    patterns = dict(patterns)
    if isinstance(cfg.get("thresholds"), dict):
        th = dict(patterns.get("thresholds", {}) if isinstance(patterns.get("thresholds"), dict) else {})
        th.update(cfg["thresholds"])
        patterns["thresholds"] = th
    if isinstance(cfg.get("category_weights"), dict):
        cw = dict(patterns.get("category_weights", {}) if isinstance(patterns.get("category_weights"), dict) else {})
        cw.update(cfg["category_weights"])
        patterns["category_weights"] = cw
    if isinstance(cfg.get("score_bands"), dict):
        patterns["score_bands"] = cfg["score_bands"]
    for listkey in ("protected_terms", "context_exceptions"):
        if isinstance(cfg.get(listkey), list):
            patterns[listkey] = list(patterns.get(listkey) or []) + list(cfg[listkey])
    return patterns


def collect_targets(inputs, recursive):
    """Expand inputs into a flat list of file paths (or '-'), walking dirs."""
    targets = []
    for inp in inputs:
        if inp == "-":
            targets.append(inp)
        elif os.path.isdir(inp):
            for root, _dirs, files in os.walk(inp):
                for fn in sorted(files):
                    if fn.endswith((".md", ".markdown", ".txt")):
                        targets.append(os.path.join(root, fn))
                if not recursive:
                    break
        else:
            targets.append(inp)
    return targets


def analyze_target(target, args, patterns, weights, bands):
    text = read_input(target)
    hits, report, words = analyze(text, args.register, args.dialect, patterns)
    hits = filter_hits(hits, set(args.enable or []), set(args.disable or []))
    floor = score(hits, words, weights)
    return {
        "schema_version": 1,
        "input": target,
        "register": args.register,
        "dialect": args.dialect,
        "words": words,
        "score": floor,
        "verdict": verdict_band(floor, bands),
        "metrics": report,
        "hits": [dict(h.as_dict(), severity=severity_of(h.category, weights)) for h in hits],
    }, hits, report, words, floor


def main(argv=None):
    ap = argparse.ArgumentParser(description="Detect surface tells of AI-written prose.")
    ap.add_argument("input", nargs="+", help="file path(s) or directory, or - for stdin")
    ap.add_argument("--register", choices=REGISTERS, default=None,
                    help="genre profile (default: technical, or .humanvoicerc)")
    ap.add_argument("--dialect", choices=["american", "british"], default=None,
                    help="enable spelling-consistency check for this dialect")
    ap.add_argument("--no-config", action="store_true", dest="no_config",
                    help="ignore any .humanvoicerc project config")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--sarif", action="store_true", help="SARIF 2.1.0 output for code scanning")
    ap.add_argument("--patterns", default=PATTERNS_FILE, help="patterns JSON path")
    ap.add_argument("--fail-over", type=float, default=None, metavar="SCORE",
                    dest="fail_over",
                    help="exit 1 when any floor score exceeds SCORE (for CI gating)")
    ap.add_argument("--baseline", metavar="FILE",
                    help="compare the input against FILE and print the score delta")
    ap.add_argument("--enable", help="comma-separated categories to keep (drop the rest)")
    ap.add_argument("--disable", help="comma-separated categories to suppress")
    ap.add_argument("--threshold", action="append", metavar="KEY=VALUE",
                    help="override a threshold (repeatable), e.g. --threshold burstiness_cov_floor=0.5")
    ap.add_argument("--max-examples", type=int, default=6, dest="max_examples",
                    help="examples shown per category in text output (default 6)")
    ap.add_argument("--quiet", action="store_true", help="print only the score line per file")
    ap.add_argument("--explain", action="store_true",
                    help="list every hit with line and fix (no per-category cap)")
    ap.add_argument("--recursive", action="store_true",
                    help="recurse into subdirectories when a directory is given")
    ap.add_argument("--lang", default="en",
                    help="language of the input (only 'en' is supported today)")
    ap.add_argument("--fix", action="store_true",
                    help="apply unambiguous 1:1 word swaps in place (files only)")
    ap.add_argument("--fix-dry-run", action="store_true", dest="fix_dry_run",
                    help="print the autofixed text to stdout without writing")
    args = ap.parse_args(argv)

    if args.lang and args.lang.lower() not in ("en", "english"):
        warn("only English ('en') is supported today; patterns are English-only. "
             "Proceeding, but results for %r are not meaningful." % args.lang)

    # normalize category filters
    args.enable = [c.strip() for c in args.enable.split(",")] if args.enable else None
    args.disable = [c.strip() for c in args.disable.split(",")] if args.disable else None

    patterns = load_patterns(args.patterns)
    # Project config (.humanvoicerc) discovered relative to the first real path.
    cfg = None
    if not args.no_config:
        first_path = next((i for i in args.input if i != "-"), None)
        cfg = find_project_config(first_path)
        if cfg:
            patterns = merge_config(patterns, cfg)
    # Resolve register/dialect: explicit flag > project config > built-in default.
    args.register = args.register or (cfg or {}).get("register") or "technical"
    if args.register not in REGISTERS:
        warn("unknown register %r from config; using technical" % args.register)
        args.register = "technical"
    args.dialect = args.dialect or (cfg or {}).get("dialect")
    if args.dialect not in (None, "american", "british"):
        args.dialect = None
    patterns = apply_threshold_overrides(patterns, args.threshold)
    # One-time sanity warning if the mute config references unknown categories.
    muted_map = patterns.get("muted_checks", {})
    if isinstance(muted_map, dict):
        for token, cats in muted_map.items():
            if isinstance(cats, list):
                for c in cats:
                    if c not in KNOWN_CATEGORIES:
                        warn("muted_checks[%r] references unknown category %r" % (token, c))

    weights = resolve_weights(patterns)
    bands = resolve_bands(patterns)

    # --- autofix mode (single file) ---
    if args.fix or args.fix_dry_run:
        if len(args.input) != 1 or args.input[0] == "-":
            sys.stderr.write("error: --fix needs exactly one file path\n")
            return 2
        target = args.input[0]
        original = read_input(target)
        fixed, swaps, emoji, dashes = autofix(original, patterns, args.register)
        if args.fix_dry_run:
            sys.stdout.write(fixed)
            return 0
        if (swaps or emoji or dashes) and not os.path.isdir(target):
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(fixed)
        sys.stderr.write("autofix: %d swap(s), %d emoji, %d dash(es) in %s\n"
                         % (swaps, emoji, dashes, target))
        return 0

    # --- compare mode (input vs baseline) ---
    if args.baseline:
        base = analyze_target(args.baseline, args, patterns, weights, bands)[0]
        cur = analyze_target(args.input[0], args, patterns, weights, bands)[0]
        delta = round(cur["score"] - base["score"], 1)
        if args.json:
            print(json.dumps({"baseline": base, "current": cur,
                              "score_delta": delta}, indent=2))
        else:
            print("compare: %s [%s %.1f]  ->  %s [%s %.1f]   delta %+.1f" % (
                base["input"], base["verdict"], base["score"],
                cur["input"], cur["verdict"], cur["score"], delta))
        return 0

    targets = collect_targets(args.input, args.recursive)
    results = []
    worst = 0.0
    for target in targets:
        payload, hits, report, words, floor = analyze_target(
            target, args, patterns, weights, bands)
        results.append(payload)
        worst = max(worst, floor)
        if not (args.json or args.sarif):
            if args.quiet:
                print("%-40s %6.1f  [%s]" % (target, floor, payload["verdict"]))
            else:
                print(render_text(target, args.register, args.dialect, hits, report,
                                  words, floor, payload["verdict"],
                                  max_examples=(10**6 if args.explain else args.max_examples)))
                if len(targets) > 1:
                    print("")

    if args.sarif:
        print(json.dumps(render_sarif(results), indent=2))
    elif args.json:
        print(json.dumps(results[0] if len(results) == 1 else results, indent=2))

    if args.fail_over is not None and worst > args.fail_over:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        os._exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
