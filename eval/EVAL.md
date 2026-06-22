# Evaluating the human-voice linter floor

This directory holds an offline, dependency-free evaluation harness for the
deterministic linter at `skills/human-voice/scripts/detect_ai_prose.py`. It
measures how well the linter's single floor score separates human-voiced prose
from classic AI-slop, where each category contributes, and provides a scaffold
for checking rewrites against an external detector.

All numbers below are MEASURED. Reproduce them:

```bash
python3 eval/run_eval.py      # classifier metrics + per-file scores -> eval/results.json
python3 eval/ablation.py      # per-category contribution -> eval/ablation_results.json
python3 eval/detector_harness.py   # offline by default; needs an API key to call a detector
```

## Methodology (run 2026-06-21)

- **Corpus**: 24 short Markdown files authored by hand for this eval
  (`eval/corpus/`), 12 labeled `human` and 12 labeled `ai`, spread across
  technical, marketing, casual, academic, email, and business registers. Labels
  and register tags live in `eval/corpus/LABELS.json`. No external or
  copyrighted text was used. The `human` samples were written to read like a
  person wrote them (varied sentence rhythm, a real stance, concrete detail);
  the `ai` samples were written to carry the standard machine signature (filler,
  rule-of-three, bold-bullet listicles, hedging, puffery, meta-commentary,
  uniform rhythm).
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

## Measured results

### Score separation

The two classes are cleanly separated on this corpus:

- human floor scores: min **0.0**, max **25.4**
- AI floor scores: min **55.9**, max **226.3**
- **ROC AUC = 1.000** (perfect rank separation; every AI file outscores every
  human file).

Four of the twelve human files score above 0 (academic abstract 25.4, casual
review 7.6, technical decision 7.0, casual story 6.8); the rest score 0.0. Every
AI file lands in `strong-tell` (>= 15).

### Classifier metrics at the default "watch" boundary (threshold 5.0)

| metric | value |
|---|---|
| precision | **0.750** |
| recall | **1.000** |
| F1 | **0.857** |
| accuracy | **0.833** |
| human-subset false-positive rate | **0.333** (4 of 12 human files flagged) |

Confusion: tp=12, fp=4, tn=8, fn=0.

The default boundary catches every AI sample (recall 1.0) but flags 4 of 12
genuine human files (a 33% false-positive rate on the human subset). Those four
are human academic/casual prose that legitimately uses some passive voice, a
rule-of-three, or an em-dash. This is the expected cost of a low threshold: the
linter's `clean` band is conservative and treats a `watch`-band human document
as "worth a second look", not as proof of AI authorship.

### Classifier metrics at the swept best-F1 threshold (40.65)

| metric | value |
|---|---|
| precision | **1.000** |
| recall | **1.000** |
| F1 | **1.000** |
| accuracy | **1.000** |
| human-subset false-positive rate | **0.000** |

Confusion: tp=12, fp=0, tn=12, fn=0.

Any threshold between 25.4 and 55.9 separates this corpus perfectly. The fact
that the best threshold (~40) is far above the product's `clean` boundary (5)
reflects that the AI samples here are heavily saturated with tells, not that the
default boundary is mis-set for real use. The default is deliberately tuned to
warn early, accepting human false positives in exchange for never missing an
obvious machine draft.

### Ablation: which categories drive the AI scores

Zeroing any single category's weight leaves AUC at 1.000 and best-F1 accuracy at
1.000 — the margin between the classes is so wide that no one category is
load-bearing for *separation* on this corpus. The more useful signal is each
category's share of the total AI-subset floor score:

| rank | category | AI score share |
|---|---|---|
| 1 | filler | 24.6% |
| 2 | bold_bullets | 24.5% |
| 3 | meta_commentary | 16.2% |
| 4 | rule_of_three | 10.5% |
| 5 | jargon | 5.9% |
| 6 | burstiness | 5.2% |
| 7 | puffery | 3.1% |
| 8 | em_dash | 3.1% |

Filler diction and bold-bullet listicles together account for roughly half the
AI-subset score; add meta-commentary and rule-of-three and you have ~75%. These
are exactly the structural and lexical tells the skill prioritizes, so the floor
score's composition matches the skill's stated theory of what gives AI away.

## Limitations (read this before trusting any number above)

- **The corpus is small and authored.** 24 hand-written samples is a
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
- **Threshold is corpus-dependent.** The "best" threshold of ~40 is an artifact
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
