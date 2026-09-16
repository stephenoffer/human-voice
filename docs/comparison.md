# How human-voice compares

[Docs home](README.md) · [Getting started](getting-started.md) · [Install](install.md) · [Usage](usage.md) · [Examples](examples.md) · [Evidence](evidence.md) · **Comparison**

Three different markets get confused with each other. Here is where this sits in
each.

## Prose linters (what human-voice is closest to)

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

## AI detectors (what human-voice is measured *against*, not competing with)

Roughly in order of independently-reported accuracy: Pangram, Originality.ai,
GPTZero, Copyleaks, Winston AI, Turnitin, Sapling, ZeroGPT, and the zero-shot
research family (DetectGPT, FastDetectGPT, Binoculars). They fall into three
groups that behave very differently on rewritten text. Statistical and zero-shot
detectors move a lot, general trained classifiers move partly, and classifiers
trained on humanizer output barely move. The table and the numbers are in
[`references/what-detectors-see.md`](../skills/human-voice/references/what-detectors-see.md).
None is ground truth: reported false-positive rates run from ~0.004% to ~10%
depending on the tool and the text, and they are systematically worse on
non-native-English writing.

## "Humanizers" (what human-voice deliberately is not)

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

human-voice does none of it, on purpose. It has no bypass rate to quote. It has a
measured claim instead: it makes prose read as though a competent person wrote
it, the only durable version of the same goal.

## The full survey

About a hundred tools and papers were reviewed in September 2026. The survey
spans the humanizer market, open-source anti-slop projects, prose linters,
editing suites, detectors, the stylometry literature and Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
catalog. It records each tool's contribution, the techniques adopted after
measurement, the ones tested and thrown out, and where this skill still falls
behind:
[`references/competitive-landscape.md`](../skills/human-voice/references/competitive-landscape.md).

The most useful part is the rejections. Contraction absence is the widest single
signal in the published research and it replicates here at nine to one, and it is
deliberately not scored, because gated to the conversational registers it fires on
four of the ten careful non-native writers in the corpus. ProWritingAid's glue
index shows no separation at all on this corpus. Both are reported as diagnostics
or dropped rather than folded into a score.

The most surprising result is about stylometry. Function-word distance from a
human reference profile is the standard technique, and on this corpus it runs
**backwards**: the human class averages 0.769 and current model output 0.690, so
the machines sit *closer* to the human centroid than the humans do. A reference
profile built from thirty authors is the centroid of thirty idiosyncrasies, and a
model writes the centroid. The tell is the absence of distance. It ships as an
unscored `style:` diagnostic, read inverted. No other number here shows the
rewrite procedure moving a distributional property rather than a surface one: the twenty rewritten files move 0.690 to 0.739 and land closer to the human
median in 16 of 20 cases.
