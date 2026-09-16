# Usage

[Docs home](README.md) · [Getting started](getting-started.md) · [Install](install.md) · **Usage** · [Examples](examples.md) · [Evidence](evidence.md) · [Comparison](comparison.md)

- [The skill](#the-skill): modes, registers, depth, and when rules bend
- [The linter](#the-linter): commands, flags, autofix
- [The detector gate](#the-detector-gate)
- [Configuration](#configuration)
- [How the score works](#how-the-score-works)
- [When it gets something wrong](#when-it-gets-something-wrong)

## The skill

```
/human-voice <file-path | pasted-text> [fix|generate] [register: <name>]
```

Arguments go in any order. Leave them out and the skill works them out from the
text and from what you asked for.

### Modes

| Mode | When | What happens |
|---|---|---|
| `fix` (default) | you hand it a file or pasted prose | rewrites the draft and keeps every invariant: numbers, code, links, citations, defined terms |
| `generate` | you hand it a brief, or say "write" or "draft" | writes new copy that reads human from the first pass, then runs the same critique loop on it |

A file gets edited in place only once the rewrite passes, and only if git tracks
the file or a `.bak` copy exists. Pasted text comes back as text.

### Registers

"Human" depends on the genre. The skill picks the register, fixes a universal
core of tells in every one of them, and flexes the rest.

| Register | Voice | Allowed here |
|---|---|---|
| `technical` (strictest) | professional, direct, present tense | nothing extra |
| `business` | professional with a little warmth | a brief courteous opener or closer |
| `marketing` | conversational, talks to "you" | "you" and "we", contractions, light enthusiasm |
| `academic` | formal, measured | measured hedging, "we", passive voice, citations |
| `casual` | personal | contractions, "I", rhetorical questions, fragments |
| `creative` | a narrator | em-dashes, fragments, any vocabulary that serves the voice |
| `email` | brief and direct, the ask up front | a one-line greeting and sign-off |
| `release_notes` | terse, user-facing, past tense | fragments, bulleted changes |
| `ux_microcopy` | minimal and plain | dropped articles, extreme brevity |
| `tutorial` | instructional, second person | imperatives, numbered steps |

The universal core holds everywhere: vacuity, fabrication, the rule-of-three
reflex, bold-bullet listicles, puffery, vague attribution, flat rhythm,
terminology drift, restatement and "not X, it's Y". A register never switches a
check off. Where a genre legitimately runs hot on a construction, its threshold
widens instead. In the linter, `--register auto` infers the genre and prints why.
On the labeled corpus it's right 82% of the time, and when unsure it falls back
to `technical`.

### Depth

The skill sizes its effort to what a mistake would cost.

| Depth | For | Runs |
|---|---|---|
| quick | a commit message, a Slack reply, a code comment | strip the assistant shape, cut empty sentences; no audit |
| standard | an email, an internal doc, a README section | the full rewrite procedure, one critique pass, the linter, a trimmed audit |
| full | anything published, graded or customer-facing | author-material intake with questions to you, the scored critique, the detector gate, the complete audit |

Depth changes how much runs, never how strictly. The no-fabrication rule and the
invariant guard hold at every level.

### It stays on

Once invoked, the skill shapes everything written for the rest of the session,
starting with the reply that hands back the rewrite.
That's deliberate. A humanized document usually loses its voice to the one
drafted an hour later in the default style. Say "stop human-voice" or "normal
voice" to turn it off. The honesty rules stay on regardless.

### When a rule fights the task

The task wins. An API reference keeps its headings, a safety notice keeps "may",
and a style guide your repo enforces beats the skill. The skill relaxes the one
rule in the way, names it in the audit and holds the rest. Details: "When a rule
fights the task" in [SKILL.md](../skills/human-voice/SKILL.md).

## The linter

`detect_ai_prose.py` is the deterministic floor: 68 checks and no dependencies.
It needs no model and no network.

```bash
L=skills/human-voice/scripts/detect_ai_prose.py
python3 $L draft.md                              # full report
python3 $L --register marketing draft.md         # score for a genre
python3 $L --register auto --recursive docs/     # infer each file's genre
python3 $L --baseline draft.md rewrite.md        # score movement between two files
python3 $L --fail-over 5 --quiet docs/*.md       # CI gate: exit 1 if any file scores over 5
printf '%s' "$TEXT" | python3 $L -               # stdin
```

| Flag | Does |
|---|---|
| `--register NAME\|auto` | genre profile (default `technical`, or `.humanvoicerc`) |
| `--dialect american\|british` | also flag spelling that drifts between dialects |
| `--fail-over SCORE` | exit 1 when any file scores above `SCORE` |
| `--baseline FILE` | compare the input against `FILE` |
| `--json`, `--sarif` | machine-readable output; SARIF shows up as code-scanning annotations |
| `--quiet`, `--explain` | one line per file, or every hit with no per-category cap |
| `--enable`, `--disable` | keep or drop comma-separated categories |
| `--threshold KEY=VALUE` | override one threshold for this run |
| `--recursive` | walk subdirectories |
| `--no-config` | ignore `.humanvoicerc` |
| `--fix`, `--fix-dry-run` | apply, or preview, the deterministic autofix |

### Autofix

`--fix` makes only the edits that need no judgment: dash normalization, removing
decorative emoji and one-to-one filler swaps. The dash rewrite varies the mark. A
paired aside becomes parentheses, an enumeration takes a colon, everything else
takes a comma, because a document with one substitute everywhere trades the
em-dash signature for a new uniform one. It skips dashes and emoji in `creative`,
keeps emoji in `casual`, and never touches code, numbers, links or table cells.
The judgment work stays with the rewrite: cutting empty sentences, unstaging
clefts, committing to a position.

## The detector gate

The linter is a floor. A document can score 0 and still get flagged by a trained
classifier. Only a real detector can answer that question, so the skill can ask
one:

```bash
export GPTZERO_API_KEY=...   # or ORIGINALITY_API_KEY, SAPLING_API_KEY, WINSTON_API_KEY
python3 skills/human-voice/scripts/verify_detector.py --before draft.md rewrite.md
python3 skills/human-voice/scripts/verify_detector.py --max-p-ai 0.05 --json rewrite.md
```

Exit 0 means clear, 1 means still flagged, and 2 means no detector is configured.
Exit 2 is not a pass. While the gate returns 1 the skill keeps rewriting, and it
stops after two passes that can't move it without damaging the prose. Until you
set a key, nothing leaves your machine. The request shapes come from each vendor's docs
and haven't been exercised against the live APIs from this repo, so a stale one
fails with an error naming the missing field. See [Evidence](evidence.md) for
how to calibrate a detector before trusting it.

## Configuration

A `.humanvoicerc` (JSON) at the root of your repo sets project defaults. The
linter finds it by walking up from the file being scored.

```json
{
  "register": "technical",
  "dialect": "american",
  "protected_terms": ["seamless handoff", "Robust Mode"],
  "context_exceptions": ["key takeaways"],
  "thresholds": { "burstiness_cov_floor": 0.35 },
  "category_weights": { "em_dash": 0.5 }
}
```

`protected_terms` are product names and required jargon that must never be
flagged. Every threshold and category weight, with its default, lives in
[`ai_prose_patterns.json`](../skills/human-voice/scripts/ai_prose_patterns.json).
If you override `score_bands`, give all three bands (`clean`, `watch` and
`strong-tell`). A partial set relabels scores.

Silence one finding in place with an HTML comment:

```markdown
We ship a seamless handoff between regions.  <!-- human-voice: ignore filler -->

<!-- human-voice: ignore-start puffery -->
A quoted customer testimonial the author can't edit.
<!-- human-voice: ignore-end -->
```

A directive on its own line covers the next line. A trailing directive covers
its own line. Document-level findings, like flat rhythm across the whole text,
have no single line to attach to. Use `--disable` for those.

On Windows, use `py` in place of `python3`, and pipe with PowerShell:
`$TEXT | py skills/human-voice/scripts/detect_ai_prose.py -`.

## How the score works

The score is **floor points**, with a band attached: below 5 reads **clean**, 5
to 15 is **watch**, and 15+ is a **strong-tell**. Lower is better.

Two kinds of finding cannot share one denominator, and conflating them was a real
bug here until v0.5. An *instance* tell (a filler word, an em-dash) recurs with
length, so it belongs in a per-1000-word density. A *document* tell (flat
burstiness, even paragraphs, an assistant heading shape) fires at most once no
matter how long the text is, so dividing it by word count made the same defect
worth 13 points in a 150-word note and 1 point in a 2000-word report. Document
findings now contribute fixed points and only instance findings are normalized by
length, and each category's density contribution is capped so one runaway check
can't swamp the rest. The regression test asserts a 10× length change moves the
score less than 40%.

Read the metrics lines, not just the number:

```text
rhythm:  CoV 0.30 (want >=0.40)   short<=8w 0.0 (want >=0.12)   mid-band 0.64 (want <=0.72)   mean 21.5 w
shape:   headings/1k 4.2   bullet-line ratio 0.0   bold/1k 0.0   em-dash/1k 0.0
syntax:  clefts 5   ',VERBing' tails 3   copula/1k 67.5   passive/1k 8.4
lexicon: TTR 0.79   Yule's K 177.7
detail:  0.84 specifics/100w (1 numbers, 1 proper nouns)
```

The `syntax:` line is the v0.6 addition and it is the one most rewrites need.
Every construction it counts is ordinary English used well by human writers, so
each check fires on the *stacking* rather than on a single instance. The document
above is fluent, has no filler and no em-dashes, and is machine-written: five
clefts and three resultative tails in 237 words is the giveaway.

The `structure:` line reads the document as a plan. On anything with headings it
reports the section count, how unevenly words are shared out, how much sits in
overview and summary sections, how many points are made twice, and how much
checkable detail each section carries. The three checks behind it
(`restatement`, `section_balance`, `depth_drift`) are covered in
[`references/content-architecture.md`](../skills/human-voice/references/content-architecture.md).

Those are the numbers the rewrite targets. Treat the score as a floor, not a
judgment: it catches cheap, regex-able tells but can't see vacuity, weak stance,
or fabrication. The real test is a skeptical human read.

Every register has a before/after pair with live scores in [Examples](examples.md).
Each "after" scores `clean`. Run the linter on both halves to confirm.

The linter is measured, not asserted: `eval/` holds a labeled corpus and
`run_eval.py`, and [`eval/EVAL.md`](../eval/EVAL.md) reports precision/recall, the
false-positive rate on human-written text, and the number that actually matters:
how it does against prose a *current* model writes rather than 2023-era
caricature.

One of those negative sets is not authored here at all. `eval/human_baseline.py`
scores the docstrings of 26 Python standard-library modules, written by hundreds
of people who never saw this repository and shipped with every interpreter, so it
runs offline with no corpus file. Pointing the linter at it found five real
false-positive bugs. The median score on that set went from 35.0 to 8.0, and the
worst module from 43.5 to 15.3.

## When it gets something wrong

If it flags text a person wrote, remember that the linter is a floor built from
patterns, and it over-flags sometimes. Lower a threshold, add a `protected_terms`
or `context_exceptions` entry, or open a
[false-positive issue](../.github/ISSUE_TEMPLATE/false-positive.md). Those reports
feed the corpus and the false-positive measurement.

If it misses something that reads machine-made, the
[missed-tell](../.github/ISSUE_TEMPLATE/missed-tell.md) template is the way to
send it.

Other languages aren't supported yet. The word lists and the dialect map are
English only, and `--lang` accepts only `en`.
