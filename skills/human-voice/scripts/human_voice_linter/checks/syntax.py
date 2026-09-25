"""syntax — the modern instruction-tuned signature.

The lexical lists catch 2023-era slop ("delve", "tapestry", "in today's
fast-paced world"). A current model does not write that way; it writes clean,
well-organized prose whose tells are SYNTACTIC. A handful of constructions carry
most of it, and all of them are ordinary English in isolation -- a person uses
each of them -- so every check here is count-gated and fires on the STACKING,
never on one instance. Each also reports a metric so a writer can see the trend
before it trips.
"""
from __future__ import annotations

import re

from ..core.check import MAX_INSTANCE_HITS, Check, DensityCheck, RateCheck, clip, context_around

# Wh-cleft ("What matters is X", "All you need is Y"): the sentence delays its
# subject to stage the point. One is rhetoric; four in a page is a cadence.
# Anchored at a clause boundary, not only a sentence boundary. Restricting this
# to sentence-initial "What" missed the commonest form in narrative prose --
# "But standing in the hallway, what she felt was mostly the practical weight"
# -- which is the same construction one clause later. Comma-anchored matches
# require the lowercase form so a mid-sentence proper "What" (a quoted question)
# does not count.
WH_CLEFT_RE = re.compile(
    r"(?:^|(?<=[.!?])\s+|(?<=[:;])\s+)(?:What|All)\s+[^.?!\n]{3,60}?\s(?:is|was|are|were)\b"
    r"|(?<=,)\s+(?:what|all)\s+[^.?!\n]{3,60}?\s(?:is|was|are|were)\b")
# Reversed wh-cleft ("The reason this works is that...", "The thing about X is").
# Anchored to a sentence start, because mid-sentence the same words are ordinary
# ("we fixed the problem and the answer was obvious" is not a cleft), and the gap
# refuses to cross a subordinator so "the problem looks like X when it is Y" no
# longer matches. The second alternative covers the zero-gap form, which is only a
# cleft when it continues with "that" or "not".
_CLEFT_HEADS = (r"thing|reason|problem|point|question|part|issue|trick|catch|"
                r"difference|answer|upshot|kicker|takeaway|challenge|surprise|"
                r"story|truth")
# Clause-start anchors. A reverse cleft can open a sentence or follow a comma or a
# coordinator ("..., and the reason my estimate was low is that ..."). Every
# alternative is fixed-width, which Python's lookbehind requires.
_CLAUSE_START = (r"(?:^|(?<=[.!?;:])\s|(?<=\n)|(?<=,\s)|(?<=\band\s)"
                 r"|(?<=\bbut\s)|(?<=\bso\s))")
REVERSE_CLEFT_RE = re.compile(
    _CLAUSE_START + r"the\s+(?:[\w-]+\s+){0,2}?(?:" + _CLEFT_HEADS + r")\b"
    r"(?:\s+(?!when\b|because\b|if\b|while\b|although\b|unless\b|so\b|but\b"
    r"|and\b|or\b)[\w'-]+){1,5}\s+(?:is|was)\b"
    r"|" + _CLAUSE_START + r"the\s+(?:[\w-]+\s+){0,2}?(?:" + _CLEFT_HEADS +
    r")\s+(?:is|was)\s+(?:that|not)\b",
    re.IGNORECASE)
# It-cleft ("It is the second call that fails").
IT_CLEFT_RE = re.compile(
    r"\bit\s+(?:is|was|isn'?t|wasn'?t)\s+(?:not\s+)?(?:the\s+|a\s+|an\s+)?"
    r"[\w'-]+(?:\s+[\w'-]+){0,3}\s+that\b",
    re.IGNORECASE)


class CleftCheck(RateCheck):
    """Cleft-construction stacking: What-X-is-Y / The-reason-is / It-is-X-that.

    A cleft front-loads emphasis by deferring the real subject. Every one of these
    is grammatical and useful, and careful human writers reach for them, so a lone
    cleft means nothing -- the human corpus has them too. What separates
    instruction-tuned prose is the RATE: the construction becomes the default way
    a point gets introduced, several times a page, because it reliably reads as
    thoughtful. Gated on both an absolute count and a per-1k density so a short
    note with two clefts stays clean.
    """

    category = "cleft"
    metric = "cleft"
    threshold_key = "cleft_per_1k"
    suggestion = "put the subject first: say the thing instead of staging it"
    min_words = 120

    def matches(self, doc):
        found = []
        for rx in (WH_CLEFT_RE, REVERSE_CLEFT_RE, IT_CLEFT_RE):
            found.extend(rx.finditer(doc.metric_prose))
        found.sort(key=lambda m: m.start())
        # Overlapping alternatives (a reverse cleft inside a wh-cleft) count once.
        deduped: list = []
        for m in found:
            if deduped and m.start() < deduped[-1].end():
                continue
            deduped.append(m)
        return deduped

    def snippet(self, doc, m):
        return clip(m.group(0).strip().replace("\n", " "), 60)


