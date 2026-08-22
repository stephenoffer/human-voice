# The syntactic signature, annotated

`syntax-signature-before.md` is the case this repo added checks for in v0.6. Read
it first without the score. It has no filler, no hedging stack, no bold bullets,
no "In conclusion", and not one em-dash. Every fact in it is concrete. It takes a
position and defends it.

It still reads machine-written, and the reason is grammatical.

## What the linter sees

| metric | before | after |
|---|---|---|
| floor score | **47.3** strong-tell | **0.0** clean |
| clefts | 9 | 0 |
| `,VERBing` tails | 3 | 0 |
| clause splices | 4 | 0 |
| copula / 1k words | 80.3 | 36.8 |
| sentences ≤ 8 words | 8% | 59% |
| length CoV | 0.41 | 0.69 |
| words | 249 | 190 |

## Nine clefts in 249 words

Every point in the before-text arrives the same way: the sentence sets up a slot
and then fills it.

> What ultimately decided it was operational cost rather than throughput.
> The problem is that Redis is not currently part of our stack.
> The reason we did not choose it is that our notification payloads routinely
> exceed the 256KB message limit.
> What matters here is that notification delivery is not latency-sensitive.

Each of those is fine on its own. A person writes "what matters here is" when
they want to mark a shift in criteria. Nine of them is not emphasis, it is a
default: the writer reaches for the same frame every time a claim arrives, which
is exactly what a model does and what a person with a stake in the argument does
not.

The fix is not a synonym. It is to state the subject:

> Operational cost decided it, not throughput.
> Redis is not in our stack today.
> Our notification payloads routinely exceed the 256KB message limit.

## The tails

> ...delivering messages in single-digit milliseconds under our test load.
> ...meaning we would be adding a second stateful system.
> ...giving us transactional enqueue for free.

Three sentences, three consequence clauses hung off the end. The construction
gives each sentence a payoff without the writer having to commit to one, and
because the tail is grammatically subordinate the claim inside it never gets
argued. Promote the good ones to sentences and delete the rest:

> Adding it means a second stateful system, with its own failure modes and its
> own page at 3 a.m.

That version can be disagreed with. The participial version cannot, because it
was never asserted.

## The welds

The before-text ends on three clauses spliced with ", and it is":

> We are going with Postgres, and it is the boring choice, and it is the right
> one.

The after ends on a period:

> We picked the boring option on purpose.

## What did not change

Every number survives: 256KB, forty milliseconds at the median, single-digit
milliseconds for Redis, three options by name. Nothing was invented to fill the
space the cuts opened up; the text got 24% shorter instead. The recommendation is
the same recommendation, moved to the first line, where a person who had made the
decision would have put it.

## Why this pair exists

Measured across this repo's corpus, `participial_tail` and `cleft` account for
30% of the floor score on realistic modern model output and 0% on 2023-era
caricature. A rewrite pass that starts at diction never touches either of them,
which is why a document can clear every word list and still read as generated.
