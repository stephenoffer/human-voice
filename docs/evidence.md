# Why it works, and how we know

[Docs home](README.md) · [Getting started](getting-started.md) · [Install](install.md) · [Usage](usage.md) · [Examples](examples.md) · **Evidence** · [Comparison](comparison.md)

## What detectors respond to

Detectors don't track machine-ness. They track the artifacts of instruction
tuning. Base models never went through it, and commercial detectors classify
their output as human more than 96% of the time. The artifacts the research names
are a preference for markdown formatting, response-length and structural
conventions, and sycophancy.

This repo's own corpus says the same thing from the other side. The categories
that catch 2023-era slop are `filler` and `meta_commentary`, both word-level, and
they contribute 0% to catching prose a current model writes. Syntax and shape
catch that instead: `participial_tail` (the ", making it easier to…" tail) at
21%, `sentence_shape` at 17%, `paragraph_uniformity` at 10%, `burstiness` at 9%,
and `cleft` ("What actually mattered was…") at 8%.

So the skill fixes shape and syntax first, then rhythm, then substance. Word
choice is the last and shallowest pass. Sources and the full landscape:
[`references/what-detectors-see.md`](../skills/human-voice/references/what-detectors-see.md).
The measured breakdown: [`eval/EVAL.md`](../eval/EVAL.md).

## Checking instead of promising

Nobody can promise a text is undetectable. The skill checks instead. Point it at
a detector and the rewrite gets a hard stopping condition:

```bash
export GPTZERO_API_KEY=...     # or ORIGINALITY / SAPLING / WINSTON
python3 skills/human-voice/scripts/verify_detector.py --before draft.md rewrite.md
```

The gate exits 1 while the detector still flags the text, 0 when it clears, and
2 when no detector is configured. Exit 2 is not a pass, and the audit has to say
so. The skill keeps looping from the rewrite while the gate returns 1. Against
the detector you care about, you get an exit code you can check rather than a
claim in a README.

## A local detector panel

`make detector-local` runs five detectors on open models, with no API key and
nothing leaving the machine. Two are statistical (perplexity and Binoculars). Three
are supervised classifiers.

Calibration comes first, because a detector that can't pass human writing says
nothing about a rewrite. One candidate labels 34 of 34 hand-written human files
as AI at p(AI)=1.000, so every count excludes it. Among the classifiers that
pass, one discriminates cleanly: 0 of 34 human files flagged, 24 of 24
caricature-AI files flagged.

Against that panel, the 12 realistic modern-AI samples put through the skill:

| | before | after |
|---|---|---|
| flagged by a usable classifier | 3 of 12 | 0 of 12 |
| median perplexity multiplier | n/a | x2.46 (all 12 rose) |
| Binoculars | n/a | rose in all 12 |

The seven shipped example pairs went from 4 of 7 flagged to 0 of 7. Across both
sets that makes 7 of 19 documents flagged before and 0 of 19 after. "Flagged"
means each classifier's own argmax label, not a threshold anyone picked.

One control makes the rest believable. The anti-AI costume pair already scores
perplexity 113.7, higher than real human writing, and the rewrite brings it down
to 60.6. A tool chasing the metric would have kept the 113.7.

The same run turned up the finding that matters more. Realistic model output is
already close to human on the distributional numbers: perplexity 30.1 against
29.5, Binoculars 0.794 against 0.780. The classifier that catches 24 of 24
caricature files catches only 3 of 12 of it. The distributional tells are gone.
The structural ones remain, and those are the ones this skill fixes.

## Limits

None of this establishes undetectability, and nothing could. No commercial API
was queried from this repo. One vendor reports ~97% accuracy for a classifier
trained on humanizer output, but that figure describes other tools' output and
hasn't been tested against this one either way. The models here are small, so
trust direction over absolute values. The sample is 19 documents from one author.
Set a key and run the gate to get your own number on your own text.

The loop has two limits built in. It is capped, and it stops early when two
passes can't move the detector without damaging the prose. A `clear` is evidence
about one detector at one threshold.
