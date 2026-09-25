"""lexical — tells that live as word and regex lists in the pattern file.

Each list in `ai_prose_patterns.json` becomes one check instance. The lists are
data; the three classes here are the only code that reads them.
"""
from __future__ import annotations

import re

from ..config.patterns import as_phrase_list
from ..core.check import Check, clip
from ..core.log import warn
from ..text.markdown import BLOCKQUOTE_RE, HEADING_LINE_RE
from ..text.phrases import compile_phrase_matchers, norm_phrase, overlaps

# A citation/source token appearing just after a phrase ("studies suggest [1]",
# "studies show (Smith 2024)") means the attribution is NOT vague.
CITATION_NEAR_RE = re.compile(
    r"\[\^?\d|\[\d+\]|\(\s*[A-Z][\w.&-]+,?\s*(?:et al\.?,?\s*)?\d{4}|\(\d{4}\)|https?://|doi:")


def _line_bounds(text, idx):
    start = text.rfind("\n", 0, idx) + 1
    end = text.find("\n", idx)
    return start, (end if end != -1 else len(text))


class PhraseListCheck(Check):
    """Flag every phrase from one pattern list, in ONE pass per boundary bucket.

    This used to compile and run a separate `\\bphrase\\b` regex per entry. With a
    thousand-plus entries in the pattern file that was 66% of total analysis time:
    a 36,000-word document meant twelve hundred full scans of the text. The
    phrases are alternated into a handful of combined regexes instead, and each
    match is mapped back to its suggestion by normalizing the matched text the
    same way `phrase_regex` normalizes the phrase.

    One deliberate behavior change comes with it: where two phrases in the SAME
    list overlap at the same position, the alternation picks the longer one rather
    than emitting both. That is what a reader would call one finding.

    `cite_guard` skips a match followed closely by a citation (vague attribution
    that is immediately sourced is not vague). `skip_quoted` skips matches on
    heading and blockquote lines and inside a double-quoted span, where the
    wording belongs to someone else.
    """

    def __init__(self, category, pattern_key=None, cite_guard=False, skip_quoted=False):
        self.category = category
        self.pattern_key = pattern_key or category
        self.cite_guard = cite_guard
        self.skip_quoted = skip_quoted

    def run(self, doc, ctx):
        pairs = as_phrase_list(ctx.patterns.get(self.pattern_key))
        if not pairs:
            return
        text = doc.code_stripped
        protected = ctx.protected
        lookup = {}
        for phrase, suggestion in pairs:
            lookup.setdefault(norm_phrase(phrase), suggestion)
        found = ctx.seen_spans.setdefault(self.category, set())
        # Collect from every chunk first, then take the longest match at each position
        # and drop anything overlapping it. Two entries in one list that cover the same
        # words ("it's worth noting" and "worth noting that") are one finding, not two,
        # and this is also what keeps chunked alternations from re-introducing the
        # double count across chunk boundaries.
        matches = []
        for rx in compile_phrase_matchers([p for p, _ in pairs]):
            matches.extend(rx.finditer(text))
        matches.sort(key=lambda m: (m.start(), -(m.end() - m.start())))
        kept = []
        last_end = -1
        for m in matches:
            if m.start() < last_end:
                continue
            kept.append(m)
            last_end = m.end()
        for m in kept:
            span = (m.start(), m.end())
            # Don't double-flag the same span across overlapping lists.
            if span in found:
                continue
            # Suppress a hit that is part of a known-legitimate phrase.
            if protected and overlaps(m.start(), m.end(), protected):
                continue
            if self.cite_guard and CITATION_NEAR_RE.search(text[m.end():m.end() + 45]):
                continue
            if self.skip_quoted and self._quoted(text, m):
                continue
            found.add(span)
            suggestion = lookup.get(norm_phrase(m.group(0)))
            ctx.emit(self.span_hit(doc.code_lines, m, m.group(0),
                                   suggestion if suggestion else "cut"))

    @staticmethod
    def _quoted(text, m):
        ls, le = _line_bounds(text, m.start())
        line = text[ls:le]
        if HEADING_LINE_RE.match(line) or BLOCKQUOTE_RE.match(line):
            return True
        return text.count('"', ls, m.start()) % 2 == 1


