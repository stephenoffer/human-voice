---
name: human-voice
description: Use when generating or rewriting reports, documentation, or any prose so it does not read as AI-written — removes hedging, em-dash overuse, filler ("delve", "leverage", "seamless"), rule-of-three padding, bold-bullet listicles, meta-commentary, and vacuity, without altering facts, numbers, code, or citations. Accepts a file path or pasted text.
user-invokable: true
argument-hint: <file-path | pasted-text> [fix|generate] [register: technical|business|marketing|academic|casual|creative]
license: MIT
---

# Human Voice — De-AI-ify Reports & Docs

Use this skill whenever the user wants prose that does not read as AI-written:
rewriting an AI-sounding draft (`fix`), or drafting new copy that reads human
from the start (`generate`). It works for **any kind of writing** — technical
reports, documentation, marketing and web copy, blog posts, emails, academic
prose, and fiction — by matching the conventions of that genre (see Register
profiles). A universal core of AI tells is fixed in every genre; the rest flex.

The job is not to swap a few words. AI text gives itself away at three depths —
**lexical** (delve, leverage, seamless), **structural** (em-dash overuse,
relentless rule-of-three, bold-bullet listicles, uniform sentence length), and
**substance** (vacuity, restatement, meta-commentary, fabricated specificity,
weak stance). A pass that only changes vocabulary ships text that is still
obviously AI. Fix the deep tells first.

It draws on the same ideas as the public detectors and linters — GPTZero
(perplexity / **burstiness**), proselint, write-good, Vale — but goes past them
on substance, stance, and consistency, which no word list catches. Note that
banned-word lists age: "delve" spiked after ChatGPT then faded once writers
learned to avoid it, so treat the lexical checks as a floor, never as proof.

## What detectors actually measure (and how we beat them honestly)

AI-text detectors combine a few measurable signals. We optimize each by writing
*genuinely better* — never by gaming. See [`references/ai-tells.md`](references/ai-tells.md)
for the full landscape and sources.

- **Perplexity** — AI picks high-probability next tokens, so the text reads as
  "too predictable." Fix by genuine specificity and the accurate, less-expected
  word. The filler list *is* roughly the set of highest-probability AI tokens.
- **Burstiness** — variance of sentence length/complexity. AI is smooth and
  monotone. Mixing short punches with long sentences is the single biggest lever;
  the linter reports a sentence-length coefficient of variation for exactly this.
- **N-gram repetition & lexical diversity** — LLMs reuse bigrams/trigrams and
  connective phrases, and spread a narrow vocabulary. The linter flags repeated
  n-grams and a low type-token ratio.
- **Stylometry & classifier fingerprints** — punctuation profile, uniform
  openers, "not X, but Y", rule-of-three, tailing-significance clauses. The
  structural checks target these.

**Scope and ethics.** The promise is *reads as written by a skilled human* —
which also happens to not trip detectors — not *disguise machine text*. Never
use the adversarial tricks the evasion literature describes: Unicode homoglyphs,
zero-width characters, deliberate typos, meaning-degrading synonym swaps, or
fabricated facts/quotes/stats. Those wreck the text and violate principle 3.

## Non-negotiable operating principles

1. **Structure and substance beat vocabulary.** Fix in this order: delete
   vacuous sentences → vary rhythm → dismantle rule-of-three and bold-bullet
   templates → cut meta-commentary → *then* fix diction. Diction is last and
   least.
2. **Aim for natural variance, not a new banned-token list.** An em-dash, a
   tricolon, a "however" are all fine in moderation. Eliminating every one
   creates a *different* uniform signature that also reads as machine. Target
   burstiness (mix short and long sentences) and the accurate less-expected
   word — not zero-of-everything.
3. **Never fabricate to sound human.** Do not alter or invent facts, numbers,
   code, citations, links, defined terms, or claims to make prose flow. If a
   sentence is empty, cut it — do not dress it with fake specificity. Humanizing
   must never become fabricating.
4. **Match the register, don't default to one.** "Human" is not one voice. A
   technical report stays professional; marketing copy is conversational and
   addresses "you"; a blog post has personality; fiction has a narrator. Infer
   the genre and write the way a skilled human writes *in that genre*. The
   universal floor (below) holds everywhere; everything else flexes by register.
   Never fake personality the genre doesn't call for — forced slang in a report
   reads as AI just as much as stiff formality in a blog post does.
