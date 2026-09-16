"""invariants — did the rewrite keep every fact it was handed?

SKILL.md makes numbers, code, links and citations invariant, and inside Claude Code
the model checks that with a diff. Through a bare API nobody runs the diff, and a
smaller model is exactly the one that turns "p99 of 340 ms" into "sub-second
latency". So the loop checks it deterministically, and a lost or invented
invariant blocks the pass from being accepted however well it scores.

This is a floor, like the linter. It sees tokens, not claims: "rose 12%" and
"fell 12%" look identical to it. It catches the common failures cheaply and hands
the model a precise list to restore.
"""
from __future__ import annotations

import re
from collections import Counter

_FENCE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[ \t]*$", re.M | re.S)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_URL = re.compile(r"\bhttps?://[^\s<>()\[\]\"']+[^\s<>()\[\]\"'.,;:!?]")
_LINK_TARGET = re.compile(r"\]\(([^)\s]+)")
# Numbers with their attached unit or sign: 3.2, 1,200, 40%, $5, v1.2.3, 2026-09-16.
_NUMBER = re.compile(r"(?<![\w.])[$€£]?v?\d[\d,]*(?:\.\d+)*(?:%|[a-zA-Z]{0,3}\b)?")
_CITATION = re.compile(r"\[\d+(?:[,–-]\s*\d+)*\]|\([A-Z][A-Za-z'-]+(?: et al\.)?(?:,| and [A-Z][A-Za-z'-]+,)? (?:19|20)\d\d[a-z]?\)")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_PLACEHOLDER = re.compile(r"\[(?:SOURCE NEEDED|VERIFY)[^\]]*\]")


def _norm_number(tok):
    return tok.replace(",", "").rstrip(".").lower()


def extract(text):
    """{kind: Counter(token)} for every invariant kind in `text`."""
    text = _COMMENT.sub(" ", text)  # editor notes, not published facts
    fences = [m.group(0).strip() for m in _FENCE.finditer(text)]
    prose = _FENCE.sub(" ", text)
    inline = _INLINE_CODE.findall(prose)
    no_code = _INLINE_CODE.sub(" ", prose)
    urls = _URL.findall(no_code) + [t for t in _LINK_TARGET.findall(no_code)
                                    if not t.startswith("http")]
    no_urls = _URL.sub(" ", _LINK_TARGET.sub("](", no_code))
    numbers = [_norm_number(n) for n in _NUMBER.findall(no_urls)]
    # A bare list marker ("1." at line start) or a single digit ordinal is not a
    # fact anyone would care to lose.
    numbers = [n for n in numbers if len(n.strip("$€£%")) > 1 or not n.isdigit()]
    return {
        "code_blocks": Counter(fences),
        "inline_code": Counter(inline),
        "links": Counter(urls),
        "numbers": Counter(numbers),
        "citations": Counter(_CITATION.findall(no_urls)),
    }


def compare(original, rewrite, context=None):
    """Report what the rewrite lost and what it introduced.

    `missing`: invariants in the original that are absent from the rewrite.
    `added`: numbers, links and citations that appear only in the rewrite, the
    shape fabrication takes. Code the model added is not listed; a rewrite that
    wraps a term in backticks has not invented anything. Anything present in
    `context` (author material the caller supplied) is sourced, not invented.
    """
    before, after = extract(original), extract(rewrite)
    sourced = extract(context) if context else None
    missing, added = {}, {}
    for kind in before:
        lost = sorted((before[kind] - after[kind]).elements()) if kind != "numbers" else \
            sorted(set(before[kind]) - set(after[kind]))
        if lost:
            missing[kind] = lost
        if kind in ("numbers", "links", "citations"):
            new = sorted(set(after[kind]) - set(before[kind])
                         - (set(sourced[kind]) if sourced else set()))
            if new:
                added[kind] = new
    placeholders = sorted(set(_PLACEHOLDER.findall(rewrite)))
    return {"ok": not missing and not added, "missing": missing, "added": added,
            "placeholders": placeholders}


def summarize(result, limit=12):
    """Plain lines a model can act on."""
    lines = []
    for label, key in (("MISSING from the rewrite (restore verbatim)", "missing"),
                       ("INTRODUCED by the rewrite (not in the source; remove, or mark [SOURCE NEEDED])", "added")):
        for kind, items in sorted(result[key].items()):
            shown = ", ".join(repr(i if len(i) < 80 else i[:77] + "...") for i in items[:limit])
            more = " (+%d more)" % (len(items) - limit) if len(items) > limit else ""
            lines.append("%s, %s: %s%s" % (label, kind, shown, more))
    return lines


__all__ = ["extract", "compare", "summarize"]
