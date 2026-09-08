# What the other tools do, and what we took from them

<!-- human-voice: ignore filler -->
<!-- human-voice: ignore llm_artifact -->

A survey of about a hundred tools and papers that overlap this skill, done in
September 2026, with one question in front of it: which of their techniques are
worth adopting, and which look good in a feature list but fail when you measure
them. Every adoption below was tested against `eval/corpus/` before it shipped.
Three techniques that the literature rates highly were tested and rejected, and
those are the more useful half of this page.

The competitive picture in one line: the humanizer market optimizes for a
detector verdict, the linter market optimizes for grammar and readability, and
almost nobody optimizes for the thing that decides whether a person believes a
human wrote it. That gap is where this skill sits.

## 1. Commercial humanizers

These take AI text and rewrite it to clear a detector. Twenty-six of them, ranked
in the trade press by bypass rate rather than by whether the output is any good.

| Tool | Pitch | Technique worth noting |
|---|---|---|
| Undetectable.ai | Category leader, refunds if flagged | Multi-detector feedback loop before returning text |
| StealthGPT | Bypass-first | Generates rather than rewrites, so there is no source signature |
| WriteHuman | Preserves the writer's voice | Voice retention over raw evasion |
| Humbot | Turnitin-specific | Single-target tuning |
| Phrasly | Ranked top on output quality | Quality as the objective, not evasion |
| QuillBot Humanizer | Paraphrase heritage | Readability gains on short text |
| Grammarly AI Humanizer | Bundled with the editor | Tone-target rewriting |
| BypassGPT, Bypass AI | Evasion | Recursive paraphrase passes |
| HIX Bypass, Rewritify | Evasion | Model-specific rewrite profiles |
| StealthWriter, Twixify | Budget tier | Style samples as few-shot input |
| Walter Writes, TextPulse | Academic angle | Register presets |
| Netus AI, GPTinf, Semihuman | Evasion | Synonym and structure shuffling |
| Ryne AI, Conch AI, Smodin | Student tools | Inline rewriting in a doc editor |
| AISEO, Surfer AI Humanizer | SEO angle | Keyword preservation during rewrite |
| Decopy, NoteGPT, SuperHumanizer | Free tier | None distinctive |
| ProofreaderPro, Paperpal, Trinka, Wordvice | Academic editing | Discipline-specific style rules |
| Microsoft Copilot "humanize" | Bundled | Prompt-level rewriting |

What they share is the failure this skill was built against. They start at
diction, they optimize against a classifier, and the classifier is now trained on
their output. Pangram reports 93.66% detection on humanized text against
GPTZero's 34.53% on the same set, and the same vendor reports the finding that
should end the strategy: the more fluent a humanizer's output, the more reliably
it is caught, because the tools that evade do it by damaging the text and the
damage is the signature.

**Adopted.** Two ideas. WriteHuman and StealthWriter both let you supply your own
writing as the target, which is the right instinct and the one the free tools
skip. This skill's author-material intake does the honest version: it pulls real
specifics from the draft, the repo, or the user rather than extracting a style
vector and applying it to invented content. Phrasly's decision to rank on output
quality rather than bypass rate is the position principle 8 already takes.

**Rejected.** The evasion tricks, individually: tortured synonyms, Unicode
homoglyphs, zero-width characters, injected typos. Each is trivially detected,
each makes the writing worse, and each violates principle 3.

## 2. Open-source anti-slop projects and agent skills

| Project | What it is | Idea taken |
|---|---|---|
| sam-paech/antislop-sampler | Inference-time backtracking that suppresses banned strings | Suppress 8,000+ patterns without banning tokens |
| sam-paech/auto-antislop | Pipeline that profiles a model against a human baseline | Profile against human text, not against a rule list |
| sam-paech/slop-forensics | Over-represented word, bigram and trigram analysis | Some patterns run 1,000x the human rate |
| Antislop / FTPO (ICLR 2026) | Token-level preference optimization | 90% slop reduction without capability loss |
| adenaufal/anti-slop-writing | Universal system prompt, 36-item checklist | Cadence uniformity ranked as the top 2026 tell |
| adewale/anti-slop-writing | Agent skill for prose review | Skill-shaped delivery for coding agents |
| deslop / anti-ai-slop topics on GitHub | Roughly a dozen pattern-list rewriters | 152-pattern rewriters, three-tier scoring |
| stop-slop style lists | Community prohibition lists | Named as an anti-pattern below |
| EQ-Bench Creative Writing v3 | Creative writing benchmark with a slop score | Slop as a measurable per-model quantity |

