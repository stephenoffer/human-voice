"""linemap — offset-to-line lookups for the texts the checks match against."""
from __future__ import annotations

import bisect


def line_of(text, index):
    return text.count("\n", 0, index) + 1


class LineMap:
    """Precomputed newline offsets for O(log n) line lookups.

    `line_of` is called once per hit; on a large document with many hits the
    naive str.count from offset 0 is quadratic. Build one of these per text and
    bisect each index instead.
    """

    __slots__ = ("offsets",)

    def __init__(self, text):
        push = self.offsets = []
        start = 0
        while True:
            nl = text.find("\n", start)
            if nl < 0:
                break
            push.append(nl)
            start = nl + 1

    def line_of(self, index):
        return bisect.bisect_left(self.offsets, index) + 1

    def loc(self, start, end):
        """Return (line, col, end_line, end_col), all 1-based, for [start, end).

        Columns are only meaningful when the index refers to a text whose
        geometry matches the source file (e.g. code_stripped or the raw text);
        callers working on markup-stripped text should not pass columns through.
        """
        line = bisect.bisect_left(self.offsets, start) + 1
        line_start = (self.offsets[line - 2] + 1) if line > 1 else 0
        end_line = bisect.bisect_left(self.offsets, end) + 1
        end_line_start = (self.offsets[end_line - 2] + 1) if end_line > 1 else 0
        return line, start - line_start + 1, end_line, end - end_line_start + 1


class MappedLineMap:
    """Reports SOURCE line numbers for positions in a derived text.

    `prose_for_metrics` joins soft-wrapped lines, so an offset in its output does not
    correspond to the same line in the source. This holds the segment table that
    function builds -- (offset in the derived text, source line) for every piece it
    contributed -- and binary-searches it, so a hit resolves to the exact source line
    rather than to the line its paragraph happened to start on.

    Without this, every check located against the metric text reported a line from
    the reduced text: a 75-line document collapses to 12, so a finding on line 42 was
    reported as line 8. That pointed readers at the wrong place and made inline
    `<!-- human-voice: ignore -->` directives, which are keyed on source lines,
    unable to match the hits they were written to suppress.
    """

    __slots__ = ("_lm", "_offsets", "_lines")

    def __init__(self, derived_text, segments):
        self._lm = LineMap(derived_text)
        segs = sorted(segments or [])
        self._offsets = [off for off, _ in segs]
        self._lines = [ln for _, ln in segs]

    def line_of(self, index):
        if not self._offsets:
            return self._lm.line_of(index)
        i = bisect.bisect_right(self._offsets, index) - 1
        if i < 0:
            i = 0
        return self._lines[i]


__all__ = ["line_of", "LineMap", "MappedLineMap"]
