"""diagnostics — metrics reported for the writer and never scored.

Each of these separates human from model text on average and overlaps it
completely somewhere that matters (fiction, careful non-native writers), so
scoring any of them would flag exactly the people detectors already mistreat.
"""
from __future__ import annotations

import re

from ..core.check import Diagnostic
from ..text.stats import per_1k
from .stylometry import report_stylometry


class PunctuationProfile(Diagnostic):
    """Per-1k-word punctuation counts (a stylometric signal)."""

    def run(self, doc, ctx):
        words = doc.word_count
        if not words:
            return
        text = doc.metric_prose
        for key, ch in (("semicolon", ";"), ("colon", ":"), ("question", "?"),
                        ("exclaim", "!")):
            ctx.report["%s_per_1k" % key] = round(text.count(ch) / words * 1000, 1)
        ctx.report["paren_per_1k"] = round(text.count("(") / words * 1000, 1)


# Checkable specifics: numbers, dates, units, and proper nouns that are not just a
# sentence-initial capital.
SPECIFIC_NUM_RE = re.compile(r"\b\d[\d,.:]*\b|\b\d+\s?%")
CAPWORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


class Specificity(Diagnostic):
    """How many checkable specifics per 100 words. A METRIC, not a tell.

    Vacuity is the tell this skill calls highest and no regex can see. This does not
    see it either, but it measures the thing vacuous prose reliably lacks: numbers,
    dates, and named entities a reader could go and check.

    Deliberately NOT scored. Measured on this corpus the medians separate (human 3.0
    per 100 words, realistic-AI 0.6) and the ranges overlap completely: plenty of
    good human writing, fiction especially, contains no number and no proper noun at
    all. What it is good for is prompting the author-material intake: near-zero
    means the draft has nothing checkable in it, so cutting tells will leave clean,
    generic, unowned prose unless real material comes from somewhere.
    """

    def run(self, doc, ctx):
        words = doc.word_count
        nums = SPECIFIC_NUM_RE.findall(doc.metric_prose)
        proper = 0
        for sent in doc.sentences:
            toks = re.findall(r"\S+", sent)
            for tok in toks[1:]:          # skip the sentence-initial capital
                w = CAPWORD_RE.match(re.sub(r"^[^A-Za-z]+", "", tok))
                if w:
                    text = w.group(0)
                    if text[:1].isupper() and not text.isupper():
                        proper += 1
        per_100 = ((len(nums) + proper) / words * 100) if words else 0.0
        ctx.report["numbers"] = len(nums)
        ctx.report["proper_nouns"] = proper
        ctx.report["specifics_per_100"] = round(per_100, 2)
        # A single flag the rewrite procedure can branch on.
        ctx.report["specifics_thin"] = bool(words >= 120 and per_100 < 0.5)


CONTRACTION_RE = re.compile(r"\b\w+['’](?:t|s|re|ve|ll|d|m)\b", re.IGNORECASE)


class ContractionRate(Diagnostic):
    """See references/competitive-landscape.md.

    Contraction rate is the single most discriminative surface feature in the
    published humanizer literature (AI ~0.00 per chunk against ~0.17 for human)
    and it is measured here for the writer's benefit: marketing copy with zero
    contractions reads stiff, and that is worth knowing. It is deliberately NOT
    a scored category. On this repo's own corpus a contraction-absence check
    gated to the conversational registers fires on four of the ten ESL/formal
    files -- careful non-native writers who use no contractions and are human.
    Scoring it would reproduce exactly the bias Liang et al. (2023) measured in
    commercial detectors, in a tool whose whole argument is that those detectors
    are wrong about that population.
    """

    def run(self, doc, ctx):
        count = len(CONTRACTION_RE.findall(doc.metric_prose))
        ctx.report["contractions"] = count
        ctx.report["contractions_per_1k"] = round(per_1k(count, doc.word_count), 1)


class Stylometry(Diagnostic):
    """Burrows's Delta against the committed human function-word profile.

    Read in the opposite direction from the obvious one: see stylometry.py. A
    missing or malformed profile leaves the key absent.
    """

    def run(self, doc, ctx):
        report_stylometry(doc.metric_prose, ctx.report)


__all__ = [
    "PunctuationProfile",
    "Specificity",
    "ContractionRate",
    "Stylometry",
]
