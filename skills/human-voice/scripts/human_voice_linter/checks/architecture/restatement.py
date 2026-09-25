"""restatement — the same point made twice, in different places."""
from __future__ import annotations

import re

from ...core.check import Check
from ...text.markdown import LIST_MARKER_RE, is_structural_line, strip_inline_markup
from ...text.tokens import WORD_RE, sentences
from .vocabulary import (
    FRAMING_TITLE_RE,
    HEAD_RE,
    REFERENCE_TITLE_RE,
    VERSION_TITLE_RE,
    content_terms,
    is_content_word,
)

MAX_RESTATEMENT_UNITS = 4000   # bound the pairwise work on a hostile input
MAX_RESTATEMENT_HITS = 40

# A unit that is really a signature or an expression that survived code stripping
# (an indented C prototype, `foo(bar) -> baz`). Two of them match on identifiers.
_CODELIKE_RE = re.compile(r"[;{}]|\w\(|=>|->|::")
_NUMBER_TOKEN_RE = re.compile(r"\d[\d,.:]*(?:\s?%|\s?[A-Za-z]{1,3}\b)?")
_RECAP_WORDS = frozenset(("summary", "summarize", "summarise", "summarizing",
                          "conclusion", "conclude", "recap", "overall"))


class Unit:
    """One sentence or list item, as the restatement comparison sees it.

    A block is a paragraph or one contiguous list; two sentences in the same block
    are the writer building a point, not repeating it, so pairs within a block are
    never compared. `release` marks a unit under a version or year heading.
    """

    __slots__ = ("terms", "line", "block", "section", "text", "title", "release")

    def __init__(self, terms, line, block, section, text, title, release):
        self.terms = terms
        self.line = line
        self.block = block
        self.section = section
        self.text = text
        self.title = title
        self.release = release


def _units(code_stripped):
    """Every sentence and list item, with where it sits in the document."""
    units = []
    block = 0
    section = 0
    title = ""
    stack = []       # (level, title) of the enclosing headings
    release = False  # inside a heading that names a version or a year
    para = []        # (text, line) for the paragraph being joined

    def flush_para():
        if not para:
            return
        joined = ""
        offsets = []
        for t, ln in para:
            offsets.append((len(joined), ln))
            joined += t + " "
        pos = 0
        for s in sentences(joined):
            at = joined.find(s[:40], pos)
            if at < 0:
                at = pos
            pos = at + 1
            line = para[0][1]
            for off, ln in offsets:
                if off <= at:
                    line = ln
            units.append(Unit(content_terms(s), line, block, section, s, title, release))
        para.clear()

    in_list = False
    for lineno, ln in enumerate(code_stripped.split("\n"), 1):
        if not ln.strip() or is_structural_line(ln):
            flush_para()
            if not ln.strip() and in_list:
                # a blank line inside a loose list keeps the list's block
                continue
            block += 1
            in_list = False
            hm = HEAD_RE.match(ln)
            if hm:
                section += 1
                title = strip_inline_markup(hm.group(2)).strip()
                level = len(hm.group(1))
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                release = any(VERSION_TITLE_RE.search(t) for _lv, t in stack)
            continue
        body = strip_inline_markup(ln)
        if LIST_MARKER_RE.match(ln):
            flush_para()
            if not in_list:
                block += 1
                in_list = True
            item = LIST_MARKER_RE.sub("", body, count=1).strip()
            units.append(Unit(content_terms(item), lineno, block, section, item, title, release))
            continue
        if in_list and ln.startswith((" ", "\t")) and units:
            # continuation of the previous item: extend its terms
            prev = units[-1]
            prev.terms = prev.terms | content_terms(body)
            prev.text = prev.text + " " + body.strip()
            continue
        if in_list:
            in_list = False
            block += 1
        para.append((body.strip(), lineno))
    flush_para()
    return units


def _norm(text):
    return " ".join(WORD_RE.findall(text.lower()))


def _opening(text):
    return tuple(w.lower() for w in WORD_RE.findall(text)[:2])


def _distinct_detail(unit_text, doc_lower, limit=5):
    """What a repeated sentence says that nothing else in the document says.

    A restated pair is rarely a perfect copy. The summary that re-words the
    overview often carries one fact the overview left out, and deleting the
    "duplicate" deletes that fact. So the finding names every number and content
    word in the repeat that appears nowhere else in the source, and the fix it
    suggests is a merge. Compared against the raw source rather than the
    code-stripped text, so a term inside backticks elsewhere still counts as
    stated. Words compare on a five-letter prefix of the word with a common suffix
    stripped (gives -> give), numbers literally. Lexical, so a paraphrase can
    still carry a distinct claim the finding does not name.
    """
    unit_lower = unit_text.lower()
    out = []
    for m in _NUMBER_TOKEN_RE.finditer(unit_text):
        tok = m.group(0).strip()
        if doc_lower.count(tok.lower()) <= unit_lower.count(tok.lower()) and tok not in out:
            out.append(tok)
    seen = set()
    for w in WORD_RE.findall(unit_text):
        lw = w.lower().strip("'’-")
        if not is_content_word(lw) or lw in _RECAP_WORDS:
            continue
        base = re.sub(r"(?:ing|ed|es|s|ly)$", "", lw) if len(lw) > 4 else lw
        prefix = base[:5]
        if prefix in seen:
            continue
        seen.add(prefix)
        pat = re.compile(r"\b" + re.escape(prefix))
        if len(pat.findall(doc_lower)) <= len(pat.findall(unit_lower)):
            out.append(w)
    return out[:limit]


