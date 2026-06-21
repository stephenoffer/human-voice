# human-voice

A Claude Code skill that rewrites or generates prose so it doesn't read as
AI-written, without touching your facts, numbers, code, or citations.

Most "humanizer" tools swap a few words and call it done. The text still reads
as a machine wrote it, because the giveaways aren't mostly lexical. They're
structural (em-dash overuse, relentless rule-of-three, bold-bullet listicles,
sentences that are all the same length) and substantive (paragraphs that say
nothing, a survey where a verdict belongs, invented specifics). This skill fixes
those first and treats word choice as the last and shallowest pass.

It ships with a linter that scores the cheap, regex-able tells: filler diction,
em-dash density, bold-bullet ratio, rule-of-three, sentence-length burstiness,
n-gram repetition, lexical diversity, and dialect drift. The linter is a floor,
not a verdict: it can't see vacuity or weak stance, and no detector is ground
truth. The real test is a skeptical human read.

## Install

### 1. Plugin marketplace (one command)

```
/plugin marketplace add stephenoffer/human-voice
/plugin install human-voice@human-voice
```

Then run `/human-voice` in any session.

### 2. Manual skill copy

```bash
git clone https://github.com/stephenoffer/human-voice.git
cp -r human-voice/skills/human-voice ~/.claude/skills/        # user scope
# or, for one project only:
cp -r human-voice/skills/human-voice <your-project>/.claude/skills/
```

### 3. Use it from this repo directly

The skill already lives at `skills/human-voice/`. Open this repo in Claude Code
and invoke `/human-voice`.

## Use

```
/human-voice <file-path | pasted-text> [fix|generate] [register: technical|business|marketing|academic|casual|creative]
```

- `fix` (default) rewrites an AI-sounding draft.
- `generate` drafts new copy that reads human from the start.
- `register` matches the genre's conventions; it's inferred if you omit it.

Run the linter on its own anytime:

```bash
python3 skills/human-voice/scripts/detect_ai_prose.py <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --register marketing <file>
python3 skills/human-voice/scripts/detect_ai_prose.py --dialect american <file>
printf '%s' "$TEXT" | python3 skills/human-voice/scripts/detect_ai_prose.py -
```

It needs only Python 3, no `pip install`. The word and spelling lists live in
`skills/human-voice/scripts/ai_prose_patterns.json`; edit them to taste.

See `skills/human-voice/examples/` for a before/after pair: the AI-sounding
`before.md` scores high and the rewritten `after.md` scores clean. Run the
linter on both to see the difference on your machine.

## What it won't do

It improves writing; it does not disguise machine text. No Unicode homoglyphs,
no zero-width characters, no deliberate typos, no meaning-degrading synonym
swaps, and never invented facts, quotes, or statistics to seem human. Passing a
detector is a side effect of good writing, not the goal.

## License

MIT. See [LICENSE](LICENSE).
