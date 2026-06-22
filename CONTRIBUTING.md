# Contributing to human-voice

Thanks for helping improve the skill. It has two halves: the **methodology**
(`skills/human-voice/SKILL.md`, `references/ai-tells.md`, `STYLE-GUIDE.md`,
`examples/`) and the **linter** (`scripts/detect_ai_prose.py` with
`scripts/ai_prose_patterns.json`). Both are pure-stdlib Python 3.8+ — no
`pip install` needed.

## Run the tests

```bash
python3 tests/stress_test.py     # 400+ checks; must print "all green"
python3 eval/run_eval.py         # corpus precision/recall/FPR
```

CI runs the stress suite on Python 3.8–3.13 (`.github/workflows/test.yml`). A PR
must keep the suite green.

## Adding or editing tells (word lists)

Edit `scripts/ai_prose_patterns.json` — the linter reads all word/phrase lists,
thresholds, category weights, and verdict bands from it.

- Add a lexical entry as `"phrase": "suggested fix"` (or `"phrase": null` to mean
  "usually cut"). The forward-compatible object form `{"suggestion": "..."}` is
  also accepted.
- Lexical lists are a **floor, not proof** — prefer high-signal phrases over broad
  words that fire on legitimate prose. If a word has a common innocent sense
  (e.g. `harness`, `vital`), add a `context_exceptions` phrase rather than the
  bare word, or leave it out.
- Every new entry should come with a stress-test case: a positive (it fires) and,
  where false positives are plausible, a negative (it stays quiet). Add both to
  `tests/stress_test.py`.
- Rotate stale tells. Banned-word lists age; bump `version`/`updated` in the
  patterns file when you do.

## Adding a new linter check

1. Write a `check_*` function that appends `Hit`s; population of report metrics is
   fine too.
2. Add its category to `CATEGORY_WEIGHTS` in the script **and** to
   `category_weights` in the patterns file (keep them in sync).
3. Wire it into `analyze()`, with a threshold read from `patterns["thresholds"]`
   via `safe_float` where relevant.
4. Mute it by register in `register_mutes`/`muted_checks` if it doesn't apply
   everywhere (e.g. passive voice in academic prose).
5. Add positive and negative tests. Confirm `examples/after.md` still scores
   `clean` — new checks must not over-flag good human prose.

## Project config

Projects can drop a `.humanvoicerc` (JSON) at their root to set a default
`register`/`dialect`, override `thresholds`/`category_weights`/`score_bands`, and
add `protected_terms` (product names and required jargon that must never be
flagged). See the README.

## Versioning

`.claude-plugin/plugin.json` is the **canonical** version. When you bump it,
update the matching `version` in `.claude-plugin/marketplace.json` — the stress
suite has a drift guard that fails if they disagree. Add a `CHANGELOG.md` entry.

## Verify install

Before release, confirm both install paths work end to end:

```bash
# from the repo
python3 skills/human-voice/scripts/detect_ai_prose.py skills/human-voice/examples/after.md
# marketplace (in Claude Code)
/plugin marketplace add stephenoffer/human-voice
/plugin install human-voice@human-voice
```

`marketplace.json` uses `"source": "./"`, so the repo root is the plugin root.

## Scope

The linter and word lists are English-only today (the dialect map covers
American/British). Non-English support would namespace the pattern lists by
language; contributions welcome.
