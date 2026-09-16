.PHONY: visuals visuals-check providers prompt test eval eval-check lint dogfood human-baseline profile profile-check detector detector-local detector-check verify quality all

# Full robustness + correctness suite (also runs in CI on Python 3.8-3.13).
test:
	python3 tests/stress_test.py
	python3 tests/test_llm.py

# Evaluation harness: regenerate the golden metrics (run after intentional changes).
eval:
	python3 eval/run_eval.py
	python3 eval/ablation.py
	python3 eval/human_baseline.py

# Regression gate: fail if metrics drift from the committed golden JSON. Writes
# nothing, so the working tree stays clean. This is what CI runs.
eval-check:
	python3 eval/run_eval.py --check
	python3 eval/ablation.py --check
	python3 eval/human_baseline.py --check
	python3 eval/structure_eval.py --check

# False-positive sweep over human prose nobody wrote for this repo: the Python
# standard library's own docstrings. Offline, no dependencies, no network. It is
# the only negative set here that the corpus author did not write.
human-baseline:
	python3 eval/human_baseline.py

# The committed human function-word profile behind the (unscored) stylometric
# delta. Regenerate when eval/corpus/human/ changes; --check gates the drift.
profile:
	python3 eval/build_profile.py

profile-check:
	python3 eval/build_profile.py --check

# Dogfood: lint the repository's own prose. The reference docs QUOTE the tells they
# teach, so they are excluded; what is gated is the prose a reader takes as the
# project's own voice. A skill that tells writers to drop the em-dash should not
# ship a spec containing sixty-six of them, which is what SKILL.md did until v0.6.
dogfood:
	python3 skills/human-voice/scripts/detect_ai_prose.py --quiet --register technical \
		README.md CONTRIBUTING.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 --quiet \
		--register technical README.md docs/README.md docs/getting-started.md docs/install.md docs/usage.md docs/examples.md docs/evidence.md docs/comparison.md
	@echo "--- em-dash density in the project's own prose (want 0 outside creative)"
	python3 skills/human-voice/scripts/detect_ai_prose.py --quiet --enable em_dash \
		--register technical README.md CONTRIBUTING.md CHANGELOG.md eval/EVAL.md \
		skills/human-voice/SKILL.md skills/human-voice/STYLE-GUIDE.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 0 --quiet \
		--enable em_dash --register technical README.md CONTRIBUTING.md CHANGELOG.md \
		docs/README.md docs/getting-started.md docs/install.md docs/usage.md \
		docs/examples.md docs/evidence.md docs/comparison.md \
		eval/EVAL.md skills/human-voice/SKILL.md skills/human-voice/STYLE-GUIDE.md \
		skills/human-voice/references/anti-jargon.md \
		skills/human-voice/references/cited-vs-matched.md \
		skills/human-voice/references/discourse-and-structure.md \
		skills/human-voice/references/over-correction.md \
		skills/human-voice/references/structural-craft.md \
		skills/human-voice/references/content-architecture.md \
		skills/human-voice/references/what-detectors-see.md \
		skills/human-voice/references/competitive-landscape.md
	# references/ai-tells.md is exempt: its dash-mechanics section cannot teach the
	# right mark without printing the wrong one, and the BAD examples throughout are
	# supposed to contain the tell.

# Lint the shipped example pairs. Every "after" must score clean; the modern-AI
# pair is the one that matters, since it starts from prose a current model writes
# rather than from 2023-era slop.
lint:
	python3 skills/human-voice/scripts/detect_ai_prose.py skills/human-voice/examples/after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 skills/human-voice/examples/after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --register technical \
		--baseline skills/human-voice/examples/modern-ai-before.md \
		skills/human-voice/examples/modern-ai-after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 \
		--register technical skills/human-voice/examples/modern-ai-after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --register technical \
		--baseline skills/human-voice/examples/syntax-signature-before.md \
		skills/human-voice/examples/syntax-signature-after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 \
		--register technical skills/human-voice/examples/syntax-signature-after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --register technical \
		--baseline skills/human-voice/examples/architecture-before.md \
		skills/human-voice/examples/architecture-after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 \
		--register technical skills/human-voice/examples/architecture-after.md

# Optional: measure the shipped pairs against a real external detector. Offline
# and exit-0 with no API key set; see eval/detector_harness.py.
detector:
	python3 eval/detector_harness.py --pairs

# Measure real detector signals locally with open models (GPT-2 surprisal + a
# supervised classifier). Opt-in and dev-only: needs ~1.5GB of weights and a heavy
# dependency tree, so it is deliberately NOT part of `test` or CI. The shipped
# linter stays dependency-free.
#   python3 -m venv .detvenv && .detvenv/bin/pip install torch transformers
# HV_CAUSAL_MODEL=gpt2 makes this ~5x faster at some fidelity cost.
detector-local:
	.detvenv/bin/python eval/detector_local.py --out eval/detector_local_results.json

# Regression gate on the detector panel: fails if more rewrites get flagged, or if
# the perplexity movement shrinks. Writes nothing.
# NOTE: the corpus and the example pairs both grew in v0.6, so the committed
# detector_local_results.json predates eight ai_modern pairs and the
# syntax-signature example. Regenerate with `make detector-local` before trusting
# a comparison; the gated metrics are counts and a median, and both move when the
# denominator does.
detector-check:
	.detvenv/bin/python eval/detector_local.py --check

# The verification gate on one file. Exit 1 while a detector still flags it, 0
# when it clears, 2 when no API key is configured (which is NOT a pass).
#   make verify FILE=draft.md
verify:
	python3 skills/human-voice/scripts/verify_detector.py $(if $(BEFORE),--before $(BEFORE)) $(FILE)

# README charts, rebuilt from the committed eval output. visuals-check fails if stale.
visuals:
	python3 docs/assets/make_visuals.py

visuals-check:
	python3 docs/assets/make_visuals.py --check

# The model-agnostic front ends. Neither calls a model.
providers:
	python3 skills/human-voice/scripts/humanize.py --list-providers

# The skill compiled for a chat app with no tools (ChatGPT, Gemini, Claude projects).
prompt:
	python3 skills/human-voice/scripts/humanize.py --print-prompt chat > human-voice-system-prompt.md

# Dev-only tooling (needs `pip install ruff mypy pytest`). Never required at
# runtime — the linter and eval run on the standard library alone.
quality:
	ruff check skills/human-voice/scripts/human_voice_linter skills/human-voice/scripts/human_voice_llm install.py eval tests
	mypy
	pytest -q

all: test eval-check profile-check visuals-check lint dogfood
