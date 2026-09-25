"""document — one input, prepared once, with every view of it a check reads."""
from __future__ import annotations

import functools

from ..text.linemap import LineMap, MappedLineMap
from ..text.markdown import blank_frontmatter, normalize_text, strip_code
from ..text.prose import list_items, prose_for_adjacency, prose_for_metrics, prose_paragraphs
from ..text.tokens import WORD_RE, sentences


class Document:
    """The texts and line maps a check matches against.

    Checks read one of three texts, and each has a line map that resolves an
    offset in it to a SOURCE line:

    - `code_stripped` (with `code_lines`): the source with code blanked and line
      geometry kept, so columns are exact. Lexical and markdown-shape checks.
    - `metric_prose` (with `metric_lines`): markup removed and soft-wrapped lines
      joined, so sentences segment correctly. Rhythm, syntax, and density checks.
    - `adjacency_prose` (with `adjacency_lines`): each stripped span replaced by
      one placeholder word, so no phantom gap appears. Dash and mechanics checks.

    `source` is the normalized text with front matter blanked. Everything derived
    beyond the core views is computed on first use and cached, and `derive()`
    gives check families outside this module the same caching (the architecture
    checks share one section model through it).
    """

    def __init__(self, text: str) -> None:
        # Normalize here too, not only in read_input: api.lint() and the eval harness
        # hand text straight to analyze, and CRLF endings alone were enough to make the
        # same file score differently through the library than through the CLI.
        self.source = blank_frontmatter(normalize_text(text))
        self.code_stripped = strip_code(self.source)
        self.metric_prose, segments = prose_for_metrics(self.code_stripped, with_line_map=True)
        self.sentences = sentences(self.metric_prose)
        self.tokens = [w.lower() for w in WORD_RE.findall(self.metric_prose)]  # tokenize once
        self.word_count = len(self.tokens)
        # One LineMap per distinct text so each hit's line lookup is O(log n).
        self.code_lines = LineMap(self.code_stripped)
        # Report SOURCE lines, not lines of the reduced metric text.
        self.metric_lines = MappedLineMap(self.metric_prose, segments)
        self._derived: dict = {}

    @functools.cached_property
    def adjacency_prose(self) -> str:
        return prose_for_adjacency(self.source)

    @functools.cached_property
    def adjacency_lines(self) -> LineMap:
        return LineMap(self.adjacency_prose)

    @functools.cached_property
    def paragraphs(self) -> list:
        """Prose paragraphs (headings, rules, tables, and list items removed)."""
        return prose_paragraphs(self.code_stripped)

    @functools.cached_property
    def list_items(self) -> list:
        return list_items(self.code_stripped)

    def derive(self, factory):
        """`factory(self)`, computed once per document and cached by factory."""
        if factory not in self._derived:
            self._derived[factory] = factory(self)
        return self._derived[factory]


__all__ = ["Document"]