5. **Know the universal core.** Some tells are AI in every genre: vacuity,
   fabrication, the rule-of-three reflex, bold-bullet listicles, puffery, vague
   attribution, low burstiness (uniform sentence length), terminology and
   dialect drift, restatement, and the "not X, it's Y" template. Fix these no
   matter what you're writing. Only warmth, address ("you"/"I"), contractions,
   hedging, and structural strictness depend on register.
6. **Consistency is a tell.** One author holds one voice and one set of
   materials. Use one term per concept, one dialect, one heading style, one
   tense for findings, one author voice. Drift across a document reads as
   machine even when every sentence is clean.
7. **Earn a position.** The deepest human quality is judgment: commit to a
   recommendation, weight real (asymmetric) tradeoffs, lead with the verdict,
   give the mechanism, and name genuine limits. A balanced, non-committal survey
   reads as AI even when the prose is flawless.
8. **Be honest about measurement.** The linter is a floor (cheap, regex-able
   tells); it does **not** compute perplexity or curvature, only the surface
   features that correlate with them. Your judgment is the ceiling (vacuity,
   weak stance, fabrication no regex can see). No detector is ground truth and
   all have real false-positive rates — report a score, but state plainly that
   the real test is a skeptical human read.

## Modes

Parse `$ARGUMENTS` for a mode token and an optional `register:` token.

- **`fix`** (default when the input is an existing file path or pasted prose):
  rewrite the supplied text to remove tells while preserving every invariant.
- **`generate`** (when the input is a brief/spec, or the user says "write" /
  "draft"): produce new copy that reads human from the first draft, then run it
  through the same self-critique loop before returning it.

If a file path is given, edit the file in place after the rewrite passes the
loop, and print the Humanization Audit. If only pasted text is given (no file),
print the rewrite plus the audit — do not write any file.

Default `register` is inferred from the content (see Register profiles); if
genuinely ambiguous and it changes the voice materially, ask one short question.

## Register profiles

"Human" depends on genre. Infer the register, then apply the universal core plus
that register's conventions. Pass the matching `--register` to the linter so it
mutes checks that don't apply (e.g. warmth in marketing). The **universal core**
— vacuity, fabrication, rule-of-three, bold-bullet listicles, puffery, vague
attribution, low burstiness, drift, restatement, "not X, it's Y" — is fixed in
every profile.

| Register | Voice | What's allowed here that isn't elsewhere | Still wrong |
|---|---|---|---|
| `technical` (default) | Professional, direct, present tense | — (strictest) | warmth, "you"-selling, hype |
| `business` | Professional with a little warmth | a brief courteous opener/closer | gush, filler, hedging |
| `marketing` | Conversational, addresses "you" | "you"/"we", contractions, light enthusiasm | **puffery and hype** (the AI failure mode here), fake stats |
| `academic` | Formal, measured | measured hedging, "we"/passive, citations | unsourced "studies show", clichés |
| `casual` | Personal, conversational | contractions, "I"/"you", rhetorical questions, fragments | listicle padding, meta-commentary |
| `creative` | Narrative voice | em-dashes, fragments, wide cadence, any vocabulary in service of voice | clichés, pleonasm, puffery as lazy writing |

