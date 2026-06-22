.PHONY: test eval lint all

# Full robustness + correctness suite (also runs in CI on Python 3.8-3.13).
test:
	python3 tests/stress_test.py

# Evaluation harness: corpus precision/recall/FPR and category ablation.
eval:
	python3 eval/run_eval.py
	python3 eval/ablation.py

# Lint the shipped example pair (after.md must score clean).
lint:
	python3 skills/human-voice/scripts/detect_ai_prose.py skills/human-voice/examples/after.md
	python3 skills/human-voice/scripts/detect_ai_prose.py --fail-over 5 skills/human-voice/examples/after.md

all: test eval lint
