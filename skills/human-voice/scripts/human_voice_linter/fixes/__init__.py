"""fixes — deterministic rewrites applied by --fix.

    masking  spans the autofixer must never edit; splicing edits back in
    fixers   the Fixer base class and the swap, emoji, and dash fixers
"""
from __future__ import annotations

from .fixers import (
    DASH_KEEP_REGISTERS,
    EMOJI_KEEP_REGISTERS,
    SAFE_FIX_KEYS,
    DashFixer,
    EmojiFixer,
    Fixer,
    SwapFixer,
    is_substitution,
)
from .masking import CODE_MASK_CHAR, apply_edits, mask_code

# Applied as sequential passes rather than one merged edit list: emoji and dash
# constructs share the whitespace between them, so merging would let one edit
# swallow the space the next one needs. Each pass re-masks the text it is given.
FIXERS = (SwapFixer(), EmojiFixer(), DashFixer())


def autofix(text, patterns, register="technical"):
    """Apply deterministic fixes. Returns (new_text, swaps, emoji, dashes).

    Three classes of edit, all unambiguous enough to apply without human
    judgment: 1:1 lexical swaps (filler/jargon/redundancy), decorative-emoji
    removal, and dash-as-pause normalization. Emoji and dash fixes are
    register-gated (kept in creative; emoji also kept in casual).
    """
    counts = []
    for fixer in FIXERS:
        text, applied = fixer.apply(text, patterns, register)
        counts.append(applied)
    swaps, emoji, dashes = counts
    return text, swaps, emoji, dashes


__all__ = [
    "FIXERS",
    "autofix",
    "Fixer",
    "SwapFixer",
    "EmojiFixer",
    "DashFixer",
    "SAFE_FIX_KEYS",
    "EMOJI_KEEP_REGISTERS",
    "DASH_KEEP_REGISTERS",
    "is_substitution",
    "CODE_MASK_CHAR",
    "apply_edits",
    "mask_code",
]