class RestatementCheck(Check):
    """The same point made twice, in different paragraphs or sections.

    Each sentence and list item is reduced to a set of stemmed content words and
    compared with every earlier one outside its own paragraph. A pair whose
    Jaccard overlap reaches `restatement_jaccard` is a restatement. The check
    fires only at `restatement_min_pairs` or more: a person repeats one key point
    on purpose, an agent re-announces its whole overview in the summary.

    Exclusions keep reference documentation quiet, each measured against long
    human READMEs and manuals:

    - Pairs inside one section of a sectioned document, or closer than `min_gap`
      units in a document without sections. Parallel option descriptions
      ("Operates in global mode, so...") sit next to each other; an agent's
      restatement is the overview coming back in the summary.
    - Verbatim copies. A human pastes the same note under two options; an agent
      re-words the point it already made.
    - Templated entries: two units opening on the same two words ("Returns the
      original...", "If the flag is truthy...") are parallel reference entries,
      unless the later one sits in a summary or conclusion, where a repeat is a
      recap. Code-like units and anything under a version or year heading (a
      changelog entry, at any depth) are skipped outright, and so are pairs where
      both headings name an API entry.
    - Documents below `restatement_per_1k` restated pairs per 1,000 words. A
      3,000-word manual that says one thing twice is not the same finding as a
      400-word design doc that says four things twice.

    Lexical, so a paraphrase built from different words passes. Units under
    `min_terms` content words are skipped because short sentences share words by
    chance.
    """

    category = "restatement"
    min_terms = 6
    min_gap = 8

    def run(self, doc, ctx):
        jaccard_min = ctx.threshold("restatement_jaccard")
        min_pairs = ctx.threshold.integer("restatement_min_pairs")
        per_1k_min = ctx.threshold("restatement_per_1k")
        units = [u for u in _units(doc.code_stripped)
                 if len(u.terms) >= self.min_terms and not _CODELIKE_RE.search(u.text)
                 and not u.release]
        units = units[:MAX_RESTATEMENT_UNITS]
        pairs = self._pairs(units, jaccard_min)
        ctx.report["restated_pairs"] = len(pairs)
        rate = len(pairs) / doc.word_count * 1000.0 if doc.word_count else 0.0
        ctx.report["restated_per_1k"] = round(rate, 1)
        if len(pairs) < min_pairs or rate < per_1k_min:
            return
        doc_lower = doc.source.lower()
        for j, i, jac in pairs[:MAX_RESTATEMENT_HITS]:
            first = units[j]
            later = units[i]
            where = "another section" if first.section != later.section else "an earlier paragraph"
            preview = " ".join(first.text.split())
            if len(preview) > 60:
                preview = preview[:57].rstrip() + "..."
            extra = _distinct_detail(later.text, doc_lower)
            if extra:
                suggestion = ("merge, don't cut: nothing else in the document says %s; "
                              "move that into the copy you keep, or ask before dropping it"
                              % ", ".join(extra))
            else:
                suggestion = ("say it once, where it does the most work; every word in this "
                              "copy is stated elsewhere")
            ctx.emit(self.hit(later.line,
                              "repeats L%d from %s (overlap %.2f): %r" % (first.line, where, jac, preview),
                              suggestion))

    def _pairs(self, units, jaccard_min):
        """(earlier index, later index, jaccard) for each restated unit."""
        sectioned = len({u.section for u in units}) >= 3
        postings = {}
        pairs = []
        for i, unit in enumerate(units):
            opening = _opening(unit.text)
            wraps_up = bool(FRAMING_TITLE_RE.match(unit.title))
            overlap = {}
            for t in unit.terms:
                for j in postings.get(t, ()):
                    overlap[j] = overlap.get(j, 0) + 1
            best = None
            for j, shared in overlap.items():
                other = units[j]
                if other.block == unit.block:
                    continue
                if (other.section == unit.section) if sectioned else (i - j < self.min_gap):
                    continue
                if _norm(other.text) == _norm(unit.text):
                    continue
                if not wraps_up and opening and _opening(other.text) == opening:
                    continue
                if REFERENCE_TITLE_RE.search(unit.title) and REFERENCE_TITLE_RE.search(other.title):
                    continue
                union = len(unit.terms) + len(other.terms) - shared
                jac = shared / union if union else 0.0
                if jac >= jaccard_min and (best is None or jac > best[1]):
                    best = (j, jac)
            if best is not None:
                pairs.append((best[0], i, best[1]))
            for t in unit.terms:
                postings.setdefault(t, []).append(i)
        return pairs


__all__ = ["RestatementCheck"]
