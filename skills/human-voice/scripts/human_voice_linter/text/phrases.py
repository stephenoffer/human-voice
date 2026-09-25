"""phrases — compiled matchers for the phrase lists in the pattern file."""
from __future__ import annotations

import functools
import re

from ..core.log import warn


@functools.lru_cache(maxsize=None)
def phrase_regex(phrase):
    body = re.escape(phrase).replace(r"\ ", r"\s+")
    # Use boundaries only where the edge is a word char, so phrases starting or
    # ending in punctuation still match.
    left = r"\b" if phrase[:1].isalnum() else ""
    right = r"\b" if phrase[-1:].isalnum() else ""
    try:
        return re.compile(left + body + right, re.IGNORECASE)
    except re.error as exc:
        warn("skipping unmatchable phrase %r: %s" % (phrase, exc))
        return None


def norm_phrase(text):
    r"""Canonical key for a matched phrase: lowercased, whitespace collapsed.

    `phrase_regex` turns each space in a phrase into `\s+`, so a phrase can match
    across a line break. Normalizing the match the same way lets a combined
    alternation look the original phrase back up.
    """
    return " ".join(text.lower().split())


def _boundary_bucket(phrase):
    """(left, right) word-boundary anchors for a phrase, as phrase_regex picks them."""
    return (r"\b" if phrase[:1].isalnum() else "",
            r"\b" if phrase[-1:].isalnum() else "")


# Python's re allowed at most 100 groups before 3.7 and alternations get slow to
# compile long before they get slow to run, so combined patterns are chunked.
_ALTERNATION_CHUNK = 200


@functools.lru_cache(maxsize=64)
def _compiled_alternation(phrases, left, right):
    r"""One case-insensitive regex matching any of `phrases` (a tuple).

    Running one `\bphrase\b` regex per entry was 66% of total analysis time once
    the pattern file passed a thousand entries: a 36,000-word document meant 1,200
    full scans. Alternating them means one scan per boundary bucket per chunk.
    Phrases are sorted longest-first so the alternation prefers the longer match,
    which is what the per-phrase loop effectively produced.
    """
    out = []
    ordered = sorted(phrases, key=lambda p: (-len(p), p))
    for i in range(0, len(ordered), _ALTERNATION_CHUNK):
        chunk = ordered[i:i + _ALTERNATION_CHUNK]
        body = "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in chunk)
        try:
            out.append(re.compile(left + "(?:" + body + ")" + right, re.IGNORECASE))
        except re.error as exc:
            warn("skipping unmatchable phrase chunk: %s" % exc)
    return tuple(out)


def compile_phrase_matchers(phrases):
    """Compiled regexes covering every phrase, grouped by boundary anchoring.

    Returns a flat tuple of compiled regexes. A match's normalized text
    (`norm_phrase`) is the key back into the caller's phrase->suggestion map.
    """
    buckets: dict = {}
    for phrase in phrases:
        if not phrase:
            continue
        buckets.setdefault(_boundary_bucket(phrase), []).append(phrase)
    out: list = []
    for (left, right), group in sorted(buckets.items()):
        out.extend(_compiled_alternation(tuple(sorted(group)), left, right))
    return tuple(out)


def overlaps(start, end, spans):
    """True if [start, end) overlaps any (s, e) in spans (small list, linear)."""
    for s, e in spans:
        if start < e and s < end:
            return True
    return False


def build_protected_spans(text, exceptions):
    """Character ranges where a lexical word is a known legitimate use.

    Driven by the `context_exceptions` patterns key, e.g. "test harness" or
    "vital signs" protect "harness"/"vital" from being flagged as filler. These
    are whole-phrase matches; any lexical hit landing inside one is suppressed.
    """
    phrases = [p.strip() for p in (exceptions or ())
               if isinstance(p, str) and p.strip()]
    if not phrases:
        return []
    spans = []
    for rx in compile_phrase_matchers(phrases):
        for m in rx.finditer(text):
            spans.append((m.start(), m.end()))
    return spans


__all__ = [
    "phrase_regex",
    "norm_phrase",
    "compile_phrase_matchers",
    "overlaps",
    "build_protected_spans",
]