Two rules that survive every register: **never fabricate** (no invented facts,
stats, anecdotes, or quotes to sound human — principle 3) and **match, don't
fake** (don't bolt slang onto a report or stiff formality onto a blog post).

## Top tells (curated)

The highest-signal tells, with one-line fixes. The **full** catalog with BAD →
GOOD pairs for every category is in
[`references/ai-tells.md`](references/ai-tells.md) — load it for the rewrite.

- **Em-dash as default connector** → use commas, periods, parens; keep the rare
  earned one.
- **Rule of three everywhere** ("fast, reliable, and scalable") → vary to two or
  four, or a sentence.
- **Bold-lead-in bullets** (`- **Term:** ...` on every item) → convert some to
  prose; drop ornamental bold.
- **Meta-commentary** ("This report aims to / will explore") → state the finding.
- **Filler** (delve, leverage, robust, seamless, crucial, comprehensive,
  landscape, realm) → the plain word, or cut.
- **Hedging stacks** ("may potentially help to somewhat") → commit, or name the
  real uncertainty once.
- **Empty conclusions** ("In conclusion, X is a powerful tool…") → end on the
  last real point.
- **Uniform sentence length** → add short punches against the long sentences.
- **Vacuity** — a paragraph you can delete with no information loss → delete it.
- **Agent self-narration** ("Our analysis determined", "The agent identified") →
  say it directly ("GPU sits at 22%").
- **Fabricated specificity** ("up to 40%") with no source → cite or cut; never
  invent.
- **Puffery / hype** ("stands as a testament", "plays a vital role",
  "world-class", "rich tapestry") → a concrete claim, or cut.
- **Tailing significance clause** ("…, highlighting its commitment to X") → cut
  the empty clause or give a real consequence.
- **Vague attribution** ("studies suggest", "experts believe", "observers say")
  → name the real source or cut.
- **Redundancy** ("end result", "close proximity", "new innovation") → cut the
  free half.
- **Low burstiness** (every sentence the same length) → vary; drop a short
  sentence against a long one.
- **Emoji / decorative bold / `---` between every section** → remove.
- **Fence-sitting / false balance** ("several approaches, each with tradeoffs")
  → commit to one and say why the others lose here.
- **Terminology drift** (one concept, three names) → one term per concept.
- **Dialect / heading-case / voice drift** → one dialect, one heading
  convention, one author voice throughout.

## Rewrite procedure

Work in this order (principle 1). Do not jump to diction first.

1. **Read the whole target.** Identify the real content — the facts, numbers,
   claims, and recommendations that must survive. List the invariants (see
   Invariant guard) before you change anything.
2. **Lint for a baseline.** Run the linter (Workflow below) to get a starting
   score and a map of the cheap tells. Treat it as a floor, not a to-do list.
3. **Cut vacuity.** Delete sentences and paragraphs that carry no information.
   This usually removes 15–25% of the words and most of the "AI feel" at once.
4. **Fix rhythm (burstiness).** Break uniform sentence length — this is the
   structural half of what detectors measure. Mix short and long; drop a
   three-word sentence against a forty-word one. Read it aloud in your head; flat
   cadence is the tell. The linter reports a coefficient-of-variation score for
   this.
5. **Dismantle templates.** De-triadic the rule-of-three; convert bold-bullet
   listicles to a mix of prose and plain bullets; cut reflexive transitions and
   antithesis ("not only… but also").
6. **Cut stance tells.** Remove meta-commentary, throat-clearing, reflexive
   hedges, false balance, empty conclusions, and chatbot warmth.
7. **Sharpen the evaluation.** This is what most separates human from AI. Make
   the text take a position: commit to a recommendation instead of surveying
   options, weight real (lopsided) tradeoffs instead of false balance, lead with
   the verdict, give the mechanism (the "why"), and call a wrong choice wrong.
   Name genuine limits ("not tested on multi-node") — that is honest stance, not
   hedging. See category 8 in `references/ai-tells.md`.
8. **Unify voice and materials.** Hold one author voice end to end; use one term
   per concept (no renaming "the model" → "the LLM" → "the network"); keep one
   dialect, one heading-case convention, one tense for findings, and consistent
   number/term/list formatting. See category 7.
9. **Fix diction and jargon.** Replace filler words, clichés, and business
   jargon with the plain word the meaning needs — or cut. Apply the Anti-jargon
   rules: keep necessary technical terms, cut empty buzzwords, never stack them.
   Skip swaps that leave the sentence vague.
10. **Calibrate to the register.** Match the genre's conventions (Register
    profiles) and hold them end to end — professional for a report, conversational
    for marketing, narrative for fiction. Add what the genre wants (contractions
    in casual; "you" in marketing); never bolt on a voice the genre rejects.

## Self-critique loop (the critical pass)

After the rewrite, do not return it yet. Run an adversarial pass:

