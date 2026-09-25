"""dashes — the dash patterns shared by the em-dash checks and the autofixer."""
from __future__ import annotations

import re

# Real dashes only. ASCII `--` belongs to `dash_style`, which owns the "that is
# raw markup, not a dash" finding; counting it here too made one double-hyphen
# worth two hits in two categories, and a document written in the old
# `name -- description` docstring style scored twice for one convention.
EM_DASH_RE = re.compile(r"\s?[—–]\s?")
PAIRED_DASH_RE = re.compile(r"[—–]\s?[^—–\n]{1,50}?\s?[—–]")


def is_numeric_en_dash(text, m):
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


def pause_dashes(text):
    """Every em/en-dash in `text` that is not a numeric range."""
    return [m for m in EM_DASH_RE.finditer(text) if not is_numeric_en_dash(text, m)]


__all__ = ["EM_DASH_RE", "PAIRED_DASH_RE", "is_numeric_en_dash", "pause_dashes"]
