"""masking — the spans the autofixer must never edit, and splicing edits back."""
from __future__ import annotations

import re

from ..text.markdown import BARE_URL_RE, CODE_FENCE_RE, FOOTNOTE_REF_RE, HTML_TAG_RE, INLINE_CODE_RE

# Code is masked with NUL rather than spaces. Blanking to spaces looked harmless
# and silently destroyed code: the dash and emoji patterns pad themselves with
# `[ \t]*`, so in "labeled `ai` — balanced" the masked span read as whitespace,
# the dash match extended across it, and splicing the replacement back into the
# original text deleted the `ai`. NUL is not whitespace, is not a word character,
# and appears in no real prose, so every pattern stops at the code boundary
# instead of consuming it.
CODE_MASK_CHAR = "\x00"

# Spans the autofixer must never rewrite, beyond code. A URL is not prose: a
# lexical swap inside one silently broke the link (`.../delve-into-it` became
# `.../examine-into-it`) and the dash rule turned a query string's `a--b` into
# `a, b`. Same for HTML tags and link reference definitions.
LINK_DEST_RE = re.compile(r"(!?\[[^\]]*\])(\([^)\n]*\))")
AUTOLINK_RE = re.compile(r"<[A-Za-z][A-Za-z0-9+.-]*:[^>\s]*>")
REF_DEF_RE = re.compile(r"^[ \t]*\[[^\]]+\]:[ \t]*\S+", re.MULTILINE)


def _mask_span(m, group=0):
    """Equal-length NUL filler for a match (newlines kept so lines still align)."""
    s = m.group(group)
    return "".join("\n" if c == "\n" else CODE_MASK_CHAR for c in s)


def mask_code(text):
    """Blank code, URLs, and markup targets with EQUAL-LENGTH non-whitespace filler
    (newlines kept in place). Unlike strip_code, which collapses a fence to bare
    newlines, this preserves exact character offsets, so a match found in the mask
    splices back into the original text correctly even after a code block.

    Masking is deliberately wider than "code": anything the autofixer would corrupt
    by editing it as prose belongs here. URLs are the important case -- swapping a
    filler word inside a link destination produces a 404, not a better sentence.
    """
    masked = CODE_FENCE_RE.sub(_mask_span, text)
    masked = INLINE_CODE_RE.sub(_mask_span, masked)
    # Link/image destinations only; the anchor text stays editable prose.
    masked = LINK_DEST_RE.sub(lambda m: m.group(1) + _mask_span(m, 2), masked)
    masked = AUTOLINK_RE.sub(_mask_span, masked)
    masked = REF_DEF_RE.sub(_mask_span, masked)
    masked = BARE_URL_RE.sub(_mask_span, masked)
    masked = HTML_TAG_RE.sub(_mask_span, masked)
    masked = FOOTNOTE_REF_RE.sub(_mask_span, masked)
    return masked


def apply_edits(text, edits):
    """Splice (start, end, replacement) edits into `text`; keep the leftmost on
    overlap. Returns (new_text, applied_count). Offsets index `mask_code(text)`,
    which shares geometry with `text`, so code is never modified."""
    edits.sort(key=lambda e: e[0])
    out, pos, last, applied = [], 0, -1, 0
    for s, e, rep in edits:
        if s < last:
            continue
        out.append(text[pos:s])
        out.append(rep)
        pos, last, applied = e, e, applied + 1
    out.append(text[pos:])
    return "".join(out), applied


__all__ = ["CODE_MASK_CHAR", "LINK_DEST_RE", "AUTOLINK_RE", "REF_DEF_RE", "mask_code", "apply_edits"]
