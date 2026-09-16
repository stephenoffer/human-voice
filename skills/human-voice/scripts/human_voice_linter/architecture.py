"""architecture — what a document spends its words on.

Every other check in the linter reads a sentence, a paragraph, or the markdown
shape. None of them reads the document as a plan: which points it makes, how many
times it makes them, how the words are shared out between sections, and whether
every section is written for the same reader. That is where an agent-written
report gives itself away after the diction and the syntax are clean. It says the
same thing in the overview, the body and the summary. It spends four hundred words
on the easy section and one sentence on the hard one. It explains what an API is
two sections after quoting a p99 at a reader it assumed was an expert.

Three checks, all of them count-gated, because every construction measured here is
also something a careful person does once:

- `restatement`: the same point made twice in different places.
- `section_balance`: stub sections next to a bloated one, sections so even they
  were plainly budgeted, framing sections that outweigh the substance, and every
  list cut to the same length.
- `depth_drift`: a long section with nothing checkable in it beside sections dense
  with specifics, or beginner explanations inside a document written for experts.

Judgment still does most of this work. A paraphrase that shares no words with the
sentence it repeats is invisible to a lexical comparison, and whether a section
deserves its length depends on what the reader needs. The checks are a floor.
"""
from __future__ import annotations

import math
import re

from .checks import STOPWORDS
from .hit import Hit
from .textutil import (
    BARE_URL_RE,
    HEADING_LINE_RE,
    INLINE_CODE_RE,
    LINK_RE,
    LIST_MARKER_RE,
    SECTION_RULE_RE,
    SETEXT_RE,
    TABLE_ROW_RE,
    WORD_RE,
    sentences,
    strip_inline_markup,
)

_HEAD_RE = re.compile(r"^[ \t]*(#{1,6})[ \t]+(\S.*?)[ \t]*#*[ \t]*$")

