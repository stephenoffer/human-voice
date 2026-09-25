"""balance — how the words are shared out between sections."""
from __future__ import annotations

import re

from ...text.stats import cov, rounded
from .sections import SectionCheck
from .vocabulary import (
    BOILERPLATE_TITLE_RE,
    FRAMING_TITLE_RE,
    RECAP_TITLE_RE,
    VERSION_TITLE_RE,
    short_title,
)


def _is_stub(s, stub_words):
    """A heading with nothing behind it.

    Not short: hollow. A README's two-line Community or Downloads section is a
    pointer, and it carries a link or a command; a changelog entry or an FAQ
    question is short by design. What an outline filled in by quota leaves behind
    is a sentence with no link, no code, no list, and nothing checkable in it: "We
    will test the migration thoroughly."
    """
    title = s.title
    return (0 < s.words < stub_words and s.code_lines < 2 and s.table_rows < 2
            and s.subsections == 0 and s.links == 0 and s.tech == 0
            and not s.lists
            and not title.rstrip().endswith("?") and not re.search(r"\d", title)
            and not BOILERPLATE_TITLE_RE.search(title))


class SectionBalanceCheck(SectionCheck):
    """How the words are shared out between sections.

    Four findings, each a different way an outline gets filled in by quota rather
    than by what the reader needs:

    - stubs: two or more hollow sections under `section_stub_words` words (see
      _is_stub), at least a fifth of all sections, in a document where another
      section runs eight times longer. The heading promised a topic and the
      writer had nothing to say about it.
    - even sections: five or more sections of real length whose word counts vary
      by less than `section_even_cov_floor`. Real topics are not the same size.
    - framing: overview, background, summary and "why it matters" sections holding
      more than `framing_share_max` of the words, where one of them is a recap
      (or framing passes half the document outright). The document spends more on
      announcing and recapping than on the subject. A long Motivation section
      with no summary is a person explaining why the project exists.
    - list symmetry: four or more lists of three or more items, spread over at
      least three sections, all cut to the same length: the "three pros, three
      cons" quota.
    """

    category = "section_balance"
    min_sections = 4
    min_words = 250

    def check_sections(self, sections, preamble, doc, ctx):
        report = ctx.report
        report["sections"] = len(sections)
        if not sections:
            report["section_words"] = None
            report["section_len_cov"] = None
            report["framing_share"] = None
            return
        sizes = [s.words for s in sections]
        total = sum(sizes)
        report["section_words"] = sizes
        report["section_len_cov"] = rounded(cov(sizes))
        framing_secs = [s for s in sections if FRAMING_TITLE_RE.match(s.title)]
        share = sum(s.words for s in framing_secs) / total if total else 0.0
        report["framing_share"] = round(share, 2)
        # Section words include list items, which the prose word count leaves out; a
        # migration plan whose substance is a schema and a bulleted runbook is still a
        # document with sections to weigh.
        if len(sections) < self.min_sections or total < self.min_words:
            return
        self._stubs(sections, ctx)
        self._even(sections, ctx)
        self._framing(framing_secs, share, ctx)
        self._list_symmetry(sections, ctx)

    def _stubs(self, sections, ctx):
        stubs = [s for s in sections if _is_stub(s, ctx.threshold("section_stub_words"))]
        ctx.report["stub_sections"] = len(stubs)
        largest = max(sections, key=lambda s: s.words)
        if (len(stubs) >= 2 and len(stubs) * 5 >= len(sections)
                and largest.words >= max(100, 8 * max(s.words for s in stubs))):
            names = ", ".join("%r (%d)" % (short_title(s.title), s.words) for s in stubs[:4])
            ctx.emit(self.hit(0, "%d stub sections %s beside %r at %d words"
                              % (len(stubs), names, short_title(largest.title), largest.words),
                              "write the thin sections, fold each into a neighbour with its "
                              "commitment intact, or mark the gap; a heading is a promise"))

    def _even(self, sections, ctx):
        # Changelog releases are even by construction; they are not a quota.
        real = [s for s in sections
                if s.words >= 40 and not BOILERPLATE_TITLE_RE.search(s.title)
                and not VERSION_TITLE_RE.search(s.title)]
        real_cov = cov([s.words for s in real])
        if len(real) >= 5 and real_cov is not None and real_cov < ctx.threshold("section_even_cov_floor"):
            mean = sum(s.words for s in real) / len(real)
            ctx.emit(self.hit(0, "%d sections all within a few words of %d (CoV %.2f)"
                              % (len(real), round(mean), real_cov),
                              "size each section by what it has to say, not by a quota"))

    def _framing(self, framing_secs, share, ctx):
        recap = any(RECAP_TITLE_RE.match(s.title) for s in framing_secs)
        if (share > ctx.threshold("framing_share_max") and len(framing_secs) >= 2
                and (recap or share > 0.5)):
            ctx.emit(self.hit(0, "%.0f%% of the words sit in framing sections (%s)"
                              % (share * 100, ", ".join(repr(short_title(s.title, 24))
                                                        for s in framing_secs[:4])),
                              "fold the framing into the body; a claim only the overview or "
                              "recap carries moves, it does not go"))

    def _list_symmetry(self, sections, ctx):
        runs = [(s.title, n) for s in sections for n in s.lists]
        owners = {t for t, _n in runs}
        if (len(runs) >= 4 and len(owners) >= 3 and runs[0][1] >= 3
                and len({n for _t, n in runs}) == 1):
            ctx.emit(self.hit(0, "all %d lists have exactly %d items" % (len(runs), runs[0][1]),
                              "let each list be as long as its content; drop the padding item "
                              "or add the missing one"))


__all__ = ["SectionBalanceCheck"]
