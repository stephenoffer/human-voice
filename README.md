# human-voice

![tests](https://github.com/stephenoffer/human-voice/actions/workflows/test.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

**Make AI-drafted docs read like a person wrote them, without changing a single fact.**

`human-voice` is a Claude Code skill that rewrites or generates prose so it
doesn't read as AI-written. Most "humanizer" tools swap a few words and call it
done. The text still reads like a machine, because the giveaways aren't lexical.

The best available evidence on what trained detectors respond to says they track
the artifacts of *instruction tuning*, not machine-ness: base models, which never
went through it, get classified human more than 96% of the time. The named
artifacts are markdown formatting preference, response-length and structural
conventions, and sycophancy. Measured on this repo's own corpus, the categories
that catch 2023-era slop are `filler` and `meta_commentary`, both word-level, and
they contribute **0%** to catching prose a current model writes. What catches that
is syntax and shape: `participial_tail` (the ", making it easier to…" tail) at
21%, `sentence_shape` at 17%, `paragraph_uniformity` at 10%, `burstiness` at 9%,
and `cleft` ("What actually mattered was…") at 8%.

So this skill fixes shape and syntax first, then rhythm, then substance. Word
choice is the last and shallowest pass. See
[`references/what-detectors-see.md`](skills/human-voice/references/what-detectors-see.md)
and the measured breakdown in [`eval/EVAL.md`](eval/EVAL.md).

## See the difference

### The easy case (2023-era slop)

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
Your team keeps its notes in six different tools. By Friday nobody
remembers which thread held the real decision. Put the chat right
next to the files, in one place, so "wait, where did we land on this?"
stops being a question anyone has to ask.
```

Nobody is fooled by the "before". Fixing it is mostly a diction exercise.

### The hard case (what a current model actually writes)

This is the one that matters. Fluent, takes a position, carries concrete detail.
No filler, no hedging stack, not one em-dash. It still reads machine-written.

```text
BEFORE   score 19.9 · strong-tell
─────────────────────────────────────────────────────────────────
For most teams under ten million vectors, pgvector is the right
starting point. You already have backups, monitoring, and access
control for Postgres. Adding a second stateful system is a real cost
that tends to get underestimated during the prototype phase, when the
dataset is small and everything is fast.
```

```text
AFTER    score 0 · clean
─────────────────────────────────────────────────────────────────
Start with pgvector. Under about ten million vectors it wins, and the
reason has nothing to do with recall benchmarks: it is the database
you already back up, already monitor, already have access control
for. A second stateful system is a cost that arrives months after the
prototype, when the dataset is small and every query is fast and
nobody is thinking about it.
```

Every sentence in that "before" is between ten and thirty words. Not one is
short. That is the whole tell, and no word list can see it: sentences ≤8 words
went 0% → 42%, the 12–26 word band went 73% → 42%, length CoV 0.33 → 0.65. The
verdict moved to the front. The both-sides concession got short and lopsided.
Nothing was invented. Full annotation in
[`examples/modern-ai-notes.md`](skills/human-voice/examples/modern-ai-notes.md).

## Why use it

- It fixes the tells that actually give AI away, in evidence order. Strip the
  assistant shape (heading density, bulleted answers, ornamental bold, the "Key
  takeaways" recap). Then the syntactic signature a current model leaves once the
  slop diction is gone: clefts that stage the subject ("What actually mattered
  was…"), resultative tails bolted onto every sentence (", making it easier
  to…"), copula-only paragraphs where nothing happens. Then the sentence-length
  *distribution*, not just its variance: model prose collapses into the 12–26
  word band and human prose reaches past both ends. Then vacuity, then the
  templates, then stance. Diction last.
- Nothing gets fabricated to sound human. Numbers, quotes, citations, defined
  terms, code: all invariant. When a draft needs a fact it doesn't have, the
  skill writes `[SOURCE NEEDED]` instead of inventing one. The anti-hallucination
  protocol is built in.
- The genre comes first, never one default voice. A technical report stays
  professional. Marketing copy addresses "you". A blog post gets a personality.
  Ten register profiles share one universal core of tells fixed everywhere.
- It adds, not only subtracts. A rewrite that can only delete produces clean,
  generic, unowned prose, which is why most humanized text still reads humanized.
  The skill runs an author-material intake first: pull the real specifics out of
  the draft, the repo, or four short questions to you. Nothing invented. Gaps get
  marked `[SOURCE NEEDED]`.
- It verifies instead of claiming, and it distinguishes the two. Configure a
  detector API key and `verify_detector.py` becomes the rewrite's stopping
  condition: exit 1 while the text is still flagged, 0 when it clears, 2 when the
  gate could not run. The floor score cannot substitute for that, because a
  document can score 0.0 and still be flagged. And the detector claims are measured:
  `eval/detector_local.py` runs real GPT-2 surprisal and a real classifier locally,
  and the numbers below come from that run, not from a vendor's marketing page.
- A bundled linter gates your CI. The dependency-free Python script scores the
  regex-able tells and prints a verdict; past a threshold you set with
  `--fail-over`, it exits non-zero. It says plainly what it can't see.
- No detector games, because they lose on their own terms. The vendor with the
  strongest published numbers on humanized text reports that *the more fluent a
  humanizer's output, the more reliably it is detected*. The tools that evade do
  it by damaging the text, and the damage is the signature. Homoglyphs, zero-width
  characters, tortured synonyms, injected typos: each trivially detected, each
  makes the writing worse. AI detectors also misclassify non-native-English
  writing as machine-made (Liang et al. 2023), so no detector is ground truth in
  either direction.

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
- `register` matches the genre's conventions. `--register auto` infers it from the
  content and prints why: 82% accurate on this repo's labeled corpus versus 19% for
  the old always-`technical` default, and it falls back to `technical` when unsure
  rather than guessing a permissive profile that would excuse real tells. An explicit
  `--register` always wins.

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

Those are the numbers the rewrite targets. Treat the score as a floor, not a
judgment: it catches cheap, regex-able tells but can't see vacuity, weak stance,
or fabrication. The real test is a skeptical human read.

`skills/human-voice/examples/` has a before/after pair for every register plus the
modern-AI pair. There is also a generate-mode example, a refusal-to-fabricate
example, a restraint case, and an annotated walkthrough. Each "after" scores `clean`; run it
on both halves to confirm.

The linter is measured, not asserted: `eval/` holds a labeled corpus and
`run_eval.py`, and [`eval/EVAL.md`](eval/EVAL.md) reports precision/recall, the
false-positive rate on human-written text, and the number that actually matters:
how it does against prose a *current* model writes rather than 2023-era
caricature.

One of those negative sets is not authored here at all. `eval/human_baseline.py`
scores the docstrings of 26 Python standard-library modules, written by hundreds
of people who never saw this repository and shipped with every interpreter, so it
runs offline with no corpus file. Pointing the linter at it found five real
false-positive bugs, and the median score on that set went from 35.0 to 8.7.

## How it compares

Three different markets get confused with each other. Here is where this sits in
each.

### Prose linters (what human-voice is closest to)

| Tool | Catches | Misses |
|---|---|---|
| proselint | weak diction, clichés, usage rules drawn from Get and Pinker | structure, shape, stance, register, AI signature |
| write-good | passive voice, weasel words, "so"/"there is" openers | everything above |
| Vale | exactly the style rules you configure, fast, markup-aware | everything you didn't encode; no AI theory |
| textlint / alex / blocklint | plugin rules; insensitive and exclusionary wording | style, structure, AI signature |
| LanguageTool | grammar and spelling in 25+ languages | style beyond grammar |
| Hemingway / readability scores | long sentences, adverbs, a grade level | grade level is not humanness; rewards flatness |
| **human-voice** | assistant shape, sentence-length distribution, substance, stance, register drift, and it **rewrites** | it's a floor, not a detector (no perplexity model) |

The category difference: those tools score or nitpick a sentence. This one has a
theory of what gives AI away, ranks its checks by measured evidence, and hands the
rewrite to a model with the priority order attached.

### AI detectors (what human-voice is measured *against*, not competing with)

Roughly in order of independently-reported accuracy: Pangram, Originality.ai,
GPTZero, Copyleaks, Winston AI, Turnitin, Sapling, ZeroGPT, and the zero-shot
research family (DetectGPT, FastDetectGPT, Binoculars). They fall into three
groups that behave very differently on rewritten text. Statistical and zero-shot
detectors move a lot, general trained classifiers move partly, and classifiers
trained on humanizer output barely move. The table and the numbers are in
[`references/what-detectors-see.md`](skills/human-voice/references/what-detectors-see.md).
None is ground truth: reported false-positive rates run from ~0.004% to ~10%
depending on the tool and the text, and they are systematically worse on
non-native-English writing.

### "Humanizers" (what human-voice deliberately is not)

The commercial humanizer market sells a bypass rate. Undetectable AI, StealthGPT,
Phrasly, Walter Writes, QuillBot Humanizer, HIX/BypassGPT, GPTinf, Humanize AI
Pro, Smodin, Writesonic, Ghost AI, TwainGPT, Just Done, Ahrefs' and Grammarly's
paraphrasers, and a long tail of clones. When one vendor tested 19 of
them, five were caught 100% of the time and most of the rest above 90%.

The reason is worth internalizing: **the more fluent a humanizer's output, the
more reliably it is detected.** The ones that do evade work by damaging the text.
Tortured synonyms ("counterfeit consciousness" for "artificial intelligence"),
homoglyphs and zero-width characters, thin-space padding, injected typos: every
one of those is itself a detectable artifact. They optimize the metric and
lose the thing the metric was measuring.

human-voice does none of it, on purpose. It has no bypass rate to quote. What it
has is a measured claim: it makes prose read as though a competent person wrote
it, which is the only durable version of the same goal.

## FAQ

**Will this make my text undetectable?** Nobody can promise that, so instead of
promising it, the skill *checks*. Point it at a detector and the rewrite gets a
hard stopping condition:

```bash
export GPTZERO_API_KEY=...     # or ORIGINALITY / SAPLING / WINSTON
python3 skills/human-voice/scripts/verify_detector.py --before draft.md rewrite.md
```

The gate exits **1 while the detector still flags the text**, 0 when it clears, 2
when no detector is configured (which is *not* a pass, and the audit has to say so).
The skill keeps looping from the rewrite while the gate returns 1. So against
whichever detector you actually care about, the answer is not a claim in a README,
it is an exit code you can check.

**Measured, not asserted.** `make detector-local` runs five real detectors locally on
open models: no API key, nothing leaving the machine. Two statistical (perplexity,
Binoculars) and three supervised classifiers.

First, calibration, because a detector that cannot pass human writing tells you
nothing about a rewrite. One candidate labels **34 of 34** hand-written human files as
AI at p(AI)=1.000, so it is excluded from every count. Among those that pass, one is
genuinely discriminating: **0 of 34** human files flagged, **24 of 24** caricature-AI
files flagged.

Against that panel, all 12 realistic modern-AI samples put through the skill:

| | before | after |
|---|---|---|
| flagged by a usable classifier | 3 of 12 | **0 of 12** |
| median perplexity multiplier | n/a | **x2.46** (all 12 rose) |
| Binoculars | n/a | rose in all 12 |

The seven shipped example pairs: **4 of 7 flagged before, 0 of 7 after.** Across both
sets, **7 of 19 documents flagged before, 0 of 19 after**, and "flagged" is each
classifier's own argmax label, not a threshold anyone picked.

The control that makes the rest believable: the anti-AI costume pair already scores
perplexity 113.7, *higher* than real human writing, and the rewrite brings it **down**
to 60.6. A tool chasing the metric would have banked the 113.7.

The same run produced the finding that matters more. Realistic model output is nearly
indistinguishable from human already: perplexity 30.1 against 29.5, Binoculars 0.794
against 0.780, and the classifier that catches 24 of 24 caricature files catches 3 of
12 of it. The distributional tells are gone. What is left is structural, which is what
this skill fixes.

What this does **not** establish is undetectability, and nothing could. No commercial
API was queried from this repo. A classifier trained specifically on humanizer output
is reported by its vendor at ~97% on rewritten text, a figure about *other tools'*
output that has not been tested either way against this one. The models here are small,
so trust direction over absolute values, and n is 19 documents from one author. Set a
key and run the gate for your own number on your own text.

Two limits are built into the loop rather than footnoted. It is capped, and it stops
early if two passes cannot move the detector without damaging the prose. And a
`clear` is evidence about one detector at one threshold.

**Why did it flag my human-written text?** The linter is a regex floor; it over-
flags sometimes. Lower a threshold, add a `protected_terms`/`context_exceptions`
entry, or open a [false-positive issue](.github/ISSUE_TEMPLATE/false-positive.md).
Those feed the corpus and the FPR measurement.

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

## Credits

The v0.4 recalibration ranks tells by what readers *cite* as AI, not by what a
scanner *matches*. It draws on two MIT-licensed projects and the ~90k-post Reddit
study behind them: [JCarterJohnson/vibecoded-design-tells](https://github.com/JCarterJohnson/vibecoded-design-tells)
and [ryanthedev/oberskills](https://github.com/ryanthedev/oberskills). See
[`references/cited-vs-matched.md`](skills/human-voice/references/cited-vs-matched.md).

## License

MIT. See [LICENSE](LICENSE).
