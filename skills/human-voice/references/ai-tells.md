# AI Tells — Full Catalog

The complete reference the skill loads during a rewrite. Eight categories,
ordered by depth: substance first (what no linter catches), diction last (the
shallowest). Each entry gives the tell and at least one `BAD →` / `GOOD →` pair.

Treat lexical lists as a floor, never proof. Banned-word lists age — the PubMed
excess-vocabulary study (arXiv 2406.07016) measured a roughly 25× jump in
"delves" in 2024 abstracts, and writers have since learned to avoid it. A clean
lexical pass does not make text human, and a single flagged word does not make
it AI. The deep categories (1, 7, 8) decide far more than the shallow ones.

---

## 1. Substance

The hardest tells and the most important. A regex cannot see these; you have to
read for them.

**Vacuity** — a sentence or paragraph you can delete with zero information loss.

- BAD → "Data infrastructure is a critical component of modern systems. It plays
  an important role in how organizations operate and is worth careful
  consideration."
- GOOD → (deleted; say something with content instead) "Pick the store before
  you know your access patterns and you'll rewrite it within a year."

**Restatement** — the conclusion repeats the intro in new words.

- BAD → "In conclusion, as discussed above, the key takeaway is that performance
  matters."
- GOOD → end on the last real point; cut the recap.

**Meta-commentary / throat-clearing** — narrating the document instead of
writing it.

- BAD → "This report aims to explore the multifaceted landscape of..."
- GOOD → state the finding: "Three things decide the outcome."

**Conversational scaffolding / chatbot framing** — the assistant register
leaking into the page: openers, fake engagement, and sign-offs that belong in a
chat reply, not a document. The single most recognizable tell in pasted-from-chat
text. The linter flags these as `chatbot_scaffold`.

- BAD → "Sure! Here's the thing about caching. Great question — let me break it
  down. I hope this helps!"
- GOOD → delete the scaffolding and open on the content: "Caching helps here only
  when reads dominate writes."

**Over-signposting / fake transitional glue** — "Furthermore", "Moreover",
"Additionally", "With that in mind", "As such" used as connective filler. The
test: a transition is earned only if removing it changes the logic.

- BAD → "Furthermore, the system is fast. Moreover, it scales. Additionally, it
  is secure."
- GOOD → drop the glue; let the sentences stand, and keep a transition only where
  it marks a real turn in the argument.

**The "it depends" / "no one-size-fits-all" non-conclusion** — the canonical AI
ending that commits to nothing (see also category 8, buried verdict).

- BAD → "Ultimately, the best choice depends on your specific needs and
  requirements."
- GOOD → commit: "Use Postgres unless you're past 50k writes/sec; then revisit."

**Fabricated specificity** — invented numbers, sources, or detail to sound
precise.

- BAD → "This approach improves performance by up to 40%." (no source)
- GOOD → cite the measurement, or cut the number. Never invent one to add texture.

**Agent self-narration** — the writing describes its own analysis.

- BAD → "Our analysis determined that the GPU utilization was suboptimal."
- GOOD → "GPU sits at 22%."

---

## 2. Structure & rhythm

The structural half of what perplexity/burstiness detectors measure. Highest
mechanical leverage after substance.

**Low burstiness** — every sentence the same length and shape. The single
strongest mechanical tell.

- BAD → "The system is fast. The system is reliable. The system is scalable. The
  system handles load well." (all ~5 words, same shape)
- GOOD → "The system is fast. Under sustained write load it holds p99 latency
  below 10ms, which is the number that actually matters when traffic spikes, and
  it degrades gracefully past that. Reliable enough."

**Rule of three** — the reflexive tricolon, everywhere.

- BAD → "fast, reliable, and scalable"
- GOOD → vary to two or four, or a clause: "fast, and reliable under load."

**Bold-lead-in listicles** — every bullet `- **Term:** explanation`.

- BAD → a list where all eight items open with a bolded term and a colon.
- GOOD → convert most to prose; keep plain bullets only where scanning helps.

**Antithesis / "not only… but also"** and **"not X, it's Y"**.

- BAD → "It's not just a tool, it's a complete solution."
- GOOD → say what it is: "It handles ingestion, indexing, and query in one
  process."

**Uniform openers** — many sentences starting the same way ("The…", "This…",
"It's important…").

- BAD → six sentences in a row opening with "The platform".
- GOOD → vary subject and structure.

**N-gram repetition** — the same bigram/trigram recurring.

