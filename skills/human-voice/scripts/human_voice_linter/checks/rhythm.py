"""rhythm — sentence length and how sentences begin.

All document-level: each asks whether the prose has the variation a person's
writing has, measured over the whole text.
"""
from __future__ import annotations

import math
from collections import Counter

from ..core.check import Check
from ..text.stats import longest_run
from ..text.tokens import WORD_RE, first_word, word_lengths


class BurstinessCheck(Check):
    """Coefficient of variation of sentence length.

    Needs at least `min_sents` sentences. At five, the CoV is dominated by
    sampling noise: a seven-sentence human abstract measured 0.33 and got flagged
    for "flat rhythm" while every AI file that actually fires has ten or more
    sentences. Raising the floor removed a false positive and cost no recall.
    """

    category = "burstiness"
    min_sents = 8

    def run(self, doc, ctx):
        lengths = word_lengths(doc.sentences)
        if len(lengths) < self.min_sents:
            ctx.report["burstiness_cov"] = None
            ctx.report["mean_sentence_len"] = round(sum(lengths) / len(lengths), 1) if lengths else 0
            return
        mean = sum(lengths) / len(lengths)
        if mean <= 0:
            ctx.report["burstiness_cov"] = None
            ctx.report["mean_sentence_len"] = 0
            return
        var = sum((n - mean) ** 2 for n in lengths) / len(lengths)
        cov = math.sqrt(var) / mean
        ctx.report["burstiness_cov"] = round(cov, 2)
        ctx.report["mean_sentence_len"] = round(mean, 1)
        floor = ctx.threshold("burstiness_cov_floor")
        if cov < floor:
            ctx.emit(self.hit(0, "sentence-length CoV %.2f (floor %.2f)" % (cov, floor),
                              "mix short punches with long sentences"))


class SentenceShapeCheck(Check):
    """Sentence-length *distribution*, not just its coefficient of variation.

    Human prose reaches: it drops three-word sentences and runs forty-word ones.
    LLM prose collapses toward the middle. CoV misses this because a single long
    sentence inflates it while the rest stay uniform, so measure the tails
    directly."""

    category = "sentence_shape"
    min_sents = 8

    def run(self, doc, ctx):
        th = ctx.threshold
        short_max = th.integer("short_sentence_max_words")
        short_floor = th("short_sentence_ratio_floor")
        mid_low = th.integer("mid_band_low")
        mid_high = th.integer("mid_band_high")
        mid_max = th("mid_band_ratio_max")
        lengths = word_lengths(doc.sentences)
        if len(lengths) < self.min_sents:
            ctx.report["short_sentence_ratio"] = None
            ctx.report["mid_band_ratio"] = None
            return
        n = len(lengths)
        short = sum(1 for x in lengths if x <= short_max) / n
        mid = sum(1 for x in lengths if mid_low <= x <= mid_high) / n
        ctx.report["short_sentence_ratio"] = round(short, 2)
        ctx.report["mid_band_ratio"] = round(mid, 2)
        ctx.report["longest_sentence"] = max(lengths)
        ctx.report["shortest_sentence"] = min(lengths)
        if short < short_floor:
            ctx.emit(self.hit(0, "only %.0f%% of sentences are <=%d words (floor %.0f%%)"
                              % (short * 100, short_max, short_floor * 100),
                              "cut in a short sentence. Like this one."))
        if mid > mid_max:
            ctx.emit(self.hit(0, "%.0f%% of sentences sit in the %d-%d word band"
                              % (mid * 100, mid_low, mid_high),
                              "push sentences out of the middle: some very short, some long"))


# The words English sentences start with by default. A third of sentences opening
# "The" or "We" is what ordinary prose looks like -- measured on this corpus, human
# and AI files overlap completely in the 0.30-0.45 band for these words, so firing
# there produced false positives and no separation. A repeated DISTINCTIVE opener
# ("However", "Additionally", "By") is a real templating signal at a much lower
# rate, and svo_monotony already covers long subject-initial runs.
COMMON_OPENERS = frozenset((
    "the", "a", "an", "i", "we", "it", "this", "that", "they", "you", "he",
    "she", "there", "our", "my", "these", "those", "his", "her", "its", "their"))
COMMON_OPENER_RATIO = 0.45
COMMON_OPENER_MIN = 5


