---
name: human-voice
description: Use when generating or rewriting reports, documentation, or any prose so it does not read as AI-written. Removes hedging, em-dash overuse, filler ("delve", "leverage", "seamless"), rule-of-three padding, bold-bullet listicles, meta-commentary, sycophancy, and vacuity, without altering facts, numbers, code, or citations. Accepts a file path or pasted text. Trigger when prose "sounds like AI" or "sounds like ChatGPT", when humanizing or de-slopping a draft, when a report, email, README or landing page reads robotic, or when drafting copy that should read human from the start. Not for translation, summarization, or grammar-only fixes.
license: MIT
compatibility: Model-agnostic Agent Skill. Works in any agent that loads SKILL.md (Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Windsurf, Cline, opencode). The optional linter needs Python 3.8+ and no packages or network.
metadata:
  argument-hint: "<file-path | pasted-text> [fix|generate] [register: technical|business|marketing|academic|casual|creative]"
  version: "0.9.0"
---

# Human Voice: de-AI-ify reports and docs

Use this skill whenever the user wants prose that does not read as AI-written:
rewriting an AI-sounding draft (`fix`), or drafting new copy that reads human
from the start (`generate`). It works for **any kind of writing**: technical
reports, documentation, marketing and web copy, blog posts, emails, academic
prose, and fiction. It matches the conventions of that genre (see Register
profiles). A universal core of AI tells is fixed in every genre; the rest flex.

The job is not to swap a few words. AI text gives itself away at five depths, and
they are not equally loud:

1. **Shape**: the document is a chat answer in a document's clothes: a heading
   every eighty words, a third of the lines bulleted, bold on every term, a "Key
   takeaways" close. This is the loudest signal and the one most passes skip.
2. **Architecture**: what the document spends its words on. The overview comes
   back as the summary, one section runs four hundred words while three hold a
   sentence each, and the depth swings from a p99 to "in simple terms, a cache
   is". No sentence is wrong, so a sentence-level pass never sees it.
3. **Rhythm**: sentences collapsed into the 12-26 word band with no short
   punches and no long runs; paragraphs all the same size.
4. **Substance**: vacuity, restatement, meta-commentary, fabricated
   specificity, a survey where a verdict belongs.
5. **Diction**: delve, leverage, seamless. Real, and least important.

Fix them in that order. A pass that starts at 5 ships text that is still
obviously machine-written, which is most of what "humanizer" tools do.

It draws on the same ideas as the public linters (proselint, write-good, Vale)
but goes past them on shape, substance, stance, and consistency, which no word
list catches. Note that banned-word lists age: "delve" spiked after ChatGPT then
faded once writers learned to avoid it, so treat the lexical checks as a floor,
never as proof. What the rest of the field does, which of their techniques were
adopted after measurement, and which were tested and thrown out:
[`references/competitive-landscape.md`](references/competitive-landscape.md).

## What detectors actually see

The evidence here has moved, and it moved in a direction that changes the edit
order. Full landscape and sources: [`references/what-detectors-see.md`](references/what-detectors-see.md).

Detectors are not responding to "machine-ness". Base models (pretrained
checkpoints that never went through instruction tuning) are classified **human**
by commercial detectors more than 96% of the time. The same weights after
instruction tuning get caught. So the signal comes from post-training, and the
artifacts it leaves are:

- **markdown formatting preference**: headings, bulleted lists, bolded runs
- **response-length and structural conventions**, the shape of a reply. Frame the
  topic, cover it in even sections, close by wrapping up
- **sycophancy**
- and only then the distributional stuff: low token surprisal (what "perplexity"
  names) and its flat variance across the text (what "burstiness" names)

Word choice sits at the bottom of that list. Swapping `delve` for `explore`
barely moves a verdict; deleting the headings from a bulleted answer moves it a
lot. Measured on this repo's own corpus, the tells that catch 2023-era caricature
are `filler` and `meta_commentary` (word-level), while the tells that catch prose
a *current* model writes are `sentence_shape`, `paragraph_uniformity`, and
`burstiness`. All shape. So: strip the assistant shape, fix the rhythm, add real
specificity, and fix diction last.

**Which detectors a rewrite actually moves.** The statistical family
(FastDetectGPT, Binoculars, most free web tools) computes token surprisal, and
rhythm plus specificity move it a long way. General trained classifiers (GPTZero,
Copyleaks, Winston, Turnitin) move partly. Classifiers trained specifically on
humanizer output do not move much, at around 97% accuracy on rewritten text. Say
this plainly when asked: the skill makes text read human, which stops most
detectors, and no honest method guarantees evasion of the hardened ones.

**Why the evasion tricks lose on their own terms.** The vendor with the strongest
published numbers reports that *the more fluent a humanizer's output, the more
reliably it is detected*, because the tools that evade do it by damaging text and
the damage is the signature. Tortured synonyms ("counterfeit consciousness"),
Unicode homoglyphs and zero-width characters, injected typos: each is trivially
detected, each makes the writing worse, and each violates principle 3. Never use
them. Detectors also carry false-positive rates that land on real people: Liang
et al. (2023) found GPT detectors systematically misclassify non-native-English
writing as machine-generated. That is a further reason no detector is ground truth
in either direction.

## Weight by what readers catch, not what a scanner matches

The tells readers actually *cite* and the tells a keyword scanner *matches*
diverge sharply (a ~90k-post study of how people spot AI writing). Generic words
like `however`, `thus`, `hence`, `nuanced`, `comprehensive`, `robust`, `when it
comes to` match constantly but are cited as a tell almost never; people just
write that way, and flagging them is how detectors wrongly catch careful and
non-native writers. So the linter parks them in `soft_filler`/`transitions` at a
low weight. What readers *do* catch is structural: flat uniform rhythm, the "not
just X, it's Y" antithesis, the five-paragraph "in conclusion" mold, **sycophancy**
("great question!", reflexive "you're absolutely right"), and **saying nothing at
length** (fluent, confident prose that makes no claim). The last two are the two
highest tells no word list can see; only your read catches them. Fix structure
and substance first; treat a generic-word hit as a whisper, not a verdict. Full
rationale and the weight tiers: [`references/cited-vs-matched.md`](references/cited-vs-matched.md).

## Non-negotiable operating principles

