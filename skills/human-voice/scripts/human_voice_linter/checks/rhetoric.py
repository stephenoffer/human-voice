"""rhetoric — reflexive figures: triads, staged questions, superlatives, stock
names, and the performed casualness of an over-corrected rewrite."""
from __future__ import annotations

import re
from collections import Counter

from ..core.check import MAX_INSTANCE_HITS, Check, DensityCheck, clip
from ..text.tokens import WORD_RE

# Triads with an optional Oxford comma, joined by "and" or "or":
# "fast, reliable, and scalable" and "fast, reliable and scalable" both match.
RULE_OF_THREE_RE = re.compile(
    r"\b([A-Za-z]+)\s*,\s+([A-Za-z]+)\s*,?\s+(?:and|or)\s+([A-Za-z]+)\b")

# Noun-PHRASE triads the single-word pattern misses ("encryption at rest,
# row-level access control, and audit logging"). Members are 1-3 words; at least
# one must be multi-word (a single-word triad is already handled above).
NOUN_TRIAD_RE = re.compile(
    r"\b([A-Za-z][\w-]*(?:\s+[\w-]+){0,2}),\s+([A-Za-z][\w-]*(?:\s+[\w-]+){0,2}),"
    r"\s+and\s+([A-Za-z][\w-]*(?:\s+[\w-]+){0,2})\b")

# Words that mark a triad member as a CLAUSE rather than a noun phrase. The
# noun-triad pattern cannot tell "encryption at rest, row-level access control,
# and audit logging" (a real triad) from "you paste code into a notebook, the
# kernel dies, and the last save is gone" (a sentence with three clauses in it),
# and flagging the second told a writer to break a sentence that was already fine.
_CLAUSE_PRONOUNS = frozenset((
    "it", "he", "she", "they", "we", "you", "i", "who", "which", "that"))
_CLAUSE_VERBS = frozenset((
    "is", "are", "was", "were", "be", "been", "am", "has", "have", "had",
    "do", "does", "did", "will", "would", "can", "could", "should", "may",
    "might", "must", "gets", "goes", "comes", "makes", "takes", "runs",
    "starts", "stops", "dies", "fails", "works", "means", "keeps", "leaves"))
# A member that OPENS with one of these is a phrase fragment captured out of a
# longer clause, not a list item.
_MEMBER_BAD_START = frozenset((
    "into", "onto", "from", "with", "for", "of", "to", "in", "on", "at", "by",
    "as", "than", "when", "while", "because", "if", "so", "but", "and", "or",
    "after", "before", "since", "though", "although", "unless", "until"))

# A triad member that is really a function word swept up by the pattern: "a field
# that, directly or indirectly, holds ..." is not a list of three.
_TRIAD_STOP_MEMBERS = frozenset((
    "that", "this", "these", "those", "which", "what", "when", "where", "while",
    "then", "than", "with", "from", "into", "onto", "over", "under", "after",
    "before", "because", "unless", "until", "since", "though", "although",
    "here", "there", "they", "them", "their", "your", "ours", "have", "been",
    "were", "will", "would", "could", "should", "does", "done", "such", "some",
    "each", "both", "also", "only", "just", "even", "well", "more", "most",
    "less", "least", "very", "much", "many", "same", "other", "another"))


def _is_noun_phrase(member):
    """Rough test: does this triad member read as a noun phrase, not a clause?"""
    words = [w.lower() for w in WORD_RE.findall(member)]
    if not words:
        return False
    if words[0] in _MEMBER_BAD_START:
        return False
    return not any(w in _CLAUSE_PRONOUNS or w in _CLAUSE_VERBS for w in words)


