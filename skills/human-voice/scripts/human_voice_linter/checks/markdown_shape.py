"""markdown_shape — markdown scaffolding: headings, bullets, bold, rules, emoji.

These run on the CODE-STRIPPED text, not the raw source. A `# comment` in a fenced
bash block is not a heading and `- **Flag**: ...` in a quoted markdown sample is
not a bold bullet; counting them flagged READMEs and style guides for showing the
anti-pattern they warn against. strip_code keeps line geometry, so reported line
numbers still line up with the file.
"""
from __future__ import annotations

import re
from collections import Counter

from ..core.check import MAX_INSTANCE_HITS, Check
from ..text.markdown import EMOJI_RE, HEADING_LINE_RE, LIST_MARKER_RE, SECTION_RULE_MULTILINE_RE

BOLD_BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+(?:\*\*[^*\n]+\*\*|__[^_\n]+__)[ \t]*:?",
                            re.MULTILINE)
BULLET_RE = re.compile(r"^[ \t]*[-*+][ \t]+\S", re.MULTILINE)


class BoldBulletsCheck(Check):
    category = "bold_bullets"

    def run(self, doc, ctx):
        text = doc.code_stripped
        bullets = BULLET_RE.findall(text)
        bold = list(BOLD_BULLET_RE.finditer(text))
        ctx.report["bullets"] = len(bullets)
        ctx.report["bold_lead_bullets"] = len(bold)
        if bullets and (len(bold) / len(bullets)) >= ctx.threshold("bold_bullet_ratio") and len(bold) >= 3:
            for m in bold[:MAX_INSTANCE_HITS]:
                ctx.emit(self.span_hit(doc.code_lines, m, m.group(0).strip(),
                                       "convert some to prose; drop ornamental bold"))


class FormattingCheck(Check):
    """Decorative emoji, and horizontal rules between every section."""

    category = "formatting"

    def run(self, doc, ctx):
        text = doc.code_stripped
        max_rules = ctx.threshold.integer("section_rule_max")
        emojis = EMOJI_RE.findall(text)
        ctx.report["emoji"] = len(emojis)
        if emojis:
            m = EMOJI_RE.search(text)
            ctx.emit(self.span_hit(doc.code_lines, m, "emoji (%d)" % len(emojis),
                                   "remove decorative emoji"))
        # A run of dashes directly under a non-blank line is a setext heading
        # underline, not a rule between sections. Counting those flagged every
        # docstring and every doc that underlines its headings.
        rules = []
        for m in SECTION_RULE_MULTILINE_RE.finditer(text):
            prev_end = text.rfind("\n", 0, m.start())
            prev_start = text.rfind("\n", 0, prev_end) + 1 if prev_end > 0 else 0
            if prev_end > 0 and text[prev_start:prev_end].strip():
                continue
            rules.append(m)
        ctx.report["section_rules"] = len(rules)
        if len(rules) > max_rules:
            for m in rules[max_rules:max_rules + MAX_INSTANCE_HITS]:
                ctx.emit(self.span_hit(doc.code_lines, m, "horizontal rule",
                                       "drop rules between every section"))


HEADING_RE = re.compile(r"^[ \t]*(#{1,6})[ \t]+(.+?)[ \t]*#*$", re.MULTILINE)


class HeadingCaseCheck(Check):
    """Headings that mix title case and sentence case."""

    category = "heading_case"

    def run(self, doc, ctx):
        styles = []
        spans = []
        for m in HEADING_RE.finditer(doc.code_stripped):
            title = m.group(2).strip()
            words = [w for w in title.split() if any(ch.isalpha() for ch in w)]
            if len(words) < 2:
                continue
            caps = sum(1 for w in words if w[0].isupper())
            style = "title" if caps >= max(2, len(words) - 1) else "sentence"
            styles.append(style)
            spans.append((m.start(), title))
        if len(set(styles)) > 1:
            majority = Counter(styles).most_common(1)[0][0]
            for (start, title), style in zip(spans, styles):
                if style != majority:
                    ctx.emit(self.hit(doc.code_lines.line_of(start), title,
                                      "match the dominant heading case (%s)" % majority))


_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$", re.M)
_LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


class HeadingStructureCheck(Check):
    """Markdown scaffolding a person does not produce by hand.

    Four distinct faults, all of them artifacts of a model emitting an outline
    rather than a writer building a document: heading levels that skip a rung
    (## straight to ####), more than one H1 in a single file, a heading whose
    entire body is the next heading, and a heading that runs straight into a
    bullet list with no sentence in between. Each is individually minor; the
    reason to score them is that a document with several has been assembled, not
    written. Catalogued by Wikipedia's AI-Cleanup project as markup signs.
    """

    category = "heading_structure"

    def run(self, doc, ctx):
        text = doc.code_stripped
        lines_map = doc.code_lines
        headings = [(m.start(), len(m.group(1)), m.group(2)) for m in _ATX_HEADING_RE.finditer(text)]
        ctx.report["heading_count"] = len(headings)
        if len(headings) < 2:
            return
        h1s = [h for h in headings if h[1] == 1]
        if len(h1s) > 1:
            ctx.emit(self.hit(lines_map.line_of(h1s[1][0]),
                              "%d level-1 headings in one document" % len(h1s),
                              "one H1 per document; demote the rest"))
        prev_level = headings[0][1]
        for start, level, title in headings[1:]:
            if level > prev_level + 1:
                ctx.emit(self.hit(lines_map.line_of(start),
                                  "heading level jumps %d -> %d at %r" % (prev_level, level, title[:40]),
                                  "use the next level down; do not skip a rung"))
            prev_level = level
        lines = text.split("\n")
        heading_lines = {}
        for m in _ATX_HEADING_RE.finditer(text):
            heading_lines[text.count("\n", 0, m.start())] = m.group(2)
        for idx, title in sorted(heading_lines.items()):
            nxt = None
            for j in range(idx + 1, min(idx + 4, len(lines))):
                if lines[j].strip():
                    nxt = (j, lines[j])
                    break
            if not nxt:
                continue
            j, body = nxt
            if j in heading_lines:
                ctx.emit(self.hit(idx + 1, "heading %r contains only another heading" % title[:40],
                                  "merge the two, or write the section"))
            elif _LIST_LINE_RE.match(body):
                ctx.emit(self.hit(idx + 1, "heading %r runs straight into a list" % title[:40],
                                  "put a sentence between the heading and the list"))


