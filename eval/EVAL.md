# Evaluating the human-voice linter floor

<!-- human-voice: ignore filler -->
This directory holds an offline, dependency-free evaluation harness for the
deterministic linter at `skills/human-voice/scripts/detect_ai_prose.py`. It
measures how well the linter's single floor score separates human-voiced prose
from classic AI-slop, where each category contributes, and provides a scaffold
for checking rewrites against an external detector.

**Read this first.** The headline number in earlier versions of this file was a
ROC AUC of 1.000, and it was close to meaningless: the `ai/` samples were authored
to carry the exact tells the linter scores, so a perfect separation measured
internal consistency and nothing else. That number is still reported below,
labeled as what it is. The number to trust is the other one: **AUC 0.938 against
`ai_modern/`**, a class written the way a contemporary instruction-tuned model
actually writes. Recall at the default boundary is 0.90, precision is 1.000, and
the two files it misses are named.

All numbers below are MEASURED. Reproduce (or regression-gate) them:

```bash
python3 eval/run_eval.py            # metrics + per-file scores -> eval/results.json
python3 eval/run_eval.py --check    # fail (exit 1) if metrics drift from the committed results.json
python3 eval/ablation.py            # per-category contribution -> eval/ablation_results.json
python3 eval/ablation.py --check    # fail if the baseline separation drifts
python3 eval/human_baseline.py      # false positives on human prose nobody wrote for this repo
python3 eval/human_baseline.py --check   # fail if that sweep breaches its ceilings
python3 eval/detector_harness.py    # offline by default; needs an API key to call a detector
python3 eval/build_profile.py       # rebuild the human function-word reference profile
python3 eval/build_profile.py --check    # fail if the committed profile drifted
```

Shared logic (loaders, metrics, bootstrap CIs, the regression comparator, corpus
validation) lives in `eval/lib.py`; the three scripts are thin consumers. The
committed `results.json` / `ablation_results.json` are golden baselines: `--check`
recomputes in memory and fails on drift, so a metric change must be regenerated
and reviewed in the git diff rather than silently overwritten in CI.

## Methodology