- BAD → "in order to" four times; "it is important to" twice.
- GOOD → rephrase; most can simply be cut.

**Enumerated-promise opener** — pre-announcing a count instead of just making the
points.

- BAD → "There are five key things to consider when choosing a database."
- GOOD → make the points; if a count helps the reader, it earns its place, but
  the list usually reads better without the throat-clear.

**Balanced-antithesis cadence** — relentless two-part symmetry, beyond the literal
"not X, it's Y". The metronome rhythm is itself the tell.

- BAD → "It's not about speed; it's about reliability. Less talk, more action.
  Not a feature, but a philosophy."
- GOOD → break the symmetry; let one idea run long and the next land short.

**Colon overuse** — the "Label: explanation" reflex outside bullets ("The answer
is simple: ...", "Here's the catch: ...").

- BAD → "The result is clear: latency wins. The reason is simple: users feel it."
- GOOD → fold the clause into the sentence: "Latency wins because users feel it."

---

## 3. Diction

The shallowest layer. Fix last. A swap that leaves the sentence vague is not an
improvement — cut instead.

**Filler verbs/adjectives** (the bulk of AI's excess vocabulary — ~66% verbs,
~18% adjectives in the PubMed study):

- delve → examine; leverage → use; utilize → use; underscore → show; showcase →
  show; facilitate → help; foster → support; harness → use.
- robust, seamless, crucial, pivotal, vital, comprehensive, multifaceted,
  cutting-edge, revolutionary → usually cut; they add no information.
- intricate → complex; realm → area; myriad/plethora → many; elevate → raise.

**Clichés** — "at the end of the day", "when it comes to", "in today's digital
age".

- BAD → "When it comes to performance, at the end of the day it's about latency."
- GOOD → "Performance here means latency."

**Business jargon** (the linter's `jargon` category) — corporate buzzwords that
delete cleanly: synergy, leverage, circle back, touch base, move the needle,
low-hanging fruit, value-add, core competency, actionable, best-in-class,
operationalize, paradigm shift, thought leadership, north star, table stakes,
mission-critical, frictionless, empower, supercharge, disruptive.

- Keep a term that does work (a precise domain term a reader needs); cut a word
  you could delete with no loss of meaning. The test is whether the word carries
  information.
- BAD → "We leverage our synergies to operationalize best-in-class, actionable
  solutions."
- GOOD → "We share one data pipeline across both teams, which cut duplicated
  ETL work in half."
- BAD → "This is mission-critical and moves the needle for stakeholders."
- GOOD → "This blocks the launch until it's fixed."

**The "not X, it's Y" template** (also structural — see category 2).

**Weak intensifiers** — "really", "very", "quite", "extremely", "incredibly"
propping up a flabby adjective.

- BAD → "This is a really important and very powerful feature."
- GOOD → delete the intensifier; if the sentence weakens, the adjective was doing
  the work and needs a stronger word, not an amplifier: "This feature ships the
  whole release."

**Gratuitous reformulation** — "In other words", "Simply put", "To put it another
way" followed by a restatement. Often the second version is the only one worth
keeping.

- BAD → "Latency is the time to first byte. In other words, how long users wait."
- GOOD → "Latency is how long users wait for the first byte."

**Hype-verb class** — "revolutionize", "transform", "unlock", "empower",
"supercharge", "elevate". The verb cousins of puffery; cut or replace with the
concrete action.

- BAD → "This unlocks new potential and empowers teams to supercharge delivery."
- GOOD → "This lets two teams share one pipeline, which cut release time in half."

---

## 4. Sourcing

**Vague attribution** — authority with no source.

- BAD → "Studies suggest that..."; "Experts believe..."; "It is widely known..."
- GOOD → name the source ("the 2024 MLPerf results show...") or cut the claim.

**Redundancy / pleonasm** — a word that pays for nothing.

- BAD → "end result", "close proximity", "new innovation", "past history",
  "completely eliminate".
- GOOD → "result", "proximity", "innovation", "history", "eliminate".

**Tailing significance clause** — an empty "highlighting/underscoring its X"
tacked on.

- BAD → "...reduced latency, highlighting its commitment to performance."
- GOOD → cut the clause, or give a real consequence: "...reduced latency, which
  let us drop two cache layers."

---

## 5. Formatting

**Decorative emoji** in headings or bullets (outside genuinely casual/social
copy) → remove.

**Ornamental bold** — bolding for emphasis on phrases that aren't terms → remove.

**Section rules everywhere** — a `---` between every section → keep structure in
the headings, not in horizontal rules.

- BAD → emoji headings, a `---` after each paragraph, bold scattered mid-sentence.
- GOOD → plain headings; rules only where a real topic break needs one.

**Emoji-as-bullet / status-glyph decoration** — ✅ / ❌ / ⚠️ / 🔑 / 🚀 opening
bullets or scattered through a listicle, outside genuinely casual/social copy.

- BAD → "✅ Fast  ✅ Reliable  🚀 Scalable".
- GOOD → plain bullets, or prose. Reserve callout glyphs for documents that
  already use a consistent severity convention.

---

## 6. Register calibration

"Human" depends on genre. Match it; never bolt on a voice the genre rejects. The
universal core (categories 1, 2, 4, 5, 7, 8 minus the register-flexible bits)
holds everywhere.

| Register | Add what the genre wants | The genre's specific AI failure mode |
|---|---|---|
| technical | nothing; stay direct and present-tense | hype, warmth, "you"-selling |
| business | a brief courteous opener/closer | gush, hedging, filler |
| marketing | "you"/"we", contractions, light enthusiasm | **puffery and hype**, fake stats |
| academic | measured hedging, citations, "we"/passive | unsourced "studies show", clichés |
| casual | contractions, "I"/"you", rhetorical questions, fragments | listicle padding, meta-commentary |
| creative | em-dashes, fragments, wide cadence | clichés, pleonasm, lazy puffery |

- BAD (report bolting on casual voice) → "So basically, our infra is super
  solid, which is awesome 🔥"
- GOOD (technical) → "The cluster sustained 50k writes/sec for six hours with no
  failovers."

**Over-explaining / audience miscalibration** — explaining what the reader
already knows. Common when the register is technical but the prose condescends.

- BAD → "As you may know, a database is a system that stores data."
- GOOD → cut it; write to the reader's actual level.

**Parenthetical over-qualification** — hedging stuffed into parentheses
("(though results may vary)", "(in most cases)", "(generally speaking)").

- BAD → "This halves latency (in most cases, though it depends on the workload)."
- GOOD → state the real condition once: "This halves latency on read-heavy
  workloads; write-heavy ones see less."

**Chatbot politeness / deference** — assistant sign-offs and apologies bleeding
into a document: "I hope this helps!", "Feel free to reach out", "Of course!",
over-apologizing. A register tell in anything that isn't a chat reply.

- BAD → "I hope this helps! Feel free to reach out with any questions."
- GOOD → cut it; a document doesn't address its reader as a support ticket.

---

## 7. Consistency

One author holds one voice and one set of materials. Drift reads as machine even
when every sentence is clean.

**Terminology drift** — one concept, several names.

- BAD → "the model" → "the LLM" → "the network" → "the system", all for the same
  thing.
- GOOD → pick one term and keep it.

**Dialect drift** — mixed American/British spelling.

- BAD → "optimize" in one paragraph, "optimise" in the next; "color" and
  "colour".
- GOOD → one dialect throughout (use `--dialect` to catch this).

**Heading-case drift** — Title Case headings mixed with sentence case.

- GOOD → pick one convention and hold it.

**Voice/tense drift** — findings in present tense, then past, then back.

- GOOD → one tense for findings, one author voice end to end.

---

## 8. Stance & evaluation

The deepest human quality: judgment. A flawless but non-committal survey still
reads as AI. This is what most separates human writing from machine writing.

**Fence-sitting / false balance** — presenting options as equally valid to avoid
committing.

- BAD → "There are several approaches, each with its own tradeoffs and merits."
- GOOD → "Use FSDP. Pipeline parallelism wins only above 70B parameters, and you
  aren't there."

**Buried verdict** — the recommendation arrives last, hedged.

- BAD → three paragraphs of survey, then "it may be worth considering option B."
- GOOD → lead with the verdict, then justify it.

**Missing mechanism** — a claim with no "why".

- BAD → "Postgres is the better choice here."
- GOOD → "Postgres is the better choice: you keep transactional guarantees and
  mature access-control tooling while partitioning handles write scale."

**Asymmetric tradeoffs stated as symmetric** — real choices are usually lopsided.

- GOOD → "NoSQL scales further, but you'd rebuild consistency and access control
  by hand — the wrong place to economize for regulated data."

**Naming genuine limits** — honest stance, not hedging.

- GOOD → "Not load-tested past 50k writes/sec, and this assumes a single region."

---

## Detector landscape (what we're up against, and the honest limits)

We target the *causes* detectors latch onto, not the detectors themselves. None
is ground truth; all have real false-positive rates.

- **Perplexity-based** (GPTZero core): runs text through a reference language
  model; low perplexity = too predictable = flagged AI. Beaten by genuine
  specificity and the accurate, less-expected word.
- **Burstiness** (GPTZero): variance of per-sentence perplexity/length. AI is
  smooth and monotone. The linter's sentence-length coefficient of variation
  targets this directly — the highest-leverage mechanical signal.
- **Curvature** (DetectGPT, Fast-DetectGPT): AI text sits in negative-curvature
  regions of a model's log-probability surface. Zero-shot, no training — but
  fragile: in the original paper, paraphrasing degraded detection substantially
  (roughly from the ~0.7–0.95 AUROC range toward chance, varying by model and
  domain), and it does not work on code. Treat the exact figure as
  dataset-specific, not a constant.
- **Newer zero-shot / feature detectors**: **Binoculars** (ratio of two models'
  perplexities — cross-perplexity — strong zero-shot), **Ghostbuster**
  (structured search over model-feature combinations; more robust to
  paraphrase), **DNA-GPT** (divergent n-gram analysis), **GLTR** (token-rank
  visualization, the ancestor of perplexity tools), and **RADAR**
  (adversarially-trained detector). The same causes drive them: low perplexity,
  low burstiness, predictable n-grams — which genuine specificity and varied
  rhythm address honestly.
- **Watermarking**: a provider-side bias in the token distribution. It is
  provider-dependent and we do not try to strip it. Note that rewriting and
  paraphrasing *do* weaken many statistical watermarks as a side effect — but
  that is not our goal, and it is not something a humanization pass should
  optimize for.
- **Trained classifiers** (Originality.ai, Copyleaks, Turnitin): fine-tuned
  transformers plus stylometric and n-gram features. Addressed by the phrase,
  n-gram, and TTR checks. These carry the documented ESL false-positive bias
  most strongly.
- **Stylometry**: sentence/word length, type-token ratio, punctuation profile,
  function-word distribution. Addressed by burstiness, TTR, em-dash/punctuation
  profile, opener-entropy, and uniform-opener checks.

Our local regex linter does **not** compute perplexity or curvature. It catches
the surface features that *correlate* with what these systems measure. The real
test is a skeptical human read — and we never use the adversarial tricks
(homoglyphs, zero-width characters, meaning-degrading synonym swaps, fabrication)
that the evasion literature describes. Those degrade the writing.

**Detectors have real, biased error rates.** Liang et al. (2023) showed leading
detectors flag non-native-English (ESL) writing as AI far more often than
native-English writing — a documented false-positive bias, not noise. Accuracy
figures also expire: every number here is a snapshot that drifts as models and
detectors change, exactly as banned-word lists age. Report a score; never treat
one as proof.

## Sources

- GPTZero — perplexity & burstiness explainers and detector docs.
- Mitchell et al., *DetectGPT: Zero-Shot Machine-Generated Text Detection using
  Probability Curvature* (arXiv:2301.11305); Fast-DetectGPT.
- Krishna et al., *Paraphrasing evades detectors of AI-generated text, but
  retrieval is an effective defense* (arXiv:2303.13408).
- Liang et al., *GPT detectors are biased against non-native English writers*
  (arXiv:2304.02819) — the ESL false-positive finding.
- Hans et al., *Spotting LLMs With Binoculars: Zero-Shot Detection of
  Machine-Generated Text* (arXiv:2401.12070).
- Verma et al., *Ghostbuster: Detecting Text Ghostwritten by Large Language
  Models* (arXiv:2305.15047).
- Yang et al., *DNA-GPT: Divergent N-Gram Analysis* (arXiv:2305.17359);
  Gehrmann et al., *GLTR* (arXiv:1906.04043); Hu et al., *RADAR*
  (arXiv:2307.03838).
- Kobak et al., *Delving into ChatGPT usage in academic writing through excess
  vocabulary* (arXiv:2406.07016) — PubMed abstracts, δ/ratio method, ~280 excess
  style words, ~66% verbs / ~18% adjectives.
- Stylometry + classifier surveys; curated practitioner word lists (plusai.com,
  embryo.com, contentbeta.com) used only as a floor.
