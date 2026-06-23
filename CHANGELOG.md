# Changelog

All notable changes to the human-voice skill and its linter are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/); versions
track `.claude-plugin/plugin.json`.

## [Unreleased]

### Linter — the "second dialect" (v0.4.1 patterns)
- `rule_of_three` now also catches **noun-phrase** triads ("encryption at rest,
  row-level access control, and audit logging") that the single-word pattern
  missed; gated to fire only when a document stacks 2+ (a lone enumeration is
  left alone). Measured 14/24 AI vs 1/34 human on the corpus.
- New `false_agency` pattern for the "[inanimate thing] lives/sits in [place]"
  locative ("a project living in five tools", "the logic lives in the
  controller").
- Documented the second-dialect tells a regex shouldn't chase (the ", and" splice
  rhythm and stacked "[noun] is [noun]" copulas — both too common in careful and
  ESL writing to flag) in `references/structural-craft.md`, and rewrote the
  shipped "after" examples to remove all four (they had become a tidier AI
  dialect: ", and" splices, copular stacks, triads, and a "project living in"
  locative).

### Linter — craft tells (v0.4.1 patterns)
- New `cowardly_passive` category: evasive actor-hiding passives ("it can be seen
  that", "the decision was made to", "mistakes were made"), distinct from the
  passive-voice density check.
- New `whether you're X or Y` antithesis pattern; resumptive connectives ("in
  terms of", "with regard to", "in the context of") added to `soft_filler` at
  Tier-C weight (common in careful/ESL writing, so a whisper not a verdict).
- New `references/structural-craft.md`: the generative companion (vary length and
  density, don't follow the outline, get specific, cowardly passives, emotional
  range, self-correction traces) drawn from `oberskills`' deep-craft material.
- Skill frontmatter: added a `when_to_use` routing field.

### Linter — evidence-based recalibration (v0.4.0 patterns)
- Retiered category weights by what readers **cite** as a tell, not what a
  keyword scanner **matches**. Source: a ~90k-post Reddit study
  (`JCarterJohnson/vibecoded-design-tells`, MIT) plus the `oberskills` write
  skill (`ryanthedev/oberskills`, MIT). The two diverge: generic words
  (`however`/`thus`/`nuanced`/`comprehensive`/`robust`/`when it comes to`) match
  often but are cited ~0% of the time. See `references/cited-vs-matched.md`.
- Split generic high-match/low-cited diction into a new `soft_filler` category at
  weight 0.5 (was weight 1.0 inside `filler`); lowered `transitions` 1.0→0.5.
  Raised the structural/artifact tells readers actually catch: `antithesis`
  1.5→2.0, `bold_bullets` 1.5→2.0; added `sycophancy` and `aidiolect` at 2.0.
- Tightened the em-dash density floor 2.0→1.5 per 1k words (AI uses the em-dash
  at 2–5× the human rate, Pangram Labs).

### Linter — new tell categories
- Lexical: `sycophancy` ("great question!", reflexive "you're absolutely right"),
  `aidiolect` (multi-word phrases overused at 10,000×+: "a testament to", "the
  complex interplay", "faced numerous challenges"), `cliche_metaphor`
  (foundation/landscape/journey/double-edged-sword frames), `internet_tells` (the
  2025–26 cadence: "load-bearing", "honestly?", "it's giving"),
  `significance_inflation` ("opens new avenues", "cannot be overstated").
- Structural: `five_paragraph_shape` (intro/three-body/"in conclusion" mold),
  `hypophora` (ask-then-immediately-answer), `superlative_creep` (absolutes with
  no number nearby), `svo_monotony` (a long run of Subject-Verb-Object openers),
  `name_selection` (Emily/Sarah/"Dr." defaults; muted outside creative/casual),
  `over_correction` (the anti-AI costume: forced lowercase + sprinkled slang).
- ~165 new lexical entries across the new and existing lists; expanded
  `antithesis_patterns`, `hedging`, `redundancy`, and `vague_attribution`.

### Evaluation — rigor
- New hard-negative classes: `eval/corpus/esl_formal/` (careful non-native and
  formal-human samples, labeled human, that real detectors over-flag) with a
  dedicated **ESL-FPR** metric; `eval/corpus/over_corrected/` (the anti-AI
  costume, held out of the binary AUC and scored on its own recall).
- Cited-ranking correlation test (`eval/tests/test_calibration.py`): the category
  weights must keep a strong rank correlation with the Reddit cited ranking.
- Expanded the balanced corpus and refreshed the golden metrics + `EVAL.md`.

### Documentation
- New references: `cited-vs-matched.md`, `over-correction.md`,
  `discourse-and-structure.md`; extended `ai-tells.md` (Pangram detector entry,
  new BAD→GOOD pairs, rhetoric-calibration rule). New example pairs
  (over-corrected, cliché-metaphor). MIT attribution to both source repos.

### Linter — architecture & quality
- Split the 1700-line `detect_ai_prose.py` monolith into a `human_voice_linter`
  package (util, defaults, hit, patterns, textutil, directives, checks, score,
  analyze, report, autofix, config, schema, api, cli). `detect_ai_prose.py` is now
  a thin entry-point shim, so the documented invocation and the importlib API
  surface are unchanged.
- Single source of truth for thresholds, category weights, and verdict bands
  (`defaults.DEFAULTS`); the shipped JSON mirrors it and a drift guard keeps them
  consistent. Removed the stale code-vs-JSON fallback divergence.
- Added type hints to the public API and the `Hit` model; surfaced previously
  silent regex-compile failures as warnings.
- New `schema.validate()` config validator: malformed `.humanvoicerc`/patterns
  values are reported on stderr (non-fatal) instead of being silently swallowed.

### Linter — new features
- Per-tell column/character spans (`col`/`end_line`/`end_col` on hits, surfaced in
  JSON and SARIF) for checks whose match geometry matches the source; document-level
  findings carry `scope: "document"`.
- Inline ignore directives: `<!-- human-voice: ignore [categories] -->` (trailing,
  next-line, or `ignore-start`/`ignore-end` block); directives inside code fences
  are inert.

### Evaluation
- Extracted shared `eval/lib.py` (loaders, one canonical metrics/auc/sweep,
  per-register breakdown, deterministic bootstrap CIs, regression comparator,
  corpus validation); the three scripts are thin consumers.
- `run_eval.py --check` / `ablation.py --check` regression-gate against the
  committed golden JSON (CI fails on metric drift instead of silently overwriting).
- Expanded the corpus to 36 balanced samples (18/18) covering every register,
  including the previously empty `creative` and human `business` samples.

### Dev tooling
- Added `pyproject.toml` with ruff + mypy + pytest (dev-only extra; runtime stays
  pure stdlib), a `quality` CI job, `make eval-check`/`make quality`, and pytest
  unit tests for the eval math.

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