def _distinct_by_text(matches):
    """First occurrence of each distinct matched phrase, order preserved.

    Used where the tell is a HABIT rather than a count: repeating one phrase is
    terminology consistency (principle 6), and charging for every copy of it turns
    a virtue into a finding.
    """
    seen = set()
    out = []
    for m in matches:
        key = " ".join(m.group(0).lower().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


class RuleOfThreeCheck(Check):
    """Triads, single-word and noun-phrase, both gated on repetition.

    A tricolon is a rhetorical figure, and principle 2 says explicitly that one is
    fine. What marks machine prose is the REFLEX: reaching for three whenever a
    list appears. Both halves of this check need two instances in a document, so
    "tuples, lists, and dicts" (a real enumeration of exactly three things) does
    not get told to become two or four.
    """

    category = "rule_of_three"
    min_single_word = 2
    min_noun_phrase = 2

    def run(self, doc, ctx):
        lines = doc.metric_lines
        single = _distinct_by_text(self._single_word(doc.metric_prose))
        if len(single) >= self.min_single_word:
            for m in single[:MAX_INSTANCE_HITS]:
                ctx.emit(self.hit(lines.line_of(m.start()), m.group(0),
                                  "vary to two or four, or a clause"))
        # Noun-phrase triads: the reflexive STACKING is the tell, so only flag when a
        # document has 2+ of them; a single legitimate enumeration is left alone.
        np_hits = _distinct_by_text(self._noun_phrase(doc.metric_prose))
        if len(np_hits) >= self.min_noun_phrase:
            for m in np_hits[:MAX_INSTANCE_HITS]:
                ctx.emit(self.hit(lines.line_of(m.start()), clip(m.group(0), 63),
                                  "break the triad: two items, four, or a clause"))

    @staticmethod
    def _single_word(text):
        out = []
        for m in RULE_OF_THREE_RE.finditer(text):
            a, b, c = m.group(1), m.group(2), m.group(3)
            # Adjective/adverb-looking triads only; require length and -ly/-ed-ish
            # endings or short words to avoid flagging proper-noun lists.
            if not all(len(w) > 3 for w in (a, b, c)):
                continue
            # Skip proper-noun lists ("Python, Django, and Flask"): a capitalized
            # member that is NOT the sentence's first word marks a name, not an
            # adjective. The first member can be capitalized merely by position.
            if b[0].isupper() or c[0].isupper():
                continue
            if any(w.lower() in _TRIAD_STOP_MEMBERS for w in (a, b, c)):
                continue
            out.append(m)
        # DISTINCT triads (the caller dedupes). One boilerplate phrase repeated
        # across twenty API docstrings ("string, bytes, or bytearray") is one habit,
        # not twenty, and counting each copy put a reference manual straight into
        # the category cap.
        return out

    @staticmethod
    def _noun_phrase(text):
        out = []
        for m in NOUN_TRIAD_RE.finditer(text):
            members = (m.group(1), m.group(2), m.group(3))
            if not any(len(x.split()) > 1 for x in members):
                continue  # all single-word -> already covered above
            # A clause list is not a rule-of-three triad. See _is_noun_phrase.
            if not all(_is_noun_phrase(x) for x in members):
                continue
            # Proper-noun list guard (members 2/3; member 1 may be capitalized by
            # sentence position): "Slack, Google Drive, and GitHub" is a real list.
            if members[1][0].isupper() or members[2][0].isupper():
                continue
            out.append(m)
        return out


class RhetoricalQuestionCheck(DensityCheck):
    category = "rhetorical"
    threshold_key = "rhetorical_per_1k"
    metric_key = "rhetorical_per_1k"
    label = "rhetorical questions"
    suggestion = "answer the question or cut it"

    def measure(self, doc, ctx):
        return sum(1 for s in doc.sentences if s.rstrip().endswith("?")), ""


HYPOPHORA_ANSWER_RE = re.compile(
    r"^\s*(?:because|the answer|it'?s\b|its\b|simple\.|yes\b|no\b|turns out|"
    r"here'?s why|that'?s because|the reason|short answer)\b",
    re.IGNORECASE)


class HypophoraCheck(Check):
    """Ask-then-immediately-answer ('Why does this matter? Because ...').

    Distinct from a bare rhetorical question: the next sentence supplies the
    answer. One is fine; a run of them is the LinkedIn-explainer cadence.
    """

    category = "hypophora"

    def run(self, doc, ctx):
        sents = doc.sentences
        count = 0
        for i in range(len(sents) - 1):
            if sents[i].rstrip().endswith("?") and HYPOPHORA_ANSWER_RE.match(sents[i + 1]):
                count += 1
        ctx.report["hypophora"] = count
        if count >= 2:
            ctx.emit(self.hit(0, "%d question-then-answer beats" % count,
                              "ask fewer rhetorical questions; just state the point"))


# Absolute/superlative claims. Kept distinct from the filler lists to limit
# double-counting; the check only fires when the claim is NOT backed by a
# nearby number, since "the best (by 12%)" is an earned superlative.
SUPERLATIVE_RE = re.compile(
    r"\b(?:the\s+)?(?:most|best|worst|greatest|finest|biggest|largest|fastest|"
    r"ultimate|perfect|unprecedented|unparalleled|unmatched|premier|foremost|"
    r"world-?class|game-?changing|the only|never before|second to none)\b",
    re.IGNORECASE)
_NUMBER_NEAR_RE = re.compile(r"\d")


class SuperlativeCreepCheck(DensityCheck):
    """Unbacked superlatives as a rate.

    ONE document finding, not one per example. Emitting six line-0 hits made a
    single density signal worth six times doc_hit_points -- more than any
    structural tell -- and gave the writer no line to go to. The examples ride
    along in the text instead.
    """

    category = "superlative_creep"
    threshold_key = "superlative_per_1k"
    metric_key = "superlative_per_1k"
    label = "unbacked superlatives"
    suggestion = "match the claim to evidence; cut the superlative or give the number"

    def measure(self, doc, ctx):
        text = doc.metric_prose
        unbacked = [m for m in SUPERLATIVE_RE.finditer(text)
                    if not _NUMBER_NEAR_RE.search(text[m.end():m.end() + 40])]
        examples = ", ".join(sorted({m.group(0).strip().lower() for m in unbacked})[:5])
        return len(unbacked), ": " + examples


# Default AI character names and reflexive honorifics (fiction/creative tell).
DEFAULT_NAME_RE = re.compile(r"\b(Emily|Sarah|Michael|Jacob|Elena|Maya)\b")
DR_TITLE_RE = re.compile(r"\bDr\.\s+[A-Z]")


class NameSelectionCheck(Check):
    category = "name_selection"

    def run(self, doc, ctx):
        text = doc.code_stripped
        names = Counter(m.group(1) for m in DEFAULT_NAME_RE.finditer(text))
        dr = len(DR_TITLE_RE.findall(text))
        ctx.report["default_names"] = sum(names.values())
        ctx.report["dr_titles"] = dr
        top = names.most_common(1)
        if top and top[0][1] >= 2:
            ctx.emit(self.hit(0, '"%s" used %d times (AI defaults to a few stock names)' % top[0],
                              "pick names that fit the era, region, and class of your characters"))
        if dr >= 3:
            ctx.emit(self.hit(0, "%d 'Dr.' honorifics" % dr,
                              "AI over-titles; use first names or nicknames after introduction"))


# The "anti-AI costume": performed casualness that is itself a tell.
COSTUME_SLANG_RE = re.compile(r"\b(?:lol|lmao|idk|tbh|ngl|imo|fr|smh|iirc)\b", re.IGNORECASE)
SENTENCE_START_RE = re.compile(r"(?:^|[.!?]\s+)([A-Za-z])")


class OverCorrectionCheck(Check):
    """Detect over-correction into the anti-AI costume.

    Forced all-lowercase sentence starts and sprinkled chat slang read as a
    *performed* humanness. A class of its own so the linter never rewards swapping
    one costume for another. Muted in casual/creative where the voice is native.
    """

    category = "over_correction"

    def run(self, doc, ctx):
        text = doc.metric_prose
        starts = SENTENCE_START_RE.findall(text)
        slang = len(COSTUME_SLANG_RE.findall(text))
        ctx.report["costume_slang"] = slang
        if len(starts) >= 6:
            lower = sum(1 for c in starts if c.islower())
            share = lower / len(starts)
            ctx.report["lowercase_sentence_share"] = round(share, 2)
            if share >= 0.5:
                ctx.emit(self.hit(0, "%d%% of sentences start lowercase" % round(share * 100),
                                  "forced lowercase is its own tell; write in a real register, "
                                  "not the anti-AI costume"))
        if slang >= 3:
            ctx.emit(self.hit(0, "%d chat-slang markers (lol/idk/tbh/...)" % slang,
                              "sprinkled slang reads as performed casualness; drop it or "
                              "commit to the register"))


__all__ = [
    "RuleOfThreeCheck",
    "RhetoricalQuestionCheck",
    "HypophoraCheck",
    "SuperlativeCreepCheck",
    "NameSelectionCheck",
    "OverCorrectionCheck",
]
