"""prompt — compile the skill into a system prompt any model can follow.

SKILL.md is written for an agent that can open files and run the linter. A bare
chat model can do neither, so three things change on the way through, and
nothing else does:

1. The frontmatter goes (it is agent metadata, not instructions).
2. The reference files the procedure tells the agent to "load" are appended, so
   the model has them rather than a path it cannot open.
3. A short adapter says who runs the tools now: in `api` mode the caller runs the
   linter and the invariant check and feeds the reports back; in `chat` mode (a
   system prompt pasted into ChatGPT, Gemini, a Claude project, anything) nobody
   does, and the model falls back to the no-tool checklist SKILL.md already has.

The rules themselves are never paraphrased or summarized. A shortened copy of the
skill is a different skill, and it would drift from the one the eval measures.
"""
from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(HERE))

# What the rewrite procedure itself loads, in the order it needs them.
CORE_REFERENCES = ("ai-tells.md", "structural-craft.md", "over-correction.md",
                   "discourse-and-structure.md", "anti-jargon.md", "cited-vs-matched.md")
# Background: evidence and survey. Useful to a human; costs ~8k tokens a call.
EXTRA_REFERENCES = ("what-detectors-see.md", "competitive-landscape.md")
REFERENCE_SETS = {"none": (), "core": CORE_REFERENCES,
                  "all": CORE_REFERENCES + EXTRA_REFERENCES}

REWRITE_OPEN, REWRITE_CLOSE = "<rewrite>", "</rewrite>"
AUDIT_OPEN, AUDIT_CLOSE = "<audit>", "</audit>"

API_ADAPTER = """\
# Running as a model behind an API

You are running the human-voice skill below through an API call, not inside an
agent. The instructions below were written for an agent with tools. Here is what
changes, and it is the only thing that changes:

- You cannot open files or run commands. Where the skill says to run
  `scripts/detect_ai_prose.py`, the caller has already run it and pasted the
  report into the message. Where it says to run `scripts/verify_detector.py`, the
  caller runs that too, if a detector is configured, and tells you the result.
  Where it says to load `references/<name>.md`, that file is appended at the end
  of this prompt under a heading with its name, or it was left out to save
  tokens, in which case work from the summary in the skill body.
- The caller also runs a deterministic invariant check (numbers, code, links,
  citations) on your rewrite and sends back anything lost or introduced. Restore
  what was lost verbatim. Anything introduced that the source does not support
  gets removed or marked `[SOURCE NEEDED]`.
- You cannot ask the user questions, so the author-material intake draws only on
  the draft and any context supplied in the message. Mark every gap
  `[SOURCE NEEDED]`; never fill one.
- You do not write files. The caller applies the rewrite.
- `$ARGUMENTS` does not exist. The mode, register, depth and any context arrive
  as labeled fields in the user message.

Return exactly two tagged sections and nothing outside them. No preamble, no
sign-off, no code fence around the whole answer:

<rewrite>
the complete rewritten (or generated) text, ready to ship, in the source's own
format (Markdown stays Markdown, plain text stays plain)
</rewrite>
<audit>
the Humanization Audit from the Output templates section, at the requested depth.
Use the linter numbers the caller supplied for "before"; leave "after" to the
caller's next report if you have not been given one.
</audit>

When the caller sends a follow-up report on your rewrite, return the full
revised text again in the same two sections, not a diff.
"""

CHAT_ADAPTER = """\
# Running as a system prompt

These are the instructions for the human-voice skill, loaded as a system prompt
in a chat product rather than inside a coding agent. What that changes:

- You probably cannot run `scripts/detect_ai_prose.py`. If you have a code tool
  and the user has attached the script, run it. Otherwise use the **no-tool
  checklist** in the Workflow section, and say in the audit that the linter did
  not run. Never report a linter score you did not compute.
- The detector gate did not run unless the user pastes a detector result. Report
  it as "not run".
- Reference files the skill tells you to load are appended at the end of this
  prompt under headings with their names. If one is missing, work from the
  summary in the skill body.
- Treat whatever the user sends as `$ARGUMENTS`: a draft to fix, a brief to
  generate from, or a message that names the mode and register.
- File operations do not apply. Print the rewrite and the audit.

Everything else holds exactly as written, including persistence: once the user
has asked for human-voice, every reply in the conversation follows it until they
turn it off.
"""

_FRONTMATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)


def read_skill(skill_dir=SKILL_DIR):
    with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as fh:
        return _FRONTMATTER.sub("", fh.read(), count=1).strip()


