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
import json
import math
import os
import re
import sys
from collections import Counter

PATTERNS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "ai_prose_patterns.json")

REGISTERS = ["technical", "business", "marketing", "academic", "casual", "creative"]

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
    "hedging": 1.0,
    "puffery": 1.5,
    "vague_attribution": 1.5,
    "redundancy": 1.0,
    "self_identifying": 4.0,
    "antithesis": 1.5,
    "em_dash": 1.0,
    "bold_bullets": 1.5,
    "rule_of_three": 1.0,
    "uniform_openers": 1.0,
    "formatting": 1.0,
    "ngram_repetition": 1.0,
    "burstiness": 2.0,
    "lexical_diversity": 1.5,
    "dialect": 0.5,
    "heading_case": 0.5,
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


def sentences(prose):
    if not prose.strip():
        return []
    protected = re.sub(r"(\d)\.(\d)", lambda m: m.group(1) + "\x00" + m.group(2), prose)
    protected = re.sub(r"\.\.\.+", lambda m: "\x00" * len(m.group(0)), protected)
    protected = re.sub(r"\b(?:[A-Za-z]\.){2,}",
                       lambda m: m.group(0).replace(".", "\x00"), protected)
    for ab in ABBREVIATIONS:
        protected = re.sub(r"\b" + re.escape(ab) + r"\.",
                           ab + "\x00", protected, flags=re.IGNORECASE)
    parts = SENTENCE_SPLIT_RE.split(protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

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


def check_lexical_list(text, value, category, hits, seen_spans):
    for phrase, suggestion in as_phrase_list(value):
        rx = _phrase_regex(phrase)
        if rx is None:
            continue
        for m in rx.finditer(text):
            span = (m.start(), m.end())
            # Don't double-flag the same span across overlapping lists.
            if span in seen_spans.get(category, set()):
                continue
            seen_spans.setdefault(category, set()).add(span)
            hits.append(Hit(category, line_of(text, m.start()), m.group(0),
                            suggestion if suggestion else "cut"))


def check_antithesis(text, patterns, hits):
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
            hits.append(Hit("antithesis", line_of(text, m.start()),
                            snippet.replace("\n", " "),
                            "drop the not-X/it's-Y framing; state it plainly"))


EM_DASH_RE = re.compile(r"\s?[—–]\s?|(?<=\w)--(?=\w)")


def check_em_dash(text, words, threshold, hits, report):
    matches = list(EM_DASH_RE.finditer(text))
    count = len(matches)
    per_1k = (count / words * 1000) if words else 0.0
    report["em_dash_per_1k"] = round(per_1k, 1)
    if per_1k > threshold and count >= 2:
        for m in matches[:8]:
            ctx = text[max(0, m.start() - 15):m.start() + 15].replace("\n", " ").strip()
            hits.append(Hit("em_dash", line_of(text, m.start()), ctx,
                            "use a comma, period, or parens"))


BOLD_BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+(?:\*\*[^*\n]+\*\*|__[^_\n]+__)[ \t]*:?",
                            re.MULTILINE)
BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+\S", re.MULTILINE)


def check_bold_bullets(text, threshold, hits, report):
    bullets = BULLET_RE.findall(text)
    bold = list(BOLD_BULLET_RE.finditer(text))
    report["bullets"] = len(bullets)
    report["bold_lead_bullets"] = len(bold)
    if bullets and (len(bold) / len(bullets)) >= threshold and len(bold) >= 3:
        for m in bold[:8]:
            hits.append(Hit("bold_bullets", line_of(text, m.start()),
                            m.group(0).strip(),
                            "convert some to prose; drop ornamental bold"))


RULE_OF_THREE_RE = re.compile(
    r"\b([A-Za-z]+(?:ly)?)\s*,\s+([A-Za-z]+(?:ly)?)\s*,\s+and\s+([A-Za-z]+(?:ly)?)\b")