The Antislop work is the strongest technical contribution in this bucket and it
operates one layer below this skill, inside the sampler and the weights. Its
central finding transfers anyway: a pattern worth suppressing is one that appears
at a rate far above the human baseline, and the way to establish that is to
measure a human corpus rather than to argue about a word list. That is the
`cited-vs-matched.md` argument arrived at from the other direction, and it is why
every check added in this survey was measured against `eval/corpus/human/` before
it was given a weight.

**Rejected.** The community prohibition lists. "Kill all adverbs", "never use an
em-dash", "always two, never three" manufacture a fresh uniform signature, which
is principle 2's failure mode and which `over_correction` exists to catch.

## 3. Prose linters and style checkers

| Tool | Domain | Overlap |
|---|---|---|
| proselint | Editorial advice from style manuals | Cliché, redundancy, jargon |
| write-good | Weak-writing heuristics | Passive, adverbs, wordiness |
| Vale | Configurable style-guide engine | Runs the two above plus custom rules |
| alex | Insensitive and inconsiderate wording | No overlap; complementary |
| textlint, retext | Pluggable natural-language linting | Rule-plugin architecture |
| LanguageTool | Grammar and style, many languages | Grammar layer this skill does not have |
| markdownlint, blocklint | Markdown and plain-language rules | Formatting hygiene |
| textstat | Readability formulas | Reading-grade metrics |
| GNU style and diction | The original Unix prose linters | Sentence-length statistics |
| RedPen | Document validation for technical writing | Section-level structure rules |
| joblint | Job-post specific | None |
| Hemingway Editor | Hard sentences, adverbs, passive | Sentence-difficulty scoring |
| Expresso, Slick Write | Browser-based analysis | Word-class distributions |
| Writer's Diet | Be-verbs, prepositions, nominalizations, waste words | The "flabby prose" diagnosis |
| Prose-linter MCP servers | Wraps five linters plus an AI-tell rule set | Delivery as an agent tool |

Every one of these is a word-and-sentence tool. None of them sees document shape,
none sees stance, and none can tell a paragraph that says nothing from a paragraph
that says something. That is not a criticism of them, since it is not what they
were built for. It does mean the whole category is a floor rather than a test,
which is what principle 8 says about this skill's own linter.

**Adopted.** Vale's configurability was already the model for `.humanvoicerc` and
the inline ignore directives. Writer's Diet contributed the framing behind the
`copula_avoidance` check added in this pass, though from the opposite direction:
Writer's Diet flags too many be-verbs, and the tell in 2026 output is the
elaborate substitute for one.

## 4. Editing suites and craft tools

| Tool | Signature report | Verdict |
|---|---|---|
| ProWritingAid | 25 reports: sticky sentences, echoes, pacing, transitions | Sticky sentences measured and rejected, below |
| Grammarly | Tone, clarity, engagement, delivery | Tone detection is genuinely good; the rest is grammar |
| AutoCrit | Fiction: repeated phrases, sentence starters, showing vs telling | Sentence-starter analysis overlaps `paragraph_openers` |
| Marlowe (Authors A.I.) | Full-manuscript narrative report | Pacing curves; out of scope here |
| Draftsmith, Wordtune, Sudowrite | Rewriting assistants | Rewrite suggestions, no diagnosis |
| Readable.com | Bulk readability scoring | Formula-based, same limits as textstat |

ProWritingAid's echoes report is the closest thing in the commercial market to
this skill's `ngram_repetition`, and its sticky-sentence report is the most
interesting single idea in the bucket. Both were tested. One survived.

## 5. Detectors

| Detector | Family | Note |
|---|---|---|
| Pangram | Trained classifier | Best published numbers on humanized text |
| GPTZero | Trained classifier | 95.7% on the RAID benchmark; 34.53% on humanized text |
| Originality.ai | Trained classifier | Strong on raw AI, weaker on paraphrase |
| Copyleaks | Trained classifier | Multi-modal, enterprise compliance |
| Turnitin | Trained classifier | Disabled by several universities over false positives |
| Winston AI, Sapling, ZeroGPT, Undetectable's checker | Trained classifiers | Consumer tier |
| GPTKit, `Content at Scale`, Crossplag | Trained classifiers | Consumer tier |
| DetectGPT, FastDetectGPT | Curvature and surprisal | Statistical family |
| Binoculars | Cross-perplexity of two models | Statistical family, no training needed |
| Ghostbuster | Feature search over model probabilities | Statistical family |
| RADAR | Adversarially trained detector | Survives paraphrase by construction |
| DAMAGE (Pangram) | Detector trained on 19 humanizers' output | The paper that closed the paraphrase loophole |
| SynthID-Text | Watermarking | Provenance rather than detection |
| RAID, M4, Beemo, LLM-DetectAIve | Benchmarks | Evaluation infrastructure |

