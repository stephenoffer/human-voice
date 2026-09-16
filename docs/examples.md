# Examples

[Docs home](README.md) · [Getting started](getting-started.md) · [Install](install.md) · [Usage](usage.md) · **Examples** · [Evidence](evidence.md) · [Comparison](comparison.md)

Ten drafts and their rewrites, one per genre or failure mode. They ship in
[`skills/human-voice/examples/`](../skills/human-voice/examples/), and the skill
reads the one matching your genre before it starts. So they're also its
calibration set.

Scores are the linter's floor score under each pair's register. Lower is better.
Under 5 is clean; 15 and up is a strong tell. A script rebuilds this table from
the files, and CI fails if it drifts.

<!-- examples-table:start -->
| Pair | Register | Before | After | What it shows |
|---|---|--:|--:|---|
| [Modern AI](../skills/human-voice/examples/modern-ai-before.md) → [after](../skills/human-voice/examples/modern-ai-after.md) · [notes](../skills/human-voice/examples/modern-ai-notes.md) | `technical` | 15.0 | 0.0 | Fluent prose a current model writes, with no filler at all |
| [Syntax signature](../skills/human-voice/examples/syntax-signature-before.md) → [after](../skills/human-voice/examples/syntax-signature-after.md) · [notes](../skills/human-voice/examples/syntax-signature-notes.md) | `technical` | 49.3 | 0.0 | No filler, no em-dashes; machine-made through its grammar |
| [Design doc](../skills/human-voice/examples/architecture-before.md) → [after](../skills/human-voice/examples/architecture-after.md) · [notes](../skills/human-voice/examples/architecture-notes.md) | `technical` | 48.9 | 0.0 | A design doc whose plan gives it away |
| [Technical report](../skills/human-voice/examples/before.md) → [after](../skills/human-voice/examples/after.md) · [notes](../skills/human-voice/examples/annotated-walkthrough.md) | `technical` | 169.7 | 0.0 | 2023-era slop in a technical report |
| [Landing page](../skills/human-voice/examples/marketing-before.md) → [after](../skills/human-voice/examples/marketing-after.md) | `marketing` | 107.7 | 0.0 | Puffery, hype and fake attribution on a landing page |
| [Email](../skills/human-voice/examples/email-before.md) → [after](../skills/human-voice/examples/email-after.md) | `email` | 66.0 | 0.0 | Jargon, padding and a buried ask |
| [Academic](../skills/human-voice/examples/academic-before.md) → [after](../skills/human-voice/examples/academic-after.md) | `academic` | 62.0 | 0.0 | Vague attribution, stacked hedges, no commitment |
| [Blog post](../skills/human-voice/examples/casual-before.md) → [after](../skills/human-voice/examples/casual-after.md) | `casual` | 55.0 | 0.0 | Listicle padding and meta-commentary in a blog post |
| [Cliché metaphors](../skills/human-voice/examples/cliche-metaphor-before.md) → [after](../skills/human-voice/examples/cliche-metaphor-after.md) | `business` | 18.3 | 0.0 | Metaphor frames doing the work of concrete language |
| [Over-corrected](../skills/human-voice/examples/over-corrected-before.md) → [after](../skills/human-voice/examples/over-corrected-after.md) | `technical` | 22.3 | 0.0 | The anti-AI costume: forced lowercase, slang, fragments |
<!-- examples-table:end -->

Read Modern AI first. Its "before" is what a current model hands you today: no
hedging, no filler, not one em-dash. It still reads generated. The notes file
walks the rhythm numbers sentence by sentence.

Syntax signature is the harder version of the lesson. Nine clefts and three
trailing ", making it…" clauses carry the whole machine signature. Nothing else
does.

## Three cases that aren't rewrites

The most useful behavior is sometimes a refusal.

| Case | What it shows |
|---|---|
| [Generate from a brief](../skills/human-voice/examples/generate-example.md) | Drafting new copy that reads human from the first pass, with every stated fact traced to the brief |
| [Refusing to fabricate](../skills/human-voice/examples/refusal-to-fabricate.md) | A flat sentence that wants a number gets `[SOURCE NEEDED]` instead of a vivid invention |
| [Restraint](../skills/human-voice/examples/restraint-case.md) | When a "tell" is correct and the edit is to leave it alone |

Every score on this page can be checked by hand. For the email pair:

```bash
python3 skills/human-voice/scripts/detect_ai_prose.py --register email \
  --baseline skills/human-voice/examples/email-before.md \
  skills/human-voice/examples/email-after.md
```

`--baseline` prints the score movement between the two files. Drop it to see the
full report for one file: every tell with its line, its category and a suggested
fix.

Seen a draft the skill gets wrong? The
[missed-tell](../.github/ISSUE_TEMPLATE/missed-tell.md) and
[false-positive](../.github/ISSUE_TEMPLATE/false-positive.md) templates feed new
pairs and corpus files.
