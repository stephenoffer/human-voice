# What changed, and why (modern-AI case)

<!-- human-voice: ignore-start meta_commentary,filler,rule_of_three -->
The other before/after pairs in this directory start from 2023-era slop: filler,
puffery, bold-bullet listicles, "In conclusion". Nobody is fooled by that text,
and fixing it is mostly a diction exercise.
<!-- human-voice: ignore-end -->

This pair starts from the harder case. `modern-ai-before.md` is what a current
instruction-tuned model writes when nobody is caricaturing it. It is fluent, it
takes a position, and it never reaches for a word from anyone's banned list. No
em-dashes either. Every lexical check in the linter passes it, and it still reads
machine-written. The four tells that do fire are all about shape.

Floor score 15.0 → 0.0. Words 251 → 207, down 18%. No fact changed.

## What gave it away

| Metric | Before | After | Target |
|---|--:|--:|--:|
| sentences ≤ 8 words | 0% | 31% | ≥ 12% |
| sentences in the 12–26 word band | 85% | 25% | ≤ 72% |
| sentence-length CoV | 0.29 | 0.67 | ≥ 0.40 |
| paragraph-length CoV | 0.21 | 0.55 | ≥ 0.30 |

Thirteen sentences in the original. The shortest runs twelve words and the
longest twenty-eight, so eleven of the thirteen land in the same narrow band.
Nothing in it is short. Every sentence sets up, qualifies and resolves at the
tempo of the one before it, which is a rhythm no word list can see and no writer
sustains for five paragraphs.

Three other things went.

**The survey opening.** "The decision comes down to how well you understand the
work you are asking for" frames the question instead of answering it. The rewrite
opens with the answer: *Start with a contractor.*

**The symmetrical concession.** "A contractor is faster to bring on and easier to
stop, but their knowledge leaves when the invoice does" is the both-sides move,
and the original runs it in every paragraph. Real judgment is lopsided. The
rewrite keeps the objection, then says why three months is when it costs least.

**The fence.** A whole paragraph of the original says there is no universally
correct answer and that both paths work. It contradicts the recommendation two
paragraphs above it, which is what fence-sitting usually does. It is the only
paragraph the rewrite deletes outright, and that deletion is the one edit here
that needed the author's sign-off.

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

A contractor starts fast and stops easily. Their knowledge of the product leaves
with the invoice. A salary buys accumulated context and a role somebody has to
manage. Three months. Brand, product surface and research as three different
jobs. Re-briefing eats a growing share of a long engagement. Portfolios are
selected work, so ask about the project that went badly. Every claim in the
source survives, and nothing joined it. An earlier pass wrote that the contractor
"was up to speed in March", a month the source never mentions and the writer
never knew, and it was reverted.
