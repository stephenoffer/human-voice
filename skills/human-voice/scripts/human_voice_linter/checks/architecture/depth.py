"""depth — is every part of the document written for the same reader?"""
from __future__ import annotations

from .sections import SectionCheck
from .vocabulary import BOILERPLATE_TITLE_RE, FRAMING_TITLE_RE, short_title


class DepthDriftCheck(SectionCheck):
    """Technical depth held level across sections.

    Depth is approximated by checkable markers per 100 words: numbers with units,
    identifiers, flags, paths, file names, acronyms, inline code, and fenced code.
    Two findings:

    - hollow section: a section of `hollow_words` or more with at most
      `depth_hollow_per_100` markers per 100 words and at least `abstract_min`
      abstract benefit words per 100 ("ensures", "reliability", "flexibility"), in
      a document where another section carries `depth_dense_per_100` or more. One
      part was written by someone who knew the system and another by someone
      describing it from outside. The abstraction requirement is what separates
      this from a person's conceptual section (a code of conduct, a "how it
      differs from X" discussion), which is light on markers too but talks about
      particular things. Framing sections (overview, summary) are exempt: saying
      nothing checkable is their job, and section_balance weighs how much room
      they take.
    - explainer whiplash: `explainer_min` or more beginner explanations ("in
      simple terms", "think of it as") in a document whose overall density is
      `depth_expert_per_100` or higher.
    """

    category = "depth_drift"
    min_section_words = 40
    hollow_words = 120
    abstract_min = 1.5
    explainer_min = 3

    def check_sections(self, sections, preamble, doc, ctx):
        qualifying = [s for s in sections if s.words >= self.min_section_words
                      and not BOILERPLATE_TITLE_RE.search(s.title)]
        dens = [round(s.density, 1) for s in qualifying]
        ctx.report["section_depth"] = dens or None
        everything = list(sections) + ([preamble] if preamble else [])
        total_words = sum(s.words for s in everything)
        total_tech = sum(s.tech for s in everything)
        explainers = sum(s.explainers for s in everything)
        doc_density = total_tech / total_words * 100.0 if total_words else 0.0
        ctx.report["depth_per_100"] = round(doc_density, 1)
        ctx.report["explainers"] = explainers

        if len(qualifying) >= 3:
            self._hollow(qualifying, ctx)

        if (explainers >= self.explainer_min and doc_density >= ctx.threshold("depth_expert_per_100")
                and total_words >= 150):
            ctx.emit(self.hit(0, "%d beginner explanations in a document at %.1f specifics/100w"
                              % (explainers, doc_density),
                              "pick one reader; drop the primer or move it to a glossary"))

    def _hollow(self, qualifying, ctx):
        densest = max(qualifying, key=lambda s: s.density)
        if densest.density < ctx.threshold("depth_dense_per_100"):
            return
        hollow_max = ctx.threshold("depth_hollow_per_100")
        for s in qualifying:
            abstract = s.abstract / s.words * 100.0
            if (s.words >= self.hollow_words and s.density <= hollow_max
                    and abstract >= self.abstract_min
                    and not FRAMING_TITLE_RE.match(s.title)):
                ctx.emit(self.hit(s.line,
                                  "section %r: %d words, %.1f specifics/100w, while %r carries %.1f"
                                  % (short_title(s.title), s.words, s.density,
                                     short_title(densest.title), densest.density),
                                  "bring in the real detail, or shrink it to the claims it "
                                  "alone makes; ask before dropping one"))


__all__ = ["DepthDriftCheck"]