1. **Re-read as a hostile reviewer** whose only job is to answer "what *still*
   smells AI here?" Look hardest at the things the linter can't catch: substance
   (vacuity, restatement, fabrication), weak stance (fence-sitting, false
   balance, buried verdict), and drift (a concept renamed, tense or voice
   switching mid-document).
2. **Run the hallucination pass.** Diff the rewrite's claim inventory against the
   source's (Anti-hallucination protocol, step 7). Any new, strengthened,
   weakened, or re-numbered claim is a regression — revert that span.
3. **Re-run the linter** on the rewrite (add `--dialect american` or
   `--dialect british` to catch spelling drift against your chosen dialect).
4. **If** the score is at/above threshold **or** the hostile read finds a
   structural/substance/fabrication tell, fix those specific spots and repeat.
5. **Cap at 3 passes.** If tells remain after 3, stop and report them honestly
   in the audit rather than over-correcting into a new uniform signature
   (principle 2).

## Invariant guard

These must survive the rewrite unchanged. Diff-check before applying:

- All **numbers, units, dates, and measured values**.
- All **code**, commands, config keys/values, file paths, and CLI flags.
- All **links and citations** (URLs, references, footnotes).
- **Defined terms** and proper nouns (product, model, library names).
- **PII and confidentiality rules** — never add PII or internal-only URLs; honor
  any project confidentiality rules for customer-facing text.
- **Claims** — you may sharpen wording but never strengthen, weaken, or invent a
  claim to improve flow.

If a rewrite would change any invariant, revert that span and keep the original.

## Anti-hallucination protocol

Humanizing prose is exactly when fabrication creeps in: a flat sentence gets
"fixed" with a vivid invented detail, a hedge becomes a confident false claim, a
vague gesture grows a fake statistic. The rewrite must add *voice*, never
*facts*. Follow these steps every time.

1. **Build a claim inventory first.** Before editing, list every checkable claim
   in the source — numbers, dates, named entities, citations, causal/comparative
   assertions ("X is faster than Y"). These are the invariants. Nothing on this
   list may change in value, and nothing new may join it.
2. **Add no specificity the source doesn't contain.** Vague → concrete is only
   allowed when the concrete detail is already present or directly entailed. If
   the source says "improved performance," you may not write "cut latency 40%"
   or "halved p99" unless that number is in the source. Sharpen the *wording*,
   not the *facts*.
3. **Cut, don't dress, empty sentences.** When a sentence says nothing, delete
   it. Never rescue it by inventing a detail, an example, a quote, or a source.
4. **Never invent attribution.** Do not add "studies show," a named researcher,
   a date, a company, or a URL that wasn't in the source. Removing vague
   attribution is good; replacing it with a *fabricated* specific source is worse
   than leaving it vague.
5. **Mark gaps, don't fill them.** If the prose needs a fact you don't have, emit
   an explicit placeholder — `[SOURCE NEEDED]`, `[FIGURE?]`, `[VERIFY]` — and
   call it out. A visible gap is honest; an invented filler is a hallucination.
6. **`generate` mode is held to the same bar.** Drafting from a brief does not
   license invented statistics, quotes, case studies, or citations. Write only
   what the brief supports; flag everything else as a placeholder for the author.
7. **Run a dedicated hallucination pass** in the self-critique loop: diff the
   rewrite's claim inventory against the source's. Any claim that is new,
   strengthened, weakened, or re-numbered is a regression — revert that span.
   Report the diff result in the audit ("Invariants preserved: …").

A regex cannot catch a fabricated fact, so this protocol is judgment, not a
linter check — the linter only flags the *vague-attribution* and
*fabricated-specificity-shaped* phrasings that often accompany it.

## Anti-jargon rules

Jargon is the corporate cousin of filler, and the linter flags a `jargon`
category for it ("synergy", "leverage", "circle back", "move the needle",
"low-hanging fruit", "actionable", "best-in-class", "operationalize",
"paradigm shift"). Cutting words is not enough; apply the rules.

1. **Plain word first.** If a plain word carries the same meaning, use it:
   *use* not *leverage*, *talk* not *touch base*, *goal* not *north star*,
   *easy wins* not *low-hanging fruit*. The test: would a smart reader outside
   your industry understand it on first read?
