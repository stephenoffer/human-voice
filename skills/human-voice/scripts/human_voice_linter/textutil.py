"""textutil — part of human_voice_linter (split from detect_ai_prose.py)."""
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


EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols, pictographs, emoticons, transport, supplemental
    "\U00002700-\U000027BF"   # dingbats (✂ ✅ ✨ ❌ ❤)
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U0000FE0F"              # emoji variation selector
    "]"
)


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
    except re.error as exc:
        warn("skipping unmatchable phrase %r: %s" % (phrase, exc))
        return None


@functools.lru_cache(maxsize=None)
def _word_regex(word):
    """Cached \\bword\\b matcher (case-insensitive) for dialect checks."""
    try:
        return re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    except re.error as exc:
        warn("skipping unmatchable dialect word %r: %s" % (word, exc))
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


__all__ = [
    'EMOJI_RE',
    'read_input',
    'blank_frontmatter',
    'CODE_FENCE_RE',
    'INLINE_CODE_RE',
    'WORD_RE',
    'SENTENCE_SPLIT_RE',
    'ABBREVIATIONS',
    'ABBREV_RE',
    'LINK_RE',
    'BARE_URL_RE',
    'FOOTNOTE_REF_RE',
    'HTML_TAG_RE',
    'EMPHASIS_RE',
    'HEADING_LINE_RE',
    'SETEXT_RE',
    'LIST_MARKER_RE',
    'BLOCKQUOTE_RE',
    'TABLE_ROW_RE',
    'TABLE_SEP_RE',
    'SECTION_RULE_RE',
    'SECTION_RULE_MULTILINE_RE',
    'strip_code',
    'line_of',
    'LineMap',
    'strip_inline_markup',
    'prose_for_metrics',
    'prose_for_adjacency',
    'sentences',
    '_phrase_regex',
    '_word_regex',
    '_overlaps',
    'build_protected_spans',
]
