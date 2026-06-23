"""hit — the finding data model emitted by every check."""
from __future__ import annotations


class Hit:
    """A single flagged tell: its category, source location, and the text."""

    __slots__ = ("category", "line", "text", "suggestion")

    def __init__(self, category: str, line: int, text: str,
                 suggestion: str | None = None) -> None:
        self.category = category
        self.line = line
        self.text = text
        self.suggestion = suggestion

    def as_dict(self) -> dict:
        d: dict = {"category": self.category, "line": self.line, "text": self.text}
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


__all__ = [
    "Hit",
]
