# Anti-jargon rules

Jargon is the corporate cousin of filler, and the linter flags a `jargon`
category for it ("synergy", "leverage", "circle back", "move the needle",
"low-hanging fruit", "actionable", "best-in-class", "operationalize",
"paradigm shift"). Cutting words is not enough; apply the rules.

1. **Plain word first.** If a plain word carries the same meaning, use it:
   *use* not *leverage*, *talk* not *touch base*, *goal* not *north star*,
   *easy wins* not *low-hanging fruit*. The test: would a smart reader outside
   your industry understand it on first read?
2. **Keep necessary technical terms; cut empty business jargon.** A precise
   domain term a reader needs ("p99 latency", "FSDP", "idempotent") stays, because it
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
   jargon. That is the marketing-specific AI failure mode. A technical report
   tolerates dense terminology but not business-speak. Match the genre; never use
   jargon as a substitute for a concrete claim.

See also principle 6 (one term per concept) and category 6 in
[`ai-tells.md`](ai-tells.md).
