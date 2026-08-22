"""autofix — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import re

from .checks import _is_numeric_en_dash  # shared dash helper
from .defaults import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403
from .patterns import *  # noqa: F401,F403
from .textutil import *  # noqa: F401,F403
from .util import *  # noqa: F401,F403


def _match_case(original, replacement):
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


# Only 1:1 lexical swaps with a concrete replacement are auto-fixable. "cut"
# suggestions and structural tells need human judgment and are never auto-applied.
SAFE_FIX_KEYS = ("filler", "soft_filler", "jargon", "redundancy")

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


def _table_row_spans(cs):
    """Character spans of markdown table rows, which the dash fixer skips.

    A lone dash in a table cell is a conventional "not applicable" marker, not a
    dash-as-pause, and rewriting it to a comma produced `| n/a |` cells reading
    `|, |`. Alignment rows (`|---|---|`) must obviously survive too.
    """
    spans = []
    pos = 0
    for line in cs.split("\n"):
        if TABLE_ROW_RE.match(line) or TABLE_SEP_RE.match(line):
            spans.append((pos, pos + len(line)))
        pos += len(line) + 1
    return spans


# A paired dashed aside on one line: "the result — surprisingly — held". Rewriting
# both dashes to commas is correct but monotonous, and parentheses are what a
# person reaches for. Matched before the single-dash rule so the pair wins.
# The aside must stay inside one clause: no sentence-ending punctuation, no table
# pipe, no code mask, and both marks the same character so a following numeric
# en-dash range cannot be mistaken for the closing mark.
PAIRED_ASIDE_RE = re.compile(
    "[ \t]*(?P<d>[\u2014\u2013])[ \t]*"
    "(?P<inner>[^\u2014\u2013\n.;:!?|\x00]{1,45}?)"
    "[ \t]*(?P=d)[ \t]*")

# A colon only reads right before an enumeration ("three things: speed, cost, and
# risk"). Everywhere else a comma is what a person writes, so the colon rule is
# deliberately narrow: converting every dash to the SAME mark is what trades the
# em-dash signature for a fresh uniform one (principle 2), and converting them to
# the wrong mark is worse than leaving the rhythm flat.
ENUMERATION_TAIL_RE = re.compile(
    r"^[^.;:!?\n]{0,80}?,[^.;:!?\n]{0,40}?,[^.;:!?\n]{0,40}?\b(?:and|or)\b")


def _dash_replacement(cs, end):
    """Pick the mark that replaces a dash-as-pause, varying by what follows."""
    tail = cs[end:end + 140]
    return ":" if ENUMERATION_TAIL_RE.match(tail) else ","


def _dash_edits(cs, register):
    """(start, end, replacement) edits that rewrite dash-as-pause marks.

    The replacement VARIES: parentheses around a paired aside, a colon before an
    appositive or list, a comma before a full clause. Numeric en-dash ranges
    (10–20, 2024 – 25) are preserved; compound hyphens (well-known) never match.
    """
    if register in DASH_KEEP_REGISTERS:
        return []
    edits = []
    table_spans = _table_row_spans(cs)
    paired_spans = []
    for m in PAIRED_ASIDE_RE.finditer(cs):
        if any(a <= m.start() < b for a, b in table_spans):
            continue
        if "–" in m.group(0) and _is_numeric_en_dash(cs, m):
            continue
        inner = m.group("inner").strip()
        if not inner:
            continue
        before = cs[m.start() - 1] if m.start() > 0 else ""
        after = cs[m.end()] if m.end() < len(cs) else ""
        lead = "" if (not before or before.isspace()) else " "
        trail = "" if (not after or after.isspace() or after in ".,;:!?") else " "
        edits.append((m.start(), m.end(), "%s(%s)%s" % (lead, inner, trail)))
        paired_spans.append((m.start(), m.end()))
    for m in AUTOFIX_DASH_RE.finditer(cs):
        if any(a <= m.start() < b for a, b in paired_spans):
            continue
        if "–" in m.group(0) and _is_numeric_en_dash(cs, m):
            continue
        if any(a <= m.start() < b for a, b in table_spans):
            continue
        start, end = m.start(), m.end()
        after = cs[end] if end < len(cs) else ""
        # A dash that opens a wrapped line must not leave the comma stranded at the
        # start of that line ("...rewritten text\n, a figure about..."). Pull the
        # edit back across the newline so the comma ends the previous line, which is
        # where a writer would have put it.
        if cs[:start].endswith("\n") or (start and cs[start - 1] == "\n"):
            nl = cs.rfind("\n", 0, start)
            if nl >= 0:
                mark = _dash_replacement(cs, end)
                start = nl
                rep = (mark + "\n") if (after and after != "\n") else mark
                edits.append((start, end, rep))
                continue
        # A comma needs no trailing space at end-of-line / end-of-text.
        mark = _dash_replacement(cs, end)
        rep = (mark + " ") if (after and after != "\n") else mark
        edits.append((start, end, rep))
    return edits


# Code is masked with NUL rather than spaces. Blanking to spaces looked harmless
# and silently destroyed code: the dash and emoji patterns pad themselves with
# `[ \t]*`, so in "labeled `ai` — balanced" the masked span read as whitespace,
# the dash match extended across it, and splicing the replacement back into the
# original text deleted the `ai`. NUL is not whitespace, is not a word character,
# and appears in no real prose, so every pattern stops at the code boundary
# instead of consuming it.
CODE_MASK_CHAR = "\x00"


# Spans the autofixer must never rewrite, beyond code. A URL is not prose: a
# lexical swap inside one silently broke the link (`.../delve-into-it` became
# `.../examine-into-it`) and the dash rule turned a query string's `a--b` into
# `a, b`. Same for HTML tags and link reference definitions.
LINK_DEST_RE = re.compile(r"(!?\[[^\]]*\])(\([^)\n]*\))")
AUTOLINK_RE = re.compile(r"<[A-Za-z][A-Za-z0-9+.-]*:[^>\s]*>")
REF_DEF_RE = re.compile(r"^[ \t]*\[[^\]]+\]:[ \t]*\S+", re.MULTILINE)


def _mask_span(m, group=0):
    """Equal-length NUL filler for a match (newlines kept so lines still align)."""
    s = m.group(group)
    return "".join("\n" if c == "\n" else CODE_MASK_CHAR for c in s)


def _mask_code(text):
    """Blank code, URLs, and markup targets with EQUAL-LENGTH non-whitespace filler
    (newlines kept in place). Unlike strip_code, which collapses a fence to bare
    newlines, this preserves exact character offsets, so a match found in the mask
    splices back into the original text correctly even after a code block.

    Masking is deliberately wider than "code": anything the autofixer would corrupt
    by editing it as prose belongs here. URLs are the important case -- swapping a
    filler word inside a link destination produces a 404, not a better sentence.
    """
    masked = CODE_FENCE_RE.sub(_mask_span, text)
    masked = INLINE_CODE_RE.sub(_mask_span, masked)
    # Link/image destinations only; the anchor text stays editable prose.
    masked = LINK_DEST_RE.sub(lambda m: m.group(1) + _mask_span(m, 2), masked)
    masked = AUTOLINK_RE.sub(_mask_span, masked)
    masked = REF_DEF_RE.sub(_mask_span, masked)
    masked = BARE_URL_RE.sub(_mask_span, masked)
    masked = HTML_TAG_RE.sub(_mask_span, masked)
    masked = FOOTNOTE_REF_RE.sub(_mask_span, masked)
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


# A suggestion is only auto-applied when it is a *substitution*. Some entries are
# guidance for a human ("use (verb only; 'harness' as a noun is fine)"), and
# splicing those in literally produces nonsense -- which it did, on this repo's own
# EVAL.md, turning "evaluation harness" into "evaluation use". Parentheses, a
# semicolon, or an explicit alternation mark the entry as advice, not a swap.
GUIDANCE_SUGGESTION_RE = re.compile(r"[();]|\bor\b|\bonly\b|\bwhen\b|\bunless\b")


def is_substitution(suggestion):
    """True when a suggestion is a literal replacement safe to splice in."""
    if not suggestion or suggestion == "cut":
        return False
    return not GUIDANCE_SUGGESTION_RE.search(suggestion)


def _swap_edits(cs, patterns):
    """(start, end, replacement) edits for unambiguous 1:1 lexical swaps."""
    edits = []
    for key in SAFE_FIX_KEYS:
        for phrase, suggestion in as_phrase_list(patterns.get(key)):
            if not is_substitution(suggestion):
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


__all__ = [
    '_match_case',
    'SAFE_FIX_KEYS',
    'EMOJI_KEEP_REGISTERS',
    'DASH_KEEP_REGISTERS',
    'AUTOFIX_EMOJI_RE',
    'AUTOFIX_DASH_RE',
    '_emoji_edits',
    '_table_row_spans',
    'PAIRED_ASIDE_RE',
    'ENUMERATION_TAIL_RE',
    '_dash_replacement',
    '_dash_edits',
    'CODE_MASK_CHAR',
    'LINK_DEST_RE',
    'AUTOLINK_RE',
    'REF_DEF_RE',
    '_mask_span',
    '_mask_code',
    '_apply_edits',
    'GUIDANCE_SUGGESTION_RE',
    'is_substitution',
    '_swap_edits',
    'autofix',
]