- **Corpus**: 113 short Markdown files authored by hand for this eval
  (`eval/corpus/`). The legacy binary classifier set is **63 files**, 39 labeled
  `human` (including a 10-file ESL/formal-human hard-negative subset, see below)
  and 24 labeled `ai`. Both classes span every register the skill supports:
  technical, business, marketing, academic, casual, creative, email. A
  further **10 files** form the held-out `over_corrected` class (the "anti-AI
  costume"), excluded from the binary AUC and scored on their own. Every
  file's label, register, and group tag lives in `eval/corpus/LABELS.json`;
  `eval/lib.py:validate_corpus` enforces that every file is labeled and every
  register is real. No external or copyrighted text was used. The `human` samples
  read like a person wrote them (varied rhythm, a real stance, concrete detail);
  the `ai` samples carry the machine signature (filler, rule-of-three,
  bold-bullet listicles, hedging, puffery, meta-commentary, aidiolect phrases,
  uniform rhythm). The two `creative` AI samples lean on those tells rather than
  em-dashes, since the creative register mutes the dash checks.
- **Hard negatives** (the FPR stress test). Two subsets probe the failure modes
  that matter most. `esl_formal/` (10 files, labeled `human`, group `esl`) are
  careful non-native and formal-but-human samples, the population GPT detectors
  demonstrably over-flag, and they stay in the binary set so they count against
  the human FPR. `over_corrected/` (10 files, label `over_corrected`) is text in
  the anti-AI costume (forced lowercase, sprinkled slang, staccato fragments);
  these *should* be flagged, so they are held out of the AUC and reported as a
  recall, not counted as human false positives. `lib.subset_fpr` reports the
  ESL-only FPR; `lib.costume_eval` reports the costume recall.
- **`ai_modern_rewritten/`** (20 files, held out). Each `ai_modern/` sample after the
  skill's rewrite procedure, under the same filename, so before and after are paired
  on identical claims. This is the class that tests the skill's actual claim rather
  than the linter's: does the procedure take prose a current model writes down to the
  clean band, and does it move a real detector? `lib.rewrite_eval` pairs by basename
  and reports any file that got *worse* by name rather than averaging it away. A
  pytest case asserts every numeric token in an after-file appears in its
  before-file, which is the anti-hallucination protocol enforced mechanically on the
  shipped rewrites.
- **Scoring**: each file is scored by importing the linter module and calling
  `dap.lint(text, register, dialect=None, patterns)`, using the register from the
  label file. The floor score is **floor points**: document-level findings (flat
  burstiness, even paragraphs, assistant shape) contribute fixed points, instance
  findings a per-1000-word density capped per category. Before v0.5 everything was
  divided by word count, which made an identical defect worth ~13 points in a
  150-word file and ~1 point in a 2000-word one. Since the corpus median is 163
  words, that quantization was distorting every number in this file.
- **Classifier**: the floor score is treated as a 1-D binary classifier,
  predicting `ai` when `score >= threshold` (positive class = AI). We report two
  thresholds: the linter's default "watch" boundary (5.0, where `clean` ends)
  and a swept best-F1 threshold. Thresholds are swept over midpoints between
  observed scores.
- **Separation**: ROC AUC is computed as the rank statistic
  P(score_ai > score_human) with ties counted as 0.5.
- **Ablation**: for each category, the corpus is re-scored with that category's
  weight forced to 0, and we recompute AUC and best-F1 accuracy. Because the
  classes separate with a large margin, we also report each category's share of the
  score mass for **both** AI classes, "AIshare" against the caricature and
  "MODshare" against `ai_modern/`. The divergence between those two columns is the
  most useful output in this directory.
- **Stylometric reference**: `eval/build_profile.py` builds a 150-feature
  function-word profile from `eval/corpus/human/` (29 files) and commits it to
  `skills/human-voice/scripts/human_reference_profile.json`, which the linter
  reports a Burrows's Delta against. It contributes nothing to any score here, and
  the direction is the opposite of the intuitive one: the human class averages
  0.769 and `ai_modern/` averages 0.690, so model output sits *closer* to the human
  centroid than human writing does and the naive rank statistic is 0.188. Read
  inverted it separates at 0.812, still below the floor score's 0.938, and it runs
  0.737 on the ESL/formal subset. Its use is paired: the twenty
  `ai_modern_rewritten/` files move 0.690 → 0.739 and land closer to the human
  median in 16 of 20 cases, which is the only number in this directory that shows
  the rewrite procedure moving a distributional property rather than a surface one.
  Reasoning and the full table:
  [`references/competitive-landscape.md`](../skills/human-voice/references/competitive-landscape.md).
- **Calibration anchor**: `eval/tests/test_calibration.py` asserts the category
  weights keep a strong rank (Spearman) correlation with the ranking of tells by
  how often the ~90k-post Reddit study found readers *cite* them, so a future
  weight edit that drifts from the evidence fails loudly. See
  `skills/human-voice/references/cited-vs-matched.md`.
- **Confidence intervals**: `run_eval.py` reports 95% stratified percentile
  bootstrap CIs (2000 resamples, fixed seed 1729 so the bounds are reproducible
  and gate-able) for ROC AUC, F1@5.0, and the human-subset FPR. With n=58 these
  quantify resampling variance *within the authored set*, not sampling intervals
  over real-world text.

## Measured results

### The number that matters: realistic modern AI vs human

`ai_modern/` (20 files) is prose a current instruction-tuned model actually
produces. Against the human class:

| metric | v0.8 | v0.6 | v0.5 |
|---|---|---|---|
| **ROC AUC vs human** | **0.938** | 0.937 | 0.901 |
| recall @ 5.0 | **0.900** (18 of 20) | 0.850 (17 of 20) | 0.750 |
| precision @ 5.0 | **1.000** | 1.000 | 0.750 |
| F1 @ 5.0 | **0.947** | 0.919 | 0.750 |
| score range | 0.0 – 47.2 (median 17.0) | 0.0 – 41.1 (median 15.0) | 0.0 – 34.0 |

Missed at the default boundary: `m09_creative_scene.md` and
`m17_email_project.md`. `m20_creative_arrival.md` was the third until v0.8, and
what caught it is worth recording, because it was a design fault rather than a
missing check. The `cleft` check was **muted** in the creative register on the
argument that clefts are legitimate rhetoric in fiction. Muting threw away the
signal above that tolerance along with the false positives below it, and
`m20_creative_arrival.md` was stacking clefts at 10.5 per 1,000 words while
scoring 3.3. The human creative samples in this corpus carry none at all. v0.8
replaces the mute with a per-register multiplier (`register_thresholds`): fiction
gets 1.3x the bar, not an exemption.

The two that remain are the honest shape of the floor's blind spot. A model
writing narrative or a two-decision status email naturally produces varied rhythm,
short sentences, and no markdown, so the surface metrics have nothing to fire on.
`m17_email_project.md` carries exactly one em-dash and the dash check needs three
before it fires, which is a deliberate choice: two em-dashes is what a person who
likes em-dashes writes in an email. What makes those files machine-written is that
the specifics are plausible and unowned: a house nobody inherited, a migration
nobody ran. No regex reaches that, which is precisely why the skill's
author-material intake and the human rubric below exist.

The v0.8 column adds `llm_artifact`, `heading_structure`, `quote_style` and
`copula_avoidance`, widens the wh-cleft pattern to clause boundaries, and replaces
two blunt register mutes with threshold multipliers. Every one of those was
measured against `eval/corpus/human/` and `eval/human_baseline.py` before it was
given a weight, and the human-subset FPR, the ESL/formal FPR, the costume recall,
and the stdlib-docstring worst score are all unchanged. The survey that produced
them, including three techniques that were tested and rejected, is in
[`skills/human-voice/references/competitive-landscape.md`](../skills/human-voice/references/competitive-landscape.md).

The v0.5 column is the same measurement before the syntactic checks
(`cleft`, `participial_tail`, `copula_density`, `clause_splice`,
`paragraph_openers`, `bullet_openers`, `noun_chain`) and before the
false-positive fixes described under Classifier metrics. Two of the three
previously-missed casual files are now caught, and the precision gain came from
removing false positives rather than from raising the threshold.

Compare that AUC of 0.938 with the 1.000 below and the audit finding is still
visible in one line.

### Legacy separation against the 2023-era `ai/` caricature

Reported for continuity, not as evidence of reach:

- human floor scores (all 39, incl. ESL subset): min **0.0**, max **4.0**
- caricature-AI floor scores: min **41.2**, max **202.3**
- **ROC AUC = 1.000** (95% bootstrap CI [1.000, 1.000])

Every `ai/` file outscores every `human` file by a wide margin. This measures that
the linter fires on the tells it was written to fire on. The samples were authored
to carry them, so it cannot measure anything else.

### Classifier metrics at the default "watch" boundary (threshold 5.0)

Legacy binary set (39 human / 24 caricature-AI):

| metric | value | v0.5 | pre-v0.5 |
|---|---|---|---|
| precision | **1.000** | 0.889 | 0.706 |
| recall | **1.000** | 1.000 | 1.000 |
| F1 | **1.000** | 0.941 | 0.828 |
| accuracy | **1.000** | 0.948 | 0.828 |
| human-subset false-positive rate | **0.000** (0 of 39) | 0.088 | 0.294 |

Confusion: tp=24, fp=0, tn=39, fn=0.

Three separate false-positive fixes closed the remaining gap in v0.6, and each one
was a real defect rather than a threshold move:

1. `uniform_openers` fired whenever 30% of sentences began with the same word. On
   this corpus, human and AI files overlap completely in the 0.30–0.45 band for
   `the`, `we`, and `I`, which are simply the words English sentences start with.
   The check now needs a much higher rate (0.45 and at least five sentences) for
   that closed set of high-frequency openers, and keeps the low bar for a
   repeated *distinctive* opener, which is the actual templating signal.
2. `burstiness` computed a coefficient of variation from as few as five
   sentences. A seven-sentence human abstract measured 0.33 and was flagged for
   flat rhythm, while every AI file that fires has ten or more sentences. The
   minimum is now eight.
3. The noun-phrase `rule_of_three` pattern could not tell a triad from a list of
   clauses, so "you paste code into a notebook, the kernel dies, and the last
   save is gone" was flagged as a rule-of-three. Members that contain a pronoun
   or a finite verb, or that open with a preposition, are no longer treated as
   noun phrases.

The `clean` band still treats a `watch`-band human document as "worth a second
look", never as proof of authorship. A 0.000 rate on 39 authored files does not
mean the real rate is zero; it means this corpus no longer contains a case that
trips it.

### Classifier metrics at the swept best-F1 threshold (10.7)

| metric | value |
|---|---|
| precision | **1.000** |
| recall | **1.000** |
| F1 | **1.000** |
| accuracy | **1.000** |
| human-subset false-positive rate | **0.000** |

Confusion: tp=24, fp=0, tn=39, fn=0.

Any threshold between 4.0 and 41.2 separates the legacy corpus perfectly. Do not
port the swept value anywhere: it is an artifact of how saturated the caricature
samples are, and at 10.7 it would miss 8 of the 20 `ai_modern` files. The product
default of 5.0 is tuned to warn early on real documents.

### The independent negative set: prose nobody wrote for this repository

Everything above is measured on text one person authored knowing what the linter
checks. `eval/human_baseline.py` removes that caveat for one class of text: it
scores the docstrings of 26 Python standard-library modules, written by hundreds
of people over three decades, none of whom had heard of this tool. It needs no
network and no corpus file, because the text ships with the interpreter.

| | v0.5 | v0.6 | v0.9 |
|---|---|---|---|
| median floor score | 35.0 | 8.7 | **8.0** |
| worst module | 43.5 | 17.7 | **15.3** |
| largest single category's share of all findings | 44% (`dash_style`) | 42% (`ngram_repetition`) | **25%** (`ngram_repetition`) |

The v0.5 and v0.6 columns were measured on partly wrong input. Until v0.9 the
sweep collected every attribute's `__doc__`, which pulled in the docstrings of
imported modules and, for every constant, the docstring of its type (`int`'s text
172 times inside `sqlite3`). The result also depended on import order: under
pytest `email` scored 34.2 against 17.7 in a plain run, which failed CI on every
push. The sweep now reads function and class docstrings once each and agrees in
and out of pytest on Python 3.8 through 3.13. On that clean input, two-word
n-grams made up 49% of all false-positive score points, nearly all of them terms
of art, so `ngram_repetition` now counts trigrams only. The labeled eval did not
move. v0.9 figures are from Python 3.14; the sweep's module set varies a little by
version, and the gate holds on every one CI runs.

Five real defects were found by pointing the linter at this set, and each one
also fires on ordinary technical documentation:

1. A run of dashes under a heading (a setext underline) counted as a horizontal
   rule between sections.
2. An aligned two-column table (`match     Match a regular expression`) counted
   as a doubled word, because the pattern allowed any run of whitespace between
   the repeats rather than the single space a typing slip leaves.
3. An emoticon (`plus one :-)`) counted as a space before punctuation.
4. ASCII `--` was counted by **both** `em_dash` and `dash_style`: one construct,
   two categories, two score contributions.
5. `rule_of_three` counted every *copy* of a repeated phrase. One type signature
   ("string, bytes, or bytearray") appearing in twenty `pathlib` docstrings was
   twenty findings, which punishes precisely the terminology consistency
   principle 6 asks for. Triads are now counted distinct, and one tricolon no
   longer fires at all: principle 2 says a tricolon in moderation is fine, so the
   tell is two or more.

Two further calibrations came out of the same sweep. Repeated n-grams are a
*rate*, so the minimum count now scales with document length instead of holding
at four for a 300-word note and a 4,000-word reference alike; and a run of one
dash convention above five occurrences is reported once, as the single
find-and-replace it is, rather than charged per occurrence.

**What this set cannot tell you.** API reference is its own genre: identifiers,
aligned tables, terse imperative fragments, deliberate repetition. A score here
is not comparable to a score on report prose, and the gate reflects that, with a
median ceiling of 12.0, a worst-case ceiling of 26.0, and a cap on how much of
the total any one category may own. Read a breach as "go and look at the new
findings", not as "the linter regressed".

### Hard negatives: ESL false positives and the over-corrected costume

| subset | metric | value | pre-v0.5 |
|---|---|---|---|
| `esl_formal` (10, labeled human) | ESL-only FPR | **0.000** | 0.300 |
| `over_corrected` (10, held out) | flagged-rate | **1.000** | 1.000 |
| `over_corrected` | trip a costume category | **1.000** | 1.000 |

The ESL subset now clears entirely at the default boundary, which was the single
most important false-positive result to fix: careful non-native and formal-human
writing is the population commercial detectors demonstrably over-flag, and a tool
that repeats that failure is worse than no tool. The over-corrected class is still
caught completely, which is the other half of the requirement, the linter must
not reward swapping the AI costume for the anti-AI costume.

### Ablation: which categories drive the scores

Zeroing any single category's weight leaves the legacy AUC at 1.000: the
caricature margin is too wide for one category to be load-bearing for
*separation*. The informative measure is each category's share of the score mass,
reported for both AI classes:

| category | caricature `ai/` share | realistic `ai_modern/` share |
|---|---|---|
| participial_tail | 0.0% | **21.1%** |
| sentence_shape | 1.0% | **16.9%** |
| paragraph_uniformity | 1.2% | **10.2%** |
| burstiness | 2.3% | **9.0%** |
| cleft | 0.0% | **8.5%** |
| assistant_shape | 1.6% | 7.0% |
| rule_of_three | 10.3% | 5.1% |
| negative_listing | 1.9% | 4.5% |
| bold_bullets | 9.2% | 4.2% |
| jargon | 5.7% | 3.1% |
| antithesis | 3.6% | 3.0% |
| filler | **12.1%** | 0.0% |
| meta_commentary | **11.5%** | 0.0% |
| puffery | **8.5%** | 0.0% |

Read the two columns side by side. The word-level categories that dominate the
caricature score, `filler`, `meta_commentary`, `puffery`, contribute **nothing at
all** to catching prose a current model writes, because current models do not
write that way any more. What reaches the modern class is syntax and shape. The
two largest contributors, `participial_tail` and `cleft`, did not exist before
v0.6 and together account for 30% of the modern score mass: they are the
", making it easier to…" tail and the "What actually mattered was…" cleft, and
they are what a model produces once the obvious diction is edited out. Rhythm and
shape (`sentence_shape`, `paragraph_uniformity`, `burstiness`, `assistant_shape`)
supply another 43%.

This is the empirical justification for the skill's edit order. A humanizer pass
that starts with vocabulary is optimizing against text nobody was fooled by.

### Content architecture: restatement, section balance, depth drift

The corpus above cannot measure these three checks. Every sample in it is one
short section, and the checks read a document's sections against each other. So
they have their own script, `eval/structure_eval.py`, and their own calibration.

**Positives.** `eval/structure/ai/` holds six multi-section documents in the shape
an agent produces for a design doc, a postmortem, a README, an options analysis, a
migration plan and an onboarding guide. Each is labeled with the finding it
carries, and all six are caught. They are authored like the rest of the corpus, so
this shows the checks see what they describe. It says nothing about how often
agents write this way.

**In-repo negatives.** The human and ESL corpus classes, the project's own README,
CONTRIBUTING, CHANGELOG and EVAL, the skill and its references, and every shipped
"after" example: 64 files, none fire. CI runs both sets with `--check`.

**Independent negatives.** The in-repo set is short or written here, so the
thresholds were set against long markdown nobody wrote for this project: every
file of 400 to 6,000 words with four or more headings under seven local trees.
None of it can be vendored, so the script takes a path, and anyone can repeat the
sweep on their own machine with `--human-dir`.

| Tree | Files | Fired | restatement | section_balance | depth_drift |
|---|---|---|---|---|---|
| Homebrew Cellar (formula READMEs and manuals) | 250 | 1 | 1 | 0 | 0 |
| Homebrew docs | 46 | 0 | 0 | 0 | 0 |
| Homebrew vendored Ruby gems | 28 | 0 | 0 | 0 | 0 |
| global npm packages | 80 | 0 | 0 | 0 | 0 |
| npx package cache | 72 | 2 | 2 | 0 | 0 |
| Rust crates (cargo registry) | 387 | 2 | 2 | 0 | 0 |
| Python site-packages | 6 | 1 | 0 | 0 | 1 |
| **Total** | **869** | **6 (0.7%)** | **5** | **0** | **1** |

Two of the six hits are the same concatenated third-party LICENSE file in two npx
caches. One is a generated permissions reference. The depth-drift hit is a mypyc
developer guide whose "Key Differences from Python" section is a conceptual
discussion beside a dense implementation section, which is the closest a human
document came to the pattern.

The first thresholds fired on 35% of these files. Four rules closed most of the
gap, and each describes a real difference between reference docs and agent output:

- a short section with a link, a command, code or a list is a pointer, not a stub;
- restatement ignores verbatim copies, entries under headings that name code, and
  anything under a version or year heading;
- restatement needs 2.5 pairs per thousand words, so a 3,000-word manual that
  repeats one note is not a 400-word design doc that says four things twice;
- a hollow section has to be written in abstract benefit words ("ensures",
  "reliability", "flexibility"), not merely lack numbers.

Framing share also requires a recap section among the framing (or over half the
words), after a Rust README with a long Motivation section and no summary fired.

**Scope.** The main eval numbers above did not move, because nothing in the main
corpus has sections. The recall claim rests on six authored documents. The
false-positive claim rests on 869 real ones, all of them technical documentation,
none of them business or academic prose.

## Limitations (read this before trusting any number above)

- **The corpus is small and authored.** 113 hand-written samples is a calibration
  set, not a benchmark. `ai_modern/` is a genuine improvement over `ai/`, it was
  written in the register a current model uses rather than to exhibit the tells the
  linter scores, but it was still written by hand for this eval and not sampled
  from real model output. n=20 also means the 0.938 AUC has a wide interval that
  this file does not bootstrap. Treat it as "clearly worse than 1.000 and clearly
  better than chance", not as a point estimate.
- **Some of the corpus post-dates the checks it exercises.** The v0.6 syntactic
  checks and eight of the twenty `ai_modern/` files were written in the same pass.
  The v0.8 checks carry the opposite risk and it is worth naming: they were chosen
  by measuring candidate signals across this corpus and keeping the ones that
  separated, which is fitting to the corpus. The guards against it are that no
  threshold was tuned to cross a specific file over the boundary, that the
  out-of-repo human baseline (`eval/human_baseline.py`) is unchanged at a worst
  score of 17.7, and that three candidate signals with clean separation here were
  rejected on principle rather than kept. Those rejections are the honest part of
  the exercise; see `references/competitive-landscape.md`.
  That is a real circularity risk and it is why the two numbers to weigh are the
  ones the new files cannot inflate: the human false-positive rate (0.000 on 39
  files, five of them also new) and the behavior on the eight *pre-existing*
  `ai_modern/` files, where recall went from **9/12 to 11/12** with no threshold
  change: `m07_casual_blog.md` and `m12_casual_review.md` are now caught, and only
  `m09_creative_scene.md` still clears. Independently authored samples remain the
  highest-value contribution this directory could receive.
- **No sample of real production text from a model.** `eval/human_baseline.py`
  now supplies an independent human negative set (stdlib docstrings, see above),
  but there is still no sample of real unedited model output across many prompts
  and models. The right benchmark needs both halves. Contributions of
  either kind, with provenance, are the single highest-value thing anyone could add
  to this directory.
- **The linter is a floor, not ground truth.** It catches cheap, regex-able
  surface features. It cannot see vacuity, a missing stance, terminology drift, or
  fabricated facts. Three of the twenty `ai_modern` files score 0.0–3.0 and are
  machine-written; what gives them away is that their concrete details are
  plausible and unowned, and no regex reads that. A document can score 0 and still
  be obviously machine-written to a careful reader. The rubric below is for exactly
  that read.
- **Detector signals are now measured locally, but with small open models.**
  `eval/detector_local.py` runs real GPT-2 token surprisal and a real supervised
  classifier (see the section above), so the repo no longer relies solely on
  third-party figures. Two limits on those numbers: GPT-2 is 124M parameters, and a
  small proxy model's perplexity is a coarse stand-in for a large one's, so the
  *direction* of travel is trustworthy and the absolute values are not. And no
  commercial detector has been queried from here; `verify_detector.py` can do it but
  needs a key the maintainer would have to hold. Contributions of commercial-API
  runs, with provenance, remain the most valuable thing this directory could
  receive.
- **External detectors are biased, so do not tune to them.** Liang et al. (2023,
  *Patterns*) showed GPT detectors systematically misclassify non-native-English
  writing as AI-generated, which is why the ESL FPR is gated here at 0.000.
  Maximizing any single detector's score optimizes for that detector's blind spots,
  not for good writing, and the humanizer market is a demonstration of where that
  ends: the vendor with the strongest published numbers reports that *the more
  fluent a humanizer's output, the more reliably it is detected*, because the tools
  that evade do it by damaging the text.
- **Threshold is corpus-dependent.** The swept "best" threshold of 29.8 is an
  artifact of how saturated the caricature samples are, and it would miss 11 of the
  12 realistic files. Do not port it. The product default of 5.0 is the right
  starting point for real documents; treat 5–15 as "look again", not "guilty".
- **The register mutes are calibrated on this corpus only.** One was outright
  wrong until v0.5: `casual` and `creative` muted the burstiness check on the
  grounds that they permit fragments, but the check fires only on *low* variance
  and fragments raise it, so those registers had no rhythm check at all. There may
  be more of that kind of error in the mute table; it is asserted by test now
  (`rhythm_never_muted_*`) but only for the rhythm checks.

## Measured against real detectors (locally, with open models)

Everything above measures the regex floor. This section measures what a *detector*
does. Reproduce with:

```bash
python3 -m venv .detvenv
.detvenv/bin/pip install torch transformers      # ~1.5GB, dev-only, never in CI
make detector-local                              # -> eval/detector_local_results.json
make detector-check                              # regression gate on the panel
```

Committed numbers use a gpt2-large observer. `HV_CAUSAL_MODEL=gpt2` runs ~5x faster;
it was run both ways and every qualitative conclusion below holds at both scales.

### The panel, and why one detector is excluded from every count

| detector | family | notes |
|---|---|---|
| perplexity (gpt2-large) | statistical | real per-token `-log P(token \| context)` |
| Binoculars (gpt2-large / gpt2) | statistical | observer perplexity over cross-perplexity; strongest published zero-shot method |
| `roberta-base-openai-detector` | supervised, 2019 | trained on GPT-2 output |
| `Hello-SimpleAI/chatgpt-detector-roberta` | supervised, 2023 | trained on real ChatGPT output |
| `fakespot-ai/roberta-base-ai-text-detection-v1` | supervised | the discriminating one, see below |
| `andreas122001/roberta-mixed-detector` | supervised | **EXCLUDED** |

Calibration on the human class comes first, because a detector that cannot pass
human writing tells you nothing about a rewrite:

| detector | human false-positive rate | verdict |
|---|---|---|
| roberta_openai_2019 | 0.0% (0 of 34) | usable |
| chatgpt_detector_2023 | 0.0% (0 of 34) | usable |
| fakespot | 0.0% (0 of 34) | usable |
| mixed_detector | **100.0% (34 of 34)** | excluded |

`mixed_detector` returns p(AI) = 1.000 for every document in the corpus, human and
machine alike. Counting it would have made the headline read "12 of 12 still
flagged" while meaning nothing at all. `calibrate()` measures this and drops any
classifier above `MAX_HUMAN_FPR` (0.20), printing which and why. That guard is the
most load-bearing thing in this section, and it is the reason to distrust any
humanizer or detector benchmark that does not report a false-positive rate.

Among the three that pass, `fakespot` is genuinely discriminating: **0 of 34** human
files, **24 of 24** caricature-AI files, 3 of 12 realistic modern-AI files, 1 of 10
over-corrected. It is the detector that makes the before/after result below mean
something, because it demonstrably catches machine text when machine text is there.

### By class

| class | n | perplexity | Binoculars | flagged by a usable classifier |
|---|---|---|---|---|
| human | 34 | 29.5 | 0.780 | **0 of 34** |
| `ai` (2023 caricature) | 24 | **12.1** | 0.705 | 24 of 24 |
| `ai_modern` (realistic) | 12 | 30.1 | 0.794 | 3 of 12 |
| `over_corrected` (costume) | 10 | **58.0** | 0.788 | 1 of 10 |

**Realistic model output is nearly indistinguishable from human.** Perplexity 30.1
against a human 29.5. Binoculars 0.794 against 0.780. A supervised classifier that
catches 24 of 24 of the 2023-era caricature catches 3 of 12 of it. The audit's central
finding reproduces at the detector level, across two families, including a classifier
trained on real ChatGPT output. The distributional tells are largely gone already;
what remains is structural, which is what this skill fixes.

**The anti-AI costume has the highest perplexity of any class**, 58.0 against a human
29.5, because forced lowercase and staccato fragments are unpredictable. Perplexity is
gameable by making prose worse, which is the humanizer failure mode as a number.

### Does the rewrite move a real detector?

All 12 realistic modern-AI samples, before and after the skill's procedure, paired on
identical claims:

| file | perplexity | multiplier | Binoculars | says AI: before → after |
|---|---|---|---|---|
| m04_academic_abstract | 18.5 → 84.4 | **x4.57** | 0.710 → 1.017 | **fakespot → no** |
| m12_casual_review | 23.7 → 74.1 | **x3.12** | 0.793 → 1.042 | no → no |
| m05_marketing_page | 30.3 → 80.5 | **x2.66** | 0.796 → 0.981 | no → no |
| m08_technical_bulleted | 35.5 → 93.9 | **x2.64** | 0.813 → 0.984 | no → no |
| m11_tutorial_steps | 25.0 → 65.8 | **x2.63** | 0.789 → 0.958 | **fakespot → no** |
| m06_email_update | 30.0 → 74.1 | **x2.47** | 0.827 → 1.015 | no → no |
| m02_business_review | 39.1 → 95.6 | **x2.44** | 0.859 → 0.998 | no → no |
| m01_technical_tradeoff | 50.8 → 116.1 | **x2.29** | 0.819 → 1.002 | no → no |
| m03_technical_scaffolded | 40.7 → 89.2 | **x2.19** | 0.826 → 1.008 | no → no |
| m10_business_proposal | 37.9 → 81.8 | **x2.16** | 0.783 → 0.949 | no → no |
| m09_creative_scene | 18.9 → 39.1 | **x2.07** | 0.701 → 0.820 | **chatgpt, fakespot → no** |
| m07_casual_blog | 22.9 → 45.2 | **x1.97** | 0.755 → 0.923 | no → no |

**Flagged by a usable classifier: 3 of 12 before, 0 of 12 after.** Median perplexity
multiplier **x2.46**, with all twelve rising, and Binoculars rising in all twelve. The
three that were caught include the one a *ChatGPT-trained* classifier caught, and none
survives the rewrite.

The seven shipped example pairs, same measurement: **4 of 7 flagged before, 0 of 7
after**, median multiplier x2.21.

Across both sets: **7 of 19 documents flagged before, 0 of 19 after.**

The `over-corrected` pair is the control that shows the tool is improving writing
rather than chasing the metric. Its "before" is the anti-AI costume, already at
perplexity 113.7, and the rewrite brings it *down* to 60.6. A tool optimizing
perplexity would have banked the 113.7 and reported a better average.

### What this does and does not establish

It establishes that for five open detectors spanning both families, including a
supervised classifier that catches 24 of 24 caricature-AI files and 0 of 39 human
files, no rewritten document in this corpus is classified as AI.

It does not establish undetectability, and nothing could:

- **No commercial API was queried from this repository.** `verify_detector.py` can
  call GPTZero, Originality.ai, Sapling, or Winston, but that needs a key the
  maintainer would have to hold.
- **A classifier trained specifically on humanizer output** is reported by its vendor
  at ~97% accuracy on rewritten text. That figure is about other tools' output and has
  not been tested either way against this one.
- **The models here are small.** gpt2-large is 774M parameters, so ordering and
  direction of travel are the trustworthy parts, not absolute values.
- **n is 19 documents from one author.** A real benchmark needs many models, many
  prompts, and many human writers.
- **Three "after" texts exceed perplexity 90**, well above the human median of 29.5.
  Pushing far past the human centre is not self-evidently good, and if a future pass
  approaches the 113.7 costume that is a signal it has started optimizing the metric
  instead of the prose.

### A correction to the previous pass

An earlier run of this harness reported that Binoculars catches the anti-AI costume,
scoring `over_corrected` at 0.780 against a human 0.891. That used a gpt2/distilgpt2
pair. With gpt2-large/gpt2 the ordering vanishes: 0.788 against 0.780. The finding was
an artifact of the model pair. It is corrected here, and the general lesson is worth
keeping: treat a single Binoculars ranking as pair-dependent until it replicates.

## Register inference, measured against the labels

The corpus register tags are ground truth for a second question the harness can
answer: can the tool guess the register from the content? It matters because every
register mutes a different set of checks, so guessing wrong changes the score.

| | correct on 113 files |
|---|---|
| old behavior (always `technical`) | 21 (18.6%) |
| `--register auto` | **93 (82.3%)** |

Per register: email 13/13, academic 14/15, technical 19/21, business 14/19,
casual 12/17, marketing 10/13, creative 9/11, tutorial 2/4.

The asymmetry of the errors matters more than the accuracy. Of 20 misses, **11 fall
back to `technical`**, the strictest profile and the previous default, so those
over-flag rather than excuse. Only **9 of 113** pick a more permissive register than
the truth, which is the direction that could hide a real tell (`creative` mutes the
dash checks, `casual` mutes the costume check). Two tests gate both properties: the
accuracy must stay above 75% and clearly beat always-technical, and the misses must
keep skewing safe.

**82% is a plateau, not a waypoint.** A grid over the two decision thresholds and
the weights of the most promiscuous cues tops out within a point of this value.
The residual errors are documents that genuinely read as two registers: a
technical blog post, a how-to about a database, a business memo written as a
personal narrative. That is why `--register` given explicitly always wins and why
the skill tells the model to prefer its own judgment over the guess.

Three tuning decisions came from measuring rather than intuition, and each fixed a
real error:

- **A minimum length.** "Hello." matches the email greeting cue and was inferred as
  email with full confidence. Under 30 words there is no register signal, so there is
  no inference.
- **A proportional margin, not an absolute one.** Requiring the winner to lead by two
  points rejected almost every correct guess at these score magnitudes, which is why
  the first version scored 51%.
- **First-person density only reinforces, never decides.** Treating "I" as a casual
  cue on its own pulled the whole `esl_formal` subset into `casual`, because careful
  non-native business and academic writing uses it freely. That is the same
  population detectors already over-flag, and the same failure this repo exists to
  avoid repeating.

## Negative result: a frequency table is not a perplexity proxy

Recorded so nobody spends a day on it twice. The obvious way to approximate what
statistical detectors measure, without shipping a model, is to bundle a
word-frequency table and treat "token in the high-frequency band" as "low-surprisal
token". Two metrics follow: the fraction of common-band tokens, and the variance of
that fraction across sentences, the latter standing in for the surprisal variance
that DetectGPT-family detectors actually key on.

It was built with a ~600-word high-frequency list and measured on this corpus
before being wired in. It does not work:

| class | common-band token ratio (median) | cross-sentence CoV (median) |
|---|---|---|
| human (34) | 0.664 | 0.182 |
| ai_modern (12) | 0.611 | 0.176 |
| ai, caricature (24) | 0.539 | 0.273 |

The ratio separates in the **wrong direction**, and by a margin that would produce
confident false accusations: the human samples use *more* common words, because the
AI samples are full of latinate filler ("comprehensive", "multifaceted",
"using") which is rarer vocabulary, not commoner. The cross-sentence variance
does not separate human from realistic AI at all, 0.182 against 0.176.

The reason is not a bad word list, and a better one will not fix it. Surprisal is
`P(token | preceding context)`, and a context-free frequency band discards exactly
the conditioning that makes perplexity discriminative. "The cat sat on the mat" and
"the mat sat on the cat" have identical unigram statistics and very different
surprisal. Approximating a conditional quantity with a marginal one throws away the
signal.

The module was deleted rather than shipped. A metric that does not separate would
have added noise and false confidence, which is the failure this whole audit was
about. If someone wants a real surprisal measurement here it needs an actual model,
which means abandoning the zero-dependency promise. The honest alternative already
shipped is the verification gate: ask a detector that *does* have a model, and treat
its answer as the stopping condition.

## Human-evaluation rubric

The linter cannot judge substance. When a skeptical human reviews a draft (the
real test), score each axis 1–5 (1 = unmistakably machine, 5 = unmistakably a
competent human with a point):

0. **Shape.** Would a person have formatted this document this way? A heading
   every eighty words, a third of the lines bulleted, bold on every key term, a
   closing "Key takeaways" section: that is the shape of a chat reply, and it is
   the loudest signal in the document. Check it before you read a sentence.
1. **Substance.** Does each paragraph make a specific, falsifiable claim, or
   does it restate the topic in fancier words? Could you delete a paragraph
   without losing information? (Machine drafts survive deletion.)
2. **Rhythm / burstiness.** Do sentence and paragraph lengths vary like real
   speech, with short punches between long sentences, or is everything the same
   medium length? Read it aloud; monotony is the tell. Count the sentences under
   eight words, if there are none in a page of prose, that is the answer.
3. **Stance.** Does the writer commit to a position and accept a cost, or hedge
   everything ("it depends", "there are pros and cons") to stay safe? A real
   author risks being wrong.
4. **Register fit.** Does the voice match the genre, a postmortem sounds
   tired and specific, marketing addresses "you", an abstract is precise and
   bounded, or is it the same flat all-purpose corporate gloss regardless of
   context?
5. **Sourcing / specificity.** Are the concrete details (numbers, names, dates,
   error codes) real and checkable, or are they vague gestures ("studies show",
   "many experts", "significant improvements")? Flag any specific that looks
   invented; the skill's protocol is to mark `[SOURCE NEEDED]`, never fabricate.
6. **Ownership.** Is there anything here only this author could have written, a
   name, a date, a thing that went wrong, an unhedged preference? If every
   specific could have come from a search summary, the text is unowned, and
   unowned is how the three `ai_modern` files that score 0.0 give themselves away.

A draft that scores `clean` on the linter and below 3 on substance, on stance, or
on ownership has passed the floor and failed the real test. Weight those three
most heavily. They are what the linter is structurally blind to.
