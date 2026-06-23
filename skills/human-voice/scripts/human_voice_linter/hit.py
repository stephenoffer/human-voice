"""hit — the finding data model emitted by every check."""
from __future__ import annotations


class Hit:
    """A single flagged tell: its category, source location, and the text.

    `line` is 1-based; `line == 0` marks a document-level finding with no single
    source position (burstiness, uniformity, etc.). `col`/`end_line`/`end_col`
    are 1-based character offsets, set only by checks whose match text shares the
    source file's geometry (so the columns point at the real characters); other
    checks leave them None and report the line only.
    """

    __slots__ = ("category", "line", "text", "suggestion", "col", "end_line", "end_col")

    def __init__(self, category: str, line: int, text: str,
                 suggestion: str | None = None, col: int | None = None,
                 end_line: int | None = None, end_col: int | None = None) -> None:
        self.category = category
        self.line = line
        self.text = text
        self.suggestion = suggestion
        self.col = col
        self.end_line = end_line
        self.end_col = end_col

    def as_dict(self) -> dict:
        d: dict = {"category": self.category, "line": self.line, "text": self.text}
        if self.suggestion:
            d["suggestion"] = self.suggestion
        if self.col is not None:
            d["col"] = self.col
        if self.end_line is not None:
            d["end_line"] = self.end_line
        if self.end_col is not None:
            d["end_col"] = self.end_col
        if self.line == 0:
            d["scope"] = "document"
        return d


__all__ = [
    "Hit",
]
