# Content architecture: what a document spends its words on

Every other reference in this skill works at the level of a sentence, a paragraph
or the markdown on the page. This one reads the document as a plan. Clean
sentences don't save a document built by filling an outline to quota. A reader who
skims the headings and then reads two sections will feel it before they can name
it.

An agent writes a report the way it was asked to: list the sections a report of
this kind has, then fill each one. That procedure leaves four marks. Its points
come back in the summary. The words go wherever writing is easy, so the risky part
gets a sentence. Every heading has to hold something, so some hold filler. Depth
tracks what the model happened to know, never what the reader needed.

## 1. Restatement

The overview says the service replaces the batch pipeline to cut latency and let
teams add event types. The architecture section says it again with details. The
summary says it a third time, word for word apart from its opening phrase. The
subtler form is a "Key design decisions" section that re-lists what the section
above it just explained, or a bulleted recap under a paragraph that already made
each point.

A model writes each section to stand alone. It has no sense that the reader has
already been told, so every section re-establishes context.

Say each point once, in the place where it does the most work. A reader who needs
the conclusion first gets it at the top, and the body then gives evidence rather
than repeating the claim. Merge the recap into the copy you keep: a summary that
re-words the overview often slips in one fact the overview never stated, and that
fact moves before the recap goes. If a long document truly needs a summary, it
carries the decision and the open questions, never the overview reworded.

`restatement` flags a sentence or list item whose content words mostly match one
in another section, once there are two or more such pairs at 2.5 per thousand
words. It ignores verbatim copies and parallel reference entries, and it misses a
paraphrase built from different words. That part is judgment. When the repeat
carries a number or a term found nowhere else in the source, the finding names it
and suggests a merge instead of a cut.

## 2. Section balance

Filling a template leaves four different shapes.

Stubs are the plainest: `## Monitoring` followed by "Dashboards and alerts will be
set up for key metrics." The heading promised a topic and the writer had nothing
to say about it.

Bloat lands on the easy section. A migration plan gives the schema four hundred
words and a SQL listing, then covers rollback in one line. The part a reviewer
will ask about got nothing.

Quota sections look tidy. Five options at eighty words apiece, each with exactly
three strengths and three weaknesses. Real topics are not the same size. Real
tradeoffs are lopsided.

Framing outweighs substance when the overview, the background, a "why this
matters" section and the summary together run longer than the part that says what
to do.

The outline comes first and the content second. Each heading gets a share of the
budget whether or not there is material for it.

Weigh each section by what the reader needs from it, not by its place in the
outline. The questions a reviewer will actually ask (what breaks, how we undo it,
what it costs) get the most words. A heading with nothing behind it goes, but its
sentence usually still commits to something ("Access to Redis will be restricted"),
so fold that commitment into a neighbour rather than deleting it. Where a section is required and the material is
missing, say so plainly ("Rollback: not yet designed; owner TBD") rather than
writing a sentence that sounds like a plan. Never invent the missing plan
(principle 3). Let lists be as long as their content.

`section_balance` fires on two or more hollow stubs beside a section eight times
their size, on five or more sections within a few words of each other, on framing
sections holding over 35% of the words with a recap among them, and on four or
more lists all cut to the same length. A stub with a link or a command in it is a
pointer, not a stub, and changelog releases are exempt.

## 3. Depth drift

One section quotes `min.insync.replicas=2`, a p99 of 41 seconds and the flush
interval. The next section, "Scalability", says the system scales horizontally,
which ensures it can handle increased load without degrading performance. The
first was written by someone who knew the system. The second could describe any
system ever built.

The other direction is the same fault. A README explains that "in simple terms, a
cache is a place where you store results so you don't have to compute them again"
two sections before a benchmark table in nanoseconds. Two readers are being
addressed, and neither is served.

The model writes each section at the depth of whatever it has. Where the prompt or
the context gave it specifics, it is precise. Where it had nothing, it falls back
on the abstract benefit vocabulary (reliability, flexibility, efficiency) that
fits any topic. And it pads toward a reader it cannot see by explaining basics
just in case.

Decide who reads this and what they already know, then hold every section to that
level. A hollow section either gets the real detail from the author-material
intake or shrinks to the claims only it makes. Primers go, or move to one glossary
line, unless the genre is a tutorial. The hardest part of the subject should be
the deepest part of the document. When it is the shallowest, the architecture is
upside down.

`depth_drift` counts checkable markers per hundred words by section: numbers with
units, and names lifted from the system itself (identifiers, flags, paths,
acronyms, code). It flags a section of 120 words or more with almost none, made of
abstract benefit words, when another section is dense. It also flags three or more
beginner explanations in a document that is otherwise technical. Tutorials get
twice the tolerance for the second.

## 4. Order (judgment only)

