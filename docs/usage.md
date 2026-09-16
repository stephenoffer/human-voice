# Using human-voice

[README](../README.md) · [Install](install.md) · [Usage](usage.md) · [Why it works](evidence.md) · [Comparison](comparison.md)

```
/human-voice <file-path | pasted-text> [fix|generate] [register: technical|business|marketing|academic|casual|creative]
```

- `fix` (default) rewrites an AI-sounding draft.
- `generate` drafts new copy that reads human from the start.
- `register` matches the genre's conventions. `--register auto` infers it from the
  content and prints why: 82% accurate on this repo's labeled corpus versus 19% for
  the old always-`technical` default, and it falls back to `technical` when unsure
  rather than guessing a permissive profile that would excuse real tells. An explicit
  `--register` always wins.

The skill sizes its own effort. A commit message gets a quick pass with no audit;
a landing page gets the intake, the scored critique and the detector gate. Depth
changes how much runs, never how strictly: the invariant guard and the
no-fabrication rule hold at every level.

It also stays on. Once invoked it shapes everything you write for the rest of the
session, including the reply that hands the rewrite back, until you say "stop
human-voice" or "normal voice". That is deliberate. The usual way a humanized
document loses its voice is the next document, drafted an hour later, in the
default one.

Rules that fight the task lose to the task. An API reference keeps its headings
and a safety notice keeps "may"; the skill relaxes the rule in the way, names it
in the audit, and holds the rest. See "When a rule fights the task" in
[`SKILL.md`](../skills/human-voice/SKILL.md).

Run it on its own anytime:

```bash
python3 skills/human-voice/scripts/detect_ai_prose.py <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --register marketing <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --register auto <file>   # infer it
python3 skills/human-voice/scripts/detect_ai_prose.py --dialect american <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 <file>   # exit 1 if score > 5 (CI gate)
python3 skills/human-voice/scripts/detect_ai_prose.py --fix <file>          # rewrite em-dashes/--/spaced hyphens to commas, strip emoji, swap filler
python3 skills/human-voice/scripts/detect_ai_prose.py --fix-dry-run <file>  # preview the autofix without writing
printf '%s' "$TEXT" | python3 skills/human-voice/scripts/detect_ai_prose.py -
```

`--fix` applies only the unambiguous, deterministic edits: dash normalization,
decorative-emoji removal, 1:1 filler/jargon swaps. The dash rewrite varies the
mark rather than turning every dash into a comma, because a document with one
punctuation mark everywhere has traded the em-dash signature for a fresh uniform
one. A paired aside becomes parentheses, an enumeration takes a colon, everything
else takes a comma. It skips dash and emoji changes in `creative` (and keeps emoji
in `casual`), and it never edits code, numbers, links, URLs, or table cells: a
lexical swap inside a link destination produces a 404, not a better sentence. The
judgment work stays with the rewrite pass: cutting the empty sentences, unstaging
the clefts, sharpening a stance that won't commit.

Verify against a real detector, which is the only thing that can answer "does this
still read as AI to a classifier". Exit 1 while flagged, 0 when clear, 2 when no
key is configured:

```bash
export GPTZERO_API_KEY=...   # or ORIGINALITY_API_KEY / SAPLING_API_KEY / WINSTON_API_KEY
python3 skills/human-voice/scripts/verify_detector.py rewrite.md
python3 skills/human-voice/scripts/verify_detector.py --before draft.md rewrite.md
python3 skills/human-voice/scripts/verify_detector.py --max-p-ai 0.05 --json rewrite.md
make verify FILE=rewrite.md BEFORE=draft.md
```

Nothing is sent anywhere until you set a key: no default endpoint, no telemetry.
The request shapes come from each vendor's docs and have not been exercised against
a live API from this repo, so a stale one surfaces as an error naming the missing
field rather than a silent wrong answer.

On Windows, use the `py` launcher (or `python`) instead of `python3`, and pipe
text with PowerShell: `$TEXT | py skills/human-voice/scripts/detect_ai_prose.py -`.

It needs only Python 3 (3.8+), no `pip install`. The word and spelling lists live
in `skills/human-voice/scripts/ai_prose_patterns.json`; edit them to taste,
including the category weights and verdict bands.

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

`skills/human-voice/examples/` has a before/after pair for every register plus the
modern-AI pair. There is also a generate-mode example, a refusal-to-fabricate
example, a restraint case, and an annotated walkthrough. Each "after" scores `clean`; run it
on both halves to confirm.

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

## Questions

**Why did it flag my human-written text?** The linter is a regex floor; it over-
flags sometimes. Lower a threshold, add a `protected_terms`/`context_exceptions`
entry, or open a [false-positive issue](../.github/ISSUE_TEMPLATE/false-positive.md).
Those feed the corpus and the FPR measurement.

**Does it work on non-English text?** No. The word lists and dialect map are
English-only today. `--lang` accepts only `en`.

**Can I tune it per project?** Yes. Drop a `.humanvoicerc` (JSON) at your repo root
to set a default register/dialect, override thresholds and category weights, and
add protected terms. See [CONTRIBUTING.md](../CONTRIBUTING.md).
