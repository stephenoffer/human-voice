"""markdown — normalization and the line-level markdown grammar every check shares.

Everything here preserves line geometry unless it says otherwise, so an offset
found in a derived text still resolves to the right source line.
"""
from __future__ import annotations

import re

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols, pictographs, emoticons, transport, supplemental
    "\U00002700-\U000027BF"   # dingbats (✂ ✅ ✨ ❌ ❤)
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U0000FE0F"              # emoji variation selector
    "]"
)

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

CODE_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?(?:\n([\s\S]*?))?(?:\n[ \t]*\1[ \t]*$|\Z)",
                           re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")
LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
BARE_URL_RE = re.compile(r"(?:https?|ftp)://\S+|www\.\S+")
FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]]+\]")
HTML_TAG_RE = re.compile(r"<[^>\n]+>")
EMPHASIS_RE = re.compile(r"\*\*\*|\*\*|\*|~~")
# Underscore emphasis only at a word boundary. CommonMark does not treat an
# intraword underscore as emphasis, and the old pattern did: `get_user_by_id`
# became `getuserbyid` and `MAX_RETRY_COUNT` became `MAXRETRYCOUNT`, which
# corrupted the word count, the n-gram counts, and the type-token ratio of every
# technical document that names an identifier outside backticks.
UNDERSCORE_EMPHASIS_RE = re.compile(
    r"(?<![A-Za-z0-9_])_{1,3}(?=\S)|(?<=\S)_{1,3}(?![A-Za-z0-9_])")
HEADING_LINE_RE = re.compile(r"^[ \t]*#{1,6}[ \t]+")
SETEXT_RE = re.compile(r"^[ \t]*(=+|-+)[ \t]*$")
LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")
BLOCKQUOTE_RE = re.compile(r"^[ \t]*>+[ \t]?")
TABLE_ROW_RE = re.compile(r"^[ \t]*\|.*\|?[ \t]*$")
TABLE_SEP_RE = re.compile(r"^[ \t]*\|?[\s:|-]*[-:][\s:|-]*\|?[ \t]*$")
SECTION_RULE_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$")
SECTION_RULE_MULTILINE_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.MULTILINE)
FOOTNOTE_DEF_RE = re.compile(r"^[ \t]*\[\^[^\]]+\]:")


def normalize_text(text):
    """Canonical form every entry point must agree on.

    CRLF endings, a UTF-8 BOM, and stray control characters all change what the
    line-anchored patterns match: `---\\r\\n` front matter is not recognized as
    front matter, and a NUL inside a word breaks tokenization. `read_input` used
    to do this and the library entry point did not, so `lint(open(f).read())`
    and the CLI could disagree about the same file. Both call this now.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("﻿"):
        text = text[1:]
    return CONTROL_CHARS_RE.sub("", text)


def blank_frontmatter(text):
    """Blank a leading YAML/TOML front-matter block (keeping line geometry).

    Front-matter delimiters (`---`) are otherwise counted as horizontal rules
    and the key/value lines are scored as prose.
    """
    if not (text.startswith("---\n") or text.startswith("+++\n")):
        return text
    fence = text[:3]
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i].strip() in (fence, "---", "..."):
            for j in range(i + 1):
                lines[j] = ""
            return "\n".join(lines)
    return text  # no closing fence: treat as ordinary content


def strip_code(text):
    """Replace fenced and inline code with newline-preserving blanks.

    Keeps the character/line geometry so reported line numbers still line up
    with the original file.
    """
    def fence_sub(m):
        return "\n" * m.group(0).count("\n")
    text = CODE_FENCE_RE.sub(fence_sub, text)
    text = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)
    return text


def strip_inline_markup(line):
    line = LINK_RE.sub(r"\1", line)        # links/images -> anchor text only
    line = BARE_URL_RE.sub(" ", line)      # drop bare URLs
    line = FOOTNOTE_REF_RE.sub(" ", line)
    line = HTML_TAG_RE.sub(" ", line)
    line = EMPHASIS_RE.sub("", line)       # drop emphasis markers, keep words
    line = UNDERSCORE_EMPHASIS_RE.sub("", line)
    return line


def is_structural_line(line):
    """Headings, setext underlines, rules, and table rows: markup, not prose."""
    return bool(HEADING_LINE_RE.match(line) or SETEXT_RE.match(line)
                or SECTION_RULE_RE.match(line) or TABLE_ROW_RE.match(line))


__all__ = [
    "EMOJI_RE",
    "CONTROL_CHARS_RE",
    "CODE_FENCE_RE",
    "INLINE_CODE_RE",
    "LINK_RE",
    "BARE_URL_RE",
    "FOOTNOTE_REF_RE",
    "HTML_TAG_RE",
    "EMPHASIS_RE",
    "UNDERSCORE_EMPHASIS_RE",
    "HEADING_LINE_RE",
    "SETEXT_RE",
    "LIST_MARKER_RE",
    "BLOCKQUOTE_RE",
    "TABLE_ROW_RE",
    "TABLE_SEP_RE",
    "SECTION_RULE_RE",
    "SECTION_RULE_MULTILINE_RE",
    "FOOTNOTE_DEF_RE",
    "normalize_text",
    "blank_frontmatter",
    "strip_code",
    "strip_inline_markup",
    "is_structural_line",
]
