# What changed, and why (modern-AI case)

<!-- human-voice: ignore-start meta_commentary,filler,rule_of_three -->
The other before/after pairs in this directory start from 2023-era slop: filler,
puffery, bold-bullet listicles, "In conclusion". Nobody is fooled by that text,
and fixing it is mostly a diction exercise.
<!-- human-voice: ignore-end -->

This pair starts from the harder case. `modern-ai-before.md` is what a current
instruction-tuned model writes when nobody is caricaturing it. It is fluent, it
is about something real, and it never reaches for a word from anyone's banned
list. No em-dashes either. Every lexical check in the linter passes it, and it
still reads machine-written. The four tells that do fire are all about shape.

Floor score 15.0 → 0.0. Words 287 → 251, down 13%. No fact changed.

## What gave it away

| Metric | Before | After | Target |
|---|--:|--:|--:|
| sentences ≤ 8 words | 0% | 15% | ≥ 12% |
| sentences in the 12–26 word band | 73% | 31% | ≤ 72% |
| sentence-length CoV | 0.31 | 0.56 | ≥ 0.40 |
| paragraph-length CoV | 0.10 | 0.35 | ≥ 0.30 |
| **mean sentence length** | **19.1** | **19.3** | **not a target** |

Read the last row first, because it is the one that gets misunderstood. The
rewrite does not write shorter sentences. Its average sentence is a word longer
than the original's. Fifteen sentences in the before file run from nine words to
twenty-nine, and eleven of them sit in the middle of that range, so the prose
arrives at one tempo and stays there for five paragraphs. The after file runs
from six words to forty-one. The long sentences got longer and carry more, two
short ones land where the argument turns, and the mean did not move.

Chasing the short-sentence count instead produces the opposite failure, which
this directory also ships: see
[`over-corrected-after.md`](over-corrected-after.md), where every sentence is a
fragment and the result reads as machine-made as the thing it replaced.

Three other things went.

**The survey opening.** "The most common complaint about one-on-ones is that they
turn into status meetings" reports on the discourse instead of telling you what to
do. The rewrite opens with the rule: *Never let it become a status meeting, and
never cancel it.*

**The hedged recommendation.** "Asking for their items first and holding yours
until the end is a reasonable compromise" is advice wearing a disclaimer. It
became "Ask for their items first and keep yours until the end."

**The fence.** A whole paragraph of the original says no single format works for
everyone and that the right cadence depends on team size, seniority and shared
context. It commits to nothing and it contradicts the four rules around it, which
is what fence-sitting usually does. It is the only paragraph the rewrite deletes
outright, and that deletion is the one edit here that needed the author's
sign-off.

## The same procedure across twelve more

`eval/corpus/ai_modern/` holds twelve realistic modern-AI samples covering every
register the skill supports, and `eval/corpus/ai_modern_rewritten/` holds each one
after the procedure, under the same filename. Measured on the floor score:

| | before | after |
|---|---|---|
| mean floor score | 12.9 | **1.2** |
| files in the `clean` band | 3 of 12 | **12 of 12** |
| files flagged at the default 5.0 boundary | 9 | **0** |
| files that got worse | n/a | **0** |

`python3 eval/run_eval.py` prints that table and names any file that regressed. A
pytest case asserts that every numeric token in an after-file appears in its
before-file, so the anti-hallucination rule is enforced mechanically rather than
promised.

## What did not change

A status meeting wastes a slot both people agreed to protect. Spoken updates are
slower than written ones. The conversations worth having are the ones that never
reach a written update. Thirty minutes, recurring, never moved. Cancelling in a
busy week cancels the week worth talking about. Your list crowds out theirs.
Silence beats a question nobody cares about, and a year of the meeting is paid
for by the few times it was already there. Every claim in the source survives,
and nothing joined it. An earlier pass had the reader feeling the status meeting
go wrong "by minute four", a number the source never gives, and it was reverted.