Two numbers from this bucket set the honest ceiling on what any rewrite can
claim. On raw AI text the leaders reach the mid-nineties; on paraphrased text
they fall to somewhere between 41% and 72%, except for the classifiers trained
specifically on humanizer output, which stay near 97%. And Turnitin flags 61.3%
of non-native-English essays as machine-written. A detector score is therefore
evidence in one direction at one threshold, never ground truth, which is what
`verify_detector.py` reports and what `MAX_HUMAN_FPR` in `eval/detector_local.py`
enforces by discarding any detector that cannot pass known-human text.

## 6. Research on detection and style

| Work | Contribution | Use here |
|---|---|---|
| Base models look human to AI detectors | Base checkpoints read human >96% of the time | The evidence behind the shape-first edit order |
| Liang et al. 2023 | Detectors misclassify non-native English | The reason `esl_formal/` exists and the reason contraction rate is unscored |
| DAMAGE (arXiv 2501.03437) | Audits 19 humanizers for faithfulness | Meaning preservation as a first-class metric |
| Stylometry of AI authorship (PLOS One 2025) | Function-word unigrams, POS bigrams and phraseology separate at 99.8% | See section 8 |
| StyleDecipher | Explainable stylistic detection | Feature-level explanation over a bare score |
| Biber multidimensional analysis benchmark | Where LLM text diverges from human on interpretable dimensions | Confirms shape and stance over diction |
| Burrows's Delta | Z-scored function-word distance | See section 8 |
| Google paraphrase-attack result | Paraphrasing evades most detectors | Why the humanizer market exists |
| Reddit ~90k-post study of cited tells | What readers notice against what scanners match | The category weight tiers |

## 7. Field guides and catalogs

Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
maintained by WikiProject AI Cleanup, is the best public catalog in existence and
the most useful single document in this survey. It is built from thousands of
flagged drafts, not from intuition. It is versioned by model era, and it covers
markup and citation residue that no style tool looks at. The rest of the
bucket is thinner: assorted "signs your text is AI" listicles, the LinkedIn
banned-word genre, and a handful of newsroom style memos.

Auditing this skill against that catalog found fifteen tells it did not cover.
Most are now covered. See below.

## 8. What was adopted, and what it measured

Everything here was added in this pass and gated on `eval/run_eval.py`,
`eval/human_baseline.py` and `tests/stress_test.py`.

**Paste residue** (`llm_artifact`, weight 4.0). Wikipedia's markup section
catalogs the strings chat products leave behind: OpenAI citation wrappers, tool-call
markers, Gemini span tags, Grok render calls, Perplexity upload paths, lenticular
bracket citations, chat-product tracking parameters on URLs, and unfilled template
slots. No writer types any of them, so unlike every other check here a single
instance is a finding rather than a whisper, and the weight says so. The corpus
contains none, so this moves no eval number. It is the highest-precision check in
the file and it catches the commonest real-world case, which is text pasted from a
chat window without being read.

**Heading scaffolding** (`heading_structure`, weight 1.0). Skipped heading levels,
a second H1, a heading whose whole body is the next heading, a heading running
straight into a bullet list with no sentence between them. Individually minor.
Together they say the document was assembled from an outline rather than written.

**Quote seams** (`quote_style`, weight 0.5). Curly and straight quotes mixed
lopsidedly in one file, which is usually the seam where pasted output meets typed
text. Held to a minimum of six quote marks and a 1-in-4 minority so that quoted
code beside quoted speech does not fire.

**Copula avoidance** (`copula_avoidance`, weight 1.0). The mirror of the existing
`copula_density` check. Where 2023-era prose over-used "is", current output
reaches for an elaborate substitute: `serves as`, `stands as`, `functions as`,
`represents`, `boasts`, `embodies`. Wikipedia's corpus measured "is" and "are" dropping
more than 10% after 2022 while these rose. Measured here at 0.8 per thousand words
in the human class against 4.0 in the caricature class, with a human maximum of
7.0, so the bar sits at 8.0 with a minimum count of three.

