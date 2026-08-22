"""textutil — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import bisect
import functools
import os
import re
import sys

from .util import *  # noqa: F401,F403

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols, pictographs, emoticons, transport, supplemental
    "\U00002700-\U000027BF"   # dingbats (✂ ✅ ✨ ❌ ❤)
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U0000FE0F"              # emoji variation selector
    "]"
)


CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def normalize_text(text):
    """Canonical form every entry point must agree on.

    CRLF endings, a UTF-8 BOM, and stray control characters all change what the
    line-anchored patterns match: `---\r\n` front matter is not recognized as
    front matter, and a NUL inside a word breaks tokenization. `read_input` used
    to do this and the library entry point did not, so `lint(open(f).read())`
    and the CLI could disagree about the same file. Both call this now.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    return CONTROL_CHARS_RE.sub("", text)


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
    return normalize_text(text)


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
EMPHASIS_RE = re.compile(r"\*\*\*|\*\*|\*|~~")
# Underscore emphasis only at a word boundary. CommonMark does not treat an
# intraword underscore as emphasis, and the old pattern did: `get_user_by_id`
# became `getuserbyid` and `MAX_RETRY_COUNT` became `MAXRETRYCOUNT`, which
# corrupted the word count, the n-gram counts, and the type-token ratio of every
# technical document that names an identifier outside backticks.
UNDERSCORE_EMPHASIS_RE = re.compile(
    r"(?<![A-Za-z0-9_])_{1,3}(?=\S)|(?<=\S)_{1,3}(?![A-Za-z0-9_])")
HEADING_LINE_RE = re.compile(r"^[ \t]*#{1,6}[ \t]+")
SETEXT_RE = re.compile(r"^[ \t]*(=+|-+)[ \t]*$")
LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")
BLOCKQUOTE_RE = re.compile(r"^[ \t]*>+[ \t]?")
TABLE_ROW_RE = re.compile(r"^[ \t]*\|.*\|?[ \t]*$")
TABLE_SEP_RE = re.compile(r"^[ \t]*\|?[\s:|-]*[-:][\s:|-]*\|?[ \t]*$")
SECTION_RULE_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$")
SECTION_RULE_MULTILINE_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.MULTILINE)
FOOTNOTE_DEF_RE = re.compile(r"^[ \t]*\[\^[^\]]+\]:")


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

    def loc(self, start, end):
        """Return (line, col, end_line, end_col), all 1-based, for [start, end).

        Columns are only meaningful when the index refers to a text whose
        geometry matches the source file (e.g. code_stripped or the raw text);
        callers working on markup-stripped text should not pass columns through.
        """
        line = bisect.bisect_left(self.offsets, start) + 1
        line_start = (self.offsets[line - 2] + 1) if line > 1 else 0
        end_line = bisect.bisect_left(self.offsets, end) + 1
        end_line_start = (self.offsets[end_line - 2] + 1) if end_line > 1 else 0
        return line, start - line_start + 1, end_line, end - end_line_start + 1


def strip_inline_markup(line):
    line = LINK_RE.sub(r"\1", line)        # links/images -> anchor text only
    line = BARE_URL_RE.sub(" ", line)      # drop bare URLs
    line = FOOTNOTE_REF_RE.sub(" ", line)
    line = HTML_TAG_RE.sub(" ", line)
    line = EMPHASIS_RE.sub("", line)       # drop emphasis markers, keep words
    line = UNDERSCORE_EMPHASIS_RE.sub("", line)
    return line


class MappedLineMap:
    """Reports SOURCE line numbers for positions in a derived text.

    `prose_for_metrics` joins soft-wrapped lines, so an offset in its output does not
    correspond to the same line in the source. This holds the segment table that
    function builds -- (offset in the derived text, source line) for every piece it
    contributed -- and binary-searches it, so a hit resolves to the exact source line
    rather than to the line its paragraph happened to start on.

    Without this, every check located against the metric text reported a line from
    the reduced text: a 75-line document collapses to 12, so a finding on line 42 was
    reported as line 8. That pointed readers at the wrong place and made inline
    `<!-- human-voice: ignore -->` directives, which are keyed on source lines,
    unable to match the hits they were written to suppress.
    """

    __slots__ = ("_lm", "_offsets", "_lines")

    def __init__(self, derived_text, segments):
        self._lm = LineMap(derived_text)
        segs = sorted(segments or [])
        self._offsets = [off for off, _ in segs]
        self._lines = [ln for _, ln in segs]

    def line_of(self, index):
        if not self._offsets:
            return self._lm.line_of(index)
        i = bisect.bisect_right(self._offsets, index) - 1
        if i < 0:
            i = 0
        return self._lines[i]


