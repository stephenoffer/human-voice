"""punctuation — dashes, quotes, doubled words, and punctuation mechanics."""
from __future__ import annotations

import re

from ..core.check import MAX_INSTANCE_HITS, Check, context_around
from ..text.dashes import PAIRED_DASH_RE, pause_dashes
from ..text.stats import per_1k


class EmDashCheck(Check):
    """Em-dash density, and the paired dashed aside even below the density bar."""

    category = "em_dash"

    def run(self, doc, ctx):
        text = doc.metric_prose
        lines = doc.metric_lines
        matches = pause_dashes(text)
        count = len(matches)
        rate = per_1k(count, doc.word_count)
        ctx.report["em_dash_per_1k"] = round(rate, 1)
        ctx.report["em_dash_count"] = sum(1 for m in matches if "—" in m.group(0) or "--" in m.group(0))
        ctx.report["en_dash_count"] = sum(1 for m in matches if "–" in m.group(0))
        paired = list(PAIRED_DASH_RE.finditer(text))
        ctx.report["paired_dash_asides"] = len(paired)
        # Three, not two. Two em-dashes is what a person who likes em-dashes writes in
        # an email; the tell is the dash becoming the default connector. The paired
        # aside below still fires at two, because "— like this —" is a distinct tic
        # rather than a rate.
        if rate > ctx.threshold("em_dash_per_1k_words") and count >= 3:
            for m in matches[:MAX_INSTANCE_HITS]:
                ctx.emit(self.hit(lines.line_of(m.start()),
                                  context_around(text, m.start(), m.start(), 15, 15),
                                  "use a comma, period, or parens"))
        # Paired dash asides are a distinctive tic even below the density floor.
        elif len(paired) >= 2:
            for m in paired[:MAX_INSTANCE_HITS]:
                ctx.emit(self.hit(lines.line_of(m.start()),
                                  m.group(0).replace("\n", " ").strip(),
                                  "rework the dashed aside as its own sentence or parens"))


# ASCII double-hyphen used as a dash ("draft--like this" or "spaced -- like so").
ASCII_DASH_RE = re.compile(r"(?<=\w)--(?=\w)|\s--\s")
# An em-dash that hugs its words on both sides (no spaces): "word—word".
EM_TIGHT_RE = re.compile(r"\w—\w")
# An em-dash spaced on both sides: "word — word".
EM_SPACED_RE = re.compile(r"\w\s—\s\w")
# Spaced hyphen standing in for a dash between lowercase words: "this - that".
SPACED_HYPHEN_DASH_RE = re.compile(r"(?<=[a-z]) - (?=[a-z])")

# Above this many occurrences of one dash convention, the finding is the
# convention rather than the instances, and it is reported once.
DASH_STYLE_INSTANCE_MAX = 5


class DashStyleCheck(Check):
    """Dash *correctness and consistency*, distinct from em-dash density.

    Flags ASCII `--` standing in for a real dash, a spaced hyphen used as a
    dash, and a document that mixes spaced and unspaced em-dashes.
    """

    category = "dash_style"

    def run(self, doc, ctx):
        text = doc.adjacency_prose
        ascii_dd = list(ASCII_DASH_RE.finditer(text))
        spaced_hyphen = list(SPACED_HYPHEN_DASH_RE.finditer(text))
        tight = len(EM_TIGHT_RE.findall(text))
        spaced = len(EM_SPACED_RE.findall(text))
        ctx.report["dash_ascii_double"] = len(ascii_dd)
        ctx.report["dash_spaced_hyphen"] = len(spaced_hyphen)
        ctx.report["em_dash_spacing_mixed"] = bool(tight and spaced)
        # A handful of stray `--` is a per-line finding a writer fixes one at a time.
        # A hundred of them is one house style and one find-and-replace, so report it
        # once rather than charging for every occurrence: a reference manual written in
        # the `name -- description` convention was otherwise pinned at the category cap
        # by a single stylistic decision.
        self._findings(ascii_dd, "--", "use an em-dash (—) or rework; '--' reads as raw markup",
                       doc, ctx)
        self._findings(spaced_hyphen, "a spaced hyphen used as a dash",
                       "a spaced hyphen isn't a dash; use a comma, period, or em-dash",
                       doc, ctx)
        if tight and spaced:
            ctx.emit(self.hit(0, "em-dash spacing is inconsistent (both word—word and word — word)",
                              "pick one em-dash spacing convention and hold it"))

    def _findings(self, matches, label, suggestion, doc, ctx):
        if not matches:
            return
        text = doc.adjacency_prose
        lines = doc.adjacency_lines
        if len(matches) <= DASH_STYLE_INSTANCE_MAX:
            for m in matches:
                ctx.emit(self.hit(lines.line_of(m.start()),
                                  context_around(text, m.start(), m.end(), 8, 8) or label,
                                  suggestion))
            return
        where = ", ".join("L%d" % lines.line_of(m.start()) for m in matches[:6])
        ctx.emit(self.hit(0, "%d occurrences of %s (first at %s)" % (len(matches), label, where),
                          suggestion + "; this is one find-and-replace, not %d edits"
                          % len(matches)))