class UniformOpenersCheck(Check):
    category = "uniform_openers"

    def run(self, doc, ctx):
        openers = [w for w in (first_word(s) for s in doc.sentences) if w]
        if len(openers) < 4:
            ctx.report["opener_repeat_ratio"] = 0.0
            ctx.report["opener_entropy"] = None
            return
        counts = Counter(openers)
        # Shannon entropy of the opener distribution (low = templated openings).
        total = len(openers)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        ctx.report["opener_entropy"] = round(entropy, 2)
        word, count = counts.most_common(1)[0]
        ratio = count / total
        ctx.report["opener_repeat_ratio"] = round(ratio, 2)
        if word in COMMON_OPENERS:
            fires = ratio >= COMMON_OPENER_RATIO and count >= COMMON_OPENER_MIN
        else:
            fires = ratio >= ctx.threshold("uniform_opener_ratio")
        if fires:
            ctx.emit(self.hit(0, '%d of %d sentences open with "%s"' % (count, total, word),
                              "vary how sentences begin"))


WH_OPENERS = frozenset(("what", "when", "where", "which", "who", "why", "how"))


class WhOpenersCheck(Check):
    """Flag the Wh-opener crutch: many sentences opening with what/when/why/...

    A specific sub-case of uniform openers ("What makes this hard is...",
    "Why does this matter?"). Fires on either a high overall ratio or a run of
    consecutive Wh-openers, so a short passage that stacks three of them is
    caught even when the document-wide ratio is diluted.
    """

    category = "wh_opener"

    def run(self, doc, ctx):
        firsts = [first_word(s) for s in doc.sentences]
        wh_flags = [f in WH_OPENERS for f in firsts]
        total = sum(1 for f in firsts if f is not None)
        count = sum(wh_flags)
        ctx.report["wh_opener_count"] = count
        ratio = (count / total) if total else 0.0
        ctx.report["wh_opener_ratio"] = round(ratio, 2)
        if total < 4:
            return
        max_streak = longest_run(wh_flags)
        if (ratio >= ctx.threshold("wh_opener_ratio")
                or max_streak >= ctx.threshold.integer("wh_opener_run")):
            ctx.emit(self.hit(0, "%d of %d sentences open with a Wh- word (run of %d)"
                              % (count, total, max_streak),
                              "lead with the subject; name the specific thing, not 'What makes this...'"))


class ParallelStructureCheck(Check):
    """Flag runs of >= `run` consecutive sentences sharing their first two words.

    Reports the run's ACTUAL length, not the threshold. The old version fired the
    instant a streak reached `run` and then went quiet, so five sentences opening
    "The system ..." and three of them read identically in the report -- the
    writer could not tell a borderline case from a severe one.
    """

    category = "parallel_structure"
    run_length = 3

    def run(self, doc, ctx):
        def head(s):
            ws = WORD_RE.findall(s.lower())
            return tuple(ws[:2]) if len(ws) >= 2 else None
        heads = [head(s) for s in doc.sentences]
        runs = []
        i = 0
        while i < len(heads):
            if heads[i] is None:
                i += 1
                continue
            j = i + 1
            while j < len(heads) and heads[j] == heads[i]:
                j += 1
            if j - i >= self.run_length:
                runs.append((j - i, heads[i]))
            i = j
        ctx.report["parallel_runs"] = len(runs)
        ctx.report["longest_parallel_run"] = max((n for n, _ in runs), default=0)
        for length, h in runs[:4]:
            ctx.emit(self.hit(0, '%d sentences in a row open "%s ..."' % (length, " ".join(h)),
                              "vary sentence openings and structure"))


# Subject-class openers: the canonical Subject-Verb-Object lead. A long run of
# them is the flat, even cadence a scanner can't see in any single sentence.
SUBJECT_OPENERS = frozenset((
    "the", "this", "that", "these", "those", "it", "we", "you", "they", "i",
    "a", "an", "our", "their", "his", "her", "its", "he", "she"))


class SvoMonotonyCheck(Check):
    """Flag a long *consecutive run* of subject-initial sentences.

    Subject-Verb-Object is English's default order, so most prose is majority
    subject-initial; an overall-share test would false-positive on careful human
    writing (and on ESL prose especially). The discriminating signal is a long
    unbroken run with no question, fragment, fronted adverbial, or transition to
    break it. Conservative on purpose; burstiness and uniform_openers cover the
    rest.
    """

    category = "svo_monotony"
    run_length = 6
    min_sents = 8

    def run(self, doc, ctx):
        flags = [first_word(s) in SUBJECT_OPENERS for s in doc.sentences]
        max_streak = longest_run(flags)
        ctx.report["subject_opener_run"] = max_streak
        if len(doc.sentences) < self.min_sents:
            return
        if max_streak >= self.run_length:
            ctx.emit(self.hit(0, "%d sentences in a row open with a subject (Subject-Verb-Object lead)"
                              % max_streak,
                              "break the run: lead with a clause, a question, or a fronted adverbial"))


__all__ = [
    "BurstinessCheck",
    "SentenceShapeCheck",
    "UniformOpenersCheck",
    "WhOpenersCheck",
    "ParallelStructureCheck",
    "SvoMonotonyCheck",
]
