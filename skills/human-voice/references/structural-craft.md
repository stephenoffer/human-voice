# Structural craft — writing human from the first draft

The linter catches surface tells. It cannot teach the moves that make prose read
human in the first place. This file is the generative companion: load it for
`generate` mode, and for the rewrite pass once the cheap tells are gone. It draws
on the structural-detection literature, where grammar and discourse features
alone separate human from AI text at ~88% F1 — the signal is in *how the prose is
built*, not which words it uses.

## Five moves that carry the most weight

1. **Lurch — vary sentence length, hard.** Humans swing: a three-word sentence
   against a forty-word one. AI clusters every sentence in a narrow mid-length
   band. If your sentences sit within a four-word range, the rhythm is the tell.
   Put a short punch after a long, winding sentence on purpose.
2. **Spike — vary information density.** Pack one paragraph tight with specifics;
   let the next breathe. Uniform density across every paragraph is a machine
   signature even when each sentence is clean.
3. **Wander — don't follow the outline.** AI marches setup → complication →
   resolution → reflection, every time. Start with the most interesting thing.
   Circle back. Leave one thread half-resolved. (See
   [`discourse-and-structure.md`](discourse-and-structure.md) for why discourse
   shape is the single largest detection signal.)
4. **Shift register — move between precise and casual.** One sustained tone is a
   costume, not a voice. A technical piece can drop into plain speech for a
   sentence and back. Match claim strength to evidence: understatement reads as
   confidence, overstatement reads as AI.
5. **Get specific — write for someone, not everyone.** Name the particular
   failure, the particular afternoon, the actual error code. Unglamorous concrete
   detail is more convincing than a dramatic generality. A detail a generic model
   could not have invented is the strongest human signal there is.

## Tells the linter only partly sees (fix these by hand)

- **Cowardly passives.** "It can be seen that…", "The decision was made to…",
  "Mistakes were made." They hide the actor. If you can name who acted, name
  them. (Legitimate actor-irrelevant passive — "the server was deployed at 3 AM"
  — stays.) The linter flags the common dodge phrases as `cowardly_passive`, but
  judgment catches the rest.
- **Clause-level parallelism.** "It reduces costs, improves efficiency, and
  increases reliability." AI stacks parallel clauses at rates humans don't. Break
  one into a different shape: "Costs dropped. The team got faster. And nothing
  broke for six weeks."
- **Emotional flatness.** AI is neutral-to-mildly-positive throughout. Humans get
  frustrated, surprised, funny, blunt. If an approach is bad, say it's bad.
  Relentless optimism is a tell no word list can measure.
- **Self-correction traces.** Human drafts show thinking: a parenthetical aside, a
  restated point, an "actually, wait." AI produces seamless first-draft prose.
  Genuine visible uncertainty reads more human than a stack of hedges.
- **Over-explanation.** AI defines the obvious and adds context nobody asked for.
  Trust the reader; write for your actual audience, not the least-informed
  possible one.
- **Resumptive filler.** "In terms of…", "When it comes to…", "At the end of the
  day…" Name the subject and get on with it. (Flagged at low weight in
  `soft_filler`/`transitions` — common in careful and non-native writing, so the
  linter treats them as a whisper, not a verdict.)

## The second dialect (what's left after the first cleanup)

Strip the obvious slop and a subtler, equally-machine register takes its place.
A sophisticated reader catches it instantly. Hunt these four down on the rewrite
pass; the first two the linter now flags, the last two are yours to catch.

- **The ", and" splice rhythm.** Joining two independent clauses with a comma +
  *and* (or *but*/*so*), sentence after sentence, builds a uniform compound
  cadence: "We shipped on Tuesday, and latency jumped. We raised the limit, and
  it held." A few are fine — banning them outright just makes a *different*
  uniform signature (principle 2). The fix is variety: split some into separate
  sentences, restructure others, keep one or two where the rhythm wants them.
  (The linter does **not** flag this — humans and ESL writers use ", and" heavily
  and legitimately — so it is judgment, not a check.)
- **Stacked "[noun] is [noun]" copulas.** Flat definitional sentences in a row:
  "Security is the constraint. The size was wrong. The keys were correct." One is
  fine; a run reads as a glossary. Break it with a verb that does work: "Security
  is the one thing you can't retrofit" → "Security shapes the schema from the
  first table you draw."
- **Reflexive triads, including noun-phrase ones.** "Encryption at rest,
  row-level access control, and audit logging." The linter's `rule_of_three` now
  catches noun-phrase triads too, but only flags a document with **two or more**
  (a single enumeration is legitimate). Either way, break the reflex: two items,
  four, or fold them into a clause.
- **"[inanimate thing] lives/sits in [place]."** "A project living in five
  tools", "the logic lives in the controller." Figurative life loaned to an
  inanimate noun. The linter flags the common shapes under `false_agency`; the
  fix is to say what literally happens ("you track one project across five
  tools").

The meta-rule: removing a tell is not the same as adding a voice. After every
cleanup pass, ask whether you traded the slop signature for a tidier one.

## Verbs and names (mostly for `creative`)

- **Weak verbs propped up by adverbs.** "effectively leverages" → "uses";
  "significantly improves" → "improves" (or give the number). In narrative, reach
  for a verb that carries the motion: not "walked quickly" but "hurried"; not
  "looked" but "scanned" or "glanced." Cut the adverb; pick the verb that already
  means it.
- **Stock names.** AI defaults to Emily/Sarah (63–70% of AI articles) and
  over-titles with "Dr." Pick names that fit the era, region, and class of the
  character; use a first name or nickname after the introduction. The linter
  flags repeated stock names as `name_selection` (active only in
  creative/casual).

## The read-aloud test

The rhythm is the tell your ear catches before your eye does. Read the draft
aloud. If it sounds like a metronome, you have not lurched enough. If every
paragraph lands at the same pitch of confidence, you have not shifted register.
If you cannot point to one concrete detail a generic model would not have
written, you have not gotten specific. Fix the one that fails first.

---

Sources: the structural-detection and counterfactual-rhetoric literature
synthesized in [`ryanthedev/oberskills`](https://github.com/ryanthedev/oberskills)
(MIT) and the cited-tell study in
[`JCarterJohnson/vibecoded-design-tells`](https://github.com/JCarterJohnson/vibecoded-design-tells)
(MIT). See [`cited-vs-matched.md`](cited-vs-matched.md) for how these weight the
linter.
