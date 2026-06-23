"""directives — inline ignore directives embedded in the prose as HTML comments.

Authors can silence findings without touching config:

    Some text we accept.  <!-- human-voice: ignore filler,em_dash -->
    <!-- human-voice: ignore -->
    The line below is exempt from everything.

    <!-- human-voice: ignore-start puffery -->
    ... a block where puffery is allowed ...
    <!-- human-voice: ignore-end -->

A bare `ignore` (no categories) suppresses every category on the affected line.
A directive alone on its own line applies to the FOLLOWING content line; a
trailing directive applies to its own line. Directives inside fenced code are
treated as example text and ignored. Document-level findings (line 0) have no
single line and are never suppressed this way — use --disable or register mutes.
"""
from __future__ import annotations

import re

from .textutil import CODE_FENCE_RE

DIRECTIVE_RE = re.compile(
    r"<!--\s*human-voice:\s*(ignore(?:-start|-end)?)\b([^>]*?)-->", re.IGNORECASE)


def _parse_cats(raw: str):
    """None means 'all categories'; otherwise a set of category names."""
    toks = [t for t in re.split(r"[,\s]+", raw.strip()) if t]
    return set(toks) if toks else None


def _merge(ignored: dict, line: int, cats) -> None:
    if line not in ignored:
        ignored[line] = None if cats is None else set(cats)
        return
    if ignored[line] is None or cats is None:
        ignored[line] = None
    else:
        ignored[line] |= cats


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def parse_directives(text: str) -> dict:
    """Map each suppressed line number to a set of categories (or None = all)."""
    fence_lines = set()
    for m in CODE_FENCE_RE.finditer(text):
        for ln in range(_line_of(text, m.start()), _line_of(text, m.end()) + 1):
            fence_lines.add(ln)

    ignored: dict = {}
    open_cats: list = []
    open_lines: list = []
    for m in DIRECTIVE_RE.finditer(text):
        line = _line_of(text, m.start())
        if line in fence_lines:
            continue
        kind = m.group(1).lower()
        cats = _parse_cats(m.group(2))
        if kind == "ignore":
            ls = text.rfind("\n", 0, m.start()) + 1
            le = text.find("\n", m.end())
            le = le if le != -1 else len(text)
            alone = not text[ls:m.start()].strip() and not text[m.end():le].strip()
            _merge(ignored, line + 1 if alone else line, cats)
        elif kind == "ignore-start":
            open_cats.append(cats)
            open_lines.append(line)
        elif kind == "ignore-end" and open_cats:
            start_cats = open_cats.pop()
            start = open_lines.pop()
            for ln in range(start, line + 1):
                _merge(ignored, ln, start_cats)
    return ignored


def directive_suppresses(hit, ignored: dict) -> bool:
    """True if an ignore directive silences this hit."""
    if not ignored or hit.line == 0 or hit.line not in ignored:
        return False
    cats = ignored[hit.line]
    return cats is None or hit.category in cats


__all__ = ["parse_directives", "directive_suppresses", "DIRECTIVE_RE"]
