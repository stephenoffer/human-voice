"""tokens — words, stopwords, and sentence segmentation."""
from __future__ import annotations

import re

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])["\')\]”’]?\s+(?=[A-Z0-9"\'(“])')

ABBREVIATIONS = {
    "e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "prof", "sr", "jr",
    "st", "inc", "ltd", "co", "corp", "fig", "al", "approx", "dept", "est",
    "u.s", "u.k", "ph.d", "no", "vol", "ch", "pp", "ca", "cf",
}

# One alternation for all abbreviations (longest first), built once. Replaces a
# per-abbreviation re.sub loop with a single pass over the text.
ABBREV_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(a) for a in sorted(ABBREVIATIONS, key=len, reverse=True))
    + r")\.", re.IGNORECASE)

STOPWORDS = set("the a an of to in and or is are was were be been being it its "
                "this that these those for on with as at by from we you they i "
                "he she but not so if then than into over under can will would "
                "should could may might do does did has have had our your their "
                "about which who whom there here when where how what why".split())


def sentences(prose):
    if not prose.strip():
        return []
    protected = re.sub(r"(\d)\.(\d)", lambda m: m.group(1) + "\x00" + m.group(2), prose)
    protected = re.sub(r"\.\.\.+", lambda m: "\x00" * len(m.group(0)), protected)
    protected = re.sub(r"\b(?:[A-Za-z]\.){2,}",
                       lambda m: m.group(0).replace(".", "\x00"), protected)
    # Protect abbreviation-final periods in one pass (e.g. -> e.g\x00).
    protected = ABBREV_RE.sub(lambda m: m.group(0)[:-1] + "\x00", protected)
    parts = SENTENCE_SPLIT_RE.split(protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def first_word(text):
    """Lowercased first word of `text`, or None."""
    m = WORD_RE.search(text)
    return m.group(0).lower() if m else None


def first_words(text, n=2):
    ws = WORD_RE.findall(text.lower())
    return tuple(ws[:n]) if len(ws) >= n else (tuple(ws) if ws else None)


def word_lengths(sents):
    """Word count of every non-empty sentence."""
    return [n for n in (len(WORD_RE.findall(s)) for s in sents) if n > 0]


__all__ = [
    "WORD_RE",
    "SENTENCE_SPLIT_RE",
    "ABBREVIATIONS",
    "ABBREV_RE",
    "STOPWORDS",
    "sentences",
    "first_word",
    "first_words",
    "word_lengths",
]
