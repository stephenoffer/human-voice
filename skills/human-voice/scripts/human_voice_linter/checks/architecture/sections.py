"""sections — the section model the architecture checks read.

Built once per document (`section_model` is passed to `Document.derive`), so the
three checks share one parse.
"""
from __future__ import annotations

from ...core.check import Check
from ...text.markdown import (
    BARE_URL_RE,
    HEADING_LINE_RE,
    INLINE_CODE_RE,
    LINK_RE,
    LIST_MARKER_RE,
    SECTION_RULE_RE,
    SETEXT_RE,
    TABLE_ROW_RE,
    strip_inline_markup,
)
from ...text.tokens import WORD_RE
from .vocabulary import ABSTRACT_RE, EXPLAINER_RE, HEAD_RE, TECH_MARKER_RE


class Section:
    """What one section spends its words on.

    `words` counts prose and list words; `tech` counts checkable markers plus
    inline code plus a capped share of fenced code; `lists` holds the item count
    of each list of two or more items.
    """

    __slots__ = ("title", "line", "subsections", "words", "prose_words", "list_words",
                 "code_lines", "table_rows", "tech", "explainers", "abstract", "links",
                 "lists")

    def __init__(self, title="", line=1, subsections=0):
        self.title = title
        self.line = line
        self.subsections = subsections
        self.words = self.prose_words = self.list_words = 0
        self.code_lines = self.table_rows = self.tech = 0
        self.explainers = self.abstract = self.links = 0
        self.lists = []

    @property
    def density(self):
        """Checkable markers per 100 words."""
        return self.tech / self.words * 100.0 if self.words else 0.0

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


def _measure(section, cs_lines, raw_lines, start, end):
    """Fill `section` with the counts for lines [start, end)."""
    markers = 0
    inline_code = 0
    lists = []           # item count of each contiguous list run
    run = 0
    for idx in range(start, min(end, len(cs_lines))):
        cs = cs_lines[idx]
        raw = raw_lines[idx] if idx < len(raw_lines) else ""
        if not cs.strip():
            if raw.strip():
                section.code_lines += 1
            continue
        if HEADING_LINE_RE.match(cs) or SETEXT_RE.match(cs) or SECTION_RULE_RE.match(cs):
            if run:
                lists.append(run)
                run = 0
            continue
        if TABLE_ROW_RE.match(cs):
            section.table_rows += 1
            continue
        inline_code += len(INLINE_CODE_RE.findall(raw))
        section.links += len(LINK_RE.findall(raw)) + len(BARE_URL_RE.findall(raw))
        body = strip_inline_markup(cs)
        is_item = bool(LIST_MARKER_RE.match(cs))
        if is_item:
            body = LIST_MARKER_RE.sub("", body, count=1)
            run += 1
        elif run and not cs.startswith((" ", "\t")):
            # A non-indented prose line ends the list; an indented one continues
            # the current item.
            lists.append(run)
            run = 0
        n = len(WORD_RE.findall(body))
        if is_item:
            section.list_words += n
        else:
            section.prose_words += n
        markers += len(TECH_MARKER_RE.findall(body))
        section.explainers += len(EXPLAINER_RE.findall(body))
        section.abstract += len(ABSTRACT_RE.findall(body))
    if run:
        lists.append(run)
    section.words = section.prose_words + section.list_words
    # Code is depth. A fenced block counts a marker for every three lines, capped
    # so a long listing cannot make an otherwise hollow section look dense.
    section.tech = markers + inline_code + min(section.code_lines, 60) // 3
    section.lists = [n for n in lists if n >= 2]
    return section


def document_sections(text, code_stripped):
    """Split a markdown document into its top-level sections.

    The section level is the shallowest heading level that occurs at least twice,
    skipping a lone title heading: `# Title` followed by `## A`, `## B`, `## C`
    gives three sections at level 2, each owning its `###` subsections. Returns
    (sections, preamble): a list of `Section`, and a `Section` for whatever
    precedes the first section heading (None when the document has fewer than two
    section headings).

    `text` is the normalized source and `code_stripped` the same text with code
    blanked; strip_code preserves line geometry, so a line that is blank in the
    stripped copy and not blank in the source is a line of fenced code.
    """
    cs_lines = code_stripped.split("\n")
    raw_lines = text.split("\n")
    heads = []
    for i, ln in enumerate(cs_lines):
        m = HEAD_RE.match(ln)
        if m:
            heads.append((i, len(m.group(1)), strip_inline_markup(m.group(2)).strip()))
    level = None
    for lvl in sorted({h[1] for h in heads}):
        at = [h for h in heads if h[1] == lvl]
        if len(at) >= 2:
            level = lvl
            break
    if level is None:
        return [], None

    starts = [h for h in heads if h[1] == level]
    sections = []
    for i, _lvl, title in starts:
        end = len(cs_lines)
        for j, l2, _t in heads:
            if j > i and l2 <= level:
                end = j
                break
        subsections = sum(1 for j, l2, _t in heads if i < j < end and l2 > level)
        sections.append(_measure(Section(title, i + 1, subsections),
                                 cs_lines, raw_lines, i + 1, end))
    preamble = _measure(Section(), cs_lines, raw_lines, 0, starts[0][0])
    return sections, preamble


def section_model(doc):
    """(sections, preamble) for a Document; pass to `doc.derive`."""
    return document_sections(doc.source, doc.code_stripped)


class SectionCheck(Check):
    """A check over the section model. Subclasses implement `check_sections`."""

    def run(self, doc, ctx):
        sections, preamble = doc.derive(section_model)
        self.check_sections(sections, preamble, doc, ctx)

    def check_sections(self, sections, preamble, doc, ctx):
        raise NotImplementedError


__all__ = ["Section", "document_sections", "section_model", "SectionCheck"]
