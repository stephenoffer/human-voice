"""engine — run the checks over one document and filter what they found."""
from __future__ import annotations

from .checks import DEFAULT_CHECKS
from .config.directives import directive_suppresses, parse_directives
from .config.registers import muted_categories
from .core.context import LintContext
from .core.document import Document


class Linter:
    """A pattern configuration and the checks to run with it.

    `Linter(patterns).analyze(text, register)` returns (hits, report, word_count).
    Pass `checks` to run a subset or a custom set; the default is every check, in
    the order the golden eval results were produced with.
    """

    def __init__(self, patterns: dict, checks=None) -> None:
        self.patterns = patterns
        self.checks = tuple(DEFAULT_CHECKS if checks is None else checks)

    def analyze(self, text: str, register: str, dialect: str | None = None) -> tuple:
        doc = Document(text)
        ctx = LintContext(doc, self.patterns, register, dialect)
        for check in self.checks:
            check.run(doc, ctx)
        muted = muted_categories(register, self.patterns)
        hits = [h for h in ctx.hits if h.category not in muted]
        # Inline ignore directives (HTML comments) suppress specific lines/categories.
        ignored = parse_directives(doc.source)
        if ignored:
            hits = [h for h in hits if not directive_suppresses(h, ignored)]
        ctx.report["word_count"] = doc.word_count
        ctx.report["sentence_count"] = len(doc.sentences)
        return hits, ctx.report, doc.word_count


def analyze(text: str, register: str, dialect: str | None,
            patterns: dict) -> tuple:
    """Run every check over `text` and return (hits, report, word_count)."""
    return Linter(patterns).analyze(text, register, dialect)


__all__ = ["Linter", "analyze"]