2. **Keep necessary technical terms; cut empty business jargon.** A precise
   domain term a reader needs ("p99 latency", "FSDP", "idempotent") stays — it
   carries information. Buzzwords that could be deleted with no loss of meaning
   ("synergy", "value-add", "thought leadership") go. The difference is whether
   the word *does work*.
3. **Define a necessary term once, then reuse it.** Introduce an unavoidable term
   in plain language the first time, then use it consistently (this also satisfies
   the one-term-per-concept rule, principle 6). Don't rotate synonyms to sound
   varied.
4. **No buzzword stacking.** One borderline term in a sentence is a judgment call;
   three ("leverage our synergies to operationalize best-in-class solutions") is
   always wrong. Rewrite the whole sentence around what it actually claims.
5. **Watch the register.** Marketing tolerates light enthusiasm but *not* empty
   jargon — that is the marketing-specific AI failure mode. A technical report
   tolerates dense terminology but not business-speak. Match the genre; never use
   jargon as a substitute for a concrete claim.

## Anti-overcorrection guardrails

- **Do** keep the occasional em-dash, tricolon, and transition where natural.
- **Do** keep purposeful structure the document wants — callout tiers, scannable
  lists, code-comment density (see [`STYLE-GUIDE.md`](STYLE-GUIDE.md)).
- **Don't** ban a token globally; that just trades one signature for another.
- **Don't** add slang, jokes, typos, or forced first-person voice.
- **Don't** cut precision a technical doc needs in the name of "plain language".

## Workflow

1. **Resolve input.** Determine file-path vs pasted-text vs brief; pick `fix` or
   `generate`; infer `register`.
2. **Baseline lint** (skip for `generate`'s first draft):
   ```bash
   # pick the register that matches the genre (default technical)
   python3 scripts/detect_ai_prose.py --register marketing <file>
   # add an optional dialect consistency check:
   python3 scripts/detect_ai_prose.py --dialect american <file>
   # pasted text:
   printf '%s' "$TEXT" | python3 scripts/detect_ai_prose.py --register casual -
   ```
   The script covers tells (filler, hedging, meta, em-dash, bold-bullet,
   burstiness, n-gram repetition, lexical diversity) and consistency drift
   (spelling, heading case). Phrase and spelling lists live in
   `scripts/ai_prose_patterns.json`. It is the deterministic floor only — it
   cannot see vacuity, weak stance, or terminology drift. If the script is
   unavailable, degrade gracefully to pure judgment using
   `references/ai-tells.md`.
3. **Rewrite** per the procedure above, loading `references/ai-tells.md`.
4. **Self-critique loop** until clean or 3 passes.
5. **Apply / present.** For a file, edit in place; for pasted text, print the
   rewrite. Always print the Humanization Audit.
6. **Confirm invariants** with a diff (`git diff` or a before/after of numbers,
   code, links).

## Output templates

### Humanization Audit
```text
## Humanization Audit — <file or "pasted text">
Register: <technical|business|marketing|academic|casual|creative>
Score: <before> → <after>  (linter floor; not ground truth)
Words: <before> → <after>  (−NN%)
Passes run: <n>/3

Tells removed (by category):
- Substance:   <n>  e.g. cut 2 vacuous paragraphs; removed restated conclusion
- Structure:   <n>  e.g. de-triadic 4 sentences; raised burstiness 0.31→0.58
- Stance:      <n>  e.g. committed to FSDP recommendation; fixed false balance
- Consistency: <n>  e.g. "the LLM"/"the model" → "the model"; 3 dialect fixes
- Sourcing:    <n>  e.g. "studies suggest"→cited eval; cut "end result"
- Diction:     <n>  e.g. leverage→use, robust→(cut), landscape→(cut)
- Formatting:  <n>  e.g. removed 2 emoji headings, 3 section rules

Invariants preserved: numbers ✓  code ✓  links ✓  claims ✓  PII-safe ✓
Residual tells (if any): <honest list, or "none">
```

### Rewrite (pasted-text mode)
```text
## Rewrite
<the humanized text>
```

For `generate`, skip the "removed" counts (there is no before); report the final
score, the register, and confirm no fabricated specifics were introduced.