**Era-3 vocabulary.** Fifteen phrases from the Wikipedia catalog that the pattern
file was missing, sorted into the lists where they belong: `ensuring`,
`showcasing`, `align with`, `valuable insights`, `diverse array`, `renowned`,
`groundbreaking`, `indelible mark`, `deeply rooted`, `in the heart of`,
`setting the stage for`, `focal point`, `enduring legacy`, plus the
vague-connection family (`in connection with`, `widely associated with`).

**Mid-sentence pseudo-clefts.** `WH_CLEFT_RE` was anchored to a sentence start,
which missed the commonest narrative form of the same construction one clause
later: "But standing in the hallway, what she felt was mostly the practical
weight". Now anchored to a clause boundary. Comma-anchored matches require the
lowercase form so a quoted question does not count.

**Per-register thresholds** (`register_thresholds`). The most consequential change
in this pass, and it is a fix to a design mistake rather than a borrowed
technique. A register that legitimately runs hot on one construction used to be
handled by muting the check outright, and muting throws away the signal above the
register's genuine tolerance along with the false positives below it. Creative
prose had `cleft` muted, so a fiction sample could stack clefts at any rate and
score zero. Two of the three files the floor missed on the modern-AI class were
exactly that. A multiplier says "fiction tolerates 1.3 times the rate" instead of
"fiction is exempt", which is what the corpus shows: the human creative samples
here carry no clefts at all. The two mute tokens it replaced, `cleft_ok` and
`long_sentences_ok`, were retired.

Measured effect on the honest separation number, the modern-AI class against
human, with everything else held constant:

| metric | before | after |
|---|---|---|
| ROC AUC vs human | 0.937 | 0.938 |
| recall at the 5.0 boundary | 0.850 (17 of 20) | **0.900 (18 of 20)** |
| precision | 1.000 | 1.000 |
| F1 | 0.919 | **0.947** |
| human-subset FPR | 0.000 | 0.000 |
| ESL/formal-human FPR | 0.000 | 0.000 |
| over-corrected costume recall | 1.000 | 1.000 |
| stdlib-docstring baseline, worst score | 17.7 | 17.7 |

Two files are still missed. `m17_email_project.md` is a short internal email whose
only surface tell is one em-dash, and the em-dash check needs three before it
fires, which is a deliberate choice rather than a gap. `m09_creative_scene.md` is
183 words of competent fiction whose tells are all in section 9.

## 9. What was tested and deliberately rejected

This is the half of the survey worth reading, because three of these are
techniques the literature or the market rates highly.

**Contraction absence.** The humanizer research names this the single most
discriminative surface feature, at roughly 0.00 contractions per chunk for AI
against 0.17 for human. It replicates here and then some: 20.3 per thousand words
in the human class against 2.2 in the modern-AI class, a nine-fold gap and the
widest of any signal tested. It is not scored, and it will not be. Gated to the
conversational registers with a pronoun floor and a minimum length, it fires on
four of the ten files in `esl_formal/`: careful non-native writers who use no
contractions and are human. Scoring it would reproduce, inside a tool whose whole
argument is that commercial detectors are wrong about that population, the exact
bias Liang et al. measured. It is reported as an unscored diagnostic instead,
because a marketing page with no contractions does read stiff and the writer
should know.

**Sticky sentences and the glue index** (ProWritingAid). Glue words as a share of
total words, with 40% given as the published-writing target. Measured across the
corpus: 44.2% in the human class, 43.5% in the modern-AI class, 40.7% in the
caricature class. No separation, and the caricature class scores *better* than the
humans. It is a quality metric, not an AI tell, and adding it would have put noise
into the score.

**The comma-anchored analogy tail.** ", the way snow lies on a road nobody
drives." A generic comparison appended to a finished sentence to make a plain
observation sound observed. It separates perfectly on this corpus: two modern-AI
files, no human files, no ESL files. It is not scored, because two files is not
evidence, because "She smiled, the way she always did" is ordinary fiction that
the pattern would flag, and because firing on a single instance is what principle
2 forbids. It is named in the creative-register guidance for the human read
instead, which is where a tell with real signal and thin evidence belongs.

Also tested and dropped for showing no separation: nonrestrictive ", which"
consequence tails (human 3.1 per thousand, modern-AI 4.3), negated relative and
complement clauses (human 9.0, modern-AI 8.3), and curly quotes on their own,
which appear nowhere in the corpus and only mean anything as a mix.

## 10. Where this skill is still behind

Honesty about the gaps, in the order they are worth closing.

**No surprisal measurement.** The statistical detector family computes token
surprisal, and the linter has no model and therefore no perplexity. Burstiness
and the sentence-length distribution are proxies for its variance, not for its
level. The function-word profile in section 11 is the nearest dependency-free
substitute and it is not the same thing.

