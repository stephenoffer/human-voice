"""artifacts — residue a model left in its own output.

Every string here is a citation marker, tool-call wrapper, or unfilled template
slot that appears only because text came out of a chat product and went into a
document unread. Unlike every other check in the linter, these are not stylistic
tendencies with a human range -- no writer types "oaicite" -- so one instance is
a finding rather than a whisper, and the category carries the weight to say so.
Catalogued by Wikipedia's WikiProject AI Cleanup across ChatGPT, Gemini, Grok,
DeepSeek and Perplexity output; see references/competitive-landscape.md.
"""
from __future__ import annotations

import re

from ..core.check import MAX_INSTANCE_HITS, Check

LLM_ARTIFACT_RES = (
    (re.compile(r"\b(?:oaicite|contentReference|attributableIndex|citeturn\w*)\b"),
     "ChatGPT citation residue: delete it"),
    (re.compile(r"\bturn\d+(?:search|news|view|image)\d+\b"),
     "ChatGPT tool-call residue: delete it"),
    (re.compile(r"\[cite:\s*\d+\s*\]|\[span_\d+\]\(start_span\)|\(end_span\)"),
     "Gemini citation residue: delete it"),
    (re.compile(r"\bgrok_(?:card|render_citation_card_json)\b"),
     "Grok render residue: delete it"),
    (re.compile(r"\b(?:ppl-ai-file-upload|attached_file:)"),
     "Perplexity upload residue: delete it"),
    (re.compile(r":::writing\b"),
     "model block marker: delete it"),
    (re.compile(r"utm_source=(?:chatgpt|openai|perplexity)[\w.]*", re.I),
     "tracking parameter added by the chat product: strip it from the URL"),
    (re.compile(r"【[^】]{0,80}】"),
     "lenticular-bracket citation residue: delete it"),
    # Template slots only. A bare "[X]" or "[X, Y]" is mathematical and
    # generic-parameter notation in real technical writing -- the Python stdlib
    # docs in eval/human_baseline.py carry eleven of them -- so the pattern
    # requires a form no equation produces: an explicit verb, a possessive, or a
    # two-word slot name.
    (re.compile(r"\[(?:INSERT[\w ]*|Insert\s+\w+|Your\s+\w+"
                r"|(?:Company|Client|Product|Customer|Recipient|Sender|Full)\s+Name"
                r"|Name\s+of\s+\w+|PLACEHOLDER\w*)[^\]\n]{0,40}\]"),
     "unfilled template placeholder: fill it or cut the sentence"),
)

# Placeholders this skill deliberately emits (anti-hallucination protocol step 5)
# are the author's to resolve, not residue to flag.
_SANCTIONED_PLACEHOLDER = re.compile(
    r"\[(?:SOURCE NEEDED|VERIFY|FIGURE\?|TODO|CITATION NEEDED)\]", re.I)

_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


class LlmArtifactCheck(Check):
    """Flag chat-product residue and unfilled placeholders. Precision check.

    Runs on the code-stripped source rather than the reduced metric prose,
    because two of these live inside a URL (`utm_source=chatgpt.com`) and the
    metric text drops link targets. Backticked spans are skipped by hand instead,
    so a document that *names* these strings -- this repo's own reference pages do
    -- is not flagged for documenting them.
    """

    category = "llm_artifact"

    def run(self, doc, ctx):
        text = doc.code_stripped
        skip = [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(text)]
        for rx, suggestion in LLM_ARTIFACT_RES:
            for m in rx.finditer(text):
                frag = m.group(0)
                if _SANCTIONED_PLACEHOLDER.fullmatch(frag):
                    continue
                if any(a <= m.start() < b for a, b in skip):
                    continue
                ctx.emit(self.span_hit(doc.code_lines, m, frag.strip(), suggestion))
                # A runaway guard on the whole run, not this check alone.
                if len(ctx.hits) > MAX_INSTANCE_HITS * 4:
                    return


__all__ = ["LLM_ARTIFACT_RES", "LlmArtifactCheck"]