def check_rule_of_three(prose_text, hits):
    for m in RULE_OF_THREE_RE.finditer(prose_text):
        a, b, c = m.group(1), m.group(2), m.group(3)
        # Adjective/adverb-looking triads only; require length and -ly/-ed-ish
        # endings or short words to avoid flagging proper-noun lists.
        if all(len(w) > 3 for w in (a, b, c)):
            hits.append(Hit("rule_of_three", line_of(prose_text, m.start()),
                            m.group(0), "vary to two or four, or a clause"))


def check_uniform_openers(sents, ratio_threshold, hits, report):
    openers = []
    for s in sents:
        m = WORD_RE.search(s)
        if m:
            openers.append(m.group(0).lower())
    if len(openers) < 6:
        report["opener_repeat_ratio"] = 0.0
        return
    word, count = Counter(openers).most_common(1)[0]
    ratio = count / len(openers)
    report["opener_repeat_ratio"] = round(ratio, 2)
    if ratio >= ratio_threshold:
        hits.append(Hit("uniform_openers", 0,
                        '%d of %d sentences open with "%s"' % (count, len(openers), word),
                        "vary how sentences begin"))


def check_formatting(text, max_rules, hits, report):
    max_rules = int(max_rules)
    emojis = EMOJI_RE.findall(text)
    report["emoji"] = len(emojis)
    if emojis:
        m = EMOJI_RE.search(text)
        hits.append(Hit("formatting", line_of(text, m.start()),
                        "emoji (%d)" % len(emojis), "remove decorative emoji"))
    rules = [m for m in re.finditer(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$", text,
                                    re.MULTILINE)]
    report["section_rules"] = len(rules)
    if len(rules) > max_rules:
        for m in rules[max_rules:max_rules + 6]:
            hits.append(Hit("formatting", line_of(text, m.start()),
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


def check_lexical_diversity(prose_text, floor, hits, report):
    words = [w.lower() for w in WORD_RE.findall(prose_text)]
    if len(words) < 50:
        report["ttr"] = None
        return
    window = 50
    ratios = []
    for i in range(0, len(words) - window + 1, window):
        chunk = words[i:i + window]
        ratios.append(len(set(chunk)) / window)
    ttr = (sum(ratios) / len(ratios)) if ratios else (len(set(words)) / len(words))
    report["ttr"] = round(ttr, 2)
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


def check_dialect(text, dialect_map, hits):
    if not isinstance(dialect_map, dict):
        return
    for wrong, right in dialect_map.items():
        if not isinstance(wrong, str) or not wrong:
            continue
        try:
            rx = re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE)
        except re.error:
            continue
        for m in rx.finditer(text):
            sug = ("use '%s' for consistent dialect" % right
                   if isinstance(right, str) else "spelling drift")
            hits.append(Hit("dialect", line_of(text, m.start()), m.group(0), sug))


HEADING_RE = re.compile(r"^[ \t]*(#{1,6})[ \t]+(.+?)[ \t]*#*$", re.MULTILINE)


def check_heading_case(text, hits):
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
                hits.append(Hit("heading_case", line_of(text, start), title,
                                "match the dominant heading case (%s)" % majority))


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
    word_count = len(WORD_RE.findall(metric_prose))
    muted = muted_categories(register, patterns)
    th = patterns.get("thresholds", {})
    if not isinstance(th, dict):
        th = {}
    hits = []
    seen = {}
    report = {}

    check_lexical_list(code_stripped, patterns.get("filler"), "filler", hits, seen)
    check_lexical_list(code_stripped, patterns.get("jargon"), "jargon", hits, seen)
    check_lexical_list(code_stripped, patterns.get("overused_transitions"), "transitions", hits, seen)
    check_lexical_list(code_stripped, patterns.get("meta_commentary"), "meta_commentary", hits, seen)
    check_lexical_list(code_stripped, patterns.get("hedging"), "hedging", hits, seen)
    check_lexical_list(code_stripped, patterns.get("puffery"), "puffery", hits, seen)
    check_lexical_list(code_stripped, patterns.get("vague_attribution"), "vague_attribution", hits, seen)
    check_lexical_list(code_stripped, patterns.get("redundancy"), "redundancy", hits, seen)
    check_lexical_list(code_stripped, patterns.get("self_identifying"), "self_identifying", hits, seen)
    check_antithesis(code_stripped, patterns.get("antithesis_patterns"), hits)

    check_em_dash(metric_prose, word_count, safe_float(th, "em_dash_per_1k_words", 6.0), hits, report)
    check_bold_bullets(text, safe_float(th, "bold_bullet_ratio", 0.5), hits, report)
    check_rule_of_three(metric_prose, hits)
    check_uniform_openers(sents, safe_float(th, "uniform_opener_ratio", 0.3), hits, report)
    check_formatting(text, safe_float(th, "section_rule_max", 2), hits, report)
    check_burstiness(sents, safe_float(th, "burstiness_cov_floor", 0.45), hits, report)
    check_lexical_diversity(metric_prose, safe_float(th, "ttr_floor", 0.40), hits, report)
    check_ngram_repetition(metric_prose, safe_int_list(th, "ngram_sizes", [2, 3]),
                           int(safe_float(th, "ngram_min_count", 3)), hits)
    check_heading_case(text, hits)

    if dialect:
        dmap = patterns.get("dialect", {})
        dmap = dmap.get(dialect, {}) if isinstance(dmap, dict) else {}
        check_dialect(code_stripped, dmap, hits)

    hits = [h for h in hits if h.category not in muted]
    report["word_count"] = word_count
    report["sentence_count"] = len(sents)
    return hits, report, word_count


def score(hits, word_count):
    weighted = sum(CATEGORY_WEIGHTS.get(h.category, 1.0) for h in hits)
    per_1k = (weighted / word_count * 1000) if word_count else 0.0
    return round(per_1k, 1)


def render_text(target, register, dialect, hits, report, word_count, floor_score):
    by_cat = {}
    for h in hits:
        by_cat.setdefault(h.category, []).append(h)

    out = []
    out.append("AI-prose floor report — %s" % target)
    out.append("register: %s%s   words: %d" % (
        register, ("   dialect: " + dialect) if dialect else "", word_count))
    out.append("score: %.1f weighted tells / 1k words  (lower is better; a FLOOR, not proof)" % floor_score)
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
        out.append("  %-18s %d" % (cat, len(items)))
        for h in items[:6]:
            loc = ("L%d: " % h.line) if h.line else ""
            sug = ("  -> %s" % h.suggestion) if h.suggestion else ""
            out.append("      %s%s%s" % (loc, h.text, sug))
        if len(items) > 6:
            out.append("      ... and %d more" % (len(items) - 6))
    out.append("")
    out.append("Floor only. The linter cannot see vacuity, weak stance, terminology")
    out.append("drift, or fabrication. A skeptical human read is the real test.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Detect surface tells of AI-written prose.")
    ap.add_argument("input", help="file path, or - for stdin")
    ap.add_argument("--register", choices=REGISTERS, default="technical",
                    help="genre profile (default: technical)")
    ap.add_argument("--dialect", choices=["american", "british"], default=None,
                    help="enable spelling-consistency check for this dialect")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--patterns", default=PATTERNS_FILE, help="patterns JSON path")
    args = ap.parse_args(argv)

    patterns = load_patterns(args.patterns)
    # One-time sanity warning if the mute config references unknown categories.
    muted_map = patterns.get("muted_checks", {})
    if isinstance(muted_map, dict):
        for token, cats in muted_map.items():
            if isinstance(cats, list):
                for c in cats:
                    if c not in KNOWN_CATEGORIES:
                        warn("muted_checks[%r] references unknown category %r" % (token, c))

    text = read_input(args.input)
    hits, report, word_count = analyze(text, args.register, args.dialect, patterns)
    floor = score(hits, word_count)

    if args.json:
        payload = {
            "input": args.input,
            "register": args.register,
            "dialect": args.dialect,
            "words": word_count,
            "score": floor,
            "metrics": report,
            "hits": [h.as_dict() for h in hits],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(args.input, args.register, args.dialect, hits, report,
                          word_count, floor))
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
