"""check — the base classes every check is built from.

A check is an object with a `category` and a `run(doc, ctx)` method. It reads the
prepared `Document`, writes metrics to `ctx.report`, and emits `Hit`s through
`ctx.emit`. Checks hold configuration only, never per-run state, so one instance
serves every document.

Four shapes cover most of the linter:

- `Check`: the base. Bespoke checks subclass it and implement `run`.
- `Diagnostic`: report-only. Writes metrics, never emits a hit.
- `DensityCheck`: one document-level finding when a construction's rate per
  1,000 words passes a threshold (passive voice, adverbs, copulas).
- `RateCheck`: one instance finding per occurrence, but only once the
  construction has become a habit: gated on a minimum count, a minimum length,
  and a per-1,000-word rate (clefts, participial tails, clause splices).
"""
from __future__ import annotations

from ..text.stats import per_1k
from .hit import Hit

# How many instance findings a single check will emit. This bounds memory and
# output on a hostile input; it is NOT a display limit. It used to be 6 or 8,
# inlined per check, and that silently capped the SCORE too: a 5,000-word document
# with fifty em-dashes emitted eight hits and scored the same as one with eight,
# because the density is computed from the hits the check produced. Display
# truncation belongs in the report layer, which already says "... and N more".
MAX_INSTANCE_HITS = 200


def clip(text, limit):
    """`text` cut to `limit` characters, ending in "..." when it was cut."""
    return text if len(text) <= limit else text[:limit - 3] + "..."


def context_around(text, start, end, before, after):
    """The match plus a little of what surrounds it, on one line."""
    return text[max(0, start - before):end + after].replace("\n", " ").strip()


class Check:
    """One tell. Subclasses set `category` and implement `run`."""

    category: str = ""

    def run(self, doc, ctx) -> None:
        raise NotImplementedError

    def hit(self, line, text, suggestion=None) -> Hit:
        """A finding at `line` (0 for a document-level finding)."""
        return Hit(self.category, line, text, suggestion)

    def span_hit(self, lines, m, text, suggestion=None) -> Hit:
        """A finding carrying a precise (line, col)->(end_line, end_col) span.

        Use only when `m` was matched against a text whose geometry matches the
        source file (code_stripped or the raw text); otherwise the columns would
        point at the wrong characters and `hit` should be used instead.
        """
        ln, col, eln, ecol = lines.loc(m.start(), m.end())
        return Hit(self.category, ln, text, suggestion, col=col, end_line=eln, end_col=ecol)

    def __repr__(self) -> str:
        return "<%s %s>" % (type(self).__name__, self.category or "(report-only)")


class Diagnostic(Check):
    """Reported, never scored: writes metrics and emits nothing."""

    category = ""


class DensityCheck(Check):
    """A document-level finding when `measure` passes `threshold_key` per 1k words.

    Subclasses implement `measure(doc, ctx) -> (count, detail)`; `detail` is
    appended to the finding's text (examples, for instance). The rate is written
    to `metric_key` every run.
    """

    threshold_key: str = ""
    metric_key: str = ""
    label: str = ""
    suggestion: str = ""
    min_words: int = 150
    min_count: int = 3

    def measure(self, doc, ctx):
        raise NotImplementedError

    def extra_metrics(self, doc, ctx) -> None:
        """Metrics recorded after the rate. Optional."""

    def run(self, doc, ctx) -> None:
        count, detail = self.measure(doc, ctx)
        rate = per_1k(count, doc.word_count)
        ctx.report[self.metric_key] = round(rate, 1)
        self.extra_metrics(doc, ctx)
        threshold = ctx.threshold(self.threshold_key)
        if doc.word_count >= self.min_words and rate > threshold and count >= self.min_count:
            ctx.emit(self.hit(0, "%s: %.0f / 1k words (floor %.0f)%s"
                              % (self.label, rate, threshold, detail), self.suggestion))


class RateCheck(Check):
    """Instance findings for a construction that is only a tell when stacked.

    Every construction a RateCheck measures is ordinary English used well by
    people, so a lone instance means nothing. Subclasses implement
    `matches(doc)` (regex matches against `doc.metric_prose`) and `snippet`.
    `<metric>_count` and `<metric>_per_1k` are reported every run.
    """

    threshold_key: str = ""
    metric: str = ""
    suggestion: str = ""
    min_count: int = 3
    min_words: int = 150

    def matches(self, doc) -> list:
        raise NotImplementedError

    def snippet(self, doc, m) -> str:
        return m.group(0).strip()

    def run(self, doc, ctx) -> None:
        found = self.matches(doc)
        count = len(found)
        rate = per_1k(count, doc.word_count)
        ctx.report[self.metric + "_count"] = count
        ctx.report[self.metric + "_per_1k"] = round(rate, 1)
        if (doc.word_count < self.min_words or count < self.min_count
                or rate <= ctx.threshold(self.threshold_key)):
            return
        for m in found[:MAX_INSTANCE_HITS]:
            ctx.emit(self.hit(doc.metric_lines.line_of(m.start()), self.snippet(doc, m),
                              self.suggestion))


__all__ = [
    "MAX_INSTANCE_HITS",
    "clip",
    "context_around",
    "Check",
    "Diagnostic",
    "DensityCheck",
    "RateCheck",
]