def prose_for_metrics(code_stripped, with_line_map=False):
    """Markdown-normalized text for sentence/burstiness/diversity metrics.

    Drops headings, table rows, rules, and footnote definitions; strips list,
    blockquote, and inline markup; terminates list items so they count as their
    own sentence; and joins soft-wrapped paragraph lines.

    This deliberately collapses lines -- a soft-wrapped paragraph becomes one line
    so sentences segment correctly -- which means a position in the result does NOT
    correspond to the same line in the source. Pass `with_line_map=True` to also get
    a list mapping each output line (0-based) to the 1-based SOURCE line it started
    on, and wrap it in `MappedLineMap` so hits report locations a reader can open.
    Without that mapping, every check located against this text reported a line
    number from the reduced text, which pointed a reader at the wrong place and made
    inline `<!-- human-voice: ignore -->` directives unable to match.
    """
    out_paras = []
    out_src_lines = []      # per output line: source line it started on
    segments = []           # (offset in final text, source line) for every piece
    cur = []                # (text, source line) for the paragraph being joined
    cur_start = 0
    pos = 0                 # running offset into the final joined text

    def _emit(text, src_line, pieces=None):
        """Append one output line and record where each piece came from."""
        nonlocal pos
        out_paras.append(text)
        out_src_lines.append(src_line)
        if pieces:
            off = pos
            for i, (piece, ln) in enumerate(pieces):
                segments.append((off, ln))
                off += len(piece) + (1 if i < len(pieces) - 1 else 0)
        else:
            segments.append((pos, src_line))
        pos += len(text) + 1    # +1 for the joining newline

    in_item = False         # the block being joined is a list item

    def _flush():
        """Emit the pending block, terminating a list item so it counts as a sentence."""
        nonlocal cur, in_item
        if not cur:
            in_item = False
            return
        text = " ".join(t for t, _ in cur)
        if in_item and text[-1:] not in ".!?":
            # A bullet rarely ends in a full stop, and without one the next block
            # runs into it and the two count as a single sentence.
            text += "."
        _emit(text, cur_start, cur)
        cur = []
        in_item = False

    for lineno, raw in enumerate(code_stripped.split("\n"), 1):
        line = raw
        if (not line.strip() or HEADING_LINE_RE.match(line) or SETEXT_RE.match(line)
                or SECTION_RULE_RE.match(line) or TABLE_SEP_RE.match(line)
                or TABLE_ROW_RE.match(line) or FOOTNOTE_DEF_RE.match(line)):
            _flush()
            continue
        is_item = bool(LIST_MARKER_RE.match(line))
        line = BLOCKQUOTE_RE.sub("", line)
        line = LIST_MARKER_RE.sub("", line)
        line = strip_inline_markup(line).strip()
        if not line:
            continue
        if is_item:
            # A new bullet ends the previous block, whatever it was.
            _flush()
            cur_start = lineno
            in_item = True
            cur.append((line, lineno))
        else:
            # A soft-wrapped continuation of a bullet belongs to that bullet. It
            # used to start a fresh block, which split one list item into two
            # "sentences" and left a full stop mid-clause ("...from 40 minutes
            # to." / "6, allowing engineers to ship..."). That corrupted the
            # sentence count, the length distribution, and every n-gram across the
            # invented boundary, on a construction as common as a wrapped bullet.
            if not cur:
                cur_start = lineno
            cur.append((line, lineno))
    _flush()
    text = "\n".join(out_paras)
    return (text, segments) if with_line_map else text


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
        line = UNDERSCORE_EMPHASIS_RE.sub("", line)
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


