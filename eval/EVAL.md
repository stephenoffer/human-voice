# Evaluating the human-voice linter floor

This directory holds an offline, dependency-free evaluation harness for the
deterministic linter at `skills/human-voice/scripts/detect_ai_prose.py`. It
measures how well the linter's single floor score separates human-voiced prose
from classic AI-slop, where each category contributes, and provides a scaffold
for checking rewrites against an external detector.

All numbers below are MEASURED. Reproduce (or regression-gate) them:

```bash
python3 eval/run_eval.py            # metrics + per-file scores -> eval/results.json
python3 eval/run_eval.py --check    # fail (exit 1) if metrics drift from the committed results.json
python3 eval/ablation.py            # per-category contribution -> eval/ablation_results.json
python3 eval/ablation.py --check    # fail if the baseline separation drifts
python3 eval/detector_harness.py    # offline by default; needs an API key to call a detector
```

Shared logic (loaders, metrics, bootstrap CIs, the regression comparator, corpus
validation) lives in `eval/lib.py`; the three scripts are thin consumers. The
committed `results.json` / `ablation_results.json` are golden baselines: `--check`
recomputes in memory and fails on drift, so a metric change must be regenerated
and reviewed in the git diff rather than silently overwritten in CI.

## Methodology

- **Corpus**: 68 short Markdown files authored by hand for this eval
  (`eval/corpus/`). The binary classifier set is **58 files** — 34 labeled
  `human` (including a 10-file ESL/formal-human hard-negative subset, see below)
  and 24 labeled `ai` — balanced across technical, business, marketing, academic,
  casual, creative, and email registers (every register has both classes). A
  further **10 files** form the held-out `over_corrected` class (the "anti-AI
  costume"), excluded from the binary AUC and scored on their own. Labels,
  register tags, and group tags live in `eval/corpus/LABELS.json`;
  `eval/lib.py:validate_corpus` enforces that every file is labeled and every
  register is real. No external or copyrighted text was used. The `human` samples
  read like a person wrote them (varied rhythm, a real stance, concrete detail);
  the `ai` samples carry the machine signature (filler, rule-of-three,
  bold-bullet listicles, hedging, puffery, meta-commentary, aidiolect phrases,
  uniform rhythm). The two `creative` AI samples lean on those tells rather than
  em-dashes, since the creative register mutes the dash checks.
- **Hard negatives** (the FPR stress test). Two subsets probe the failure modes
  that matter most. `esl_formal/` (10 files, labeled `human`, group `esl`) are
  careful non-native and formal-but-human samples — the population GPT detectors
  demonstrably over-flag — and they stay in the binary set so they count against
  the human FPR. `over_corrected/` (10 files, label `over_corrected`) is text in
  the anti-AI costume (forced lowercase, sprinkled slang, staccato fragments);
  these *should* be flagged, so they are held out of the AUC and reported as a
  recall, not counted as human false positives. `lib.subset_fpr` reports the
  ESL-only FPR; `lib.costume_eval` reports the costume recall.
- **Scoring**: each file is scored by importing the linter module and calling
  `dap.lint(text, register, dialect=None, patterns)`, using the register from
  the label file. The floor score is *weighted tells per 1000 words*.
- **Classifier**: the floor score is treated as a 1-D binary classifier,
  predicting `ai` when `score >= threshold` (positive class = AI). We report two
  thresholds: the linter's default "watch" boundary (5.0, where `clean` ends)
  and a swept best-F1 threshold. Thresholds are swept over midpoints between
  observed scores.
- **Separation**: ROC AUC is computed as the rank statistic
  P(score_ai > score_human) with ties counted as 0.5.
- **Ablation**: for each category, the corpus is re-scored with that category's
  weight forced to 0, and we recompute AUC and best-F1 accuracy. Because the
  classes separate with a large margin, we also report each category's share of
  the total AI-subset floor score ("AIshare") as a more discriminating measure
  of which tells drive the AI scores.
- **Calibration anchor**: `eval/tests/test_calibration.py` asserts the category
  weights keep a strong rank (Spearman) correlation with the ranking of tells by
  how often the ~90k-post Reddit study found readers *cite* them — so a future
  weight edit that drifts from the evidence fails loudly. See
  `skills/human-voice/references/cited-vs-matched.md`.
- **Confidence intervals**: `run_eval.py` reports 95% stratified percentile
  bootstrap CIs (2000 resamples, fixed seed 1729 so the bounds are reproducible
  and gate-able) for ROC AUC, F1@5.0, and the human-subset FPR. With n=58 these
  quantify resampling variance *within the authored set* — not sampling intervals
  over real-world text.

## Measured results

### Score separation

The two classes are cleanly separated on this corpus:

- human floor scores (all 34, incl. ESL subset): min **0.0**, max **25.4**
- AI floor scores: min **95.4**, max **364.4**
- **ROC AUC = 1.000** (perfect rank separation; every AI file outscores every
  human file; 95% bootstrap CI [1.000, 1.000]).

A handful of human files score in the `watch` band (academic abstract 25.4, the
rest single digits); none reaches the AI range. Every AI file lands in
`strong-tell` (>= 15) by a wide margin.

### Classifier metrics at the default "watch" boundary (threshold 5.0)

| metric | value |
|---|---|
| precision | **0.706** |
| recall | **1.000** |
| F1 | **0.828** |
| accuracy | **0.828** |
| human-subset false-positive rate | **0.294** (10 of 34 human files flagged; 95% CI [0.147, 0.471]) |

Confusion: tp=24, fp=10, tn=24, fn=0.

The default boundary catches every AI sample (recall 1.0) but flags 10 of 34
genuine human files — all in the `watch` band (5–15), none in `strong-tell`.
This is the deliberate cost of a low threshold, and it is *higher by design* than
the old 36-file corpus: the human set now includes 10 ESL/formal hard negatives
chosen to sit near the boundary. The `clean` band is conservative and treats a
`watch`-band human document as "worth a second look", never as proof of AI
authorship. The wide FPR CI is the point — this n cannot pin the rate precisely.

### Classifier metrics at the swept best-F1 threshold (60.4)

| metric | value |
|---|---|
| precision | **1.000** |
| recall | **1.000** |
| F1 | **1.000** |
| accuracy | **1.000** |
| human-subset false-positive rate | **0.000** |

Confusion: tp=24, fp=0, tn=34, fn=0.

Any threshold between 25.4 and 95.4 separates this corpus perfectly. That the
best threshold sits far above the product's `clean` boundary (5) reflects how
saturated these AI samples are, not that the default is mis-set for real use. The
default is tuned to warn early, accepting human `watch` flags in exchange for
never missing an obvious machine draft.

### Hard negatives: ESL false positives and the over-corrected costume

The two stress subsets behave as intended (threshold 5.0):

| subset | metric | value |
|---|---|---|
| `esl_formal` (10, labeled human) | ESL-only FPR | **0.300** (3 of 10, all in `watch` at 7–8; none `strong-tell`) |
| `over_corrected` (10, held out) | flagged-rate | **1.000** (10 of 10) |
| `over_corrected` | trip a costume category | **1.000** (10 of 10 fire `over_correction`/`internet_tells`) |

The ESL false positives are all low-`watch` (7.8 max), i.e. "look again", not
"guilty" — and every one of them clears at the swept threshold (ESL FPR 0 there).
The over-corrected class is caught completely, which is the point: the linter
must not reward swapping the AI costume for the anti-AI costume.

### Ablation: which categories drive the AI scores

Zeroing any single category's weight leaves AUC at 1.000 and best-F1 accuracy at
1.000 — the margin is wide enough that no one category is load-bearing for
*separation*. The more useful signal is each category's share of the total
AI-subset floor score:

| rank | category | AI score share |
|---|---|---|
| 1 | filler | 19.9% |
| 2 | bold_bullets | 14.1% |
| 3 | meta_commentary | 10.6% |
| 4 | aidiolect | 7.7% |
| 5 | rule_of_three | 7.1% |
| 6 | puffery | 6.1% |
| 7 | jargon | 5.5% |
| 8 | soft_filler | 3.8% |

The new `aidiolect` phrase category is already the 4th-largest driver, and the
generic diction moved to `soft_filler` now contributes a modest 3.8% (down from
its old weight-1.0 share inside `filler`) — exactly the rebalancing the v0.4
recalibration intended. Filler and bold-bullet listicles still lead, matching the
skill's theory of what gives AI away.

## Limitations (read this before trusting any number above)

- **The corpus is small and authored.** 68 hand-written samples is a
  calibration set, not a benchmark. The AI samples were written to exhibit the
  tells the linter scores, and the human samples to avoid them, so the perfect
  AUC measures *internal consistency* — does the linter fire on what it claims
  to fire on — not real-world detection accuracy. Real AI text (especially
  carefully prompted or already-edited text) and real human text (especially
  formal corporate or non-native-English writing) will overlap far more.
- **The linter is a floor, not ground truth.** It catches cheap, regex-able
  surface features. It cannot see vacuity, a missing stance, terminology drift,
  or fabricated facts. A document can score 0 and still be obviously machine-
  written to a careful reader. The real test is a skeptical human read; the
  rubric below is for exactly that.
- **External detectors are biased.** The `detector_harness.py` scaffold can call
  a commercial detector (GPTZero etc.), but such detectors are not ground truth
  either. Liang et al. (2023, *Patterns*) showed GPT detectors systematically
  misclassify non-native-English writing as AI-generated. Do not tune the skill
  to maximize any single detector's score; that optimizes for the detector's
  blind spots, not for good writing.
- **Threshold is corpus-dependent.** The "best" threshold of ~46 is an artifact
  of how saturated these AI samples are. Do not port it to production. The
  product default of 5.0 is the right starting point for real documents; treat
  scores between 5 and 15 as "look again", not "guilty".

## Human-evaluation rubric

The linter cannot judge substance. When a skeptical human reviews a draft (the
real test), score each axis 1–5 (1 = unmistakably machine, 5 = unmistakably a
competent human with a point):

1. **Substance.** Does each paragraph make a specific, falsifiable claim, or
   does it restate the topic in fancier words? Could you delete a paragraph
   without losing information? (Machine drafts survive deletion.)
2. **Rhythm / burstiness.** Do sentence and paragraph lengths vary like real
   speech, with short punches between long sentences, or is everything the same
   medium length? Read it aloud; monotony is the tell.
3. **Stance.** Does the writer commit to a position and accept a cost, or hedge
   everything ("it depends", "there are pros and cons") to stay safe? A real
   author risks being wrong.
4. **Register fit.** Does the voice match the genre — a postmortem sounds
   tired and specific, marketing addresses "you", an abstract is precise and
   bounded — or is it the same flat all-purpose corporate gloss regardless of
   context?
5. **Sourcing / specificity.** Are the concrete details (numbers, names, dates,
   error codes) real and checkable, or are they vague gestures ("studies show",
   "many experts", "significant improvements")? Flag any specific that looks
   invented; the skill's protocol is to mark `[SOURCE NEEDED]`, never fabricate.

A draft that scores `clean` on the linter but below 3 on substance or stance has
passed the floor and failed the real test. Weight axes 1 and 3 most heavily;
they are what the linter is structurally blind to.