class PatternListCheck(Check):
    """Run a JSON-supplied list of regexes and emit hits under one category.

    For the structural tells that live as regex lists in the patterns file
    (antithesis, false agency, negative listing, dramatic fragmentation).
    `honor_protected` applies the protected spans the phrase lists use.
    """

    def __init__(self, category, pattern_key, suggestion, honor_protected=True):
        self.category = category
        self.pattern_key = pattern_key
        self.suggestion = suggestion
        self.honor_protected = honor_protected

    def run(self, doc, ctx):
        patterns = ctx.patterns.get(self.pattern_key)
        if not isinstance(patterns, list):
            return
        text = doc.code_stripped
        protected = ctx.protected if self.honor_protected else ()
        for pat in patterns:
            if not isinstance(pat, str) or not pat:
                continue
            try:
                rx = re.compile(pat, re.IGNORECASE)
            except re.error as exc:
                warn("skipping invalid %s pattern %r: %s" % (self.category, pat, exc))
                continue
            for m in rx.finditer(text):
                if protected and overlaps(m.start(), m.end(), protected):
                    continue
                ctx.emit(self.span_hit(doc.code_lines, m,
                                       clip(m.group(0), 70).replace("\n", " "),
                                       self.suggestion))


def _is_identifier_context(text, start, end):
    """True when a match sits in a code identifier rather than prose.

    Skips dialect hits on tokens like `optimizer`, `Color.RED`, `analyse()`, or
    SCREAMING_CASE constants, where the spelling is a fixed API name, not drift.
    """
    word = text[start:end]
    if word.isupper() and len(word) > 1:
        return True
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if before in "_$" or after in "_(":
        return True
    # `obj.method` / `pkg.name` is attribute access; `we optimise.` is a sentence.
    # Requiring an identifier character on the far side of the dot keeps the check
    # from silently skipping every word that ends a sentence.
    if before == "." and start >= 2 and (text[start - 2].isalnum() or text[start - 2] == "_"):
        return True
    if after == "." and end + 1 < len(text) and (text[end + 1].isalnum() or text[end + 1] == "_"):
        return True
    return False


class DialectCheck(Check):
    """Spelling drift against the chosen dialect, in one pass over the text.

    Runs only when a dialect was requested. Sixty separate `\\bword\\b` scans
    became one alternation for the same reason the phrase lists did: the cost is
    a full pass per pattern, and a long document pays it once per word in the map.
    """

    category = "dialect"

    def run(self, doc, ctx):
        if not ctx.dialect:
            return
        dmap = ctx.patterns.get("dialect", {})
        dialect_map = dmap.get(ctx.dialect, {}) if isinstance(dmap, dict) else {}
        if not isinstance(dialect_map, dict):
            return
        words = [w for w in dialect_map if isinstance(w, str) and w]
        if not words:
            return
        text = doc.code_stripped
        lower = {w.lower(): dialect_map[w] for w in words}
        for rx in compile_phrase_matchers(words):
            for m in rx.finditer(text):
                if _is_identifier_context(text, m.start(), m.end()):
                    continue
                right = lower.get(norm_phrase(m.group(0)))
                sug = ("use '%s' for consistent dialect" % right
                       if isinstance(right, str) else "spelling drift")
                ctx.emit(self.span_hit(doc.code_lines, m, m.group(0), sug))


# The phrase lists, in the order they run. Order matters where two lists can
# match the same span: the first to claim it keeps it.
PHRASE_LIST_CHECKS = (
    PhraseListCheck("filler"),
    PhraseListCheck("soft_filler"),
    PhraseListCheck("jargon"),
    PhraseListCheck("transitions", "overused_transitions"),
    PhraseListCheck("meta_commentary"),
    PhraseListCheck("chatbot_scaffold"),
    PhraseListCheck("sycophancy"),
    PhraseListCheck("aidiolect"),
    PhraseListCheck("cliche_metaphor"),
    PhraseListCheck("internet_tells"),
    PhraseListCheck("significance_inflation"),
    PhraseListCheck("hedging"),
    PhraseListCheck("puffery"),
    PhraseListCheck("vague_attribution", cite_guard=True),
    PhraseListCheck("redundancy", skip_quoted=True),
    PhraseListCheck("cowardly_passive"),
    PhraseListCheck("self_identifying"),
    PhraseListCheck("narrator_distance"),
    PhraseListCheck("vague_declarative"),
)

PATTERN_LIST_CHECKS = (
    PatternListCheck("antithesis", "antithesis_patterns",
                     "drop the not-X/it's-Y framing; state it plainly",
                     honor_protected=False),
    PatternListCheck("false_agency", "false_agency_patterns",
                     "name the human actor (or use 'you'); don't invent one"),
    PatternListCheck("negative_listing", "negative_listing_patterns",
                     "state the final answer; cut the list of what it isn't"),
    PatternListCheck("dramatic_fragmentation", "dramatic_fragmentation_patterns",
                     "use complete sentences; trust the content over the staccato"),
)

__all__ = [
    "CITATION_NEAR_RE",
    "PhraseListCheck",
    "PatternListCheck",
    "DialectCheck",
    "PHRASE_LIST_CHECKS",
    "PATTERN_LIST_CHECKS",
]