1. **Shape beats structure beats substance beats vocabulary.** Fix in this
   order: strip the assistant shape (heading/bullet/bold density, the recap
   section) → fix the architecture (merge restated points, weigh sections by what
   the reader needs, hold one depth throughout, never cutting a distinct claim
   without the author's approval) → delete vacuous sentences → fix the sentence-length *distribution*,
   not just its variance → dismantle rule-of-three and bold-bullet templates →
   cut meta-commentary → *then* fix diction. Diction is last and least. This
   order is not a preference; it is what the measurement says (see What
   detectors actually see).
2. **Aim for natural variance, not a new banned-token list.** A tricolon, a
   "however", a semicolon are all fine in moderation. Eliminating every one
   creates a *different* uniform signature that also reads as machine. Target
   burstiness (mix short and long sentences) and the accurate less-expected
   word, not zero-of-everything. **The em-dash is the exception:** outside the
   `creative` register, treat it as a strong tell and replace nearly all of
   them. The trick that keeps this from becoming its own uniform signature is to
   *vary the replacement*. A comma here, a period there, a colon or parentheses
   or an outright restructure elsewhere, so the rhythm stays bursty even as the
   dashes go. The linter holds you to this: a document with an unusual semicolon
   rate and not one dash anywhere fires `over_correction`, because swapping every
   dash for the same substitute installs a fresh uniform signature in place of the
   old one. Emoji are not human in most registers either; cut them.
3. **Never fabricate to sound human.** Do not alter or invent facts, numbers,
   code, citations, links, defined terms, or claims to make prose flow. If a
   sentence is empty, cut it. Do not dress it with fake specificity. Humanizing
   must never become fabricating.
4. **Match the register, don't default to one.** "Human" is not one voice. A
   technical report stays professional; marketing copy is conversational and
   addresses "you"; a blog post has personality; fiction has a narrator. Infer
   the genre and write the way a skilled human writes *in that genre*. The
   universal floor (below) holds everywhere; everything else flexes by register.
   Never fake personality the genre doesn't call for. Forced slang in a report
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
8. **Be honest about measurement.** Three instruments, three limits. The linter
   is a floor: cheap regex-able tells, no perplexity, no model, and a document can
   score 0.0 and still be flagged. The verification gate
   (`scripts/verify_detector.py`) is the only thing that actually asks a detector,
   and it is one detector at one threshold, not a guarantee about another, and it is
   worthless until you have checked that detector against writing you know is human.
   Your judgment is the ceiling: vacuity, weak stance, and fabrication that no regex
   and no classifier reliably catch. Report all three, never upgrade a gate that
   could not run into a pass, and never treat a detector score as the objective. No
   detector is ground truth in either direction, all carry real false-positive rates,
   and the skeptical human read is still the test that matters.

## Scope and persistence

Once this skill is invoked it governs prose for the rest of the session, not only
the file in front of you. The rules do not expire after a turn or two, and they
do not lapse when the topic changes. If you are unsure whether they still apply,
they do.

That matters more here than it looks. Most of the damage does not come from a bad
rewrite. It comes from a good one handed back inside a paragraph of
chat-assistant prose, or from a second document drafted an hour later in the
default voice because nobody thought to say "humanize" twice.

So the scope is everything you write while the skill is on. The artifact is the
obvious case. The response carrying it is the one people miss: no "Great
question", no "I've now rewritten your document to remove several AI tells", no
"Let me know if you'd like me to adjust anything". Open on the finding. Stop when
the finding is done. A pass that strips sycophancy out of a report and then hands
it over with "Hope this helps!" has taught the reader nothing. The same rule
reaches commit messages, PR descriptions, issue comments and the doc comments you
leave in code, and it holds for every later draft until the user turns it off.

They turn it off by saying so: "stop human-voice", "normal voice", "drop the
voice rules". Confirm in one line, then go back to your default style.

Two things stay on either way, because they were never stylistic. Never fabricate
(principle 3). Never alter an invariant (Invariant guard). Those are honesty
rules wearing a style skill's clothes, and switching off the voice does not
switch them off.

## Modes

Parse the invocation arguments (`$ARGUMENTS` where the agent substitutes it,
otherwise the user's message) for a mode token and an optional `register:` token. Parsing is
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
  specific). Before drafting anything with sections, budget the words by what the
  reader needs rather than by the outline, and decide the reader's depth once
  ([`references/content-architecture.md`](references/content-architecture.md)).
  The linter catches tells but can't teach voice.

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
pasted text is given (no file), print the rewrite plus the audit. Do not write
any file.

Default `register` is inferred from the content (see Register profiles); if
genuinely ambiguous and it changes the voice materially, ask one short question.

## Pick the depth of the pass

The procedure below runs twelve steps, plus an intake, a three-angle critique and
a detector gate. Spend all of that on a two-line Slack message and you have spent
more than the message is worth, which in practice means the skill gets skipped
entirely the next time it would have helped. Use the fewest steps that still fix
the text. A short pass finished beats a full pass abandoned.

Pick the depth by what it costs if a reader decides a machine wrote this.

**Quick**: a chat reply, a Slack message, a code comment, a commit message.
Roughly under 150 words. Strip the assistant shape, cut the vacuity, fix diction
on the way past. No intake, no linter, no audit. Report in one line or not at all.

**Standard**: an email, an internal doc, a README section, release notes;
nothing a stranger will judge the author by. Intake from material already in the
draft and the surrounding context, without stopping to ask. Full rewrite
procedure, one self-critique pass, linter if it is there. Audit trimmed to the
score, the word delta, and the categories you actually touched.

**Full**: anything published, customer-facing, graded, or submitted.
Anything where being taken for AI carries a real cost. Everything: intake including
questions to the user, the rewrite procedure, the three-angle critique scored to
the 0–2 bar, the concrete targets, the hallucination diff, the detector gate, the
complete audit.

When the depth is genuinely unclear, ask, or go one level up. Guessing low on a
landing page is the expensive mistake. Guessing high on a Slack message costs a
little time.

Depth changes how much you run, never how strictly you run it. The invariant
guard and the anti-hallucination protocol apply at every level, and a gap gets
marked rather than filled whether or not there is an audit to list it in.

## Register profiles

"Human" depends on genre. Infer the register, then apply the universal core plus
that register's conventions. Pass the matching `--register` to the linter so it
mutes checks that don't apply (e.g. warmth in marketing). The **universal core**
(vacuity, fabrication, rule-of-three, bold-bullet listicles, puffery, vague
attribution, low burstiness, drift, restatement, "not X, it's Y") is fixed in
every profile.

| Register | Voice | What's allowed here that isn't elsewhere | Still wrong |
|---|---|---|---|
| `technical` (default) | Professional, direct, present tense | none (strictest) | warmth, "you"-selling, hype |
| `business` | Professional with a little warmth | a brief courteous opener/closer | gush, filler, hedging |
| `marketing` | Conversational, addresses "you" | "you"/"we", contractions, light enthusiasm | **puffery and hype** (the AI failure mode here), fake stats |
| `academic` | Formal, measured | measured hedging, "we"/passive, citations | unsourced "studies show", clichés |
| `casual` | Personal, conversational | contractions, "I"/"you", rhetorical questions, fragments | listicle padding, meta-commentary |
| `creative` | Narrative voice | em-dashes, fragments, wide cadence, any vocabulary in service of voice | clichés, pleonasm, puffery as lazy writing |
| `email` | Brief, courteous, direct | a one-line greeting/sign-off, "you"/"I" | jargon, padding, burying the ask; chatbot sign-offs |
| `release_notes` | Terse, user-facing, past tense | imperative/past bullets, fragments | marketing hype, vague "various improvements" |
| `ux_microcopy` | Minimal, plain, "you" | fragments, dropped articles, terseness | full-sentence padding, cleverness over clarity |
| `tutorial` | Instructional, second person, present | "you", imperatives, numbered steps | over-explaining the obvious, rhetorical filler |

Each register has a worked before/after pair in [`examples/`](examples/). Read the
one matching your genre before you start. Two pairs are worth reading whatever the
genre: [`modern-ai-before.md`](examples/modern-ai-before.md) (prose a current model
writes, and why it still reads generated) and
[`syntax-signature-before.md`](examples/syntax-signature-before.md), which has no
filler, no hedging, no bold bullets and not one em-dash, scores 47.3, and is
machine-written entirely through its grammar. Its annotation
([`syntax-signature-notes.md`](examples/syntax-signature-notes.md)) walks the nine
clefts and three participial tails line by line.

**Register-specific constraints** (beyond voice). Honor the format the genre
demands: a commit message uses imperative mood and a ~50-character subject; a
release note is past-tense and user-facing ("Fixed a crash when…", not "We
refactored…"); UX microcopy is terse and may drop articles; an email leads with
the ask. These are hard conventions, not stylistic preferences.

**When registers blend** (a technical blog post is `technical` + `casual`): the
universal core still holds; resolve voice toward the dominant audience and hold
one voice rather than switching mid-document. The calibration test: write as the
most respected human author in that genre would, and ask whether this voice would
survive in the publication it's bound for.

Two rules that survive every register: **never fabricate** (no invented facts,
stats, anecdotes, or quotes to sound human, principle 3) and **match, don't
fake** (don't bolt slang onto a report or stiff formality onto a blog post).

**A register is never exempt from a check, only more tolerant of it.** Where a
genre legitimately runs hot on a construction, the linter widens the bar rather
than switching the check off (`register_thresholds`). Creative prose gets 1.3x
the cleft rate before `cleft` fires, not an exemption, because the exemption was
letting fiction stack the construction at any rate and score zero.

Two tells to watch by eye in `creative`, where the linter deliberately stays
quiet: the **comma-anchored analogy tail** (", the way snow lies on a road nobody
drives") and the **negated definition** (a coffee he did not want, a name that was
not his). Both separate cleanly on this repo's corpus and neither is scored,
because each is also ordinary fiction and firing on one instance is what principle
2 forbids. Reasoning: [`references/competitive-landscape.md`](references/competitive-landscape.md).

## Top tells, in order of how loud they are

Tiered, because a flat list of forty prohibitions gives no priority signal and
produces keyword-avoidance instead of writing. The tiers come from the
measurement (see What detectors actually see): Tier 1 is shape and rhythm, and
it is where the signal is. The **full** catalog with BAD → GOOD pairs for every
category is [`references/ai-tells.md`](references/ai-tells.md). Load it for the
rewrite.

### Tier 1: shape and rhythm (fix these first; they carry most of the signal)

- **Assistant shape** (a heading every ~80 words, a third of lines bulleted, bold
  on every term, a "Key takeaways"/"In conclusion" recap section) → reformat to
  what the *genre* would look like written by a person. Usually far less markdown.
  Linter: `assistant_shape`.
- **Compressed sentence lengths** (everything 12–26 words, no short punches, no
  long runs) → reach past both ends. At least one sentence in eight at ≤8 words.
  Linter: `sentence_shape`, `burstiness`.
- **Even paragraphs** (every block the same size) → let a paragraph be one
  sentence when that's what the point needs. Linter: `paragraph_uniformity`.
- **Bold-lead-in bullets** (`- **Term:** ...` on every item) → convert some to
  prose; drop ornamental bold.
- **Five-paragraph mold** (intro previews, three even body blocks, "In
  conclusion…" recap) → let structure follow the argument; end on the last real
  point.
- **Uniform openers / Wh-opener runs / SVO monotony** (a run of "What makes
  this… / Why does this…"; every sentence Subject-Verb-Object) → vary the entry
  point; lead with the subject and name the thing.
- **Dashes** → outside `creative`, the em-dash is a loud tell: replace nearly all
  of them, *varying* the mark (comma, period, colon, parentheses, restructure) so
  the rhythm doesn't flatten. Keep the hyphen for compounds and the en-dash for
  ranges (10–20). Never `--` or a spaced ` - ` as a dash. `--fix` does the
  mechanical part.
- **Rule of three everywhere** ("fast, reliable, and scalable"; also the
  noun-phrase kind, "encryption at rest, row-level access control, and audit
  logging") → vary to two or four, or a sentence.
- **Paste residue** (`oaicite`, `turn0search3`, `[cite: 4]`, `grok_render_...`,
  `utm_source=chatgpt.com` on a link, an unfilled `[Your Name]`) → delete it.
  These are the only tells here that are proof rather than evidence: no writer
  types them, and they mean the text went from a chat window into a document
  unread. Linter: `llm_artifact`.
- **Assembled heading trees** (a level skipped, a second H1, a heading whose whole
  body is the next heading, a heading running straight into a bullet list) →
  write the section, or merge the headings. Linter: `heading_structure`.
- **Content architecture** (the overview reworded as the summary; stub sections
  beside a bloated one; five sections of identical length; framing that outweighs
  the subject; a hollow "Scalability" section next to one quoting config keys;
  "in simple terms" in a document for experts) → build a section map, merge
  restatements, weigh sections by the reader's questions, and hold one depth.
  Anything a section alone says moves; it is not cut without the author's
  approval. Linter: `restatement`, `section_balance`, `depth_drift`. Full pass:
  [`references/content-architecture.md`](references/content-architecture.md).
- **The "second dialect"**: what's left after the obvious slop is gone: a uniform
  ", and" splice rhythm, stacked "[noun] is [noun]" copulas, "[thing] lives in
  [place]" locatives. Trade the slop signature for a *voice*, not a tidier
  signature. See [`references/structural-craft.md`](references/structural-craft.md).

#### The syntactic signature (what a current model writes when the slop is gone)

The lexical lists catch 2023. A model in 2026 writes clean, well-organized prose
whose tells are grammatical rather than lexical. Four constructions carry most of
it. Each one is ordinary English that good writers use, so **the tell is the
stacking, never the single instance**, and that is how the linter gates them.

- **Clefts** ("What actually consumed the time was the reconciliation", "The
  reason this was hard is that…", "It is the second call that fails") → the
  sentence delays its subject to stage the point. One is rhetoric. Four in a page
  is a cadence. Put the subject first and say the thing. Linter: `cleft`.
- **Resultative participial tails** (", making it easier to…", ", allowing teams
  to…", ", ensuring that…", ", giving us a concrete list") → a consequence clause
  bolted onto sentence after sentence, manufacturing payoff for free. It also
  slips the claim past unexamined, so cutting it usually improves the argument
  and not just the rhythm. Split it into its own sentence or drop it. Linter:
  `participial_tail`.
- **Copula avoidance**: the opposite failure, and the newer one. Nothing is
  allowed simply to *be* anything, so each subject instead *serves as*, *stands
  as*, *functions as*, *represents*, *embodies* or *boasts*. Wikipedia's
  AI-Cleanup corpus measured "is" and "are" falling more than 10% after 2022 while
  these rose. Say what the thing is. Linter: `copula_avoidance`.
- **Copula density**: everything simply *is*. X is Y, Y is important, the result
  is Z. A paragraph where nothing happens reads as a glossary read aloud, and it
  correlates with the vacuity in Tier 2. Give the sentences verbs that do work.
  Linter: `copula_density`.
- **Clause welding** (", and it is…", ", but this means…" four or five times a
  page) → correct English, and doing it repeatedly flattens the prose into one
  continuous middle-length line. End the sentence. Linter: `clause_splice`.

Two more shape checks in the same family: every paragraph opening with the same
two words (`paragraph_openers`) and every list item opening with the same word or
an -ing verb (`bullet_openers`). Both are templating a reader sees while skimming.

### Tier 2: substance and stance (no regex sees these; only your read does)

- **Vacuity**: a paragraph you can delete with no information loss → delete it.
  The highest tell in the list and the one no tool catches.
- **Sycophancy** ("Great question!", "You're absolutely right", "Good catch",
  "I'd be happy to help") → cut entirely; open on the content.
- **Fence-sitting / false balance** ("several approaches, each with tradeoffs")
  → commit to one and say why the others lose here.
- **Meta-commentary** ("This report aims to / will explore") → state the finding.
- **Chatbot scaffolding** ("Sure! Here's…", "Let's break it down") → delete; open
  on the content.
- **Empty conclusions** ("In conclusion, X is a powerful tool…") → end on the
  last real point.
- **Fabricated specificity** ("up to 40%") with no source → cite or cut; never
  invent.
- **Vague attribution** ("studies suggest", "experts believe") → name the real
  source or cut.
- **Telling not showing / vague declarative** ("The implications are
  significant", "the reasons are structural") → name the specific thing, or cut.
- **Agent self-narration** ("Our analysis determined", "The agent identified") →
  say it directly ("GPU sits at 22%").
- **False agency** (abstract subject + human verb: "the data tells us", "the
  market rewards") → name the human who acted, or use "you"; never invent an
  actor. Muted for `academic` ("the data show").
- **Narrator-from-a-distance** ("Nobody designed this", "People tend to…") → put
  the reader in the scene with "you". Fine in `academic`.
- **Hedging stacks** ("may potentially help to somewhat") → commit, or name the
  real uncertainty once.
- **Cowardly passives** ("It can be seen that…", "Mistakes were made") → name the
  actor. Actor-irrelevant passive ("deployed at 3 AM") is fine.
- **Negative listing** ("It wasn't X. It wasn't Y. It was Z.") → state Z; drop
  the runway.
- **Tailing significance clause** ("…, highlighting its commitment to X") → cut
  it, or give a real consequence.

### Tier 3: diction, mechanics, consistency (last, and least)

- **Filler** (delve, leverage, robust, seamless, crucial, comprehensive,
  landscape, realm) → the plain word, or cut.
- **Aidiolect phrases** ("a testament to", "speaks volumes", "the complex
  interplay", "faced numerous challenges") → multi-word tics the model overuses
  at thousands of times the human rate; rewrite the claim.
- **Puffery / hype** ("stands as a testament", "world-class", "rich tapestry") →
  a concrete claim, or cut.
- **Significance inflation** ("opens new avenues", "paves the way", "cannot be
  overstated") → state the finding; match claim to evidence.
- **Cliché metaphor** ("building blocks", "double-edged sword", "tip of the
  iceberg") → literal or domain-specific language. If the metaphor fits any
  topic, it fits none.
- **Over-signposting** ("Furthermore / Moreover / Additionally" as glue) → keep a
  transition only where removing it would change the logic.
- **Redundancy** ("end result", "close proximity", "new innovation") → cut the
  free half.
- **Terminology drift** (one concept, three names) → one term per concept. This is
  the repetition you *keep*.
- **Dialect / heading-case / voice drift** → one dialect, one heading convention,
  one author voice throughout.
- **Emoji / decorative bold / `---` between every section** → remove. (`--fix`
  strips decorative emoji outside `creative`/`casual`.)
- **Doubled words** ("the the") → cut the duplicate; it's an editing typo.
- **Punctuation mechanics** → no space before `,;:!?`; one terminal mark; one
  quote and ellipsis style throughout. Curly quotes mixed lopsidedly with straight
  ones usually marks the seam where pasted output meets typed text. Linter:
  `quote_style`.
- **N-gram repetition** → vary repeated bigrams and repeated sentence openers.

### The costume is not the fix

- **Over-correction costume** (forced all-lowercase, sprinkled "lol/idk/honestly?",
  staccato fragments, conspicuous dash-avoidance, "it's giving", "load-bearing")
  → the anti-AI costume is its own uniform signature, and the linter flags it as
  `over_correction`/`internet_tells`. Deleting the old tell is not the same as
  having a voice. See [`references/over-correction.md`](references/over-correction.md).
- **Performative fragmentation** ("Speed. That's it. That's the tradeoff.") →
  complete sentences in exposition; fragments stay only in `creative`/`casual`.
- **One-mark punctuation substitution** (every em-dash became a semicolon, or a
  colon, or a comma) → the tool's own fingerprint, and the linter flags it as
  `over_correction`. The human maximum on this repo's corpus is 5.5 semicolons per
  1,000 words; above 7 with no dash anywhere, the document has been through a
  mechanical pass rather than an edit.

### Five highest-signal fixes (BAD → GOOD)

Concrete anchors for the most common tells. The full catalog with a pair for every
category is in [`references/ai-tells.md`](references/ai-tells.md).

- **Vacuity.** BAD: "Data infrastructure is a critical component of modern
  systems and plays an important role." → GOOD: "Pick the store before you know
  your access patterns and you'll rewrite it within a year."
- **Rule of three + puffery.** BAD: "Our robust, scalable, and seamless platform
  stands as a testament to innovation." → GOOD: "It handles ingestion, indexing,
  and query in one process."
- **Buried verdict / fence-sitting.** BAD: "There are several approaches, each
  with tradeoffs; ultimately it depends on your needs." → GOOD: "Use FSDP.
  Pipeline parallelism only wins above 70B parameters, and you aren't there."
- **Chatbot scaffolding.** BAD: "Great question! Let's dive in. Here's the thing
  about caching…" → GOOD: open on the content: "Caching helps here only when
  reads dominate writes."
- **False agency.** BAD: "The complaint becomes a fix and the data tells us
  where to invest." → GOOD: name the actor: "The on-call engineer shipped the
  fix; the conversion logs showed where users dropped off." (Never invent the
  actor: if the source names none, use "you" or flag it.)

## Author-material intake

A rewrite that can only subtract cannot produce a voice. Deleting every tell
leaves clean, generic, unowned prose. That is the over-correction failure mode,
and a careful reader still calls it machine-written, because nothing in it could
only have come from one person.

What makes text read as authored is *material*: a name, a date, a number, a thing
that went wrong, a preference held without justification, an admitted gap. That
material also does the work of lowering predictability, which is the honest
version of "raising perplexity". And principle 3 forbids inventing any of it. So
it has to be sourced. Do this **before** the subtractive passes, because knowing
what you can add changes what you delete.

Where to get it, in order of preference:

1. **Already in the draft, buried.** Vague sentences often sit on top of a real
   specific. "Performance improved significantly" next to a table with a p99
   column means the number is right there; use it.
2. **In the surrounding context you already have.** For a file in a repo: the git
   log, the issue it references, the test that covers it, the config it reads.
   For a document with sources attached: the sources. This is legitimate, because
   it is the same material the author had.
3. **From the user, by asking.** When the draft needs specifics it does not have,
   ask for them in one short batch rather than one at a time. Three or four
   questions, concrete, answerable in a sentence each:
   - What actually happened here that a stranger wouldn't guess?
   - What number, date, or name belongs in this paragraph?
   - What did you try that didn't work?
   - What do you believe about this that you can't fully defend?
   The last one is the highest-yield question in the set. An unhedged preference
   is something models produce almost never and people produce constantly.
4. **Nowhere, so mark it.** `[SOURCE NEEDED]`, and enumerate it in the audit.
   Never fill the gap (principle 3, anti-hallucination protocol).

Ask only when it will change the output. For a short internal email, skip the
intake and rewrite what's there. For a report, a landing page, or anything that
will be read by someone deciding whether a person wrote it, the intake is the
step that does the most work, and skipping it is why most humanized text still
reads humanized.

In `generate` mode the intake *is* the brief: everything you write must trace to
it, and the audit lists every stated fact the brief did not supply.

## Rewrite procedure

Work in this order (principle 1). Do not jump to diction first.

1. **Read the whole target.** Identify the real content: the facts, numbers,
   claims, and recommendations that must survive. List the invariants (see
   Invariant guard) before you change anything.
2. **Lint for a baseline.** Run the linter (Workflow below) to get a starting
   score and a map of the cheap tells. Treat it as a floor, not a to-do list.
3. **Strip the assistant shape.** Do this before touching a single word. Ask
   what this document would look like if a person had written it in this genre,
   and reformat to that. Concretely: cut headings that are dividing a continuous
   argument rather than marking real sections; turn bulleted answers back into
   paragraphs where the items are not genuinely parallel list material; delete
   bold that decorates rather than distinguishes; delete any "In conclusion" /
   "Key takeaways" / "Final thoughts" recap section and end on the last real
   point. An essay has almost no markdown. A reference doc has headings but not
   one every eighty words. A postmortem has prose and maybe a timeline. Keep the
   formatting the *genre* wants, not the formatting a chat reply wants. The
   linter measures this as `assistant_shape`; the metrics line reports headings
   per 1k words, the bullet-line ratio, and bold spans per 1k. This single move
   changes more than every diction fix combined. See What detectors actually see.
4. **Fix the architecture.** Still before any sentence work. Build the section map
   from [`references/content-architecture.md`](references/content-architecture.md):
   one line per section with its word count, the one thing it says, its depth
   (0 framing to 3 implementation), what it repeats, and what it alone says. Then
   merge restated points into the copy that does the most work, fold stubs into
   their neighbours, give the most words to what a reviewer will ask about, bring
   hollow sections to the depth of the rest, and move the decision to the top.
   **Distinct information is never cut without approval.** A fact, number, name,
   commitment, decision, caveat or owner that appears in only one place moves or
   gets reworded. It does not get deleted. If it should go, ask the author (in an
   interactive session, before editing), or leave it and list it under Proposed
   cuts in the audit. The linter reports `restatement` (naming what a repeat alone
   carries), `section_balance` and `depth_drift`, plus a `structure:` metrics line.
5. **Cut vacuity.** Delete sentences and paragraphs that carry no information.
   This usually removes 15–25% of the words and most of the remaining "AI feel".
6. **Fix the sentence-length distribution.** Not just its variance. Its shape.
   Model prose collapses into the 12–26 word band; human prose reaches past both
   ends. Coefficient of variation misses this because one long sentence inflates
   it while everything else stays uniform, so aim at the tails directly: at least
   12% of sentences at eight words or fewer, under 72% inside the mid band. Drop
   a four-word sentence against a forty-word one. Read it aloud in your head;
   flat cadence is the tell. The linter reports CoV, the short-sentence ratio,
   and the mid-band ratio (`burstiness` and `sentence_shape`).
7. **Dismantle templates.** De-triadic the rule-of-three; convert bold-bullet
   listicles to a mix of prose and plain bullets; cut reflexive transitions and
   antithesis ("not only… but also").
   Then take a pass for the **syntactic signature** (Tier 1): unstage the clefts
   ("What made this hard was X" → "X made this hard"), cut the ", making it
   easier to…" tails or promote them to their own sentence, give the copula
   sentences real verbs, and break the ", and it is…" chains into separate
   sentences. The linter's `syntax:` metrics line reports all four counts. These
   are the constructions a current model produces most reliably, and a draft can
   pass every diction check while still being written entirely in them.
8. **Cut stance tells.** Remove meta-commentary, throat-clearing, reflexive
   hedges, false balance, empty conclusions, and chatbot warmth.
9. **Sharpen the evaluation.** This is what most separates human from AI. Make
   the text take a position: commit to a recommendation instead of surveying
   options, weight real (lopsided) tradeoffs instead of false balance, lead with
   the verdict, give the mechanism (the "why"), and call a wrong choice wrong.
   Name genuine limits ("not tested on multi-node"). That is honest stance, not
   hedging. See category 8 in `references/ai-tells.md`.
10. **Unify voice and materials.** Hold one author voice end to end; use one term
   per concept (no renaming "the model" → "the LLM" → "the network"); keep one
   dialect, one heading-case convention, one tense for findings, and consistent
   number/term/list formatting. See category 7.
11. **Fix diction, jargon, and mechanics.** Replace filler words, clichés, and
   business jargon with the plain word the meaning needs, or cut. Apply the
   Anti-jargon rules: keep necessary technical terms, cut empty buzzwords, never
   stack them. Fix punctuation and dashes here too: outside `creative`, replace
   nearly all em-dashes with a varied mark (comma, period, colon, parens), keep
   the hyphen for compounds and en-dash for ranges, no `--`/spaced-hyphen dashes,
   no doubled words, no space before `,;:!?`, one terminal mark. Running the
   linter with `--fix` clears the mechanical ones (em-dashes, `--`, spaced
   hyphens, emoji) before you do the judgment work. Skip swaps that leave the
   sentence vague. See category 9.
12. **Calibrate to the register.** Match the genre's conventions (Register
    profiles) and hold them end to end: professional for a report, conversational
    for marketing, narrative for fiction. Add what the genre wants (contractions
    in casual; "you" in marketing); never bolt on a voice the genre rejects.

## Self-critique loop (the critical pass)

After the rewrite, do not return it yet. Run an adversarial pass.

**Review from three angles, not one.** A single hostile reviewer misses whole
classes of tells. Read the rewrite as each of:
- the **detector researcher**: shape first (would a person have formatted this
  document this way?), then rhythm, the sentence-length distribution, predictable
  phrasing, uniform openers;
- the **domain expert**: vacuity, weak stance, wrong or unsupported claims (the
  substance);
- the **genre editor**: register fit, length, format conventions (does it read
  like real writing in this genre?), and the architecture: does every section
  earn its length, is anything said twice, is every section pitched at the same
  reader?;
- the **author's colleague**: is there anything here only this author could have
  written? If every specific could have come from a search summary, the intake
  did not do its job.

**Score each dimension 0–2**, where 0 = clearly AI, 1 = passable, 2 = genuinely
human: Shape, Architecture, Substance, Rhythm, Stance, Consistency, Sourcing, Diction, Register. The
bar to return: no dimension below 1, and the mechanical ones (Rhythm, Diction)
not the only thing carrying it. This makes "good enough" measurable instead of a
vibe.

**Hit concrete targets**, not "improve it". All of these are in the linter's
metrics line, so check them rather than guessing:
- **short-sentence ratio ≥ 0.12**: at least one sentence in eight is eight words
  or fewer. This is the target most rewrites miss;
- **mid-band ratio ≤ 0.72**: under three quarters of sentences in the 12–26 word
  band;
- **burstiness CoV ≥ ~0.5**;
- **no `assistant_shape` hits**: heading density, bullet ratio, bold density all
  under threshold, and no recap section;
- **paragraph-length CoV ≥ 0.3**: paragraphs are not all the same size;
- **no `restatement`, `section_balance` or `depth_drift` hits** on a sectioned
  document, and every "only here" item from the section map still present in the
  rewrite (the `structure:` metrics line has the counts);
- em-dash density ≈0 outside `creative` (replace nearly all with varied marks);
- **no `cleft` or `participial_tail` hits**: the syntactic signature is Tier 1
  and it survives every diction fix, so check the `syntax:` metrics line
  explicitly rather than assuming a clean score covers it;
- in `fix` mode, expect to cut 15–25% of the words;
- at least one specific a generic model could not have produced (from the intake,
  never invented);
- no run of 3+ same-length sentences. Read the length sequence aloud in your head.

**Final self-check** (the rhythm is the tell your ear catches before your eye):
read the rewrite aloud. If it sounds like a metronome, vary it. Then scan: (a)
shortest vs longest sentence, under a ~20-word gap? add a short punch; (b) any
three consecutive sentences sharing a shape (all Subject-Verb-Object)? break one;
(c) did the register shift at least once between plain and precise? (d) em-dashes
> 1 outside `creative`? replace the extras; (e) any sycophancy, "in conclusion"
recap, or "not X, it's Y"? cut it; (f) one concrete detail a generic model
wouldn't have written? (g) would this document have this much markdown in it if a
person had typed it? (h) read only the headings and the first sentence under
each: does any point come round twice, and does the hardest topic get the most
room? If a Reddit commenter would call it slop, it isn't done.

Then:

1. **Run the hallucination pass.** Diff the rewrite's claim inventory against the
   source's (Anti-hallucination protocol, step 6). Any new, strengthened,
   weakened, or re-numbered claim is a regression. Revert that span. Check for
   *dropped* claims too: a cut caveat is silent information loss. Anything the
   architecture step removed that existed nowhere else in the source must be
   restored, unless the author approved that cut.
2. **A/B against the original.** Did I lose any real content? Is the rewrite
   genuinely *better*, or merely *different*? Trading the AI signature for a new
   uniform signature (everything de-listed, every em-dash gone) is a failure
   (principle 2).
3. **Re-run the linter** on the rewrite (add `--dialect american` or
   `--dialect british` to catch spelling drift against your chosen dialect).
4. **If** the score is at/above threshold **or** any dimension scores below 1,
   fix those specific spots and repeat.
5. **Run the verification gate** if a detector is configured (Workflow step 7).
   A `flagged` verdict means the pass is not finished regardless of what the floor
   score says, and the loop continues from the rewrite. A gate that could not run
   is reported as not run, never as a pass.
6. **Stop at a fixed point.** Without a detector configured: stop when a pass
   produces no net improvement or no dimension is below the bar, capped at 3
   passes. With the gate active it is the exit criterion, so keep looping while it
   returns 1, capped at 5 passes, but only while each pass genuinely improves the
   writing. Two consecutive passes that cannot move the detector without damaging
   the prose means stop: the remaining signal is not reachable by honest editing,
   and grinding past that point is how humanizer tools produce the mangled text
   detectors catch most easily. Either way the cap bounds cost and is not a target,
   and anything left over is reported honestly in the audit rather than
   over-corrected.

## Invariant guard

These must survive the rewrite unchanged. Diff-check before applying:

- All **numbers, units, dates, and measured values**.
- All **code**, commands, config keys/values, file paths, and CLI flags.
- All **links and citations** (URLs, references, footnotes).
- **Defined terms** and proper nouns (product, model, library names).
- **PII and confidentiality rules**: never add PII or internal-only URLs; honor
  any project confidentiality rules for customer-facing text.
- **Claims**: you may sharpen wording but never strengthen, weaken, or invent a
  claim to improve flow.

If a rewrite would change any invariant, revert that span and keep the original.

## Anti-hallucination protocol

Humanizing is exactly when fabrication creeps in: a flat sentence gets "fixed"
with a vivid invented detail, a hedge becomes a confident false claim, a vague
gesture grows a fake statistic. The rewrite adds *voice*, never *facts*.

1. **Build a claim inventory first.** Before editing, list every checkable claim
   as `{claim, value, source-span}`: numbers, dates, named entities, citations,
   causal and comparative assertions ("X is faster than Y"). Nothing on the list
   may change value; nothing new may join it. This is the artifact you diff
   against in step 6.
2. **Add no specificity the source doesn't contain.** "Improved performance" may
   not become "cut latency 40%" unless that number is in the source or the
   intake. Sharpen the *wording*, not the *facts*.
3. **Cut, don't dress, empty sentences.** When a sentence says nothing, delete
   it. Never rescue it with an invented detail, example, quote, or source.
4. **Never invent attribution.** Removing "studies show" is good; replacing it
   with a fabricated named source is worse than leaving it vague.
5. **Mark gaps, don't fill them.** Emit `[SOURCE NEEDED]` / `[FIGURE?]` /
   `[VERIFY]`, enumerate every one in the audit, and flag the output as
   draft-pending. Placeholders are removed by the author, never silently by you.
   Quotes and citations stay verbatim: never turn a paraphrase into a quote, and
   never attach a citation to a claim it doesn't support.
6. **Run a dedicated hallucination pass** in the self-critique loop. Diff the
   rewrite's claim inventory against the source's and sort every difference into
   **added / strengthened / weakened / dropped** (re-numbered counts as changed).
   The first three are regressions. Revert that span. A *dropped* real claim or
   caveat is silent information loss: restore it unless the deletion was
   deliberate and logged. Report the bucketed diff in the audit.
7. **`generate` mode is held to the same bar**: the brief is the invariant set.
   Drafting does not license invented statistics, quotes, case studies, or
   citations. The audit must list every fact stated that the brief did not supply.

A regex cannot catch a fabricated fact, so this is judgment, not a linter check.
The linter only flags the *vague-attribution* and *fabricated-specificity-shaped*
phrasings that tend to accompany it.

## Anti-jargon rules

Jargon is the corporate cousin of filler (linter category `jargon`: "synergy",
"leverage", "circle back", "move the needle", "low-hanging fruit", "actionable",
"best-in-class", "operationalize"). The test that decides every case: **does the
word do work?** A precise domain term a reader needs ("p99 latency", "FSDP",
"idempotent") stays because it carries information. A word you could delete with
no loss of meaning goes. Plain word first (*use* not *leverage*); define a
necessary term once and then reuse it rather than rotating synonyms; never stack
three borderline terms in one sentence. Rewrite the sentence around what it
actually claims. Marketing tolerates light enthusiasm but *not* empty jargon;
that is the marketing-specific failure mode. Worked rules and examples:
[`references/anti-jargon.md`](references/anti-jargon.md).

## Anti-overcorrection guardrails

- **Do** keep the occasional tricolon and transition where natural. The
  em-dash is the exception: replace nearly all of them outside `creative`,
  varying the replacement mark so the rhythm doesn't flatten.
- **Do** keep purposeful structure the document wants: callout tiers, scannable
  lists, code-comment density (see [`STYLE-GUIDE.md`](STYLE-GUIDE.md)).
- **Do** widen a bar for a register rather than muting the check
  (`register_thresholds` in the pattern file). Muting throws away the signal above
  the register's genuine tolerance along with the false positives below it.
- **Don't** ban a token globally; that just trades one signature for another.
  Target *patterns in excess* (false agency, the Wh-opener run, three same-length
  fragments), not a category to zero. The newer structural checks fire on
  density and runs, not on a single instance. Keep them that way. (Public lists
  like stop-slop reach for "kill all adverbs / no em dashes ever / always two not
  three"; those manufacture a fresh uniform signature, which is exactly principle
  2's failure mode.)
- **Don't** add slang, jokes, typos, or forced first-person voice. Forced
  all-lowercase, sprinkled "lol/honestly?", staccato fragments, and conspicuous
  dash-avoidance are the **anti-AI costume**, a fresh uniform signature the
  linter now flags as `over_correction`/`internet_tells` (muted only in
  `casual`/`creative`). The fix is a real deliberate voice, not the absence of
  the old tell. See [`references/over-correction.md`](references/over-correction.md).
- **Don't** cut precision a technical doc needs in the name of "plain language".

These guardrails cover a rule applied too hard. For the cases where a rule should
not have applied at all, see When a rule fights the task, immediately below.

## When a rule fights the task

Every rule here has a case that beats it. When one does, the constraint wins and
the rest of the shape stays. You relax the single rule in the way, not the skill.

1. **Structure the genre actually requires.** An API reference wants a heading
   per endpoint. A runbook wants numbered steps. Release notes are a bulleted
   list by definition and a comparison is a table. What Tier 1 targets is
   *assistant* shape: the heading every eighty words chopping up a continuous
   argument, the bold on every noun, the "Key takeaways" close. Structure that
   carries information stays. Strip the structure that only decorates. The same
   holds for architecture: a template with a mandatory Security section keeps the
   section, and an API reference keeps its parallel entries.
2. **The user asked for something else.** Translation, summarization, a
   grammar-only fix, a factual check. Do the job that was asked for. Offer the
   voice pass afterward if it would help, but never fold it in unannounced: a
   rewrite hidden inside a translation is a change the user cannot see and did
   not approve.
3. **Fidelity beats rhythm.** If the only way to hit the short-sentence ratio is
   to drop a caveat or round a number, the number wins and the ratio goes unhit.
   Say so in the audit. Principle 3 outranks every metric in this file, because
   the metrics are proxies for the thing rather than the thing.
4. **Required hedging is not hedging.** A safety warning, a legal notice, a
   clinical statement, a disclosure with regulatory wording: there the qualifier
   carries the meaning. "May cause drowsiness" is precise. "Causes drowsiness" is
   a false claim, not a braver sentence. The same protection covers quoted
   passages, defined terms of art, and any house style guide the author is
   contractually stuck with.
5. **Genuine ambiguity about register.** One short question beats guessing and
   rewriting twice. Ask it once, then commit.
6. **A change that is hard to undo.** Editing a file in place, touching what git
   does not track, rewriting a doc someone else owns. Confirm first, or leave a
   `.bak`. Recoverability outranks finishing in one turn.
7. **The harness outranks the skill.** A system prompt, a project CLAUDE.md, AGENTS.md or GEMINI.md, a rules file, or a
   style guide the repo enforces beats this file wherever they collide. Same
   principle as 1: the constraint wins, the shape stays.

None of these licenses a quiet return to the default voice. Each scopes one rule,
in one place, for a reason you can state, and the reason belongs in the audit.

## Workflow

Script paths below are relative to this skill's own directory, the folder that
holds this SKILL.md, not to the user's working directory. Resolve them from there.
The skill does not depend on any one agent or model. Whichever agent loaded it,
the tools fall back in the same order: run the script if you have a shell and
Python 3; otherwise call the `lint_prose`, `check_invariants` and
`verify_detector` tools if the human-voice MCP server is connected; otherwise use
the no-tool checklist in step 3 and say in the audit that the linter did not run.

1. **Resolve input.** File-path vs pasted-text vs brief; pick `fix` or
   `generate`; infer `register`. Set the depth here too (Pick the depth of the
   pass): quick, standard, or full. Steps 3, 6 and 7 are the ones that scale down.
2. **Author-material intake** (above), before you subtract anything.
3. **Baseline lint** (skip for `generate`'s first draft):
   ```bash
   # pick the register that matches the genre (default technical)
   python3 scripts/detect_ai_prose.py --register marketing <file>
   python3 scripts/detect_ai_prose.py --register auto <file>   # infer it, and say why
   python3 scripts/detect_ai_prose.py --dialect american <file>   # spelling drift
   printf '%s' "$TEXT" | python3 scripts/detect_ai_prose.py --register casual -
   python3 scripts/detect_ai_prose.py --quiet <file>              # score only
   python3 scripts/detect_ai_prose.py --json <file>               # machine-readable
   python3 scripts/detect_ai_prose.py --baseline <original> <rewrite>   # the delta
   ```
   `--register auto` infers the register from the content and prints its reasoning;
   it is right on about 82% of this repo's labeled corpus against 19% for the old
   always-technical default, and when unsure it falls back to `technical` (the
   strictest profile) rather than guessing something permissive. **Prefer your own
   judgment over it**: you have the whole document and the user's intent, it has
   keyword cues. Use it as a second opinion, and pass `--register` explicitly when
   you disagree, which always wins.

   Read the metrics lines, not just the score: `short_sentence_ratio`,
   `mid_band_ratio`, `burstiness CoV`, `headings_per_1k`, `bullet_line_ratio`, and
   the `syntax:` line (cleft count, `,VERBing` tail count, copula per 1k) are the
   numbers the self-critique targets. Two lines are **diagnostics, never targets**.
   The `voice:` line reports contractions per 1,000 words: a marketing page at zero
   reads stiff and is worth fixing, but the same measurement scored as a tell flags
   careful non-native writers, which is the bias this skill exists to argue against.
   The `style:` line reports a Burrows's Delta against a committed human
   function-word profile, and it is **read in the inverted direction**: a *low*
   delta is the suspicious one, because a model writes near the centroid of the
   human population while an individual writer departs from it. Below the human
   minimum the linter says so. Anything inside the range says nothing, and the
   value is far more useful across a pair than on one document, so use
   `--baseline`, which prints the movement and which way it went. Full
   measurements: [`references/competitive-landscape.md`](references/competitive-landscape.md). `specifics_per_100` is a diagnostic, not a
   tell: when it is near zero the draft contains nothing a reader could check, so the
   author-material intake is mandatory rather than optional, because cutting tells
   from a document with no material in it just yields clean generic prose. Quote the before/after score in the
   audit (`--baseline` prints the delta directly).

   The linter is the deterministic floor only. It cannot see vacuity, weak
   stance, terminology drift, or fabrication. If it is unavailable, degrade to
   judgment with this **no-tool checklist**: (a) count headings and bullet lines.
   Would a person have formatted it this way? (b) read the sentence-length
   sequence and flag any run of 3+ similar lengths; (c) is there a single sentence
   under eight words? (d) scan the first word of each sentence for repeated
   openers; (e) grep for the top filler (delve, leverage, robust, seamless,
   crucial, comprehensive, landscape); (f) count em-dashes, since outside
   `creative` essentially any is a tell; (g) check every list for the
   `- **Term:**` pattern; (h) count sentences that open "What …" or "The reason
   …" and sentences carrying a ", VERB-ing …" tail, and cut most of both; (i) for
   a document with headings, write the section map: words per section, the one
   thing each says, what repeats, what each alone says.
4. **Optional autofix.** Clear the mechanical tells before the judgment work:
   `python3 scripts/detect_ai_prose.py --fix --register <reg> <file>` rewrites
   em-dashes, `--`, spaced hyphens and non-numeric en-dashes to commas, strips
   decorative emoji, and applies 1:1 filler/jargon swaps (dash and emoji fixes
   skipped in `creative`; emoji kept in `casual`). `--fix-dry-run` previews. It
   never touches code, numbers, or links, and it does not vary the replacement
   mark, so the rewrite pass still has work to do.
5. **Rewrite** per the procedure above, loading `references/ai-tells.md`.
6. **Self-critique loop** until the targets are met or 3 passes.
7. **Verification gate** (run it whenever a detector is configured). The linter is
   a floor and cannot stand in for a detector: a document can score 0.0 and still
   be flagged. Close the loop:
   ```bash
   python3 scripts/verify_detector.py --before <original> <rewrite>
   python3 scripts/verify_detector.py --max-p-ai 0.05 <rewrite>   # stricter
   python3 scripts/verify_detector.py --json <rewrite>
   ```
   It exits **1 while the text is still flagged**, 0 when it clears, and 2 when no
   detector is configured. That is the stopping condition: **while the gate returns
   1, the job is not done: go back to step 5.** Fix in the same priority order,
   because that is what moves a detector: shape first (headings, bullet ratio, bold
   density, the recap section), then the sentence-length distribution, then real
   specificity from the intake. Each loop must make the text *better*; if two
   consecutive passes cannot move the detector without damaging the writing, stop
   and report the residual honestly rather than grinding. Never reach for synonym
   mangling, Unicode homoglyphs, zero-width characters, or injected typos: those are
   detected *by* the damage they leave, so they lose on their own terms as well as
   violating principle 3.

   Report the gate's outcome in the audit verbatim, including "not run". Exit 2 is
   **not** a pass. A `clear` is evidence against one detector at one threshold, not
   a guarantee against another, and detectors carry real false-positive rates in
   both directions.

   **Calibrate before you believe a detector.** Any classifier you point this at
   should be checked against text you know a person wrote, first. One of the
   open detectors in this repo's own panel labels **34 of 34** hand-written human
   files as AI, at p(AI)=1.000. A detector like that will "flag" your rewrite
   forever and it is telling you nothing, so its verdict has to be discarded rather
   than chased. `eval/detector_local.py` does this automatically (see
   `MAX_HUMAN_FPR`) and prints which detectors it excluded and why; do the same by
   hand for a commercial API before you treat its verdict as a target.
8. **Apply / present.** For a file, ensure it is recoverable (git-tracked or
   `.bak`d), show the rewrite or diff, then edit in place; for pasted text, print
   the rewrite. Always print the Humanization Audit.
9. **Confirm invariants** with a diff (`git diff`, or a before/after of numbers,
   code, links).
10. **Pre-return check** (below) on the response itself, then send.

## Pre-return check

The last gate before anything leaves. The self-critique loop judges the prose;
this one judges the handoff.

Delete from your response every time:

1. The first sentence, if it announces what you are about to do or compliments
   the request.
2. The last sentence, if it recaps what just happened or asks whether there is
   anything else.
3. Any sidebar opening "by the way" or "as a side note".
4. Any hedging adverb carrying no information ("perhaps", "it might be worth").
   Keep the hedge that names real uncertainty, because cutting that one
   manufactures confidence, and false confidence is the worse failure.

Then confirm four things. Where one fails, fix it rather than caveat it:

- **Nothing was invented.** Every specific traces back to the draft, the
  surrounding context, or the user. Gaps are marked, never filled.
- Invariants survived: numbers, code, links, claims.
- **The audit names its residual risk**, or says "none". "Some tells may remain"
  tells a reader nothing they had not already assumed, and vagueness of exactly
  that kind is what this skill exists to delete.
- The gate is reported as it ran: clear, flagged, or not run. Exit 2 never
  gets written up as a pass.

When the linter could not run or the detector was unreachable, give the cause and
what you did instead, in one line. No "Uh oh", no apology, no hedging around it.
The tone that suits a broken tool is the tone that suits everything else here.

## Output templates

### Humanization Audit
```text
## Humanization Audit: <file or "pasted text">
Register: <technical|business|marketing|academic|casual|creative|email|release_notes|ux_microcopy|tutorial>
Depth: <quick|standard|full>   (what was run; a quick pass is shorter, not looser)
Score: <before> → <after> [<band>]  (linter floor; not ground truth)
Words: <before> → <after>  (−NN%)
Passes run: <n>/3

Shape:  headings/1k <before> → <after>   bullet-line ratio <before> → <after>
Struct: sections <before> → <after>   framing share <before> → <after>   restated pairs <before> → <after>   depth/100w by section <before> → <after>
Rhythm: short-sentence ratio <before> → <after>   mid-band <before> → <after>   CoV <before> → <after>
Syntax: clefts <before> → <after>   ",VERBing" tails <before> → <after>   copula/1k <before> → <after>
Style:  function-word delta <before> → <after>  (human median <m>; diagnostic, unscored, read inverted)

Tells removed (by category):
- Shape:       <n>  e.g. cut 4 headings, un-bulleted 2 lists, dropped the recap
- Architecture: <n> e.g. merged summary into overview; folded 3 stubs into rollout; levelled "Scalability"
- Substance:   <n>  e.g. cut 2 vacuous paragraphs; removed restated conclusion
- Rhythm:      <n>  e.g. added 3 short sentences; mid-band 0.81→0.55
- Structure:   <n>  e.g. de-triadic 4 sentences; 6 em-dashes → varied marks
- Syntax:      <n>  e.g. unstaged 3 clefts; cut 4 ", making it…" tails
- Stance:      <n>  e.g. committed to FSDP recommendation; fixed false balance
- Consistency: <n>  e.g. "the LLM"/"the model" → "the model"; 3 dialect fixes
- Sourcing:    <n>  e.g. "studies suggest"→cited eval; cut "end result"
- Diction:     <n>  e.g. leverage→use, robust→(cut), landscape→(cut)

Author material added: <specifics sourced from the draft/context/user, or "none">
  (every one traceable, nothing invented; see Author-material intake)
Detector gate: <clear|flagged|not run>  p(AI) <before> → <after>  (<detector>, gate <threshold>)
  "not run" means no detector was configured. It is not a pass.

Dimension scores (0–2): Shape _ · Architecture _ · Substance _ · Rhythm _ · Stance _ · Consistency _ · Sourcing _ · Diction _ · Register _
Invariants preserved: numbers ✓  code ✓  links ✓  claims ✓  PII-safe ✓  (claim diff: +0 added / 0 strengthened / 0 weakened / 0 dropped)
Placeholders left for author: <list of [SOURCE NEEDED]/[VERIFY], or "none">
Proposed cuts (awaiting approval): <each distinct claim the rewrite would drop, kept in place until the author says, or "none">
Rules relaxed: <which rule, where, and why, or "none">  (see When a rule fights the task)
Residual risk: <why a skeptical human might still flag this, or "none">
Next: <one thing the author does now, or "nothing; this is ready to ship">
```

The `Next:` line is one action, not a menu. Usually it is filling a placeholder
("supply the p99 number in para 3"), answering an intake question the draft still
needs, or nothing at all. "Let me know if you'd like any changes" is not a next
action and does not go there.

### Rewrite (pasted-text mode)
```text
## Rewrite
<the humanized text>
```

For `generate`, skip the "removed" counts (there is no before); report the final
score, the register, and confirm no fabricated specifics were introduced.

At `quick` depth the audit collapses to one line, or disappears. A Slack message
does not need a report card. `Depth`, `Rules relaxed` and `Residual risk` are the
lines that still earn their place at `standard`.