# Resultative participial tail: a comma followed by an -ing verb that explains the
# consequence of the main clause. LLM prose appends one to sentence after sentence
# because it manufactures a sense of consequence for free.
#
# Abstract, resultative participles only. "turning", "letting", "leaving" and
# "freeing" were in this list and are ordinary narrative motion (", turning toward
# the door"), which would have made the check fire on fiction for doing the thing
# fiction does. What stays is the consequence-clause vocabulary: verbs that assert
# an effect rather than describe an action.
PARTICIPIAL_TAIL_RE = re.compile(
    r",\s+(?:making|allowing|enabling|ensuring|helping|giving|providing|creating|"
    r"offering|delivering|driving|reducing|improving|increasing|"
    r"reflecting|highlighting|underscoring|demonstrating|showcasing|emphasizing|"
    r"emphasising|reinforcing|meaning|resulting|leading|"
    r"saving|boosting|streamlining|unlocking|empowering|positioning|paving)\s+\w",
    re.IGNORECASE)


class ParticipialTailCheck(RateCheck):
    """The ", making it easier to..." tail, counted as a rate.

    One resultative participle is fine English. Three or four in a page is the
    single most repeatable syntactic habit of instruction-tuned prose: every
    sentence is given a consequence clause so it sounds like it earned a payoff,
    whether or not one follows from it. Because the tail is grammatically
    subordinate, it also lets a claim slide past unexamined, which is why cutting
    it usually improves the argument and not just the rhythm.
    """

    category = "participial_tail"
    metric = "participial_tail"
    threshold_key = "participial_tail_per_1k"
    suggestion = "split it: state the consequence as its own sentence, or drop it"
    min_words = 120

    def matches(self, doc):
        return list(PARTICIPIAL_TAIL_RE.finditer(doc.metric_prose))

    def snippet(self, doc, m):
        return context_around(doc.metric_prose, m.start(), m.end(), 24, 12)


# Two independent clauses welded with ", and" / ", but" where a period belongs.
# The give-away shape is a comma, a coordinator, and a fresh pronoun subject.
SPLICE_RE = re.compile(
    r",\s+(?:and|but|so|yet)\s+(?:it|this|that|they|we|you|he|she|there)\s+"
    r"(?:is|was|are|were|has|have|had|will|can|could|would|does|did|do|"
    r"means?|makes?|becomes?|gives?|takes?|works?|helps?)\b",
    re.IGNORECASE)


class ClauseSpliceCheck(RateCheck):
    """Repeated ', and it is ...' clause-welding.

    Chaining two full clauses with a comma plus a coordinator is correct English
    and every writer does it. Doing it four or five times a page flattens the
    prose into one continuous middle-length line, which is the same defect
    burstiness measures from the other side. Count-gated hard, and low-weighted,
    because the construction itself is innocent.
    """

    category = "clause_splice"
    metric = "clause_splice"
    threshold_key = "clause_splice_per_1k"
    suggestion = "end the sentence and start a new one; the comma is doing a period's job"
    min_count = 4

    def matches(self, doc):
        return list(SPLICE_RE.finditer(doc.metric_prose))

    def snippet(self, doc, m):
        return context_around(doc.metric_prose, m.start(), m.end(), 20, 6)


# Copula avoidance: the elaborate substitute for "is". Present-tense third person
# only, because "represented" and "featured" in a past-tense narrative are doing
# ordinary work. "Serves as" and its family are the constructions the Wikipedia
# AI-Cleanup corpus found rising as "is"/"are" fell.
COPULA_AVOID_RE = re.compile(
    r"\b(?:serves?|stands?|functions?|operates?|acts?)\s+as\b"
    r"|\b(?:represents|embodies|exemplifies|encompasses|constitutes)\b"
    r"|\b(?:boasts|features|offers|maintains|possesses)\s+(?:a|an|the|its|several|numerous|\d)",
    re.IGNORECASE)