def _norm_phrase(text):
    r"""Canonical key for a matched phrase: lowercased, whitespace collapsed.

    `_phrase_regex` turns each space in a phrase into `\s+`, so a phrase can match
    across a line break. Normalizing the match the same way lets a combined
    alternation look the original phrase back up.
    """
    return " ".join(text.lower().split())


def _boundary_bucket(phrase):
    """(left, right) word-boundary anchors for a phrase, as _phrase_regex picks them."""
    return (r"\b" if phrase[:1].isalnum() else "",
            r"\b" if phrase[-1:].isalnum() else "")


# Python's re allowed at most 100 groups before 3.7 and alternations get slow to
# compile long before they get slow to run, so combined patterns are chunked.
_ALTERNATION_CHUNK = 200


@functools.lru_cache(maxsize=64)
def _compiled_alternation(phrases, left, right):
    r"""One case-insensitive regex matching any of `phrases` (a tuple).

    Running one `\bphrase\b` regex per entry was 66% of total analysis time once
    the pattern file passed a thousand entries: a 36,000-word document meant 1,200
    full scans. Alternating them means one scan per boundary bucket per chunk.
    Phrases are sorted longest-first so the alternation prefers the longer match,
    which is what the per-phrase loop effectively produced.
    """
    out = []
    ordered = sorted(phrases, key=lambda p: (-len(p), p))
    for i in range(0, len(ordered), _ALTERNATION_CHUNK):
        chunk = ordered[i:i + _ALTERNATION_CHUNK]
        body = "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in chunk)
        try:
            out.append(re.compile(left + "(?:" + body + ")" + right, re.IGNORECASE))
        except re.error as exc:
            warn("skipping unmatchable phrase chunk: %s" % exc)
    return tuple(out)


def compile_phrase_matchers(phrases):
    """[(regex, ...)] covering every phrase, grouped by boundary anchoring.

    Returns a flat tuple of compiled regexes. A match's normalized text
    (`_norm_phrase`) is the key back into the caller's phrase->suggestion map.
    """
    buckets: dict = {}
    for phrase in phrases:
        if not phrase:
            continue
        buckets.setdefault(_boundary_bucket(phrase), []).append(phrase)
    out: list = []
    for (left, right), group in sorted(buckets.items()):
        out.extend(_compiled_alternation(tuple(sorted(group)), left, right))
    return tuple(out)


def _overlaps(start, end, spans):
    """True if [start, end) overlaps any (s, e) in spans (small list, linear)."""
    for s, e in spans:
        if start < e and s < end:
            return True
    return False


def build_protected_spans(text, exceptions):
    """Character ranges where a lexical word is a known legitimate use.

    Driven by the `context_exceptions` patterns key, e.g. "test harness" or
    "vital signs" protect "harness"/"vital" from being flagged as filler. These
    are whole-phrase matches; any lexical hit landing inside one is suppressed.
    """
    phrases = [p.strip() for p in (exceptions or ())
               if isinstance(p, str) and p.strip()]
    if not phrases:
        return []
    spans = []
    for rx in compile_phrase_matchers(phrases):
        for m in rx.finditer(text):
            spans.append((m.start(), m.end()))
    return spans


# A citation/source token appearing just after a phrase ("studies suggest [1]",
# "studies show (Smith 2024)") means the attribution is NOT vague.


__all__ = [
    'MappedLineMap',
    'CONTROL_CHARS_RE',
    'normalize_text',
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
    'UNDERSCORE_EMPHASIS_RE',
    'HEADING_LINE_RE',
    'SETEXT_RE',
    'LIST_MARKER_RE',
    'BLOCKQUOTE_RE',
    'TABLE_ROW_RE',
    'TABLE_SEP_RE',
    'SECTION_RULE_RE',
    'SECTION_RULE_MULTILINE_RE',
    'FOOTNOTE_DEF_RE',
    'strip_code',
    'line_of',
    'LineMap',
    'strip_inline_markup',
    'prose_for_metrics',
    'prose_for_adjacency',
    'sentences',
    '_phrase_regex',
    '_norm_phrase',
    '_boundary_bucket',
    'compile_phrase_matchers',
    '_word_regex',
    '_overlaps',
    'build_protected_spans',
]
