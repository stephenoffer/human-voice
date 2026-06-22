# Refusing to fabricate: the missing-fact case

The most dangerous moment in a humanizing pass is a flat sentence that *wants* a
number. The reflex is to make it vivid. Vivid usually means invented, and an
invented statistic is a hallucination no matter how human it reads.

## The flat AI sentence

> Our caching layer improves performance and makes the application feel much
> faster for users.

It's vague and a little limp. It clearly needs a figure to land. The source
material — the brief, the data, the original draft — does **not** contain one.

## Wrong: invent a number to make it sing

> Our caching layer cut p99 latency by 40%, so pages now feel instant.

This reads great. It's also a fabrication. "40%" appears nowhere in the source;
neither does "p99" or "instant". The rewrite added *facts*, not *voice*, and
crossed the one line the skill never crosses (principle 3). A reader, an editor,
or a detector's human reviewer who checks the claim finds nothing behind it.

## Right: keep it honest, mark the gap

> Our caching layer cut latency on repeat reads. [SOURCE NEEDED: latency figure
> — by how much?]

Or, if no measurement exists and the sentence can't earn its keep, cut it. A
visible `[SOURCE NEEDED]` is honest: it tells the author exactly what to supply.
The sharpening that *is* allowed here is narrow — "performance" became "latency
on repeat reads" only because caching repeat reads is what the layer does, which
is entailed by the source. The magnitude is not, so it stays a placeholder.

The rule in one line: sharpen the *wording*, never the *facts*. When the prose
needs a fact you don't have, mark it — don't make it up.
