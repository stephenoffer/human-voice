"""paragraphs — the paragraph and list-item level: even lengths, templated
openings, and the essay mold that ends by restating its introduction."""
from __future__ import annotations

import re
from collections import Counter

from ..core.check import Check
from ..text.markdown import HEADING_LINE_RE, SECTION_RULE_RE, TABLE_ROW_RE, strip_inline_markup
from ..text.prose import BLANK_LINE_SPLIT_RE
from ..text.stats import cov, rounded
from ..text.tokens import STOPWORDS, WORD_RE, first_words


class ParagraphUniformityCheck(Check):
    category = "paragraph_uniformity"
    min_paras = 4

    def run(self, doc, ctx):
        counts = [len(WORD_RE.findall(p)) for p in doc.paragraphs]
        spread = cov(counts)
        ctx.report["paragraph_len_cov"] = rounded(spread)
        floor = ctx.threshold("paragraph_cov_floor")
        if len(counts) >= self.min_paras and spread is not None and spread < floor:
            ctx.emit(self.hit(0, "paragraph-length CoV %.2f (floor %.2f)" % (spread, floor),
                              "vary paragraph length; AI drafts are suspiciously even"))


class ListUniformityCheck(Check):
    category = "list_uniformity"
    min_items = 4

    def run(self, doc, ctx):
        counts = [len(WORD_RE.findall(item)) for item in doc.list_items]
        spread = cov(counts)
        ctx.report["list_item_cov"] = rounded(spread)
        floor = ctx.threshold("list_item_cov_floor")
        if len(counts) >= self.min_items and spread is not None and spread < floor:
            ctx.emit(self.hit(0, "list-item-length CoV %.2f (floor %.2f)" % (spread, floor),
                              "uniform list items read as generated; vary or convert to prose"))


class CircularConclusionCheck(Check):
    """A closing block built from the opening block's words."""

    category = "circular_conclusion"
    min_paras = 3
    overlap = 0.5

    def run(self, doc, ctx):
        prose = []
        for block in BLANK_LINE_SPLIT_RE.split(doc.code_stripped):
            if not block.strip():
                continue
            lines = [ln for ln in block.split("\n")
                     if not (HEADING_LINE_RE.match(ln) or SECTION_RULE_RE.match(ln)
                             or TABLE_ROW_RE.match(ln))]
            text = strip_inline_markup(" ".join(lines))
            if WORD_RE.findall(text):
                prose.append([w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOPWORDS])
        ctx.report["prose_blocks"] = len(prose)
        if len(prose) < self.min_paras:
            ctx.report["conclusion_overlap"] = None
            return
        first, last = set(prose[0]), set(prose[-1])
        if not first or not last:
            ctx.report["conclusion_overlap"] = None
            return
        jacc = len(first & last) / len(first | last)
        ctx.report["conclusion_overlap"] = round(jacc, 2)
        if jacc >= self.overlap:
            ctx.emit(self.hit(0, "closing paragraph repeats the opening (overlap %.2f)" % jacc,
                              "end on the last real point; cut the recap"))


CONCLUSION_OPENER_RE = re.compile(
    r"^\s*(?:in conclusion|in summary|to sum up|to summarize|to summarise|"
    r"in closing|all in all|in short|to conclude|overall,|ultimately,)\b",
    re.IGNORECASE)


class FiveParagraphShapeCheck(Check):
    """The intro / three-body / 'in conclusion' wrap-up essay mold.

    A doc-level structural tell readers cite often (the five-paragraph shape).
    Fires only when a multi-paragraph piece closes on an explicit conclusion
    marker, so a normal essay that simply ends is left alone.
    """

    category = "five_paragraph_shape"
    # The upper bound was 9, which let a 12-paragraph report close on "In
    # conclusion, ..." unflagged -- the recap is the tell, and it does not stop
    # being one because the piece is long. Only the floor is a real constraint:
    # a three-paragraph note has no essay shape to critique.
    min_paras = 4

    def run(self, doc, ctx):
        paras = doc.paragraphs
        ctx.report["prose_paragraphs"] = len(paras)
        if len(paras) < self.min_paras:
            return
        if CONCLUSION_OPENER_RE.match(paras[-1]):
            ctx.emit(self.hit(0, "%d-paragraph essay closing on a conclusion wrap-up" % len(paras),
                              "let the structure follow the argument; end on the last real "
                              "point, not a recap"))


class ParagraphOpenersCheck(Check):
    """Paragraphs that all open with the same PHRASE.

    `uniform_openers` measures sentences and misses this: a draft can vary inside
    a paragraph and still start every paragraph the same way. Paragraph openings
    are what a reader skims, so repetition there is disproportionately visible.

    Keyed on the first TWO words, not the first one. "The" is the most common word
    in English and three paragraphs starting with it says nothing -- that version
    of the check flagged a human business proposal whose paragraphs opened "The
    math:", "The real win", "The warehouse". Two words separate a shared article
    from a shared opening move.
    """

    category = "paragraph_openers"
    min_paras = 5
    repeat_ratio = 0.4

    def run(self, doc, ctx):
        paras = doc.paragraphs
        openers = [w for w in (first_words(p, 2) for p in paras) if w and len(w) == 2]
        ctx.report["paragraph_count"] = len(paras)
        if len(openers) < self.min_paras:
            ctx.report["paragraph_opener_repeat"] = None
            return
        phrase, count = Counter(openers).most_common(1)[0]
        ratio = count / len(openers)
        ctx.report["paragraph_opener_repeat"] = round(ratio, 2)
        if ratio >= self.repeat_ratio and count >= 3:
            ctx.emit(self.hit(0, '%d of %d paragraphs open with "%s"'
                              % (count, len(openers), " ".join(phrase)),
                              "vary how paragraphs begin; readers skim the first words of each"))


class BulletOpenersCheck(Check):
    """List items that all open with the same word or the same part of speech.

    Templated bullets ("Improve...", "Reduce...", "Increase...") are the list-level
    version of parallel structure: the shape is filled in rather than written. A
    deliberately parallel list is a real technique, so this needs a clear majority
    and at least four items before it says anything.
    """

    category = "bullet_openers"
    min_items = 4
    repeat_ratio = 0.6

    def run(self, doc, ctx):
        items = doc.list_items
        if len(items) < self.min_items:
            ctx.report["bullet_opener_repeat"] = None
            return
        firsts = [WORD_RE.findall(i.lower())[0] for i in items]
        word, count = Counter(firsts).most_common(1)[0]
        ratio = count / len(firsts)
        ctx.report["bullet_opener_repeat"] = round(ratio, 2)
        gerunds = sum(1 for f in firsts if f.endswith("ing") and len(f) > 5)
        if ratio >= self.repeat_ratio and count >= 3:
            ctx.emit(self.hit(0, '%d of %d list items open with "%s"' % (count, len(firsts), word),
                              "vary the item openings, or fold the list into a sentence"))
        elif len(firsts) >= self.min_items and gerunds / len(firsts) >= 0.75:
            ctx.emit(self.hit(0, "%d of %d list items open with an -ing verb"
                              % (gerunds, len(firsts)),
                              "a list of gerunds reads as generated; use varied phrasing"))


__all__ = [
    "ParagraphUniformityCheck",
    "ListUniformityCheck",
    "CircularConclusionCheck",
    "FiveParagraphShapeCheck",
    "ParagraphOpenersCheck",
    "BulletOpenersCheck",
]
