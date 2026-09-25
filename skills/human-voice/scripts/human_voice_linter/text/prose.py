"""prose — the derived texts checks measure: metric prose, adjacency prose, and
the paragraph and list-item views of a document."""
from __future__ import annotations

import re

from .markdown import (
    BARE_URL_RE,
    BLOCKQUOTE_RE,
    CODE_FENCE_RE,
    EMPHASIS_RE,
    FOOTNOTE_DEF_RE,
    FOOTNOTE_REF_RE,
    HEADING_LINE_RE,
    HTML_TAG_RE,
    INLINE_CODE_RE,
    LINK_RE,
    LIST_MARKER_RE,
    SECTION_RULE_RE,
    SETEXT_RE,
    TABLE_ROW_RE,
    TABLE_SEP_RE,
    UNDERSCORE_EMPHASIS_RE,
    strip_inline_markup,
)
from .tokens import WORD_RE

BLANK_LINE_SPLIT_RE = re.compile(r"\n[ \t]*\n")


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


def prose_paragraphs(code_stripped):
    """Prose paragraphs as plain strings (headings, rules, tables, lists removed)."""
    out = []
    for block in BLANK_LINE_SPLIT_RE.split(code_stripped):
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


def list_items(code_stripped):
    """The text of every single-line list item that contains a word."""
    items = []
    for ln in code_stripped.split("\n"):
        if LIST_MARKER_RE.match(ln):
            body = strip_inline_markup(LIST_MARKER_RE.sub("", ln)).strip()
            if WORD_RE.findall(body):
                items.append(body)
    return items


__all__ = [
    "BLANK_LINE_SPLIT_RE",
    "prose_for_metrics",
    "prose_for_adjacency",
    "prose_paragraphs",
    "list_items",
]
