# Restraint: when not to edit, and when a "tell" is actually right

Over-editing has its own signature. Strip every em-dash, every tricolon, every
"however", and you trade one uniform fingerprint for another (principle 2). Two
hard cases show where restraint matters more than zeal.

## Case 1: a passage that is already fine

This is a technical paragraph from a postmortem:

> The retry storm started at 14:02 when the payments service began returning
> 503s. Each client retried three times with no backoff, so a brief upstream
> blip turned into 40x normal traffic in under a minute. We added exponential
> backoff with jitter and capped retries at two.

A zealous pass might "vary the rhythm", swap "turned into" for something
livelier, or break up the second sentence. Don't. It already has burstiness (a
long causal sentence between two shorter ones), every number is load-bearing,
the stance is committed, and there's no filler. The linter scores it clean. The
correct edit here is **no edit**. Touching it can only add risk to the
invariants (those numbers) and flatten prose that's doing its job.

## Case 2: a tell that the register earns — keep it

This is the opening of a personal essay (register: creative):

> The kitchen at 3 a.m. is a different room — colder, larger, honest in a way it
> never is by daylight.

That em-dash and the trailing rule-of-three ("colder, larger, honest") would both
be flagged as tells in a technical report. Here they stay. The creative register
allows em-dashes, fragments, and wide cadence in service of voice (see the
register table), and the tricolon is *earned*: it's not three interchangeable
adjectives padding a claim, it builds to "honest", which the sentence is actually
about. Cutting it to two items would weaken the line, not humanize it.

The distinction that decides both cases: a tell is a tell when it's reflexive
padding. The same construction is good writing when it's doing real work and the
register welcomes it. Judge the instance, not the pattern. Match the register;
don't apply the strictest profile everywhere.
