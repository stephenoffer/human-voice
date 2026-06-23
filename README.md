# human-voice

![tests](https://github.com/stephenoffer/human-voice/actions/workflows/test.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

**Make AI-drafted docs read like a person wrote them, without changing a single fact.**

`human-voice` is a Claude Code skill that rewrites or generates prose so it
doesn't read as AI-written. Most "humanizer" tools swap a few words and call it
done. The text still reads like a machine, because the giveaways aren't mostly
lexical. They're structural (em-dash overuse, relentless rule-of-three,
bold-bullet listicles, sentences that are all the same length) and substantive
(paragraphs that say nothing, a survey where a verdict belongs, invented
specifics). This skill fixes those first and treats word choice as the last and
shallowest pass.

## See the difference

Same claim, two voices. The scores come from the bundled linter — run it on both
yourself.

```text
BEFORE   score 354 · strong-tell · 16 tells
─────────────────────────────────────────────────────────────────
In today's fast-paced digital landscape, leveraging cutting-edge
solutions is crucial for success. Our robust, scalable, and seamless
platform empowers teams to delve into actionable insights, unlock
their full potential, and move the needle. It's not just a tool, it's
a game-changer that stands as a testament to innovation.
```

```text
AFTER    score 0 · clean
─────────────────────────────────────────────────────────────────
Your team's notes live in six different tools, and the context dies
with each one. We put the conversation, the files, and the decision
in one place. The first thing you'll notice is small: you stop asking
"where did we land on this?"
```

The "before" isn't a vocabulary problem. It's the whole machine signature at
once: filler (`leverage`, `delve`, `seamless`), business jargon
(`move the needle`, `actionable`), a rule-of-three, the `it's not X, it's Y`
reflex, and puffery (`stands as a testament`). Swapping synonyms leaves all of
that standing. The skill strips it and commits to one concrete claim.

## Why use it

- It fixes the tells that actually give AI away. The signature is structural and
  substantive, not just word choice. human-voice cuts vacuity, breaks uniform
  sentence rhythm (what detectors call *burstiness*), dismantles rule-of-three
  and bold-bullet templates, and makes the text take a position. Diction comes
  last.
- It never fabricates to sound human. Numbers, quotes, citations, defined terms,
  and code are invariants. When a draft needs a fact it doesn't have, the skill
  marks `[SOURCE NEEDED]` rather than inventing one. That anti-hallucination
  protocol is built in.
- It matches the genre instead of forcing one voice. A technical report stays
  professional, marketing copy addresses "you", a blog post has personality. Six
  register profiles share one universal core of tells fixed everywhere.
- It ships a linter you can gate CI on. A dependency-free Python script scores
  the regex-able tells and prints a verdict. Wire it into a build with
  `--fail-over`. It stays honest about what it can't see.
- It's honest about detectors. No homoglyph or zero-width tricks, no deliberate
  typos. The goal is genuinely better writing, not a passing score. AI detectors
  also misclassify non-native-English writing as machine-made (Liang et al.
  2023), so no detector is ground truth anyway.

## Install

### 1. Plugin marketplace (one command)

```
/plugin marketplace add stephenoffer/human-voice
/plugin install human-voice@human-voice
```

Then run `/human-voice` in any session.

### 2. Manual skill copy

```bash
git clone https://github.com/stephenoffer/human-voice.git
cp -r human-voice/skills/human-voice ~/.claude/skills/        # user scope
# or, for one project only:
cp -r human-voice/skills/human-voice <your-project>/.claude/skills/
```

### 3. Use it from this repo directly

The skill already lives at `skills/human-voice/`. Open this repo in Claude Code
and invoke `/human-voice`.

## Use

```
/human-voice <file-path | pasted-text> [fix|generate] [register: technical|business|marketing|academic|casual|creative]
```

- `fix` (default) rewrites an AI-sounding draft.
- `generate` drafts new copy that reads human from the start.
- `register` matches the genre's conventions; it's inferred if you omit it.

Run it on its own anytime:

```bash
python3 skills/human-voice/scripts/detect_ai_prose.py <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --register marketing <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --dialect american <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 <file>   # exit 1 if score > 5 (CI gate)
python3 skills/human-voice/scripts/detect_ai_prose.py --fix <file>          # rewrite em-dashes/--/spaced hyphens to commas, strip emoji, swap filler
python3 skills/human-voice/scripts/detect_ai_prose.py --fix-dry-run <file>  # preview the autofix without writing
printf '%s' "$TEXT" | python3 skills/human-voice/scripts/detect_ai_prose.py -
```

`--fix` applies only the unambiguous, deterministic edits: dash-to-comma
normalization, decorative-emoji removal, and 1:1 filler/jargon swaps. It skips
dash and emoji changes in the `creative` register (and keeps emoji in `casual`),
never touches code, numbers, or links, and leaves the judgment work — varying
the replacement mark, cutting vacuity, sharpening stance — to the rewrite pass.

On Windows, use the `py` launcher (or `python`) instead of `python3`, and pipe
text with PowerShell: `$TEXT | py skills/human-voice/scripts/detect_ai_prose.py -`.

It needs only Python 3 (3.8+), no `pip install`. The word and spelling lists live
in `skills/human-voice/scripts/ai_prose_patterns.json`; edit them to taste,
including the category weights and verdict bands.

## How the score works

The score is *weighted tells per 1000 words*, with a band attached: below 5
reads **clean**, 5 to 15 is **watch**, and 15+ is a **strong-tell**. Lower is
better. Treat it as a floor, not a judgment: it catches cheap, regex-able tells
but can't see vacuity, weak stance, or fabrication. The real test is a skeptical
human read.

`skills/human-voice/examples/` has a before/after pair for every register
(technical, marketing, casual, academic, email) plus a generate-mode example, a
refusal-to-fabricate example, a restraint case, and an annotated walkthrough. Each
"after" scores `clean`; run it on both halves to confirm.

The linter is measured, not asserted: `eval/` holds a labeled corpus and
`run_eval.py`, and [`eval/EVAL.md`](eval/EVAL.md) reports precision/recall and the
false-positive rate on human-written text.

## How it compares

| Tool | Catches | Misses |
|---|---|---|
| proselint / write-good | weak diction, clichés, lint rules | structure, stance, register |
| Vale | style rules you configure | everything you didn't encode |
| GPTZero / detectors | a perplexity/burstiness verdict | *why*, and they flag human text too |
| **human-voice** | structure + substance + stance + register, and **rewrites** | it's a floor, not a detector — no perplexity model |

The difference: other tools score or nitpick. human-voice fixes the structural and
substantive tells first, matches the genre, and treats word choice as the last and
shallowest pass.

## FAQ

**Will this beat GPTZero?** Sometimes, as a side effect, but that isn't the point
and isn't a promise. The aim is prose a skeptical human reads as human-written. No
detector is ground truth; they carry real false-positive rates.

**Why did it flag my human-written text?** The linter is a regex floor; it over-
flags sometimes. Lower a threshold, add a `protected_terms`/`context_exceptions`
entry, or open a [false-positive issue](.github/ISSUE_TEMPLATE/false-positive.md) —
those feed the corpus and the FPR measurement.

**Does it work on non-English text?** No. The word lists and dialect map are
English-only today. `--lang` accepts only `en`.

**Can I tune it per project?** Yes. Drop a `.humanvoicerc` (JSON) at your repo root
to set a default register/dialect, override thresholds and category weights, and
add protected terms. See [CONTRIBUTING.md](CONTRIBUTING.md).

## What it won't do

It improves writing; it does not disguise machine text. No Unicode homoglyphs,
no zero-width characters, no deliberate typos, no meaning-degrading synonym
swaps, and never an invented fact or a faked quote to seem human. Passing a
detector is a side effect of good writing, not the objective.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Tests:
`python3 tests/stress_test.py` (also run on Python 3.8–3.13 in CI).

## License

MIT. See [LICENSE](LICENSE).
