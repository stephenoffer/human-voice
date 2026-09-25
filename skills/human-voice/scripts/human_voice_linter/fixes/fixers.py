"""fixers — the three deterministic rewrites, each a Fixer.

A Fixer proposes (start, end, replacement) edits against the masked text; the
base class masks, collects, and splices. Only edits unambiguous enough to apply
without human judgment belong here.
"""
from __future__ import annotations

import re

from ..config.patterns import as_phrase_list
from ..text.dashes import is_numeric_en_dash
from ..text.markdown import EMOJI_RE, TABLE_ROW_RE, TABLE_SEP_RE
from ..text.phrases import phrase_regex
from .masking import apply_edits, mask_code


class Fixer:
    """One class of edit. Subclasses implement `edits(masked, patterns, register)`."""

    name = ""

    def edits(self, masked, patterns, register) -> list:
        raise NotImplementedError

    def apply(self, text, patterns, register):
        """(new_text, applied_count). Re-masks `text`, so code is never touched."""
        return apply_edits(text, self.edits(mask_code(text), patterns, register))


def _match_case(original, replacement):
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


# Only 1:1 lexical swaps with a concrete replacement are auto-fixable. "cut"
# suggestions and structural tells need human judgment and are never auto-applied.
SAFE_FIX_KEYS = ("filler", "soft_filler", "jargon", "redundancy")

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


class SwapFixer(Fixer):
    """Unambiguous 1:1 lexical swaps (filler, jargon, redundancy)."""

    name = "swaps"

    def edits(self, masked, patterns, register):
        edits = []
        for key in SAFE_FIX_KEYS:
            for phrase, suggestion in as_phrase_list(patterns.get(key)):
                if not is_substitution(suggestion):
                    continue
                rx = phrase_regex(phrase)
                if rx is None:
                    continue
                for m in rx.finditer(masked):
                    edits.append((m.start(), m.end(), _match_case(m.group(0), suggestion)))
        return edits


# Registers where decorative emoji can be legitimate (casual/social copy), so the
# autofixer leaves them alone; everywhere else it strips them.
EMOJI_KEEP_REGISTERS = frozenset({"creative", "casual"})

# An emoji run plus the inline whitespace hugging it, collapsed in one edit so
# stripping never leaves a doubled or dangling space. (`[ \t]` only, never a
# newline, so line geometry is preserved.)
AUTOFIX_EMOJI_RE = re.compile(r"[ \t]*" + EMOJI_RE.pattern + r"+[ \t]*")


class EmojiFixer(Fixer):
    """Strip decorative emoji, outside the registers where they belong."""

    name = "emoji"

    def edits(self, masked, patterns, register):
        if register in EMOJI_KEEP_REGISTERS:
            return []
        edits = []
        for m in AUTOFIX_EMOJI_RE.finditer(masked):
            before = masked[m.start() - 1] if m.start() > 0 else ""
            after = masked[m.end()] if m.end() < len(masked) else ""
            # Keep one space only when the emoji sat between two words; otherwise the
            # emoji (and its padding) goes entirely.
            flanked = bool(before) and not before.isspace() and bool(after) and not after.isspace()
            edits.append((m.start(), m.end(), " " if flanked else ""))
        return edits


# The em-dash is the creative writer's native tool, so dash normalization is
# skipped there; in every other register the autofixer replaces it.
DASH_KEEP_REGISTERS = frozenset({"creative"})

# Dash-as-pause constructs the autofixer rewrites to a comma. Each alternative
# keeps the surrounding inline spaces in the match so they collapse cleanly:
#   em-dash (tight or spaced), en-dash (range guard applied below),
#   ASCII `--`, and a spaced hyphen between lowercase words.
AUTOFIX_DASH_RE = re.compile(
    r"[ \t]*—[ \t]*|[ \t]*–[ \t]*|(?<=\w)[ \t]*--[ \t]*(?=\w)|[ \t]--[ \t]"
    r"|(?<=[a-z]) - (?=[a-z])")

# A paired dashed aside on one line: "the result — surprisingly — held". Rewriting
# both dashes to commas is correct but monotonous, and parentheses are what a
# person reaches for. Matched before the single-dash rule so the pair wins.
# The aside must stay inside one clause: no sentence-ending punctuation, no table
# pipe, no code mask, and both marks the same character so a following numeric
# en-dash range cannot be mistaken for the closing mark.
PAIRED_ASIDE_RE = re.compile(
    "[ \t]*(?P<d>[—–])[ \t]*"
    "(?P<inner>[^—–\n.;:!?|\x00]{1,45}?)"
    "[ \t]*(?P=d)[ \t]*")

# A colon only reads right before an enumeration ("three things: speed, cost, and
# risk"). Everywhere else a comma is what a person writes, so the colon rule is
# deliberately narrow: converting every dash to the SAME mark is what trades the
# em-dash signature for a fresh uniform one (principle 2), and converting them to
# the wrong mark is worse than leaving the rhythm flat.
ENUMERATION_TAIL_RE = re.compile(
    r"^[^.;:!?\n]{0,80}?,[^.;:!?\n]{0,40}?,[^.;:!?\n]{0,40}?\b(?:and|or)\b")


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


def _dash_replacement(cs, end):
    """Pick the mark that replaces a dash-as-pause, varying by what follows."""
    tail = cs[end:end + 140]
    return ":" if ENUMERATION_TAIL_RE.match(tail) else ","


class DashFixer(Fixer):
    """Rewrite dash-as-pause marks.

    The replacement VARIES: parentheses around a paired aside, a colon before an
    appositive or list, a comma before a full clause. Numeric en-dash ranges
    (10–20, 2024 – 25) are preserved; compound hyphens (well-known) never match.
    """

    name = "dashes"

    def edits(self, masked, patterns, register):
        if register in DASH_KEEP_REGISTERS:
            return []
        cs = masked
        edits = []
        table_spans = _table_row_spans(cs)
        paired_spans = []
        for m in PAIRED_ASIDE_RE.finditer(cs):
            if any(a <= m.start() < b for a, b in table_spans):
                continue
            if "–" in m.group(0) and is_numeric_en_dash(cs, m):
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
            if "–" in m.group(0) and is_numeric_en_dash(cs, m):
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


__all__ = [
    "Fixer",
    "SAFE_FIX_KEYS",
    "GUIDANCE_SUGGESTION_RE",
    "is_substitution",
    "SwapFixer",
    "EMOJI_KEEP_REGISTERS",
    "AUTOFIX_EMOJI_RE",
    "EmojiFixer",
    "DASH_KEEP_REGISTERS",
    "AUTOFIX_DASH_RE",
    "PAIRED_ASIDE_RE",
    "ENUMERATION_TAIL_RE",
    "DashFixer",
]
