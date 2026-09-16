# Architecture pass: notes on the rate-limiter pair

[`architecture-before.md`](architecture-before.md) scores 48.9. Most of that
comes from sentence tells a normal pass would catch. The interesting part is what
stays wrong after those are fixed. Rewrite every sentence of the before file and
keep its outline, and you still ship a document that says its point three times,
explains rate limiting to engineers reading a Lua sliding-window design, and puts
three headings over nothing.

The linter's `structure:` line for the before file:

```text
structure: sections 9   section-length CoV 0.85   framing share 0.44   restated pairs 2   depth 3.8/100w by section [2.0, 4.5, 0.0, 9.6, 0.0, 1.7]
```

## The section map

| Section | Words | The one thing it says | Depth | Repeats | Only here |
|---|---|---|---|---|---|
| Overview | 51 | shared Redis limiter replaces per-instance buckets | 0 | | fairness across customers |
| Background | 67 | limits grow with the fleet; support can't explain throttles | 1 | | worked on a few instances |
| What is Rate Limiting? | 63 | what a rate limiter is | 0 | | one busy client crowding out the rest |
| Design | 166 | Lua sliding window, key shape, 429 headers, fail-open, latency | 3 | | every number in the document |
| Scalability | 124 | (nothing specific) | 0 | | cluster can be expanded; richer policies later |
| Security | 6 | (nothing) | 0 | | Redis access will be restricted |
| Testing | 6 | (nothing) | 0 | | limiter will be tested |
| Rollout | 6 | (nothing) | 0 | | rollout will be gradual |
| Summary | 58 | shared Redis limiter replaces per-instance buckets | 0 | Overview | (none) |

Nine headings, two things to say. The problem sits in Background. The design sits
in Design. The last column is why this pass is not just deletion: seven of the
nine rows carry something no other row says, including the three stubs.

## What each row became

Overview and Summary merged into the two opening paragraphs. The problem comes
first because a reviewer has to believe the problem before the design matters.
`restatement` flagged the summary lines that repeated the overview. Cutting the
summary cleared both.

"What is Rate Limiting?" went as a section. Anyone reviewing a design that names
`EVALSHA` knows what a rate limiter is. Its one distinct idea, that one busy
client should not crowd out the rest, moved into the opening as a reason for the
change. That removed the three beginner explanations `depth_drift` counted.

Scalability went as a section too. `depth_drift` flagged it as a 124-word section
with no specifics beside a design section at 9.6 per hundred words. Its claim that
shared state keeps limits steady was already in the opening. Its two distinct
claims were not, so they moved: the cluster can be expanded (now in Cost and
failure) and a shared counter makes richer policies easier later (now in the
opening). What went was the sentences with nothing only they said, such as
"Scalability has been a key consideration throughout the design process."

Design split in two, by what a reviewer asks: how a request is counted, then what
it costs and what happens when Redis fails. The fail-open behaviour was the second
paragraph of Design, easy to miss. It now closes the document, because it
is the decision most worth arguing about. That is the one sentence of stance the
rewrite adds, and it adds no fact.

Security, Testing and Rollout were the stubs `section_balance` named. Each is a
single sentence, but each is a commitment, so none of them could simply be deleted.
Principle 3 forbids inventing the plan behind them. They became one closing
paragraph that keeps all three commitments, says the
document does not yet explain how, and leaves an `[OWNER NEEDED]` placeholder.

An earlier draft of this rewrite got that wrong. It replaced the three stubs with
"nothing is designed yet for access control, testing or rollout" and dropped the
line about expanding the cluster. That draft scored 0.0 too. It also turned three
commitments into a statement the author never made and deleted a claim without
asking, which is exactly what a structure pass must not do.

## Claim diff

No claim was added or strengthened, and none was weakened. Every number and
every name from the system in the before file is in the after file unchanged: `EVALSHA`, the key
pattern, 120-second TTL, 60-second windows, three shards with one replica each,
12,000 requests per second, 0.4 ms and 1.9 ms, the 5 ms timeout,
`ratelimit_redis_timeout_total`, `429`, `Retry-After`, `X-RateLimit-Remaining`.

Every "only here" item from the map survives: fairness, the old design working on
a few instances, cluster expansion, richer policies later, and the three
commitments. The dropped bucket is empty, so no cut needed the author's approval.

Cut as having nothing distinct: the rate-limiting definition, the bouncer
analogy, "scalability has been a key consideration", "a high level of
performance for all customers", "respond efficiently to changes in demand", and
the summary, whose every claim already appears above it.

Proposed cuts awaiting approval: none. If the author wants the "richer policies"
sentence gone, which is the vaguest claim left, that is their call to make.

## Numbers

| | before | after |
|---|---|---|
| score | 48.9 | 0.0 |
| words | 547 | 304 |
| sections | 9 | 2 |
| framing share | 0.44 | 0.00 |
| restated pairs | 2 | 0 |
| hollow sections | 1 | 0 |
| stub sections | 3 | 0 |
