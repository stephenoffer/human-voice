# What detectors actually see

Load this when you need to know *why* a fix matters, or when someone asks
whether the skill "beats" a detector. The short version: the thing trained
detectors respond to is not vocabulary, and it is not even "machine-ness". It is
the shape that instruction tuning puts on a model's output.

## The finding that reorders everything

Base language models (the pretrained checkpoints, before any instruction tuning or
RLHF) are classified as **human** by commercial detectors at rates above 96%.
Their instruction-tuned siblings, generating from the same weights on the same
topic, get caught. The generator is equally "AI" in both cases, so whatever the
detector is keying on came from post-training, not from being a language model.

The artifacts named in that work are response-length conventions (an answer that
arrives at the length an assistant answers in), markdown formatting preference
(headings, bulleted lists, bolded runs), the structural conventions of a reply
(frame the topic, cover it in even sections, close by wrapping up), and sycophancy
markers. One more is contextual rather than intrinsic: a passage preceded by
human-written text scores more human than the same passage after a
machine-written prefix.

Word choice is downstream of all of it. This is why a pass that swaps `delve` for
`explore` changes a detector's verdict so little, and why deleting the section
headings from a bulleted answer changes it so much.

## The three detector families, and which ones a rewrite moves

| Family | How it decides | Does honest rewriting move it? |
|---|---|---|
| Statistical / zero-shot (DetectGPT, FastDetectGPT, Binoculars, most free web tools) | token-level surprisal and its variance, computed with a proxy model | **Yes, substantially.** These are what "perplexity and burstiness" describes, and rhythm and specificity are the levers. |
| Trained classifiers, general (GPTZero, Copyleaks, Winston, Turnitin) | supervised model over stylistic and distributional features | **Partly.** Reported accuracy on rewritten text falls well below their accuracy on raw output. |
| Trained classifiers, hardened against rewriting (Pangram class) | supervised model trained specifically on humanizer output | **Barely.** Published accuracy on humanized text is around 97%. |

Two consequences worth stating plainly.

First, the reported accuracy of the statistical family on rewritten text is low
enough (GPTZero around 46%, FastDetectGPT around 23%, Binoculars around 7% in one
vendor's comparison) that a thorough rewrite reliably reads as human to them.
That is most of what people actually encounter.

Second, no amount of legitimate rewriting guarantees anything against a
classifier trained on rewritten text. Anyone promising "undetectable" is either
testing against the weak family or using tricks. Which brings us to the tricks.

## Why the tricks lose

The vendor with the best published numbers on humanized text reports the
counterintuitive result directly: **the more fluent a humanizer's output, the
more reliably it is detected.** The tools that evade do it by damaging the text,
and the damage is itself a signature. Tortured synonyms ("counterfeit
consciousness" for "artificial intelligence") read as machine-mangled, because
they are. Unicode substitution is trivially stripped, and homoglyphs or
zero-width joiners in a document are stronger evidence of automated laundering
than the original text ever was. Injected typos are a fingerprint rather than a
disguise: they cluster unlike real ones.

Every one of those is a detectable artifact, and every one makes the writing
worse. That is the whole reason this skill refuses them (principle 3): they fail
on their own terms, before the ethics.

## What this changes about the rewrite

The evidence reorders the edit priority:

1. **Strip the assistant shape first.** If the draft is a chat answer wearing a
   document's clothes (heading every eighty words, a third of its lines bullets,
   bold on every term, a "Key takeaways" close), that shape is the loudest thing in
   it. Reformatting into continuous prose with the conventions of the genre
   moves more than every word swap combined. The linter measures this as
   `assistant_shape`.
2. **Then fix the length distribution, not just its variance.** Human prose
   reaches: it drops four-word sentences and runs forty-word ones. Model prose
   collapses toward the 12-26 word band. Coefficient of variation misses this,
   because one long sentence inflates it while everything else stays uniform. The
   linter measures the tails directly as `sentence_shape`; target at least 12% of
   sentences at eight words or fewer, and under 72% inside the mid band.
3. **Then add real specificity.** Low surprisal is what the statistical family
   measures, and the only honest way to lower predictability is to say something
   a generic model would not have said. That means material: a name, a date, a
   number, a preference, a thing that went wrong. A rewrite cannot invent any of it
   (principle 3), so it has to *source* it. See the author-material intake in
   SKILL.md.
4. **Diction last**, as always.

Measured on this repo's own corpus: against 2023-era caricature, the score is
driven by `filler` (12%) and `meta_commentary` (12%), both word-level categories.
Against prose a current model actually writes, it is driven by `sentence_shape`
(23%), `paragraph_uniformity` (14%), and `burstiness` (13%). All shape. The word
lists catch the text nobody is fooled by anyway.

## The honest claim

The skill's promise is *reads as written by a competent human*, and against the
statistical and general-classifier families that also means it stops tripping
them. It is not a guarantee of evasion, cannot be, and any version of this tool
that promised one would be lying. Detectors also carry false-positive rates that
land on real people: Liang et al. (2023, *Patterns*) found GPT detectors
systematically misclassify non-native-English writing as machine-generated. No
detector is ground truth, in either direction.

## Sources

- "Base Models Look Human To AI Detectors": <https://arxiv.org/abs/2605.19516>
- Pangram, "How well does Pangram perform on humanizers?":
  <https://www.pangram.com/blog/humanizers-aug-25>
- Liang et al., "GPT detectors are biased against non-native English writers",
  *Patterns* 4(7), 2023: <https://doi.org/10.1016/j.patter.2023.100779>
<!-- human-voice: ignore filler -->
- Kobak et al., "Delving into LLM-assisted writing in biomedical publications
  through excess vocabulary", *Science Advances*, 2025:
  <https://www.science.org/doi/10.1126/sciadv.adt3813>