def read_references(names, skill_dir=SKILL_DIR):
    out = []
    for name in names:
        path = os.path.join(skill_dir, "references", name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                out.append((name, fh.read().strip()))
    return out


def build_system_prompt(target="api", references="core", skill_dir=SKILL_DIR):
    """The whole skill as one string. `target` is "api" or "chat"."""
    if references not in REFERENCE_SETS:
        raise ValueError("references must be one of %s" % ", ".join(REFERENCE_SETS))
    adapter = API_ADAPTER if target == "api" else CHAT_ADAPTER
    parts = [adapter.strip(), "---", read_skill(skill_dir)]
    for name, body in read_references(REFERENCE_SETS[references], skill_dir):
        parts += ["---", "# Reference: references/%s\n\n%s" % (name, body)]
    return "\n\n".join(parts) + "\n"


def build_task(text, mode="fix", register="auto", depth="standard", context=None,
               lint_report=None, inferred=None, source_name="pasted text"):
    """The first user message of a rewrite run."""
    fields = ["mode: %s" % mode,
              "register: %s%s" % (register, (" (inferred by the linter: %s)" % inferred)
                                  if inferred else ""),
              "depth: %s" % depth,
              "source: %s" % source_name]
    msg = ["# Task", "\n".join(fields)]
    if context:
        msg += ["# Author context (real material you may use; nothing outside it or "
                "the draft may be stated as fact)", context.strip()]
    if lint_report:
        msg += ["# Baseline linter report (scripts/detect_ai_prose.py, run by the caller)",
                "```text\n%s\n```" % lint_report.strip()]
    label = "Brief" if mode == "generate" else "Draft"
    msg += ["# %s" % label, "<source>\n%s\n</source>" % text]
    return "\n\n".join(msg)


def build_feedback(pass_no, max_passes, lint_report, invariant_lines, detector_line=None,
                   truncated=False, format_error=None):
    """The follow-up message after a pass that did not meet the targets."""
    msg = ["# Report on pass %d of %d" % (pass_no, max_passes)]
    if format_error:
        msg.append("FORMAT: %s Return the full text inside <rewrite></rewrite> and the "
                   "audit inside <audit></audit>." % format_error)
    if truncated:
        msg.append("TRUNCATED: your last response hit the output limit. Return the "
                   "complete text; shorten the audit if you must, never the rewrite.")
    if invariant_lines:
        msg.append("Invariant check FAILED. This outranks every style target:\n- "
                   + "\n- ".join(invariant_lines))
    if lint_report:
        msg.append("Linter on your rewrite:\n```text\n%s\n```" % lint_report.strip())
    if detector_line:
        msg.append("Detector gate: %s" % detector_line)
    msg.append("Revise in the skill's priority order (shape, rhythm, substance, "
               "diction) and return the full text again in the same two sections. "
               "Do not grind: if a target cannot move without making the prose "
               "worse, leave it and name it under Residual risk.")
    return "\n\n".join(msg)


_TAG: dict = {}


def _section(text, open_tag, close_tag):
    key = (open_tag, close_tag)
    if key not in _TAG:
        _TAG[key] = re.compile(re.escape(open_tag) + r"\s*\n?(.*?)\n?\s*" + re.escape(close_tag), re.S)
    found = _TAG[key].findall(text)
    return found[-1] if found else None


_OUTER_FENCE = re.compile(r"\A```[a-zA-Z]*\n(.*)\n```\s*\Z", re.S)


def parse_response(text, source=""):
    """(rewrite, audit, error). `error` is None when the contract was honored.

    Models differ in how faithfully they follow an output format, so the parse is
    lenient where leniency is safe: an unclosed final tag is accepted, and a
    fence wrapped around the whole rewrite is removed unless the source itself
    was a single fenced block.
    """
    rewrite = _section(text, REWRITE_OPEN, REWRITE_CLOSE)
    if rewrite is None and REWRITE_OPEN in text:
        tail = text.rsplit(REWRITE_OPEN, 1)[1]
        rewrite = tail.split(AUDIT_OPEN, 1)[0].strip()
    audit = _section(text, AUDIT_OPEN, AUDIT_CLOSE)
    if audit is None and AUDIT_OPEN in text:
        audit = text.rsplit(AUDIT_OPEN, 1)[1].strip()
    if rewrite is None:
        return None, audit, "no <rewrite> section in the response."
    m = _OUTER_FENCE.match(rewrite.strip())
    if m and not _OUTER_FENCE.match(source.strip()):
        rewrite = m.group(1)
    if not rewrite.strip():
        return None, audit, "the <rewrite> section was empty."
    return rewrite.strip("\n"), (audit or "").strip(), None


__all__ = ["CORE_REFERENCES", "EXTRA_REFERENCES", "REFERENCE_SETS", "SKILL_DIR",
           "read_skill", "build_system_prompt", "build_task", "build_feedback",
           "parse_response"]