# ---------------------------------------------------------------------------
# The strongest published evidence about what trained detectors respond to is
# that they track *post-training* artifacts rather than "machine-ness": base
# models, which never went through instruction tuning, are classified human at
# >96%, while their instruction-tuned siblings are caught. The artifacts named
# are response length conventions, markdown formatting preference (headings,
# lists, bolded runs), and assistant-style structural conventions. Word choice
# is downstream of all of that. See references/what-detectors-see.md.
# ---------------------------------------------------------------------------

BOLD_SPAN_RE = re.compile(r"\*\*[^*\n]{1,80}\*\*|__[^_\n]{1,80}__")

# Section titles that mark an answer wrapping itself up for the reader. A human
# report has a conclusion; an assistant response almost always does.
SUMMARY_HEADING_RE = re.compile(
    r"^[ \t]*#{1,6}[ \t]+(?:in\s+)?(?:conclusion|summary|in\s+summary|takeaways?|"
    r"key\s+takeaways?|final\s+thoughts?|tl;?dr|wrapping\s+up|closing\s+thoughts?|"
    r"the\s+bottom\s+line|next\s+steps)\b",
    re.IGNORECASE | re.MULTILINE)


class AssistantShapeCheck(Check):
    """Markdown scaffolding density: does this read as a written document or as a
    chat answer? Density-based, so a README's headings are fine and a heading
    every sixty words is not.

    The content-line denominator comes from the SOURCE, so a code-heavy page is
    not judged as if the code were not there.
    """

    category = "assistant_shape"
    min_words = 120  # too short for a density to mean anything

    def run(self, doc, ctx):
        text = doc.code_stripped
        word_count = doc.word_count
        heading_lines = [ln for ln in text.splitlines() if HEADING_LINE_RE.match(ln)]
        content_lines = [ln for ln in doc.source.splitlines() if ln.strip()]
        bullet_lines = [ln for ln in text.splitlines() if LIST_MARKER_RE.match(ln)]
        bold_spans = BOLD_SPAN_RE.findall(text)

        h_per_1k = (len(heading_lines) / word_count * 1000.0) if word_count else 0.0
        b_ratio = (len(bullet_lines) / len(content_lines)) if content_lines else 0.0
        bold_1k = (len(bold_spans) / word_count * 1000.0) if word_count else 0.0
        ctx.report["headings"] = len(heading_lines)
        ctx.report["headings_per_1k"] = round(h_per_1k, 1)
        ctx.report["bullet_line_ratio"] = round(b_ratio, 2)
        ctx.report["bold_spans"] = len(bold_spans)
        ctx.report["bold_spans_per_1k"] = round(bold_1k, 1)

        if word_count < self.min_words:
            return
        if h_per_1k > ctx.threshold("headings_per_1k_words") and len(heading_lines) >= 3:
            ctx.emit(self.hit(0, "a heading every %d words (%d headings / %d words)"
                              % (int(word_count / max(1, len(heading_lines))),
                                 len(heading_lines), word_count),
                              "let paragraphs carry the structure; keep headings for real sections"))
        if b_ratio > ctx.threshold("bullet_line_ratio") and len(bullet_lines) >= 5:
            ctx.emit(self.hit(0, "%.0f%% of content lines are list items" % (b_ratio * 100),
                              "turn the bulleted answer back into paragraphs"))
        if bold_1k > ctx.threshold("bold_spans_per_1k_words") and len(bold_spans) >= 4:
            ctx.emit(self.hit(0, "%d bold spans in %d words" % (len(bold_spans), word_count),
                              "drop emphasis that is decorating rather than distinguishing"))
        # The tell is a document that WRAPS ITSELF UP, so the recap heading has to be
        # the last one. A "Next steps" section in the middle of a project doc is a
        # section, not a chat answer signing off, and flagging it was wrong.
        summary = None
        for m in SUMMARY_HEADING_RE.finditer(text):
            summary = m
        if summary and len(heading_lines) >= 2:
            later = [ln for ln in text[summary.end():].splitlines()
                     if HEADING_LINE_RE.match(ln)]
            if not later:
                ctx.emit(self.hit(0, "closes with a %r section"
                                  % summary.group(0).strip().lstrip("# ").strip(),
                                  "end on the last real point; drop the recap section"))


__all__ = [
    "BoldBulletsCheck",
    "FormattingCheck",
    "HeadingCaseCheck",
    "HeadingStructureCheck",
    "AssistantShapeCheck",
]