The outline order is not the reader's order. Background, goals, architecture,
risks, summary is the order a template lists them in. A reviewer wants the
decision, the thing that could go wrong, and the cost, usually in that order, with
background only as far as it explains those. No count sees this. Ask what the
reader has to decide after reading, and move whatever serves that decision to the
top.

## The section map

Run this before the sentence-level passes. It takes a few minutes, and it changes
what the later passes have to do.

For each section, write one line:

| Section | Words | The one thing it says | Depth (0-3) | Repeats | Only here |
|---|---|---|---|---|---|
| Overview | 90 | replaces batch with streaming | 0 | | |
| Architecture | 195 | Kafka, validators, sinks, p99 41s | 3 | | |
| Scalability | 110 | (nothing specific) | 0 | | cluster can be expanded |
| Monitoring | 8 | (nothing) | 0 | | alerts will exist |
| Summary | 85 | replaces batch with streaming | 0 | Overview | "within 60 seconds" |

Depth: 0 framing or nothing checkable, 1 conceptual, 2 operational (what to run,
what to set), 3 implementation (numbers, mechanisms, failure modes).

The last column is the one that protects the author. It lists every fact, number,
name, commitment, decision, caveat or owner that appears in that section and
nowhere else in the document. Fill it before deciding anything. A section can look
empty in the third column and still carry something in the last.

Then act on the map. A row whose "one thing" matches another row gets merged, and
its "only here" items move into the row that stays. A row with nothing in the
third column is filled from the intake, or reduced to its "only here" items and
folded into a neighbour, or marked as a gap. Rows at depth 0 beside rows at
depth 3 are levelled. A table whose largest row is the easiest topic gets
rebalanced toward the risky one. Last, reorder the rows for the reader's
decision.

## Nothing distinct is cut without the author's say-so

A structure pass deletes more than any other pass in this skill, which makes it
the likeliest to lose something the author meant to keep. So every deletion it
makes falls into one of three kinds, and only two of them are yours to make.

Moving is always allowed. Reordering sections, merging two into one and folding a
stub into its neighbour lose nothing, as long as every "only here" item lands
somewhere.

Cutting a true duplicate is allowed. The test is the map's last column: if a
sentence has nothing in it, every claim it makes survives elsewhere, so delete the
copy that does less work. The `restatement` finding does this check lexically and
names what a repeat alone carries. Treat its "every word is stated elsewhere" as
evidence, not proof, since a paraphrase can say something new in old words.

Cutting distinct information needs approval. If a sentence or section is the only
place a fact, number, name, commitment, decision, caveat or owner appears, it
stays in the document until the author agrees it should go, however vague or
badly placed it is. Vagueness gets fixed by rewording ("Monitoring: alerts will be
set up" becomes one clause in the rollout paragraph), not by deletion. When a
distinct item really should go (it is wrong, out of scope, or a commitment the
team has dropped), propose the cut instead of making it:

- in an interactive session, ask before applying the edit, in one batch listing
  each item and why;
- when editing a file, leave the item in place and list it under "Proposed cuts"
  in the audit;
- when nobody can answer, keep it. A redundant sentence costs the reader a few
  seconds. A deleted commitment can cost the author a promise they did not know
  had disappeared.

The claim diff in the self-critique loop checks this afterwards. For a structure
pass the "dropped" bucket must be empty, or contain only items the author approved.

The linter's `structure:` line gives the raw numbers (section count, length
spread, framing share, restated pairs, depth per section) so the map starts from
measurement rather than impression.

## When the rule fights the task

Some genres are built from the shapes above, and there the shape stays.

An API reference repeats "Returns true if…" under every function, and each entry
is short by design. That parallelism is the genre, so the linter skips entries
under headings that name code.

Changelogs have even releases, repeated entries and thin sections.
`section_balance` is muted in `release_notes`.

A template with a mandatory Security section gets a Security section. Fill it with
the true answer, even a short one ("no new network surface; reads one existing
table"). That is content, not a stub.

In a tutorial, explaining the basics is the job. Depth drift in the other
direction still counts: a tutorial that explains what a container is and then
skips the step where people get stuck has put its depth in the wrong place.

A long runbook may restate the one rule nobody can afford to miss ("never run this
against production"). Once, on purpose, is emphasis. The linter needs two restated
pairs before it says anything.

## Measurement

Calibrated on 869 long, sectioned markdown documents written by people: the
READMEs and manuals that ship with Homebrew formulae, npm packages, Rust crates
and Python packages, each 400 to 6,000 words with four or more headings. At the
shipped thresholds the three checks fired on 6 of them: restatement on 5, depth
drift on 1, section balance on none. The positives in `eval/structure/ai/` are all
caught. They are authored, so that is a check that the detectors see what they
describe, not an estimate of how often agents write this way. Details and the
reproduction command are in `eval/EVAL.md`.