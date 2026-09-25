"""diction — word choice measured as rates: vocabulary range, repetition, and the
constructions that thicken prose (passives, adverbs, nominalizations)."""
from __future__ import annotations

import re
from collections import Counter

from ..core.check import Check, DensityCheck
from ..text.tokens import STOPWORDS, WORD_RE, sentences


def _yules_k(words):
    """Yule's K — vocabulary richness, robust to text length (lower = richer)."""
    n = len(words)
    if n < 2:
        return None
    freqs = Counter(words)
    spectrum = Counter(freqs.values())  # how many words occur m times
    inner = sum(vm * (m * m) for m, vm in spectrum.items())
    return round(1e4 * (inner - n) / (n * n), 1)


class LexicalDiversityCheck(Check):
    """Moving-average type-token ratio, with Yule's K reported beside it."""

    category = "lexical_diversity"
    window = 50

    def run(self, doc, ctx):
        words = [w.lower() for w in WORD_RE.findall(doc.metric_prose)]
        if len(words) < 50:
            ctx.report["ttr"] = None
            ctx.report["yules_k"] = None
            return
        window = self.window
        # Moving-average TTR (MATTR): overlapping windows for a smoother estimate.
        # Fall back to non-overlapping stride on very large inputs to bound cost.
        stride = 1 if len(words) <= 50000 else window
        ratios = []
        for i in range(0, len(words) - window + 1, stride):
            ratios.append(len(set(words[i:i + window])) / window)
        ttr = (sum(ratios) / len(ratios)) if ratios else (len(set(words)) / len(words))
        ctx.report["ttr"] = round(ttr, 2)
        ctx.report["yules_k"] = _yules_k(words)
        floor = ctx.threshold("ttr_floor")
        if ttr < floor:
            ctx.emit(self.hit(0, "type-token ratio %.2f (floor %.2f)" % (ttr, floor),
                              "vary word choice; avoid repeating concept terms verbatim"))


class NgramRepetitionCheck(Check):
    """Repeated n-grams, reported at the first occurrence and capped.

    This is an *instance* check, not a document one: a long repetitive text has
    genuinely more of them. It used to emit unbounded positionless hits, which
    both hid the location from the reader and let one category swamp the score on
    a long document (hundreds of hits on an 800-word input). Each finding now
    carries the line of its first occurrence, and the count is capped the same way
    every other instance check caps its examples.
    """

    category = "ngram_repetition"
    max_report = 8
    per_words = 400
    # A repeated n-gram is only a tell when it repeats *content*. Requiring two
    # content words keeps the check off "the text", "the skill", "the rewrite" --
    # article-plus-defined-term pairs that are precisely the terminology
    # consistency principle 6 tells you to hold. Flagging them pushed writers
    # toward rotating synonyms, which is the opposite of the guidance and a tell in
    # its own right.
    min_content = 2

    def run(self, doc, ctx):
        prose_text = doc.metric_prose
        sizes = ctx.threshold.int_list("ngram_sizes")
        min_count = ctx.threshold.integer("ngram_min_count")
        # Count n-grams WITHIN sentences. Sliding a window over the whole token stream
        # manufactured phrases that straddle a full stop -- "...to the client. The
        # client retries..." yielded the trigram "client the client" -- which is an
        # artifact of the window, not a repetition anybody wrote.
        per_sentence = [[w.lower() for w in WORD_RE.findall(sent)]
                        for sent in sentences(prose_text)]
        if not per_sentence:
            per_sentence = [[w.lower() for w in WORD_RE.findall(prose_text)]]
        total_words = sum(len(ws) for ws in per_sentence)
        # Repetition is a RATE. A bigram appearing four times is a tic in a 300-word
        # note and unremarkable in a 4,000-word reference, where the same four
        # occurrences are terminology consistency (principle 6). Scale the floor with
        # length instead of holding one absolute count for every document.
        min_count = max(min_count, 3 + total_words // self.per_words)
        found = []
        for n in sizes:
            if n < 2 or total_words < n:
                continue
            grams = Counter()
            for words in per_sentence:
                for i in range(len(words) - n + 1):
                    gram = tuple(words[i:i + n])
                    # A single letter is not a content word. "e.g." tokenizes to
                    # ("e", "g"), which passed the two-content-word test and made
                    # every document that abbreviates read as repetitive.
                    if sum(1 for w in gram
                           if len(w) > 2 and w not in STOPWORDS) < self.min_content:
                        continue
                    grams[gram] += 1
            for gram, count in grams.most_common():
                if count < min_count:
                    break  # most_common is descending; nothing further qualifies
                found.append((count, n, gram))
        found.sort(key=lambda t: (-t[0], t[1], t[2]))
        for count, n, gram in found[:self.max_report]:
            # Tokens are joined by single spaces, but the source may separate them
            # with a newline or runs of whitespace, so a literal find() misses.
            m = re.search(r"\s+".join(re.escape(w) for w in gram), prose_text, re.IGNORECASE)
            line = doc.metric_lines.line_of(m.start()) if m else 0
            ctx.emit(self.hit(line, '"%s" x%d' % (" ".join(gram), count),
                              "rephrase repeated %d-grams" % n))


# Passive voice: a "to be" form (optionally with an adverb) + a past participle.
# Deliberately conservative — flagged only when density is high, since some
# passive is normal and necessary.
PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|got|gets)\s+(?:\w+ly\s+)?"
    r"(?:\w+ed|written|made|done|given|taken|seen|known|built|held|kept|sent|"
    r"shown|told|found|put|set|read|lost|won|paid|met|drawn|grown|chosen)\b",
    re.IGNORECASE)
NOMINALIZATION_RE = re.compile(r"\b\w{4,}(?:tion|ment|ance|ence|ity|ization|isation)s?\b",
                               re.IGNORECASE)


class PassiveVoiceCheck(DensityCheck):
    category = "passive_voice"
    threshold_key = "passive_per_1k"
    metric_key = "passive_per_1k"
    label = "passive constructions"
    suggestion = "prefer the active voice where the actor matters"

    def measure(self, doc, ctx):
        return len(PASSIVE_RE.findall(doc.metric_prose)), ""


class AdverbCheck(DensityCheck):
    category = "adverbs"
    threshold_key = "adverb_per_1k"
    metric_key = "adverb_per_1k"
    label = "-ly adverbs"
    suggestion = "cut weak adverbs; pick a stronger verb or adjective"

    def measure(self, doc, ctx):
        return sum(1 for t in doc.tokens if len(t) > 3 and t.endswith("ly")), ""


class NominalizationCheck(DensityCheck):
    category = "nominalization"
    threshold_key = "nominalization_per_1k"
    metric_key = "nominalization_per_1k"
    label = "nominalizations"
    suggestion = "turn -tion/-ment nouns back into verbs"

    def measure(self, doc, ctx):
        return len(NOMINALIZATION_RE.findall(doc.metric_prose)), ""


__all__ = [
    "LexicalDiversityCheck",
    "NgramRepetitionCheck",
    "PassiveVoiceCheck",
    "AdverbCheck",
    "NominalizationCheck",
]
