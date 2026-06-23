# Contributing to human-voice

Thanks for helping improve the skill. It has two halves: the **methodology**
(`skills/human-voice/SKILL.md`, `references/ai-tells.md`, `STYLE-GUIDE.md`,
`examples/`) and the **linter**, the `scripts/human_voice_linter/` package with
`scripts/ai_prose_patterns.json`, run via the `scripts/detect_ai_prose.py` entry
point. Both are pure-stdlib Python 3.8+, so no `pip install` is needed to run them.

The linter package is split into small modules: `defaults` (the single source of
truth for thresholds/weights/bands), `checks` (every `check_*`), `analyze` (the
orchestrator), `score`, `report`, `autofix`, `config`, `schema` (config
validation), `directives` (inline ignore comments), `cli`, and `api`.
`detect_ai_prose.py` is a thin shim that re-exports the package.

## Run the tests

```bash
make test          # stress suite (500+ checks); must print "all green"
make eval-check    # fail if eval metrics drift from the committed golden JSON
make eval          # regenerate the golden metrics after an intentional change
make quality       # dev-only: ruff + mypy + pytest (needs `pip install ruff mypy pytest`)
```

CI runs the stress suite on Python 3.8–3.13 plus a single-version `quality` job
(ruff/mypy/pytest) and the eval regression gate (`.github/workflows/test.yml`).
The runtime stays pure stdlib; ruff/mypy/pytest are dev-only (the `dev` extra in
`pyproject.toml`). A PR must keep all of it green.

If you change patterns or a check and the eval metrics move intentionally, run
`make eval` to regenerate `eval/results.json` / `eval/ablation_results.json` and
review the diff. That committed change is what `make eval-check` gates against.

## Adding or editing tells (word lists)

Edit `scripts/ai_prose_patterns.json`. The linter reads all word/phrase lists,
thresholds, category weights, and verdict bands from it.

- Add a lexical entry as `"phrase": "suggested fix"` (or `"phrase": null` to mean
  "usually cut"). The forward-compatible object form `{"suggestion": "..."}` is
  also accepted.
- Lexical lists are a **floor, not proof**, so prefer high-signal phrases over
  broad words that fire on legitimate prose. If a word has a common innocent sense
  (e.g. `harness`, `vital`), add a `context_exceptions` phrase rather than the
  bare word, or leave it out.
- Every new entry should come with a stress-test case: a positive (it fires) and,
  where false positives are plausible, a negative (it stays quiet). Add both to
  `tests/stress_test.py`.
- Rotate stale tells. Banned-word lists age; bump `version`/`updated` in the
  patterns file when you do.

## Adding a new linter check

1. Write a `check_*` function in `scripts/human_voice_linter/checks.py` that
   appends `Hit`s (and populates report metrics if useful). For source-accurate
   columns on text whose geometry matches the file, build hits with `_span_hit`.
2. Add its category to `DEFAULTS["category_weights"]` in `defaults.py` **and** to
   `category_weights` in the patterns file (a stress-test drift guard fails if
   they disagree). Add any threshold to `DEFAULTS["thresholds"]` too.
3. Wire it into `analyze()` in `analyze.py`, reading thresholds via the local
   `thr("key")` helper where relevant.
4. Mute it by register in `register_mutes`/`muted_checks` if it doesn't apply
   everywhere (e.g. passive voice in academic prose).
5. Add positive and negative tests. Confirm `examples/after.md` still scores
   `clean`. New checks must not over-flag good human prose.

## Project config

Projects can drop a `.humanvoicerc` (JSON) at their root to set a default
`register`/`dialect`, override `thresholds`/`category_weights`/`score_bands`, and
add `protected_terms` (product names and required jargon that must never be
flagged). See the README.

## Versioning

`.claude-plugin/plugin.json` is the **canonical** version. When you bump it,
update the matching `version` in `.claude-plugin/marketplace.json`; the stress
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