# Consecutive identical words ("the the"), case-insensitive. The gap is spaces
# or tabs only (no newline), so a word ending one line/heading and the same word
# opening the next (e.g. "...use it" / "It does...") is not a false doubling.
# Excludes words that legitimately repeat ("had had", "that that").
# The gap is ONE space or tab. A doubled word is a typing slip and it leaves a
# single space; three or more spaces is column alignment, and matching it flagged
# every two-column reference table ("match     Match a regular expression").
DOUBLED_WORD_RE = re.compile(r"\b([A-Za-z]{2,})\b[ \t]{1,2}\1\b", re.IGNORECASE)
DOUBLE_OK = {"that", "had", "ha", "no", "so", "very", "really", "blah", "yeah",
             "ok", "bye", "din", "tut", "hear", "now"}


class DoubledWordCheck(Check):
    category = "doubled_word"

    def run(self, doc, ctx):
        matches = [m for m in DOUBLED_WORD_RE.finditer(doc.adjacency_prose)
                   if m.group(1).lower() not in DOUBLE_OK]
        ctx.report["doubled_words"] = len(matches)
        for m in matches[:MAX_INSTANCE_HITS]:
            ctx.emit(self.hit(doc.adjacency_lines.line_of(m.start()),
                              m.group(0).replace("\n", " "),
                              "remove the duplicated word"))


# Space before sentence punctuation: "word ," / "word ;" / "word ?".
# `word :` is a mechanical error; `plus one :-)` is a smiley and `see :func:`x``
# is a role marker. Require the punctuation NOT to be the head of an emoticon or a
# reStructuredText role.
SPACE_BEFORE_PUNCT_RE = re.compile(r"\w[ \t]+([,;:!?])(?![-)(|/\\DPpO0<>*^]|\w+:)")
# Repeated terminal punctuation: "!!", "??", or 3+ mixed ("?!?"). A lone "?!"
# (one of each) is left alone as a legitimate interrobang.
MULTI_PUNCT_RE = re.compile(r"!{2,}|\?{2,}|[!?]{3,}")


class MechanicsCheck(Check):
    category = "mechanics"

    def run(self, doc, ctx):
        text = doc.adjacency_prose
        lines = doc.adjacency_lines
        space_before = list(SPACE_BEFORE_PUNCT_RE.finditer(text))
        multi_punct = list(MULTI_PUNCT_RE.finditer(text))
        ctx.report["space_before_punct"] = len(space_before)
        ctx.report["multi_terminal_punct"] = len(multi_punct)
        for m in space_before[:MAX_INSTANCE_HITS]:
            ctx.emit(self.hit(lines.line_of(m.start()),
                              context_around(text, m.start(), m.end(), 6, 4),
                              "no space before '%s'" % m.group(1)))
        for m in multi_punct[:MAX_INSTANCE_HITS]:
            ctx.emit(self.hit(lines.line_of(m.start()), m.group(0),
                              "one punctuation mark is enough"))


_CURLY_RE = re.compile(r"[‘’“”]")
_STRAIGHT_QUOTE_RE = re.compile(r"(?<![\w=])[\"'](?=\w)|(?<=\w)[\"'](?![\w=])")


class QuoteStyleCheck(Check):
    """Straight and curly quotes mixed in one document.

    Either convention is fine held consistently, and a word processor produces
    curly quotes throughout. A document carrying BOTH usually has a seam in it:
    text that came out of a chat product (which emits curly) pasted beside text
    someone typed (straight). Same logic as the dialect and heading-case checks
    -- the tell is the inconsistency, not either style.
    """

    category = "quote_style"

    def run(self, doc, ctx):
        text = doc.metric_prose
        curly = list(_CURLY_RE.finditer(text))
        straight = list(_STRAIGHT_QUOTE_RE.finditer(text))
        ctx.report["curly_quotes"] = len(curly)
        ctx.report["straight_quotes"] = len(straight)
        if not curly or not straight:
            return
        total = len(curly) + len(straight)
        minority = curly if len(curly) <= len(straight) else straight
        # A seam is a lopsided mix in a document with enough quotes to judge. Two of
        # each is a document that quotes code beside quoted speech, not a paste.
        if total < 6 or len(minority) * 4 > total:
            return
        for m in minority[:6]:
            ctx.emit(self.hit(doc.metric_lines.line_of(m.start()), m.group(0),
                              "hold one quote convention through the document"))


class PunctuationSubstitutionCheck(Check):
    """The humanizer's own fingerprint: every em-dash swapped for one other mark.

    Principle 2 says the em-dash fix has to VARY the replacement, and this is the
    check that holds the tool to it. A writer who reaches for semicolons also
    reaches for dashes; a document with an unusual semicolon rate and not one dash
    has been through a mechanical pass, and the flat substitution is a fresh
    uniform signature in place of the old one. Measured on this repo's corpus the
    human maximum is 5.5 semicolons per 1,000 words, and three of the shipped
    rewrites were over it before this check existed.
    """

    category = "over_correction"
    min_words = 150

    def run(self, doc, ctx):
        words = doc.word_count
        if not words:
            return
        text = doc.metric_prose
        semis = text.count(";")
        rate = semis / words * 1000.0
        dashes = len(pause_dashes(text))
        ctx.report["semicolon_per_1k"] = round(rate, 1)
        if (words >= self.min_words and rate > ctx.threshold("semicolon_per_1k_max")
                and semis >= 3 and dashes == 0):
            ctx.emit(self.hit(0, "%.0f semicolons / 1k words and no dashes at all" % rate,
                              "vary the replacement mark: a comma here, a period there, "
                              "parentheses elsewhere. One substitute everywhere is a new "
                              "uniform signature"))


__all__ = [
    "EmDashCheck",
    "DashStyleCheck",
    "DoubledWordCheck",
    "MechanicsCheck",
    "QuoteStyleCheck",
    "PunctuationSubstitutionCheck",
]
