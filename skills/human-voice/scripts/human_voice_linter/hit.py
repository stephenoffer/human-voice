"""hit — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations



class Hit:
    __slots__ = ("category", "line", "text", "suggestion")

    def __init__(self, category, line, text, suggestion=None):
        self.category = category
        self.line = line
        self.text = text
        self.suggestion = suggestion

    def as_dict(self):
        d = {"category": self.category, "line": self.line, "text": self.text}
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


# ---------------------------------------------------------------------------
# Loading / input (never raises on bad data; exits 2 only when truly unusable)
# ---------------------------------------------------------------------------


__all__ = [
    'Hit',
]
