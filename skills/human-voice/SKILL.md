---
name: human-voice
description: Use when generating or rewriting reports, documentation, or any prose so it does not read as AI-written — removes hedging, em-dash overuse, filler ("delve", "leverage", "seamless"), rule-of-three padding, bold-bullet listicles, meta-commentary, sycophancy, and vacuity, without altering facts, numbers, code, or citations. Accepts a file path or pasted text.
when_to_use: When prose "sounds like AI" or "sounds like ChatGPT", when humanizing or de-slopping a draft, when a report/email/README/landing-page reads robotic, or when drafting copy that should read human from the start. Not for: translation, summarization, or grammar-only fixes.
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
  word. The filler list is a hand-curated *proxy* for some of these
  high-probability tokens — a correlate, not a computed perplexity measurement.
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
Detectors are also demonstrably unreliable in ways that matter ethically: Liang
et al. (2023) found they disproportionately misclassify non-native-English
writing as AI. That is the strongest reason no detector is ground truth, and
another reason the goal is genuinely better writing, not a passing score.

## Weight by what readers catch, not what a scanner matches

The tells readers actually *cite* and the tells a keyword scanner *matches*
diverge sharply (a ~90k-post study of how people spot AI writing). Generic words
— `however`, `thus`, `hence`, `nuanced`, `comprehensive`, `robust`, `when it
comes to` — match constantly but are cited as a tell almost never; people just
write that way, and flagging them is how detectors wrongly catch careful and
non-native writers. So the linter parks them in `soft_filler`/`transitions` at a
low weight. What readers *do* catch is structural: flat uniform rhythm, the "not
just X, it's Y" antithesis, the five-paragraph "in conclusion" mold, **sycophancy**
("great question!", reflexive "you're absolutely right"), and **saying nothing at
length** (fluent, confident prose that makes no claim). The last two are the two
highest tells no word list can see — only your read catches them. Fix structure
and substance first; treat a generic-word hit as a whisper, not a verdict. Full
rationale and the weight tiers: [`references/cited-vs-matched.md`](references/cited-vs-matched.md).

## Non-negotiable operating principles

1. **Structure and substance beat vocabulary.** Fix in this order: delete
   vacuous sentences → vary rhythm → dismantle rule-of-three and bold-bullet
   templates → cut meta-commentary → *then* fix diction. Diction is last and
   least.
2. **Aim for natural variance, not a new banned-token list.** A tricolon, a
   "however", a semicolon are all fine in moderation. Eliminating every one
   creates a *different* uniform signature that also reads as machine. Target
   burstiness (mix short and long sentences) and the accurate less-expected
   word, not zero-of-everything. **The em-dash is the exception:** outside the
   `creative` register, treat it as a strong tell and replace nearly all of
   them. The trick that keeps this from becoming its own uniform signature is to
   *vary the replacement* — a comma here, a period there, a colon or parentheses
   or an outright restructure elsewhere — so the rhythm stays bursty even as the
   dashes go. Emoji are not human in most registers either; cut them.
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

Parse `$ARGUMENTS` for a mode token and an optional `register:` token. Parsing is
order-independent and case-insensitive: accept `fix`/`generate` in any position,
`register: marketing`, `register=marketing`, or a bare register name; treat
anything that resolves to an existing path as the input file, not a mode.

- **`fix`** (default when the input is an existing file path or pasted prose):
  rewrite the supplied text to remove tells while preserving every invariant.
- **`generate`** (when the input is a brief/spec, or the user says "write" /
  "draft"): produce new copy that reads human from the first draft, then run it
  through the same self-critique loop before returning it. Load
  [`references/structural-craft.md`](references/structural-craft.md) for the
  generative moves (vary length and density, don't follow the outline, get
  specific) — the linter catches tells but can't teach voice.

**Resolution decision tree:**

```
input is a brief/spec, or user said "write"/"draft"?  → generate
otherwise                                              → fix
contains code, metrics, or config?                     → register: technical
has a call-to-action / sells to "you"?                 → register: marketing
has citations / measured "we"?                         → register: academic
first-person anecdote, casual contractions?            → register: casual
greeting + sign-off?                                   → register: email
versioned, past-tense, bulleted change list?           → register: release_notes
numbered "how-to" steps?                               → register: tutorial
cues conflict and change the voice?                    → ask one short question
```

