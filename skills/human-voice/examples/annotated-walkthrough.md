# Annotated walkthrough: turning the technical BEFORE into the AFTER

This traces the existing `before.md` to `after.md` edit by edit, naming the tell
each change removes and the catalog category it belongs to. Register: technical.
Linter: before 383.1 strong-tell -> after 0.0 clean. Read it top to bottom to see
the rewrite order in action — substance first, diction last (principle 1).

## The starting text (before.md)

> # Leveraging Cutting-Edge Solutions: A Comprehensive Overview
>
> In today's fast-paced digital landscape, it's important to note that
> organizations must delve into the intricate world of data infrastructure. This
> report aims to explore the multifaceted realm of distributed systems and
> showcase how a robust, scalable, and seamless architecture can elevate
> operational efficiency.
>
> ## Key Considerations
> - **Performance:** Our solution is fast, reliable, and efficient.
> - **Scalability:** The platform leverages cutting-edge technology to handle growth.
> - **Security:** Robust security measures play a vital role in protecting data.
>
> Furthermore, studies suggest that adopting a comprehensive strategy is crucial
> for success. Moreover, it's worth noting that experts believe a holistic
> approach yields the best results. Additionally, the system boasts a vibrant
> ecosystem of integrations. We leverage our synergies to operationalize
> best-in-class, actionable solutions that move the needle for every stakeholder.
>
> It's not just about technology, it's about people. The platform — which our
> team built from the ground up — stands as a testament to innovation —
> highlighting its commitment to excellence. This isn't merely a tool -- it's a
> complete solution that unlocks the potential of your organization. ✨
>
> ## Conclusion
> In conclusion, navigating the ever-evolving landscape of technology requires a
> robust, comprehensive, and seamless approach. By leveraging these cutting-edge
> solutions, organizations can unlock new opportunities and embark on a
> transformative journey toward success. 🚀

## Edit 1 — cut the vacuous opener (Substance: vacuity, meta-commentary)

The title and the entire first paragraph carry no information. "This report aims
to explore the multifaceted realm of..." narrates the document instead of saying
anything (meta-commentary). "In today's fast-paced digital landscape" and "it's
important to note" are pure filler vacuity. Deleted, and replaced with the actual
thesis the report defends:

> Most teams pick their data infrastructure before they understand their access
> patterns. That order is backwards, and it costs them a rewrite a year later.

This is the highest-leverage move: cutting vacuity removes most of the AI feel at
once and lets a real position surface (Stance: earn a position).

## Edit 2 — dismantle the bold-bullet listicle (Structure: bold-bullets, rule-of-three)

The three `- **Term:** ...` bullets are the bold-lead-in listicle template, and
two of them ("fast, reliable, and efficient"; the implicit triad) are rule-of-
three padding. Bullets that just gesture ("handle growth", "protecting data")
become prose that states the real tradeoff:

> Performance and scalability usually pull in opposite directions. A system tuned
> for low single-query latency tends to shard poorly, so growth forces a redesign.

The list didn't help scanning; it hid the absence of content. Prose forces the
claim into the open.

## Edit 3 — kill transitional glue and vague attribution (Sourcing + Structure)

"Furthermore... Moreover... Additionally..." is fake transitional glue
(over-signposting); none marks a real turn in the argument. "Studies suggest" and
"experts believe" are vague attribution — authority with no source. Both go.
Where the source had no citation, the claim is either stated on its own merit or
cut, never propped up with an invented reference (anti-hallucination protocol).

## Edit 4 — remove jargon stacks and puffery (Diction + Substance)

"Leverage our synergies to operationalize best-in-class, actionable solutions
that move the needle" is buzzword stacking (Anti-jargon rule 4 — three is always
wrong). "Stands as a testament to innovation, highlighting its commitment to
excellence" is puffery plus a tailing significance clause. These don't get
swapped word-for-word; the whole sentence is rebuilt around a concrete claim, or
deleted when there's nothing under it.

## Edit 5 — drop the "not X, it's Y" templates and the dash pile-up (Structure: antithesis, dashes)

"It's not just about technology, it's about people" and "This isn't merely a
tool, it's a complete solution" are the antithesis template firing twice. The
same paragraph also piles up dashes — two em-dash asides, a trailing em-dash, and
a raw ASCII `--` — which is one of the loudest tells on the page (category 9).
Running `--fix` first would rewrite every one of those to a comma and strip the
trailing ✨ in a single deterministic pass; the rewrite then varies the marks
(comma, period, colon) so the rhythm doesn't flatten into all-commas. Here the
whole paragraph is vacuous, so it's replaced wholesale by saying what the thing
actually is — in the after, a worked recommendation with a mechanism:

> For a service expecting rapid growth and handling regulated data, we recommend a
> partitioned Postgres cluster over a NoSQL store. The reason is concrete: you keep
> transactional guarantees and mature access-control tooling while still scaling
> writes through partitioning.

That sentence does what the templates only gestured at: it commits to a verdict,
gives the mechanism, and weights an asymmetric tradeoff (Stance, category 8).

## Edit 6 — delete the empty conclusion and the emoji (Substance + Formatting)

"In conclusion, navigating the ever-evolving landscape... embark on a
transformative journey toward success. 🚀" is restatement (it adds nothing the
body didn't say), wrapped in puffery, capped with a decorative emoji. The whole
section goes. In its place, the after ends on the last real point — the genuine
limits of the recommendation:

> This recommendation has limits. We have not load-tested it past 50,000 writes
> per second, and it assumes a single region.

Naming real limits is honest stance, not hedging (category 8). It's a far stronger
ending than a recap.

## Edit 7 — fix rhythm and diction last (Structure: burstiness; Diction)

With the structure fixed, the remaining pass varies sentence length (the before
sat at CoV 0.33, under the 0.40 floor; the after reaches 0.45) and swaps any
surviving filler — "leverage" to "use", "elevate" to "raise" — only where the
swap keeps the meaning. Diction is last and least (principle 1). The result is
`after.md`, which the linter scores 0.0 clean. The real proof, though, is that it
now reads like one engineer who has an opinion, not a template.