**No author style profile.** The human reference profile now ships (section 11),
but nothing builds a profile of *your* writing and reports distance from it. The
commercial tools that advertise voice retention do a shallow version of this.
`eval/build_profile.py` already contains everything a `--profile` flag pointed at
the user's own past work would need, and that is the next capability worth
adding.

**No POS tagging.** Several tells in section 6 need it and every check here is
regex-only, which is a deliberate constraint (no dependencies, no network) with a
real cost.

**English only.** The Wikipedia catalog has model-specific and language-specific
sections this skill does not attempt.

## 11. Stylometry, and the direction everyone reads it backwards

The strongest single technique in the survey came out of section 6, and applying
it as written would have made this tool worse. It is worth the space.

The finding in the literature is that function-word frequencies separate human
from LLM writing, with one PLOS One study reporting 99.8% from function-word
unigrams, part-of-speech bigrams and phraseology. Burrows's Delta is the standard
way to turn that into a number: take the most frequent words, z-score each one
against a reference population, and average the absolute z-scores. The obvious
linter feature is to build a human reference profile and flag documents that sit
far from it.

Built and measured, over 150 features from the 29 files in `eval/corpus/human/`:

| class | n | mean delta | median | range |
|---|---|---|---|---|
| human | 29 | **0.769** | 0.781 | 0.615 to 0.937 |
| over_corrected | 10 | 0.772 | 0.768 | 0.704 to 0.865 |
| ai (caricature) | 24 | 0.728 | 0.722 | 0.612 to 0.857 |
| ai_modern_rewritten | 20 | 0.739 | 0.742 | 0.639 to 0.850 |
| esl_formal (human) | 10 | 0.737 | 0.725 | 0.682 to 0.890 |
| ai_modern | 20 | **0.690** | 0.693 | 0.565 to 0.831 |

The order is inverted. Model output sits **closer** to the human centroid than
human writing does, and the rank statistic in the naive direction is 0.188. A
check that flagged distance from the human profile would have flagged the humans
and passed the machines.

The reason is obvious once the number is in front of you. A reference profile
built from thirty authors is the centroid of thirty idiosyncrasies. An
instruction-tuned model writes very close to that centroid, because averaging the
population is what the objective rewards. Any individual writer departs from it.
So the tell is not distance, it is **the absence of distance**: a low delta means
the function-word profile carries no fingerprint.

Read inverted it separates at 0.812, which is real and still below the floor
score's own 0.938, so it does not belong in the score. And it runs 0.737 on the
ESL/formal human subset, between the AI classes and the rest of the human class,
which is the same objection that killed contraction absence and is sufficient on
its own.

Where it earns its place is across a pair. The twenty rewritten files move from
0.690 to 0.739 and end closer to the human median in 16 of 20 cases. That is the
rewrite procedure doing what it claims, and this is the only number in the repo
that shows it. So the profile ships (`human_reference_profile.json`, generated by
`eval/build_profile.py`, gated by `make profile-check`), the linter prints the
delta with the human range beside it on the `style:` line, `--baseline` prints the
movement and which way it went, and none of it touches the score.

## Sources

Everything cited above, in the order the sections use it.

- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) and [WikiProject AI Cleanup](https://en.wikipedia.org/wiki/Wikipedia:WikiProject_AI_Cleanup)
- [Antislop: identifying and eliminating repetitive patterns in language models](https://arxiv.org/pdf/2510.15061) (ICLR 2026), [antislop-sampler](https://github.com/sam-paech/antislop-sampler), [slop-forensics](https://github.com/sam-paech/slop-forensics)
- [DAMAGE: Detecting Adversarially Modified AI Generated Text](https://arxiv.org/abs/2501.03437)
- [Pangram: humanizer detection](https://www.pangram.com/blog/humanizers-announcement)
- [Stylometry can reveal artificial intelligence authorship](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0335369) (PLOS One)
- [Benchmark of stylistic variation in LLM-generated texts](https://arxiv.org/pdf/2509.10179)
- [StyleDecipher](https://arxiv.org/pdf/2510.12608)
- [proselint](https://github.com/amperser/proselint), [Vale](https://vale.sh), [write-good](https://github.com/btford/write-good), [alex](https://alexjs.com), [textlint](https://textlint.github.io)
- [ProWritingAid sticky sentences](https://help.prowritingaid.com/article/50-how-to-use-the-sticky-sentences-report)
- [anti-slop-writing](https://github.com/adenaufal/anti-slop-writing)