If a file path is given, do not overwrite it blindly. First confirm the file is
tracked by git (so the change is recoverable); if it is not, write a `<file>.bak`
copy before editing. Show the rewrite (or a before/after diff) and the
Humanization Audit, then edit in place once the rewrite passes the loop. If only
pasted text is given (no file), print the rewrite plus the audit — do not write
any file.

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
| `email` | Brief, courteous, direct | a one-line greeting/sign-off, "you"/"I" | jargon, padding, burying the ask; chatbot sign-offs |
| `release_notes` | Terse, user-facing, past tense | imperative/past bullets, fragments | marketing hype, vague "various improvements" |
| `ux_microcopy` | Minimal, plain, "you" | fragments, dropped articles, terseness | full-sentence padding, cleverness over clarity |
| `tutorial` | Instructional, second person, present | "you", imperatives, numbered steps | over-explaining the obvious, rhetorical filler |

Each register has a worked before/after pair in [`examples/`](examples/) — read the
one matching your genre before you start.

**Register-specific constraints** (beyond voice). Honor the format the genre
demands: a commit message uses imperative mood and a ~50-character subject; a
release note is past-tense and user-facing ("Fixed a crash when…", not "We
refactored…"); UX microcopy is terse and may drop articles; an email leads with
the ask. These are hard conventions, not stylistic preferences.

**Register detection cues** (when inferring). Code blocks, metrics, or config →
`technical`. A call to action, "you", or product benefit → `marketing`.
Citations, "we", measured hedging → `academic`. First-person anecdote, casual
contractions → `casual`. A greeting + sign-off → `email`. Versioned, bulleted,
past-tense change list → `release_notes`. Numbered "how to" steps → `tutorial`.
When the cues genuinely conflict and it changes the voice, ask one short question.

**When registers blend** (a technical blog post is `technical` + `casual`): the
universal core still holds; resolve voice toward the dominant audience and hold
one voice rather than switching mid-document. The calibration test: write as the
most respected human author in that genre would, and ask whether this voice would
survive in the publication it's bound for.

Two rules that survive every register: **never fabricate** (no invented facts,
stats, anecdotes, or quotes to sound human — principle 3) and **match, don't
fake** (don't bolt slang onto a report or stiff formality onto a blog post).

## Top tells (curated)

The highest-signal tells, with one-line fixes. The **full** catalog with BAD →
GOOD pairs for every category is in
[`references/ai-tells.md`](references/ai-tells.md) — load it for the rewrite.

- **Dashes** → the em-dash is one of the loudest AI tells: outside `creative`,
  replace nearly all of them with a comma, period, colon, or parentheses (vary
  the mark; don't swap every one for a comma). Keep the hyphen for compounds and
  the en-dash for ranges (10–20). Never `--` or a spaced ` - ` as a dash. The
  `--fix` autofixer rewrites em-dashes, `--`, spaced hyphens, and non-numeric
  en-dashes to commas automatically (skipped in `creative`). See category 9 in
  `references/ai-tells.md`.
- **Rule of three everywhere** ("fast, reliable, and scalable", and the
  noun-phrase kind: "encryption at rest, row-level access control, and audit
  logging") → vary to two or four, or a sentence.
- **The "second dialect"** — what's left after the obvious slop is gone: a
  uniform ", and" splice rhythm, stacked "[noun] is [noun]" copulas, and
  "[thing] lives in [place]" locatives ("a project living in five tools"). Trade
  the slop signature for a *voice*, not a tidier signature. See
  [`references/structural-craft.md`](references/structural-craft.md).
- **Bold-lead-in bullets** (`- **Term:** ...` on every item) → convert some to
  prose; drop ornamental bold.
- **Meta-commentary** ("This report aims to / will explore") → state the finding.
- **Chatbot scaffolding** ("Sure! Here's…", "Great question", "Hope this helps!",
  "Let's break it down") → delete; open on the content.
- **Over-signposting** ("Furthermore / Moreover / Additionally" as glue) → keep a
  transition only where removing it would change the logic.
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
- **False agency** (abstract subject + human verb: "the complaint becomes a fix",
  "the data tells us", "the market rewards") → name the human who acted, or use
  "you"; never invent an actor. Muted for `academic` ("the data show").
- **Narrator-from-a-distance** ("Nobody designed this", "People tend to…") → put
  the reader in the scene with "you" (a tell in reader-facing genres; fine in
  `academic`).
- **Telling not showing / vague declarative** ("The implications are
  significant", "the reasons are structural") → name the specific thing, or cut.
- **Negative listing** ("It wasn't X. It wasn't Y. It was Z.") → state Z; drop
  the runway.
- **Performative fragmentation** ("Speed. That's it. That's the tradeoff.") →
  complete sentences in exposition; fragments stay only in creative/casual.
- **Wh-opener crutch** (a run of "What makes this… / Why does this…") → lead with
  the subject and name the thing.
- **Fabricated specificity** ("up to 40%") with no source → cite or cut; never
  invent.
- **Sycophancy** ("Great question!", "You're absolutely right", "Good catch",
  "I'd be happy to help") → cut entirely; open on the content. One of the
  highest-cited tells, and a word list barely catches it.
- **Aidiolect phrases** ("a testament to", "speaks volumes", "the complex
  interplay", "faced numerous challenges", "as a powerful reminder") → multi-word
  tics the model overuses at thousands of times the human rate; rewrite the claim.
- **Cliché metaphor** ("building blocks", "the foundation of", "landscape of",
  "double-edged sword", "tip of the iceberg") → literal or domain-specific
  language; if the metaphor fits any topic, it fits none.
- **Significance inflation** ("opens new avenues", "paves the way", "cannot be
  overstated", "now more than ever") → state the finding; match claim to evidence.
- **Five-paragraph mold** (intro previews, three even body blocks, "In
  conclusion…" recap) → let the structure follow the argument; end on the last
  real point.
- **Over-correction costume** (forced all-lowercase, sprinkled "lol/idk/honestly?",
  staccato fragments, conspicuous dash-avoidance, "it's giving", "load-bearing")
  → the anti-AI costume is its own tell; write a real voice, don't just delete
  the old one. See [`references/over-correction.md`](references/over-correction.md).
- **Puffery / hype** ("stands as a testament", "plays a vital role",
  "world-class", "rich tapestry") → a concrete claim, or cut.
- **Tailing significance clause** ("…, highlighting its commitment to X") → cut
  the empty clause or give a real consequence.
- **Cowardly passives** ("It can be seen that…", "The decision was made to…",
  "Mistakes were made") → name the actor. (Actor-irrelevant passive — "deployed
  at 3 AM" — is fine.)
- **Vague attribution** ("studies suggest", "experts believe", "observers say")
  → name the real source or cut.
- **Redundancy** ("end result", "close proximity", "new innovation") → cut the
  free half.
- **Low burstiness** (every sentence the same length) → vary; drop a short
  sentence against a long one.
- **Emoji / decorative bold / `---` between every section** → remove. (`--fix`
  strips decorative emoji outside `creative`/`casual`.)
- **Doubled words** ("the the", "to to") → cut the duplicate; it's an editing typo.
- **Repetition** → vary repeated bigrams and repeated sentence openers, but keep
  one term per concept (terminology consistency is not the repetition to fix).
- **Punctuation mechanics** → no space before `,;:!?`; one terminal mark (not
  "!!" / "?!?"); one quote and ellipsis style throughout. See category 9.
- **Fence-sitting / false balance** ("several approaches, each with tradeoffs")
  → commit to one and say why the others lose here.
- **Terminology drift** (one concept, three names) → one term per concept.
- **Dialect / heading-case / voice drift** → one dialect, one heading
  convention, one author voice throughout.

### Five highest-signal fixes (BAD → GOOD)

Concrete anchors for the most common tells. The full catalog with a pair for every
category is in [`references/ai-tells.md`](references/ai-tells.md).

- **Vacuity** — BAD: "Data infrastructure is a critical component of modern
  systems and plays an important role." → GOOD: "Pick the store before you know
  your access patterns and you'll rewrite it within a year."
- **Rule of three + puffery** — BAD: "Our robust, scalable, and seamless platform
  stands as a testament to innovation." → GOOD: "It handles ingestion, indexing,
  and query in one process."
- **Buried verdict / fence-sitting** — BAD: "There are several approaches, each
  with tradeoffs; ultimately it depends on your needs." → GOOD: "Use FSDP.
  Pipeline parallelism only wins above 70B parameters, and you aren't there."
- **Chatbot scaffolding** — BAD: "Great question! Let's dive in. Here's the thing
  about caching…" → GOOD: open on the content: "Caching helps here only when
  reads dominate writes."
- **False agency** — BAD: "The complaint becomes a fix and the data tells us
  where to invest." → GOOD: name the actor: "The on-call engineer shipped the
  fix; the conversion logs showed where users dropped off." (Never invent the
  actor — if the source names none, use "you" or flag it.)

## Quick reference (one pass)

The whole skill on one screen. The detailed procedure, loop, and protocol below
expand each step.

1. **Pre-flight.** Infer mode (`fix`/`generate`) and register. List the
   invariants and build the claim inventory (numbers, dates, named entities,
   citations, causal/comparative claims). Baseline-lint for a floor score.
2. **Five edit moves, in order** (structure beats vocabulary):
   ① cut vacuity → ② vary rhythm (mix short and long sentences) → ③ dismantle
   templates (rule-of-three, bold-bullet listicles, "not X, it's Y") → ④ cut
   stance tells (meta-commentary, chatbot scaffolding, fence-sitting, empty
   conclusions) → ⑤ fix diction and jargon last.
3. **Unify.** One term per concept, one dialect, one heading case, one tense, one
   voice end to end.
4. **Critique.** Hostile re-read for what still smells AI; diff the claim
   inventory (nothing added/strengthened/weakened/dropped); re-lint. Repeat up to
   3 passes, then stop.
5. **Audit.** Print the Humanization Audit; confirm invariants with a diff.

Never fabricate to sound human. Match the register; don't bolt on a voice the
genre rejects.

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
9. **Fix diction, jargon, and mechanics.** Replace filler words, clichés, and
   business jargon with the plain word the meaning needs — or cut. Apply the
   Anti-jargon rules: keep necessary technical terms, cut empty buzzwords, never
   stack them. Fix punctuation and dashes here too: outside `creative`, replace
   nearly all em-dashes with a varied mark (comma, period, colon, parens), keep
   the hyphen for compounds and en-dash for ranges, no `--`/spaced-hyphen dashes,
   no doubled words, no space before `,;:!?`, one terminal mark. Running the
   linter with `--fix` clears the mechanical ones (em-dashes, `--`, spaced
   hyphens, emoji) before you do the judgment work. Skip swaps that leave the
   sentence vague. See category 9.
10. **Calibrate to the register.** Match the genre's conventions (Register
    profiles) and hold them end to end — professional for a report, conversational
    for marketing, narrative for fiction. Add what the genre wants (contractions
    in casual; "you" in marketing); never bolt on a voice the genre rejects.

## Self-critique loop (the critical pass)

After the rewrite, do not return it yet. Run an adversarial pass.

**Review from three angles, not one.** A single hostile reviewer misses whole
classes of tells. Read the rewrite as each of:
- the **detector researcher** — rhythm, burstiness, predictable phrasing, uniform
  openers (the mechanical signature);
- the **domain expert** — vacuity, weak stance, wrong or unsupported claims (the
  substance);
- the **genre editor** — register fit, length, format conventions (does it read
  like real writing in this genre?).

**Score each dimension 0–2**, where 0 = clearly AI, 1 = passable, 2 = genuinely
human: Substance, Rhythm, Stance, Consistency, Sourcing, Diction, Register. The
bar to return: no dimension below 1, and the mechanical ones (Rhythm, Diction)
not the only thing carrying it. This makes "good enough" measurable instead of a
vibe.

**Hit concrete targets**, not "improve it":
- burstiness CoV ≥ ~0.5 (sentence-length variation);
- em-dash density ≈0 outside `creative` (replace nearly all with varied marks);
- in `fix` mode, expect to cut 15–25% of the words;
- no run of 3+ same-length sentences — read the length sequence aloud in your head.

**Final self-check** (the rhythm is the tell your ear catches before your eye):
read the rewrite aloud. If it sounds like a metronome, vary it. Then scan: (a)
shortest vs longest sentence — under a ~15-word gap? add a short punch; (b) any
three consecutive sentences sharing a shape (all Subject-Verb-Object)? break one;
(c) did the register shift at least once between plain and precise? (d) em-dashes
> 1 outside `creative`? replace the extras; (e) any sycophancy, "in conclusion"
recap, or "not X, it's Y"? cut it; (f) one concrete detail a generic model
wouldn't have written? If a Reddit commenter would call it slop, it isn't done.

Then:

1. **Run the hallucination pass.** Diff the rewrite's claim inventory against the
   source's (Anti-hallucination protocol, step 7). Any new, strengthened,
   weakened, or re-numbered claim is a regression — revert that span. Check for
   *dropped* claims too: a cut caveat is silent information loss.
2. **A/B against the original.** Did I lose any real content? Is the rewrite
   genuinely *better*, or merely *different*? Trading the AI signature for a new
   uniform signature (everything de-listed, every em-dash gone) is a failure
   (principle 2).
3. **Re-run the linter** on the rewrite (add `--dialect american` or
   `--dialect british` to catch spelling drift against your chosen dialect).
4. **If** the score is at/above threshold **or** any dimension scores below 1,
   fix those specific spots and repeat.
5. **Stop at a fixed point, capped at 3 passes.** Stop when a pass produces no
   net improvement (diminishing returns) or no dimension is below the bar —
   whichever comes first. The cap of 3 bounds cost; it is not a target. If tells
   remain after 3, report them honestly in the audit rather than over-correcting.

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
   in the source as a `{claim, value, source-span}` triple — numbers, dates,
   named entities, citations, causal/comparative assertions ("X is faster than
   Y"). These are the invariants. Nothing on this list may change in value, and
   nothing new may join it. This list is the artifact you diff against in step 7.
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
   Every placeholder must be **enumerated in the audit**, and any output that
   still contains one is flagged as draft-pending, never presented as finished.
   Placeholders are removed only by the author, never silently by you.
6. **Preserve quotes and citations verbatim.** Never alter wording inside
   quotation marks, never turn a paraphrase into a quote, and never attach a
   citation to a claim it doesn't support to make a sharpened sentence look
   sourced.
7. **`generate` mode is held to the same bar — the brief is the invariant set.**
   Drafting from a brief does not license invented statistics, quotes, case
   studies, or citations. Write only what the brief supports; anything asserted
   beyond it is a placeholder, and the audit must **list every fact stated that
   the brief did not provide** so the author can verify or cut it.
8. **Run a dedicated hallucination pass** in the self-critique loop: diff the
   rewrite's claim inventory against the source's and sort every difference into
   four buckets — **added / strengthened / weakened / dropped** (re-numbered
   counts as changed). Added/strengthened/weakened are regressions: revert that
   span. A *dropped* real claim or caveat is silent information loss: restore it
   unless the deletion was deliberate and logged. Report the bucketed diff in the
   audit ("Invariants preserved: …").

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

- **Do** keep the occasional tricolon and transition where natural — but the
  em-dash is the exception: replace nearly all of them outside `creative`,
  varying the replacement mark so the rhythm doesn't flatten.
- **Do** keep purposeful structure the document wants — callout tiers, scannable
  lists, code-comment density (see [`STYLE-GUIDE.md`](STYLE-GUIDE.md)).
- **Don't** ban a token globally; that just trades one signature for another.
  Target *patterns in excess* (false agency, the Wh-opener run, three same-length
  fragments), not a category to zero. The newer structural checks fire on
  density and runs, not on a single instance — keep them that way. (Public lists
  like stop-slop reach for "kill all adverbs / no em dashes ever / always two not
  three"; those manufacture a fresh uniform signature, which is exactly principle
  2's failure mode.)
- **Don't** add slang, jokes, typos, or forced first-person voice. Forced
  all-lowercase, sprinkled "lol/honestly?", staccato fragments, and conspicuous
  dash-avoidance are the **anti-AI costume** — a fresh uniform signature the
  linter now flags as `over_correction`/`internet_tells` (muted only in
  `casual`/`creative`). The fix is a real deliberate voice, not the absence of
  the old tell. See [`references/over-correction.md`](references/over-correction.md).
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
   # score-only / machine-readable, and an after-vs-before comparison:
   python3 scripts/detect_ai_prose.py --quiet <file>
   python3 scripts/detect_ai_prose.py --json <file>
   python3 scripts/detect_ai_prose.py --baseline <original> <rewrite>   # prints the delta
   ```
   Run the same command on the rewrite to confirm the score and verdict band drop,
   and quote both numbers in the audit (`--baseline` prints the delta directly).
   The script covers tells (filler, hedging, meta, em-dash, bold-bullet,
   burstiness, n-gram repetition, lexical diversity) and consistency drift
   (spelling, heading case). Phrase and spelling lists live in
   `scripts/ai_prose_patterns.json`. It is the deterministic floor only — it
   cannot see vacuity, weak stance, or terminology drift. If the script is
   unavailable, degrade gracefully to pure judgment using
   `references/ai-tells.md` and this **no-tool checklist**: (a) read the
   sentence-length sequence and flag any run of 3+ similar lengths; (b) scan the
   first word of each sentence for repeated openers; (c) grep your draft for the
   top filler words (delve, leverage, robust, seamless, crucial, comprehensive,
   landscape); (d) count em-dashes (outside `creative`, essentially any is a
   tell); (e) check every list for the bold-lead-in `- **Term:**` pattern.
3. **Optional autofix.** Clear the mechanical, unambiguous tells in one pass
   before the judgment work: `python3 scripts/detect_ai_prose.py --fix --register
   <reg> <file>` rewrites em-dashes, `--`, spaced hyphens, and non-numeric
   en-dashes to commas, strips decorative emoji, and applies 1:1 filler/jargon
   swaps (em-dash + emoji fixes are skipped in `creative`; emoji also kept in
   `casual`). Use `--fix-dry-run` to preview. This never touches code, numbers,
   or links. It does not vary the replacement mark, so still do the rewrite pass.
4. **Rewrite** per the procedure above, loading `references/ai-tells.md`.
5. **Self-critique loop** until clean or 3 passes.
6. **Apply / present.** For a file, ensure it is recoverable (git-tracked or
   `.bak`d), show the rewrite/diff, then edit in place; for pasted text, print the
   rewrite. Always print the Humanization Audit.
7. **Confirm invariants** with a diff (`git diff` or a before/after of numbers,
   code, links).

## Output templates

### Humanization Audit
```text
## Humanization Audit — <file or "pasted text">
Register: <technical|business|marketing|academic|casual|creative|email|release_notes|ux_microcopy|tutorial>
Score: <before> → <after> [<band>]  (linter floor; not ground truth)
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

Dimension scores (0–2): Substance _ · Rhythm _ · Stance _ · Consistency _ · Sourcing _ · Diction _ · Register _
Invariants preserved: numbers ✓  code ✓  links ✓  claims ✓  PII-safe ✓  (claim diff: +0 added / 0 strengthened / 0 weakened / 0 dropped)
Placeholders left for author: <list of [SOURCE NEEDED]/[VERIFY], or "none">
Residual risk: <why a skeptical human might still flag this, or "none">
```

### Rewrite (pasted-text mode)
```text
## Rewrite
<the humanized text>
```

For `generate`, skip the "removed" counts (there is no before); report the final
score, the register, and confirm no fabricated specifics were introduced.