class CopulaAvoidanceCheck(RateCheck):
    """The mirror of copula_density: reaching past 'is' on every definition.

    One "serves as" is unremarkable. A document where nothing is allowed to
    simply BE anything -- where each subject instead stands as, represents,
    embodies or boasts -- has the register of a press release written to fill a
    length, and it is the construction that replaced plain copulas in
    post-2022 encyclopedic text. Count- and density-gated like every other
    syntactic check here, because each phrase on its own is fine English.
    """

    category = "copula_avoidance"
    metric = "copula_avoidance"
    threshold_key = "copula_avoidance_per_1k"
    suggestion = "use the plain copula, or a verb that does real work"

    def matches(self, doc):
        return list(COPULA_AVOID_RE.finditer(doc.metric_prose))


# Copula ("to be") as the main verb. Counted per sentence, not per document,
# because the tell is a paragraph where nothing happens -- everything simply IS.
COPULA_RE = re.compile(r"\b(?:is|are|was|were|be|been|being|isn'?t|aren'?t|"
                       r"wasn'?t|weren'?t)\b", re.IGNORECASE)


class CopulaDensityCheck(DensityCheck):
    """How much of the prose leans on 'to be' instead of a verb that does work.

    Reported always, flagged only well above the human range. High copula density
    is what makes a passage feel like a definition list read aloud: X is Y, Y is
    important, the result is Z. It correlates with vacuity, which is the tell this
    skill ranks highest and no regex can see directly.
    """

    category = "copula_density"
    threshold_key = "copula_per_1k"
    metric_key = "copula_per_1k"
    label = "'to be' as the main verb"
    suggestion = "give the sentences real verbs; 'X is Y' twice a paragraph reads as a glossary"
    min_count = 8

    def measure(self, doc, ctx):
        return sum(self._per_sentence(doc)), ""

    def extra_metrics(self, doc, ctx):
        ctx.report["copula_stacked_sentences"] = sum(1 for n in self._per_sentence(doc) if n >= 3)

    @staticmethod
    def _per_sentence(doc):
        return [len(COPULA_RE.findall(s)) for s in doc.sentences]


# Nominal chain: "the reduction of the complexity of the interface". Three or more
# "of the" links in one sentence is a noun pile-up rather than a sentence.
OF_CHAIN_RE = re.compile(r"\b(?:of|for|in|to)\s+the\s+[\w-]+\s+"
                         r"(?:of|for|in)\s+the\s+[\w-]+\s+(?:of|for|in)\s+the\b",
                         re.IGNORECASE)


class NounChainCheck(Check):
    """Stacked prepositional-noun chains ('the X of the Y of the Z')."""

    category = "noun_chain"
    min_count = 2

    def run(self, doc, ctx):
        matches = list(OF_CHAIN_RE.finditer(doc.metric_prose))
        ctx.report["noun_chains"] = len(matches)
        if len(matches) < self.min_count:
            return
        for m in matches[:MAX_INSTANCE_HITS]:
            ctx.emit(self.hit(doc.metric_lines.line_of(m.start()),
                              m.group(0).replace("\n", " "),
                              "unstack the nouns: make one of them the verb"))


COLON_SUMMARY_RE = re.compile(
    r"\b(?:the\s+)?(?:key|answer|takeaway|bottom line|point|truth|reality|catch|"
    r"problem|reason|result|upshot|short of it)\s+(?:here\s+)?is:\s*\S",
    re.IGNORECASE)


class ColonSummaryCheck(Check):
    """'The key is: ...' as the default lead-in, three or more times."""

    category = "colon_summary"

    def run(self, doc, ctx):
        matches = list(COLON_SUMMARY_RE.finditer(doc.metric_prose))
        ctx.report["colon_summary"] = len(matches)
        if len(matches) >= 3:
            for m in matches[:MAX_INSTANCE_HITS]:
                ctx.emit(self.hit(doc.metric_lines.line_of(m.start()),
                                  m.group(0).strip().replace("\n", " "),
                                  "vary the lead-in; not every point needs 'X is: ...'"))


__all__ = [
    "CleftCheck",
    "ParticipialTailCheck",
    "ClauseSpliceCheck",
    "CopulaAvoidanceCheck",
    "CopulaDensityCheck",
    "NounChainCheck",
    "ColonSummaryCheck",
]
