# Changelog

All notable changes to the human-voice skill and its linter are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/); versions
track `.claude-plugin/plugin.json`.

## [Unreleased]

### Linter — detection
- New checks: chatbot-scaffold phrases, over-signposting glue, "it depends"
  non-conclusions, multi-word AI openers, "worth noting" family, hook openers,
  passive-voice density, -ly adverb density, nominalization density,
  rhetorical-question density, colon-summary reflex, paired em-dash asides,
  paragraph-length uniformity, list-item uniformity, circular conclusion, and
  parallel-structure runs.
- New report metrics: em/en-dash profile, punctuation profile, Yule's K,
  sentence-opener entropy, paragraph-length CoV, list-item CoV.
- Broadened rule-of-three (optional Oxford comma, `and`/`or`); MATTR moving-window
  type-token ratio; spaced double-hyphen counted as an em-dash.

### Linter — fewer false positives
- Rule-of-three skips proper-noun lists (`Python, Django, and Flask`).
- En-dash number ranges (`2024–2025`) no longer count as em-dashes.
- Dialect drift skips code identifiers (`analyse()`, `Color.RED`, `OPTIMISE_FLAGS`).
- `context_exceptions` protect legitimate fixed phrases (`test harness`,
  `vital signs`); cited attribution (`studies show [1]`) is not flagged as vague;
  redundancy is skipped inside quotes and headings; density checks have a
  minimum-word floor.

### Linter — scoring, API & config
- Category weights, score bands, and thresholds are externalized to
  `ai_prose_patterns.json`; verdict bands (`clean`/`watch`/`strong-tell`) in text
  and JSON; `schema_version` and per-hit `severity` in JSON.
- New flags: `--fail-over` (CI gate), `--baseline`/compare, `--fix` and
  `--fix-dry-run` (autofix safe swaps), `--sarif`, `--enable`/`--disable`,
  `--threshold`, `--quiet`, `--explain`, `--max-examples`, `--recursive`,
  `--no-config`; multiple inputs and directory walking.
- Importable `lint()` library API; auto-discovered `.humanvoicerc` project config;
  project-specific `protected_terms` allowlist.
- Performance: cached regex compilation, `LineMap` bisect for line lookups,
  single-pass abbreviation handling, tokenize-once.
- Four new registers: `email`, `release_notes`, `ux_microcopy`, `tutorial`.

### Methodology & docs
- Catalog expanded with the tells above plus weak intensifiers, gratuitous
  reformulation, hype verbs, over-explaining, parenthetical over-qualification,
  chatbot politeness, and emoji-as-bullet decoration.
- Self-critique loop gains a three-persona review, a 0–2 dimension rubric,
  measurable targets, an A/B-against-original check, and a fixed-point stop rule.
- Anti-hallucination protocol gains a structured four-bucket claim diff
  (added/strengthened/weakened/dropped), a completeness check, quote/citation
  integrity, and an explicit generate-mode path.
- Detector-science section updated: modern detectors (Binoculars, Ghostbuster,
  DNA-GPT, GLTR, RADAR), the ESL false-positive finding (Liang et al. 2023), and
  qualified watermarking/curvature claims.
- New examples per register, a generate-mode example, a refusal-to-fabricate
  example, a restraint case, and an annotated walkthrough.
- Evaluation harness (`eval/`) with a labeled corpus, precision/recall/FPR
  measurement, an ablation script, an offline-safe external-detector scaffold,
  and `EVAL.md`.

## [0.1.0]
- Initial release: skill instructions, AI-tells catalog, style guide, regex
  linter with the patterns file, before/after example pair, and stress test.
