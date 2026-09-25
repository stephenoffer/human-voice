"""vocabulary — the title and body patterns the architecture checks classify by."""
from __future__ import annotations

import re

from ...text.tokens import STOPWORDS, WORD_RE

HEAD_RE = re.compile(r"^[ \t]*(#{1,6})[ \t]+(\S.*?)[ \t]*#*[ \t]*$")

# Words too generic to make two sentences "the same point". Added to the shared
# STOPWORDS so a pair of sentences does not match on "also", "more" and "use".
EXTRA_STOP = frozenset((
    "also", "more", "most", "such", "each", "other", "some", "any", "all", "only",
    "just", "very", "one", "two", "new", "make", "makes", "made", "well", "like",
    "way", "ways", "need", "needs", "get", "gets", "set", "both", "same", "even",
    "much", "many", "then", "once", "still", "every", "because", "while", "through",
    "without", "within", "across", "between", "after", "before", "per", "via",
    "them", "him", "her", "his", "us", "me", "my", "its", "it's", "don't", "no",
    "yes", "own", "out", "up", "down", "off", "again", "further", "first", "last",
))

# Sections a person writes short on purpose. A one-line License section is not a
# stub any reader would complain about.
BOILERPLATE_TITLE_RE = re.compile(
    r"\b(?:licen[cs]e|contribut\w*|credits?|authors?|acknowledg\w*|support|contact|"
    r"links?|see\s+also|references?|bibliography|changelog|change\s+log|history|"
    r"related|sponsors?|maintainers?|thanks|disclaimer|copyright|footnotes?|"
    r"table\s+of\s+contents|contents|toc|badges?|status|faq)\b",
    re.IGNORECASE)

# Section titles whose job is framing rather than substance: announcing the topic,
# motivating it, or wrapping it up.
FRAMING_TITLE_RE = re.compile(
    r"^(?:\d+[.)]?\s*)?(?:an?\s+|the\s+)?(?:introduction|intro|overview|background|"
    r"context|motivation|purpose|scope|summary|executive\s+summary|conclusions?|"
    r"in\s+conclusion|in\s+summary|key\s+takeaways?|takeaways?|final\s+thoughts?|"
    r"closing\s+thoughts?|wrapping\s+up|the\s+bottom\s+line|tl;?dr|why\s+.+\s+matters?|"
    r"why\s+this\s+matters?|what\s+is\s+.+|about(?:\s+this\s+\w+)?)\s*[:?.!]?$",
    re.IGNORECASE)

# The closing half of the framing: the document summarizing itself. A README with a
# long Motivation section is explaining why it exists; an overview plus a recap of
# the overview is the assistant shape.
RECAP_TITLE_RE = re.compile(
    r"^(?:\d+[.)]?\s*)?(?:summary|executive\s+summary|conclusions?|in\s+conclusion|"
    r"in\s+summary|key\s+takeaways?|takeaways?|final\s+thoughts?|closing\s+thoughts?|"
    r"wrapping\s+up|the\s+bottom\s+line|tl;?dr|recap)\s*[:?.!]?$",
    re.IGNORECASE)

# A changelog entry. Release notes repeat "Fixed a crash in X" by design.
VERSION_TITLE_RE = re.compile(r"\bv?\d+\.\d+|\b(?:19|20)\d\d\b")

# An API reference entry: a heading that names a function, method or identifier
# (`parse(input)`, `Consumer.prototype.eachMapping`, `max_retries`), or one whose
# whole text was inline code and is blank once code is stripped. Entries under two
# such headings describe parallel things in parallel words.
REFERENCE_TITLE_RE = re.compile(r"^\W*$|\w\(|\w\.\w|\w_\w|\b[a-z]+[A-Z]\w*")

