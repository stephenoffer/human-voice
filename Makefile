.PHONY: test eval eval-check lint quality all

# Full robustness + correctness suite (also runs in CI on Python 3.8-3.13).
test:
	python3 tests/stress_test.py

# Evaluation harness: regenerate the golden metrics (run after intentional changes).
eval:
	python3 eval/run_eval.py
	python3 eval/ablation.py

# Regression gate: fail if metrics drift from the committed golden JSON. Writes
# nothing, so the working tree stays clean. This is what CI runs.
eval-check:
	python3 eval/run_eval.py --check
	python3 eval/ablation.py --check

# Lint the shipped example pair (after.md must score clean).
lint:
	python3 skills/human-voice/scripts/detect_ai_prose.py skills/human-voice/examples/after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 skills/human-voice/examples/after.md

# Dev-only tooling (needs `pip install ruff mypy pytest`). Never required at
# runtime — the linter and eval run on the standard library alone.
quality:
	ruff check skills/human-voice/scripts/human_voice_linter eval tests
	mypy
	pytest -q

all: test eval-check lint
