---
name: False positive on human text
about: The linter flagged genuinely human-written prose
title: "[FP] "
labels: false-positive
---

**The text** (a short excerpt the linter flagged — paste it):

```
...
```

**Register used** (technical / marketing / academic / casual / email / ...):

**What the linter reported** (run `detect_ai_prose.py --json <file>` and paste the
score, verdict, and the offending `hits`):

```
...
```

**Why this is human/legitimate:**

False positives on real human prose are the most important bug class — they feed
the corpus in `eval/` and the false-positive-rate measurement in `EVAL.md`. If you
can, note whether a `context_exceptions` or `protected_terms` entry would fix it.