# Markers of technical depth a reader could act on: numbers and units, identifiers,
# flags, file names, paths, acronyms. Code is counted separately from the raw text.
TECH_MARKER_RE = re.compile(
    r"\b\d[\d,.:]*\s?(?:%|ms|s|sec|min|h|hrs?|kb|mb|gb|tb|kib|mib|gib|x|rps|qps|"
    r"tokens?|rows?|cores?|nodes?|gpus?)?\b"
    r"|\b[a-z]+(?:[A-Z][a-z0-9]+)+\b"                 # camelCase
    r"|\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b"         # PascalCase
    r"|\b[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+\b"            # snake_case
    r"|(?<![\w-])--?[a-z][\w-]*"                      # --flag, -v
    r"|\b[\w-]+\.(?:py|js|ts|go|rs|md|json|ya?ml|toml|sh|sql|cfg|ini|conf|txt|csv)\b"
    r"|(?<![\w/])/[\w.-]+/[\w./-]*"                   # /a/path
    r"|\b[A-Z]{2,6}s?\b")                             # API, SLOs

# Explanations pitched at a reader who has never seen the topic. Ordinary in a
# tutorial; whiplash in a document that elsewhere assumes an expert.
EXPLAINER_RE = re.compile(
    r"\b(?:in\s+simple\s+terms|simply\s+put|put\s+simply|in\s+layman'?s\s+terms|"
    r"think\s+of\s+(?:it|this|them|a|an)\s+(?:as|like)|for\s+those\s+(?:unfamiliar|new\s+to)|"
    r"if\s+you'?re\s+(?:new|not\s+familiar)|for\s+(?:the\s+)?(?:uninitiated|beginners)|"
    r"a\s+quick\s+primer|in\s+plain\s+english|to\s+put\s+it\s+simply|"
    r"at\s+its\s+(?:core|simplest|heart)|(?:is|are)\s+essentially\s+(?:a|an|just)|"
    r"(?:is|are)\s+basically\s+(?:a|an|just)|imagine\s+(?:you|a|an|that)\b|"
    r"you\s+can\s+think\s+of)\b",
    re.IGNORECASE)

# The vocabulary a section falls back on when it has nothing specific to say:
# abstract benefits and qualities with no object a reader could check. On its own
# every one of these is ordinary; a long section made of them and nothing else is
# the tell. Used only to confirm a hollow section, never scored by itself.
ABSTRACT_RE = re.compile(
    r"\b(?:ensur\w*|reliab\w*|scalab\w*|flexib\w*|efficien\w*|robust\w*|seamless\w*|"
    r"significant\w*|important\w*|importance|critical\w*|crucial\w*|essential\w*|overall|"
    r"various|numerous|meaningful\w*|valuable|effective\w*|comprehensive\w*|streamlin\w*|"
    r"enhanc\w*|optimi[sz]\w*|leverag\w*|facilitat\w*|resilien\w*|holistic\w*|"
    r"best\s+practices?|high\s+level\s+of|key\s+metrics|as\s+needed|going\s+forward|"
    r"long-term\s+success|continue\s+to|well-positioned)\b",
    re.IGNORECASE)


def stem(word):
    """A deliberately crude stem: lowercase and the first six letters.

    configure / configured / configuration all land on "config", and latency /
    latencies on "latenc". A real stemmer would be more accurate and would add a
    dependency to a linter that has none; the comparison only needs "these two
    sentences are built from the same words".
    """
    w = word.lower().strip("'’-")
    if w.endswith("'s") or w.endswith("’s"):
        w = w[:-2]
    return w[:6]


def is_content_word(lw):
    return len(lw) >= 3 and lw not in STOPWORDS and lw not in EXTRA_STOP


def content_terms(text):
    """The stemmed content words of `text`, as a set."""
    return {stem(w.lower()) for w in WORD_RE.findall(text) if is_content_word(w.lower())}


def short_title(title, n=32):
    return title if len(title) <= n else title[:n - 3].rstrip() + "..."


__all__ = [
    "HEAD_RE",
    "EXTRA_STOP",
    "BOILERPLATE_TITLE_RE",
    "FRAMING_TITLE_RE",
    "RECAP_TITLE_RE",
    "VERSION_TITLE_RE",
    "REFERENCE_TITLE_RE",
    "TECH_MARKER_RE",
    "EXPLAINER_RE",
    "ABSTRACT_RE",
    "stem",
    "is_content_word",
    "content_terms",
    "short_title",
]
