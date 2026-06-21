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
  fragile: paraphrasing drops its accuracy from ~70% to near chance, and it
  fails on code.
- **Watermarking**: a provider-side bias in the token distribution. Nothing a
  rewrite can or should change; it exists and is provider-dependent.
- **Trained classifiers** (Originality.ai, Copyleaks, Turnitin): fine-tuned
  transformers plus stylometric and n-gram features. Addressed by the phrase,
  n-gram, and TTR checks.
- **Stylometry**: sentence/word length, type-token ratio, punctuation profile,
  function-word distribution. Addressed by burstiness, TTR, em-dash density, and
  uniform-opener checks.

Our local regex linter does **not** compute perplexity or curvature. It catches
the surface features that *correlate* with what these systems measure. The real
test is a skeptical human read — and we never use the adversarial tricks
(homoglyphs, zero-width characters, meaning-degrading synonym swaps, fabrication)
that the evasion literature describes. Those degrade the writing.

## Sources

- GPTZero — perplexity & burstiness explainers and detector docs.
- Mitchell et al., *DetectGPT: Zero-Shot Machine-Generated Text Detection using
  Probability Curvature* (arXiv:2301.11305); Fast-DetectGPT.
- Krishna et al., *Paraphrasing evades detectors of AI-generated text, but
  retrieval is an effective defense* (arXiv:2303.13408).
- Kobak et al., *Delving into ChatGPT usage in academic writing through excess
  vocabulary* (arXiv:2406.07016) — PubMed abstracts, δ/ratio method, ~280 excess
  style words, ~66% verbs / ~18% adjectives.
- Stylometry + classifier surveys; curated practitioner word lists (plusai.com,
  embryo.com, contentbeta.com) used only as a floor.
