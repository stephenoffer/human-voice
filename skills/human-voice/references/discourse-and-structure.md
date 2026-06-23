# Discourse and Structure

Structure is the highest-value, hardest-to-fake AI signal. Discourse-level
organization is about **34% of the detection signal** — the single largest
category, ahead of syntax (28%), lexical choice (24%), and morphology (14%). You
can swap every flagged word and still get caught on shape.

It is hard to fake because the shape is unconscious. A model defaults to the same
arc across prompts, and RLHF narrows it further — roughly **76.2% diversity loss**
in the training that makes models agreeable. The result is convergence: GPT,
Claude, and Gemini structurally resemble *each other* more than any of them
resembles a human. Detection from grammar alone reaches **88.85% F1**, no
vocabulary required.

## The template to break

AI prose falls into a default arc:

> setup -> complication -> resolution -> reflection

State the situation, introduce a tension, resolve it, then close with a tidy
lesson. It is competent and lifeless because every piece arrives on schedule.

**Fix:** start in the middle. Open on the resolution and backfill the setup, or
end on the complication and leave the reflection off. Real writing skips beats the
reader can supply and lingers on the one that matters.

- BAD → "Caching is a common technique. The challenge is invalidation. We solved
  it with TTLs. This taught us the value of simplicity."
- GOOD → "We set every cache entry to a 60-second TTL and stopped chasing
  invalidation bugs. The stale reads cost us nothing; the bug reports went to
  zero."

## The five-paragraph shape

An intro that previews three points, three body paragraphs, and a conclusion
opening with "in conclusion" or "in summary" that restates the intro. Cited at
~2.5% on its own. The conclusion that loops back to the opening is the loudest
part.

**Fix:** cut the preview and the recap. End on the last real point. If the reader
needs a summary, the body was too long.

- BAD → "In conclusion, as we have seen, caching, TTLs, and simplicity all
  matter."
- GOOD → (end on the last concrete finding; delete the recap.)

The linter flags the loop as `circular_conclusion` and the overall mold as
`five_paragraph_shape`.

## SVO monotony

Subject-verb-object, sentence after sentence, with no subordination or inversion.
The grammar is correct and the rhythm is a metronome. This is what burstiness
detectors measure, and what `svo_monotony` and `burstiness` target.

**Fix:** vary the grammar, not just the length. Lead with a subordinate clause,
front an object, break one sentence in two and run the next one long.

- BAD → "The job reads the queue. The worker processes the batch. The system
  writes the result. The cache stores the value."
- GOOD → "The job reads the queue and hands each batch to a worker. Whatever the
  worker produces, the system writes once and caches."

## Vary the implicit question order

Every paragraph silently answers a question: *what is it? why does it matter? how
does it work? what now?* AI answers them in the same order every time. The
sameness is the tell, even when each sentence is fine.

**Fix:** reorder the implicit questions across paragraphs. Sometimes lead with the
"so what." Sometimes open on the mechanism and let the significance land last.
Uniform paragraph shape is what `paragraph_uniformity` catches.

## The structural checks

The linter targets this category directly:

- `burstiness` — sentence-length and complexity variance.
- `paragraph_uniformity` — paragraphs of near-identical length and shape.
- `circular_conclusion` — a close that restates the open.
- `five_paragraph_shape` — the preview/body/recap mold.
- `svo_monotony` — a run of flat subject-verb-object sentences.
- `parallel_structure` — over-regular parallelism across sentences or bullets.
- `hypophora` — the pose-a-question-then-answer-it reflex, repeated.

## Sources

- JCarterJohnson/vibecoded-design-tells (MIT) — cited-tell frequencies.
- ryanthedev/oberskills, write skill (MIT) — discourse-tell catalog.
- Reported detection breakdowns: discourse ~34%, syntax 28%, lexical 24%,
  morphology 14%; grammar-only detection 88.85% F1; RLHF diversity loss ~76.2%.
