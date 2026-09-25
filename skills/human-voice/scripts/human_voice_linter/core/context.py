"""context — the mutable state of one lint run, shared by every check."""
from __future__ import annotations

import functools

from ..config.registers import Thresholds
from ..text.phrases import build_protected_spans
from .document import Document
from .hit import Hit


class LintContext:
    """What a check reads (config) and writes (hits, metrics) during one run.

    - `threshold(key)`: the resolved, register-scaled threshold.
    - `patterns`: the merged pattern file, for checks that read a list from it.
    - `emit(hit)`: record a finding. `hits` is the ordered list.
    - `report[key] = value`: record a metric. Metrics are reported whether or not
      the check fires, so a writer can see a trend before it trips.
    - `seen_spans`: per-category spans already flagged, so overlapping phrase
      lists never double-flag the same words.
    """

    def __init__(self, doc: Document, patterns: dict, register: str,
                 dialect: str | None = None) -> None:
        self.doc = doc
        self.patterns = patterns
        self.register = register
        self.dialect = dialect
        self.threshold = Thresholds(patterns, register)
        self.hits: list = []
        self.report: dict = {}
        self.seen_spans: dict = {}

    def emit(self, hit: Hit) -> None:
        self.hits.append(hit)

    @functools.cached_property
    def protected(self) -> list:
        """Spans where an otherwise-flagged word is legitimate: fixed phrases
        (context_exceptions) plus project-specific protected terms."""
        return build_protected_spans(
            self.doc.code_stripped,
            list(self.patterns.get("context_exceptions") or [])
            + list(self.patterns.get("protected_terms") or []))


__all__ = ["LintContext"]