# Words too generic to make two sentences "the same point". Added to the shared
# STOPWORDS so a pair of sentences does not match on "also", "more" and "use".
_EXTRA_STOP = frozenset((
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
_BOILERPLATE_TITLE_RE = re.compile(
    r"\b(?:licen[cs]e|contribut\w*|credits?|authors?|acknowledg\w*|support|contact|"
    r"links?|see\s+also|references?|bibliography|changelog|change\s+log|history|"
    r"related|sponsors?|maintainers?|thanks|disclaimer|copyright|footnotes?|"
    r"table\s+of\s+contents|contents|toc|badges?|status|faq)\b",
    re.IGNORECASE)

# Section titles whose job is framing rather than substance: announcing the topic,
# motivating it, or wrapping it up.
_FRAMING_TITLE_RE = re.compile(
    r"^(?:\d+[.)]?\s*)?(?:an?\s+|the\s+)?(?:introduction|intro|overview|background|"
    r"context|motivation|purpose|scope|summary|executive\s+summary|conclusions?|"
    r"in\s+conclusion|in\s+summary|key\s+takeaways?|takeaways?|final\s+thoughts?|"
    r"closing\s+thoughts?|wrapping\s+up|the\s+bottom\s+line|tl;?dr|why\s+.+\s+matters?|"
    r"why\s+this\s+matters?|what\s+is\s+.+|about(?:\s+this\s+\w+)?)\s*[:?.!]?$",
    re.IGNORECASE)

# The closing half of the framing: the document summarizing itself. A README with a
# long Motivation section is explaining why it exists; an overview plus a recap of
# the overview is the assistant shape.
_RECAP_TITLE_RE = re.compile(
    r"^(?:\d+[.)]?\s*)?(?:summary|executive\s+summary|conclusions?|in\s+conclusion|"
    r"in\s+summary|key\s+takeaways?|takeaways?|final\s+thoughts?|closing\s+thoughts?|"
    r"wrapping\s+up|the\s+bottom\s+line|tl;?dr|recap)\s*[:?.!]?$",
    re.IGNORECASE)

# Markers of technical depth a reader could act on: numbers and units, identifiers,
# flags, file names, paths, acronyms. Code is counted separately from the raw text.
_TECH_MARKER_RE = re.compile(
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
_EXPLAINER_RE = re.compile(
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
_ABSTRACT_RE = re.compile(
    r"\b(?:ensur\w*|reliab\w*|scalab\w*|flexib\w*|efficien\w*|robust\w*|seamless\w*|"
    r"significant\w*|important\w*|importance|critical\w*|crucial\w*|essential\w*|overall|"
    r"various|numerous|meaningful\w*|valuable|effective\w*|comprehensive\w*|streamlin\w*|"
    r"enhanc\w*|optimi[sz]\w*|leverag\w*|facilitat\w*|resilien\w*|holistic\w*|"
    r"best\s+practices?|high\s+level\s+of|key\s+metrics|as\s+needed|going\s+forward|"
    r"long-term\s+success|continue\s+to|well-positioned)\b",
    re.IGNORECASE)

MAX_RESTATEMENT_UNITS = 4000   # bound the pairwise work on a hostile input
MAX_RESTATEMENT_HITS = 40


def _stem(word):
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


def _content_terms(text):
    terms = set()
    for w in WORD_RE.findall(text):
        lw = w.lower()
        if len(lw) < 3 or lw in STOPWORDS or lw in _EXTRA_STOP:
            continue
        terms.add(_stem(lw))
    return terms


def _is_structural(line):
    return bool(HEADING_LINE_RE.match(line) or SETEXT_RE.match(line)
                or SECTION_RULE_RE.match(line) or TABLE_ROW_RE.match(line))


# ---------------------------------------------------------------------------
# Section model
# ---------------------------------------------------------------------------

def document_sections(text, code_stripped):
    """Split a markdown document into its top-level sections.

    The section level is the shallowest heading level that occurs at least twice,
    skipping a lone title heading: `# Title` followed by `## A`, `## B`, `## C`
    gives three sections at level 2, each owning its `###` subsections. Returns
    (sections, preamble) where each section is a dict of counts and the preamble
    is the same shape for whatever precedes the first section heading (None when
    the document has fewer than two section headings).

    `text` is the normalized source and `code_stripped` the same text with code
    blanked; strip_code preserves line geometry, so a line that is blank in the
    stripped copy and not blank in the source is a line of fenced code.
    """
    cs_lines = code_stripped.split("\n")
    raw_lines = text.split("\n")
    heads = []
    for i, ln in enumerate(cs_lines):
        m = _HEAD_RE.match(ln)
        if m:
            heads.append((i, len(m.group(1)), strip_inline_markup(m.group(2)).strip()))
    level = None
    for lvl in sorted({h[1] for h in heads}):
        at = [h for h in heads if h[1] == lvl]
        if len(at) >= 2:
            level = lvl
            break
    if level is None:
        return [], None

    starts = [h for h in heads if h[1] == level]
    sections = []
    for i, _lvl, title in starts:
        end = len(cs_lines)
        for j, l2, _t in heads:
            if j > i and l2 <= level:
                end = j
                break
        sec = _measure(cs_lines, raw_lines, i + 1, end)
        sec["title"] = title
        sec["line"] = i + 1
        sec["subsections"] = sum(1 for j, l2, _t in heads if i < j < end and l2 > level)
        sections.append(sec)
    preamble = _measure(cs_lines, raw_lines, 0, starts[0][0])
    preamble["title"] = ""
    preamble["line"] = 1
    preamble["subsections"] = 0
    return sections, preamble


def _measure(cs_lines, raw_lines, start, end):
    prose_words = 0
    list_words = 0
    code_lines = 0
    table_rows = 0
    inline_code = 0
    markers = 0
    explainers = 0
    abstract = 0
    links = 0
    lists = []           # item count of each contiguous list run
    run = 0
    for idx in range(start, min(end, len(cs_lines))):
        cs = cs_lines[idx]
        raw = raw_lines[idx] if idx < len(raw_lines) else ""
        if not cs.strip():
            if raw.strip():
                code_lines += 1
            continue
        if HEADING_LINE_RE.match(cs) or SETEXT_RE.match(cs) or SECTION_RULE_RE.match(cs):
            if run:
                lists.append(run)
                run = 0
            continue
        if TABLE_ROW_RE.match(cs):
            table_rows += 1
            continue
        inline_code += len(INLINE_CODE_RE.findall(raw))
        links += len(LINK_RE.findall(raw)) + len(BARE_URL_RE.findall(raw))
        body = strip_inline_markup(cs)
        is_item = bool(LIST_MARKER_RE.match(cs))
        if is_item:
            body = LIST_MARKER_RE.sub("", body, count=1)
            run += 1
        elif run and not cs.startswith((" ", "\t")):
            # A non-indented prose line ends the list; an indented one continues
            # the current item.
            lists.append(run)
            run = 0
        n = len(WORD_RE.findall(body))
        if is_item:
            list_words += n
        else:
            prose_words += n
        markers += len(_TECH_MARKER_RE.findall(body))
        explainers += len(_EXPLAINER_RE.findall(body))
        abstract += len(_ABSTRACT_RE.findall(body))
    if run:
        lists.append(run)
    words = prose_words + list_words
    # Code is depth. A fenced block counts a marker for every three lines, capped
    # so a long listing cannot make an otherwise hollow section look dense.
    tech = markers + inline_code + min(code_lines, 60) // 3
    return {
        "words": words,
        "prose_words": prose_words,
        "list_words": list_words,
        "code_lines": code_lines,
        "table_rows": table_rows,
        "tech": tech,
        "explainers": explainers,
        "abstract": abstract,
        "links": links,
        "lists": [n for n in lists if n >= 2],
    }


def _density(sec):
    return sec["tech"] / sec["words"] * 100.0 if sec["words"] else 0.0


def _cov(values):
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean <= 0:
        return None
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)) / mean


def _short(title, n=32):
    return title if len(title) <= n else title[:n - 3].rstrip() + "..."


# ---------------------------------------------------------------------------
# restatement
# ---------------------------------------------------------------------------

def _units(code_stripped):
    """(terms, line, block, section, text, title, release) per sentence and list item.

    A block is a paragraph or one contiguous list; two sentences in the same block
    are the writer building a point, not repeating it, so pairs within a block are
    never compared. Headings delimit sections for the message.
    """
    units = []
    block = 0
    section = 0
    title = ""
    stack = []       # (level, title) of the enclosing headings
    release = False  # inside a heading that names a version or a year
    para = []        # (text, line) for the paragraph being joined

    def flush_para():
        if not para:
            return
        joined = ""
        offsets = []
        for t, ln in para:
            offsets.append((len(joined), ln))
            joined += t + " "
        pos = 0
        for s in sentences(joined):
            at = joined.find(s[:40], pos)
            if at < 0:
                at = pos
            pos = at + 1
            line = para[0][1]
            for off, ln in offsets:
                if off <= at:
                    line = ln
            units.append((_content_terms(s), line, block, section, s, title, release))
        para.clear()

    in_list = False
    for lineno, ln in enumerate(code_stripped.split("\n"), 1):
        if not ln.strip() or _is_structural(ln):
            flush_para()
            if not ln.strip() and in_list:
                # a blank line inside a loose list keeps the list's block
                continue
            block += 1
            in_list = False
            hm = _HEAD_RE.match(ln)
            if hm:
                section += 1
                title = strip_inline_markup(hm.group(2)).strip()
                level = len(hm.group(1))
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                release = any(_VERSION_TITLE_RE.search(t) for _lv, t in stack)
            continue
        body = strip_inline_markup(ln)
        if LIST_MARKER_RE.match(ln):
            flush_para()
            if not in_list:
                block += 1
                in_list = True
            item = LIST_MARKER_RE.sub("", body, count=1).strip()
            units.append((_content_terms(item), lineno, block, section, item, title, release))
            continue
        if in_list and ln.startswith((" ", "\t")) and units:
            # continuation of the previous item: extend its terms
            terms, line, b, sec, prev, t, rel = units[-1]
            units[-1] = (terms | _content_terms(body), line, b, sec,
                         prev + " " + body.strip(), t, rel)
            continue
        if in_list:
            in_list = False
            block += 1
        para.append((body.strip(), lineno))
    flush_para()
    return units


def _norm(text):
    return " ".join(WORD_RE.findall(text.lower()))


def _opening(text):
    return tuple(w.lower() for w in WORD_RE.findall(text)[:2])


# A unit that is really a signature or an expression that survived code stripping
# (an indented C prototype, `foo(bar) -> baz`). Two of them match on identifiers.
_CODELIKE_RE = re.compile(r"[;{}]|\w\(|=>|->|::")
# An API reference entry: a heading that names a function, method or identifier
# (`parse(input)`, `Consumer.prototype.eachMapping`, `max_retries`), or one whose
# whole text was inline code and is blank once code is stripped. Entries under two
# such headings describe parallel things in parallel words.
_REFERENCE_TITLE_RE = re.compile(r"^\W*$|\w\(|\w\.\w|\w_\w|\b[a-z]+[A-Z]\w*")
# A changelog entry. Release notes repeat "Fixed a crash in X" by design.
_VERSION_TITLE_RE = re.compile(r"\bv?\d+\.\d+|\b(?:19|20)\d\d\b")


_NUMBER_TOKEN_RE = re.compile(r"\d[\d,.:]*(?:\s?%|\s?[A-Za-z]{1,3}\b)?")


_RECAP_WORDS = frozenset(("summary", "summarize", "summarise", "summarizing",
                          "conclusion", "conclude", "recap", "overall"))


def _distinct_detail(unit_text, doc_lower, limit=5):
    """What a repeated sentence says that nothing else in the document says.

    A restated pair is rarely a perfect copy. The summary that re-words the
    overview often carries one fact the overview left out, and deleting the
    "duplicate" deletes that fact. So the finding names every number and content
    word in the repeat that appears nowhere else in the source, and the fix it
    suggests is a merge. Compared against the raw source rather than the
    code-stripped text, so a term inside backticks elsewhere still counts as
    stated. Words compare on a five-letter prefix of the word with a common suffix
    stripped (gives -> give), numbers literally. Lexical, so a paraphrase can
    still carry a distinct claim the finding does not name.
    """
    unit_lower = unit_text.lower()
    out = []
    for m in _NUMBER_TOKEN_RE.finditer(unit_text):
        tok = m.group(0).strip()
        if doc_lower.count(tok.lower()) <= unit_lower.count(tok.lower()) and tok not in out:
            out.append(tok)
    seen = set()
    for w in WORD_RE.findall(unit_text):
        lw = w.lower().strip("'’-")
        if len(lw) < 3 or lw in STOPWORDS or lw in _EXTRA_STOP or lw in _RECAP_WORDS:
            continue
        base = re.sub(r"(?:ing|ed|es|s|ly)$", "", lw) if len(lw) > 4 else lw
        prefix = base[:5]
        if prefix in seen:
            continue
        seen.add(prefix)
        pat = re.compile(r"\b" + re.escape(prefix))
        if len(pat.findall(doc_lower)) <= len(pat.findall(unit_lower)):
            out.append(w)
    return out[:limit]


def check_restatement(code_stripped, word_count, jaccard_min, min_pairs,
                      per_1k_min, hits, report, min_terms=6, min_gap=8, source=None):
    """The same point made twice, in different paragraphs or sections.

    Each sentence and list item is reduced to a set of stemmed content words and
    compared with every earlier one outside its own paragraph. A pair whose
    Jaccard overlap reaches `jaccard_min` is a restatement. The check fires only
    at `min_pairs` or more: a person repeats one key point on purpose, an agent
    re-announces its whole overview in the summary.

    Three exclusions keep reference documentation quiet, each measured against
    long human READMEs and manuals:

    - Pairs inside one section of a sectioned document, or closer than `min_gap`
      units in a document without sections. Parallel option descriptions ("Operates in global mode, so...")
      sit next to each other; an agent's restatement is the overview coming back
      in the summary.
    - Verbatim copies. A human pastes the same note under two options; an agent
      re-words the point it already made.
    - Templated entries: two units opening on the same two words ("Returns the
      original...", "If the flag is truthy...") are parallel reference entries,
      unless the later one sits in a summary or conclusion, where a repeat is a
      recap. Code-like units and anything under a version or year heading (a
      changelog entry, at any depth) are skipped outright, and so
      are pairs where both headings name an API entry.
    - Documents below `per_1k_min` restated pairs per 1,000 words. A 3,000-word
      manual that says one thing twice is not the same finding as a 400-word
      design doc that says four things twice.

    Lexical, so a paraphrase built from different words passes. Units under
    `min_terms` content words are skipped because short sentences share words by
    chance.
    """
    units = [u for u in _units(code_stripped)
             if len(u[0]) >= min_terms and not _CODELIKE_RE.search(u[4])
             and not u[6]]
    units = units[:MAX_RESTATEMENT_UNITS]
    sectioned = len({u[3] for u in units}) >= 3
    postings = {}
    pairs = []
    for i, (terms, _line, block, sec, text, title, _rel) in enumerate(units):
        opening = _opening(text)
        wraps_up = bool(_FRAMING_TITLE_RE.match(title))
        overlap = {}
        for t in terms:
            for j in postings.get(t, ()):
                overlap[j] = overlap.get(j, 0) + 1
        best = None
        for j, shared in overlap.items():
            o_terms, _l, o_block, o_sec, o_text, o_title, _orel = units[j]
            if o_block == block:
                continue
            if (o_sec == sec) if sectioned else (i - j < min_gap):
                continue
            if _norm(o_text) == _norm(text):
                continue
            if not wraps_up and opening and _opening(o_text) == opening:
                continue
            if _REFERENCE_TITLE_RE.search(title) and _REFERENCE_TITLE_RE.search(o_title):
                continue
            union = len(terms) + len(o_terms) - shared
            jac = shared / union if union else 0.0
            if jac >= jaccard_min and (best is None or jac > best[1]):
                best = (j, jac)
        if best is not None:
            pairs.append((best[0], i, best[1]))
        for t in terms:
            postings.setdefault(t, []).append(i)
    report["restated_pairs"] = len(pairs)
    rate = len(pairs) / word_count * 1000.0 if word_count else 0.0
    report["restated_per_1k"] = round(rate, 1)
    if len(pairs) < min_pairs or rate < per_1k_min:
        return
    doc_lower = (source if source is not None else code_stripped).lower()
    for j, i, jac in pairs[:MAX_RESTATEMENT_HITS]:
        first = units[j]
        later = units[i]
        where = "another section" if first[3] != later[3] else "an earlier paragraph"
        preview = " ".join(first[4].split())
        if len(preview) > 60:
            preview = preview[:57].rstrip() + "..."
        extra = _distinct_detail(later[4], doc_lower)
        if extra:
            suggestion = ("merge, don't cut: nothing else in the document says %s; "
                          "move that into the copy you keep, or ask before dropping it"
                          % ", ".join(extra))
        else:
            suggestion = ("say it once, where it does the most work; every word in this "
                          "copy is stated elsewhere")
        hits.append(Hit("restatement", later[1],
                        "repeats L%d from %s (overlap %.2f): %r" % (first[1], where, jac, preview),
                        suggestion))


# ---------------------------------------------------------------------------
# section_balance
# ---------------------------------------------------------------------------

def _is_stub(s, stub_words):
    """A heading with nothing behind it.

    Not short: hollow. A README's two-line Community or Downloads section is a
    pointer, and it carries a link or a command; a changelog entry or an FAQ
    question is short by design. What an outline filled in by quota leaves behind
    is a sentence with no link, no code, no list, and nothing checkable in it: "We
    will test the migration thoroughly."
    """
    title = s["title"]
    return (0 < s["words"] < stub_words and s["code_lines"] < 2 and s["table_rows"] < 2
            and s["subsections"] == 0 and s["links"] == 0 and s["tech"] == 0
            and not s["lists"]
            and not title.rstrip().endswith("?") and not re.search(r"\d", title)
            and not _BOILERPLATE_TITLE_RE.search(title))


def check_section_balance(sections, stub_words, even_cov_floor,
                          framing_share_max, hits, report, min_sections=4,
                          min_words=250):
    """How the words are shared out between sections.

    Four findings, each a different way an outline gets filled in by quota rather
    than by what the reader needs:

    - stubs: two or more hollow sections under `stub_words` words (see _is_stub),
      at least a fifth of all sections, in a document where another section runs
      eight times longer. The heading promised a topic and the writer had nothing
      to say about it.
    - even sections: five or more sections of real length whose word counts vary
      by less than `even_cov_floor`. Real topics are not the same size.
    - framing: overview, background, summary and "why it matters" sections holding
      more than `framing_share_max` of the words, where one of them is a recap
      (or framing passes half the document outright). The document spends more on
      announcing and recapping than on the subject. A long Motivation section
      with no summary is a person explaining why the project exists.
    - list symmetry: four or more lists of three or more items, spread over at
      least three sections, all cut to the same length: the "three pros, three
      cons" quota.
    """
    report["sections"] = len(sections)
    if not sections:
        report["section_words"] = None
        report["section_len_cov"] = None
        report["framing_share"] = None
        return
    sizes = [s["words"] for s in sections]
    total = sum(sizes)
    report["section_words"] = sizes
    cov = _cov(sizes)
    report["section_len_cov"] = round(cov, 2) if cov is not None else None
    framing = sum(s["words"] for s in sections if _FRAMING_TITLE_RE.match(s["title"]))
    share = framing / total if total else 0.0
    report["framing_share"] = round(share, 2)
    # Section words include list items, which the prose word count leaves out; a
    # migration plan whose substance is a schema and a bulleted runbook is still a
    # document with sections to weigh.
    if len(sections) < min_sections or total < min_words:
        return

    stubs = [s for s in sections if _is_stub(s, stub_words)]
    report["stub_sections"] = len(stubs)
    largest = max(sections, key=lambda s: s["words"])
    if len(stubs) >= 2 and len(stubs) * 5 >= len(sections) and largest["words"] >= max(100, 8 * max(s["words"] for s in stubs)):
        names = ", ".join("%r (%d)" % (_short(s["title"]), s["words"]) for s in stubs[:4])
        hits.append(Hit("section_balance", 0,
                        "%d stub sections %s beside %r at %d words"
                        % (len(stubs), names, _short(largest["title"]), largest["words"]),
                        "write the thin sections, fold each into a neighbour with its "
                        "commitment intact, or mark the gap; a heading is a promise"))

    # Changelog releases are even by construction; they are not a quota.
    real = [s for s in sections
            if s["words"] >= 40 and not _BOILERPLATE_TITLE_RE.search(s["title"])
            and not _VERSION_TITLE_RE.search(s["title"])]
    real_cov = _cov([s["words"] for s in real])
    if len(real) >= 5 and real_cov is not None and real_cov < even_cov_floor:
        mean = sum(s["words"] for s in real) / len(real)
        hits.append(Hit("section_balance", 0,
                        "%d sections all within a few words of %d (CoV %.2f)"
                        % (len(real), round(mean), real_cov),
                        "size each section by what it has to say, not by a quota"))

    framing_secs = [s for s in sections if _FRAMING_TITLE_RE.match(s["title"])]
    recap = any(_RECAP_TITLE_RE.match(s["title"]) for s in framing_secs)
    if share > framing_share_max and len(framing_secs) >= 2 and (recap or share > 0.5):
        hits.append(Hit("section_balance", 0,
                        "%.0f%% of the words sit in framing sections (%s)"
                        % (share * 100, ", ".join(repr(_short(s["title"], 24))
                                                  for s in framing_secs[:4])),
                        "fold the framing into the body; a claim only the overview or "
                        "recap carries moves, it does not go"))

    runs = [(s["title"], n) for s in sections for n in s["lists"]]
    owners = {t for t, _n in runs}
    if (len(runs) >= 4 and len(owners) >= 3 and runs[0][1] >= 3
            and len({n for _t, n in runs}) == 1):
        hits.append(Hit("section_balance", 0,
                        "all %d lists have exactly %d items" % (len(runs), runs[0][1]),
                        "let each list be as long as its content; drop the padding item "
                        "or add the missing one"))


# ---------------------------------------------------------------------------
# depth_drift
# ---------------------------------------------------------------------------

def check_depth_drift(sections, preamble, dense_min, hollow_max, expert_min,
                      hits, report, min_section_words=40, hollow_words=120,
                      abstract_min=1.5, explainer_min=3):
    """Is every part of the document written for the same reader?

    Technical depth is approximated by checkable markers per 100 words: numbers
    with units, identifiers, flags, paths, file names, acronyms, inline code, and
    fenced code. Two findings:

    - hollow section: a section of `hollow_words` or more with at most
      `hollow_max` markers per 100 words and at least `abstract_min` abstract
      benefit words per 100 ("ensures", "reliability", "flexibility"), in a
      document where another section carries `dense_min` or more. One part was
      written by someone who knew the system and another by someone describing it
      from outside. The abstraction requirement is what separates this from a
      person's conceptual section (a code of conduct, a "how it differs from X"
      discussion), which is light on markers too but talks about particular
      things. Framing sections (overview, summary) are exempt: saying nothing
      checkable is their job, and section_balance weighs how much room they take.
    - explainer whiplash: `explainer_min` or more beginner explanations ("in
      simple terms", "think of it as") in a document whose overall density is
      `expert_min` or higher.
    """
    qualifying = [s for s in sections if s["words"] >= min_section_words
                  and not _BOILERPLATE_TITLE_RE.search(s["title"])]
    dens = [round(_density(s), 1) for s in qualifying]
    report["section_depth"] = dens or None
    everything = list(sections) + ([preamble] if preamble else [])
    total_words = sum(s["words"] for s in everything)
    total_tech = sum(s["tech"] for s in everything)
    explainers = sum(s["explainers"] for s in everything)
    doc_density = total_tech / total_words * 100.0 if total_words else 0.0
    report["depth_per_100"] = round(doc_density, 1)
    report["explainers"] = explainers

    if len(qualifying) >= 3:
        densest = max(qualifying, key=_density)
        if _density(densest) >= dense_min:
            for s in qualifying:
                abstract = s["abstract"] / s["words"] * 100.0
                if (s["words"] >= hollow_words and _density(s) <= hollow_max
                        and abstract >= abstract_min
                        and not _FRAMING_TITLE_RE.match(s["title"])):
                    hits.append(Hit("depth_drift", s["line"],
                                    "section %r: %d words, %.1f specifics/100w, while %r carries %.1f"
                                    % (_short(s["title"]), s["words"], _density(s),
                                       _short(densest["title"]), _density(densest)),
                                    "bring in the real detail, or shrink it to the claims it "
                                    "alone makes; ask before dropping one"))

    if explainers >= explainer_min and doc_density >= expert_min and total_words >= 150:
        hits.append(Hit("depth_drift", 0,
                        "%d beginner explanations in a document at %.1f specifics/100w"
                        % (explainers, doc_density),
                        "pick one reader; drop the primer or move it to a glossary"))


def run_architecture_checks(text, code_stripped, word_count, thr, hits, report):
    """Entry point from analyze(): builds the section model once and runs all three."""
    sections, preamble = document_sections(text, code_stripped)
    check_restatement(code_stripped, word_count, thr("restatement_jaccard"),
                      int(thr("restatement_min_pairs")), thr("restatement_per_1k"),
                      hits, report, source=text)
    check_section_balance(sections, thr("section_stub_words"),
                          thr("section_even_cov_floor"), thr("framing_share_max"),
                          hits, report)
    check_depth_drift(sections, preamble, thr("depth_dense_per_100"),
                      thr("depth_hollow_per_100"), thr("depth_expert_per_100"),
                      hits, report)


__all__ = [
    "document_sections",
    "check_restatement",
    "check_section_balance",
    "check_depth_drift",
    "run_architecture_checks",
]
