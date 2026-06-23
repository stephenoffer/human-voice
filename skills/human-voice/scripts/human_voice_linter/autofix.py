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


__all__ = [
    '_match_case',
    'SAFE_FIX_KEYS',
    'EMOJI_KEEP_REGISTERS',
    'DASH_KEEP_REGISTERS',
    'AUTOFIX_EMOJI_RE',
    'AUTOFIX_DASH_RE',
    '_emoji_edits',
    '_dash_edits',
    '_mask_code',
    '_apply_edits',
    '_swap_edits',
    'autofix',
]
