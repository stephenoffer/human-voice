# Cited vs. Matched

A keyword scanner ranks tells by what it can *match*. Readers rank them by what
they actually *cite* as AI. These two orders diverge, and v0.4.0 recalibrates the
weights to follow the second one.

The evidence: a study of ~90,000 Reddit posts where people pointed at specific
text and said "this is AI" (JCarterJohnson/vibecoded-design-tells, MIT), cross-
read against the oberskills write skill (ryanthedev/oberskills, MIT). When you
sort tells by how often a human cited them, the list looks nothing like the list
a regex would produce.

## The divergence

Some tells get cited constantly and are easy to match. Some get cited constantly
and *cannot* be matched by any word list. And some match all day but nobody cites
them, because that is just how people write.

**Top cited tells** (approximate share of audited posts citing each):

| Tell | Cited | Matchable? |
|---|---|---|
| Em dash overuse | ~7.1% | yes (punctuation) |
| Flat, uniform sentence rhythm | ~4.0% | structural only |
| "not just X, it's Y" antithesis | ~2.8% | partly (regex-blind variants) |
| Five-paragraph + "in conclusion" shape | ~2.5% | structural only |
| Sycophancy ("great question!", reflexive "you're absolutely right") | high | no word list |
| Saying nothing at length (fluent but empty) | high | no word list |

The em dash is the single most-cited tell. AI uses it at two to five times the
human rate (Pangram Labs). That is why it sits at the top of the weight table and
why the autofixer rewrites it everywhere outside `creative`.

Two of the top tells — sycophancy and saying-nothing-at-length — can never be
caught by a vocabulary list. You have to read for them. The linter flags the
stock openers it can see (`chatbot_scaffold`, `vague_declarative`), but the real
catch is a skeptical human read.

**High-match, low-cited words** — these match at up to 6.3% but are cited near
0%, because people genuinely write this way:

- however
- thus
- hence
- nuanced
- comprehensive
- robust
- when it comes to

A linter that weights these like the em dash flags clean human prose and misses
the actual machine cadence. So v0.4.0 demotes them.

## The three weight tiers

The linter sorts every tell into one of three tiers. The tier reflects how often
the tell is *cited*, not how easy it is to match.

- **Tier A (weight >= 2.0)** — high-cited structural tells and hard artifacts:
  em-dash overuse, flat rhythm, the antithesis template, the five-paragraph
  shape. These move the score the most because readers react to them the most.
- **Tier B (weight 1.5)** — moderate tells: real but secondary, the kind a reader
  notices on a second pass.
- **Tier C (weight <= 0.5)** — generic diction, parked in `soft_filler` and
  `transitions`. The high-match/low-cited words live here. A hit nudges the score;
  it never carries a verdict on its own.

The "however/thus/comprehensive" set sits in `soft_filler` at weight 0.5
precisely because it matches often and means little.

## How to read a result

The **relative order** of the tells matters more than the exact percentages. The
~7.1% and ~4.0% figures come from one corpus at one moment; they will drift as
models and writers change, exactly as banned-word lists age. What holds is the
ranking: punctuation and structure over diction.

A hit is a **floor signal, never proof**. One flagged em dash does not make a
sentence AI, and a clean lexical pass does not make a paragraph human. The score
tells you where to look. The decision is still a read.

## Sources

- JCarterJohnson/vibecoded-design-tells (MIT) — the ~90,000-post Reddit audit of
  what readers cite as AI.
- ryanthedev/oberskills, the write skill (MIT) — corroborating tell catalog.
- Pangram Labs — em-dash rate measurement (2-5x human) and phrase-overuse counts.
