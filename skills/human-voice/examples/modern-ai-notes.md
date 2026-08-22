# What changed, and why (modern-AI case)

<!-- human-voice: ignore-start meta_commentary,filler,rule_of_three -->
The other before/after pairs in this directory start from 2023-era slop: filler,
puffery, bold-bullet listicles, "In conclusion". Nobody is fooled by that text,
and fixing it is mostly a diction exercise.
<!-- human-voice: ignore-end -->

This pair starts from the harder case. `modern-ai-before.md` is what a current
instruction-tuned model produces when it is not being caricatured. It is fluent.
It takes a position, and it carries concrete detail. No filler, no hedging stack, no
em-dashes at all. The linter's word lists have nothing to say about
it, and it still reads as machine-written.

Floor score 19.9 → 0.0. Words 206 → 173 (−16%). No fact changed.

## What gave it away

| Metric | Before | After | Target |
|---|---|---|---|
| sentences ≤ 8 words | 0% | 42% | ≥ 12% |
| sentences in the 12–26 word band | 73% | 42% | ≤ 72% |
| sentence-length CoV | 0.33 | 0.65 | ≥ ~0.5 |

Every sentence in the original is between ten and thirty words. Not one is short.
That is the whole tell, and it is invisible to a word list. Read the original
aloud and it never lands anywhere. Each sentence sets up, qualifies, and resolves
at the same tempo as the last.

Four other things went.

The survey opening, first. "The decision comes down to how much operational surface
you want to own" frames a tradeoff instead of answering one, so the rewrite leads with
the verdict instead: *Start with pgvector.*

Then the symmetrical concession. "Managed services handle X for you, but you pay Y and
you are bound to Z" is the balanced both-sides move, and it recurs in every paragraph
of the original. The rewrite lets a concession be short and lopsided. "What you give
up is real." Then two sentences of what.

<!-- human-voice: ignore-start rule_of_three -->
The reflexive tricolon went too. "backups, monitoring, and access control" became
"already back up, already monitor, already have access control for", which is
repetition doing rhetorical work rather than filling a slot.
<!-- human-voice: ignore-end -->

And "One caveat worth naming", a phrase that announces a caveat instead of stating
one. The rewrite states it.

## The same procedure across all twelve

This pair is one of twelve. `eval/corpus/ai_modern/` holds twelve realistic
modern-AI samples covering every register the skill supports, and
`eval/corpus/ai_modern_rewritten/` holds each one after the procedure, under the same
filename. Measured on the floor score:

| | before | after |
|---|---|---|
| mean floor score | 12.9 | **1.2** |
| files in the `clean` band | 3 of 12 | **12 of 12** |
| files flagged at the default 5.0 boundary | 9 | **0** |
| files that got worse | n/a | **0** |

`python3 eval/run_eval.py` prints that table and names any file that regressed. A
pytest case asserts every numeric token in an after-file appears in its before-file,
so the anti-hallucination protocol is enforced mechanically rather than promised.

## What did not change

Ten million vectors, HNSW, working memory, pre-filtering, sequential scan, tail
versus mean: every claim from the source survives, and nothing joined it. The
draft said "several metadata predicates", so the rewrite says "several", an
earlier pass of this example wrote "three or four", which is exactly the kind of
invented specificity principle 3 forbids, and it was reverted.
