#!/usr/bin/env python3
"""Rewrite or generate prose with the human-voice skill on any LLM provider.

    export OPENAI_API_KEY=...        # or ANTHROPIC / GEMINI / MISTRAL / XAI / ... 
    python3 humanize.py draft.md
    python3 humanize.py draft.md -m anthropic/claude-sonnet-5 --in-place
    python3 humanize.py draft.md -m ollama/qwen3:32b --references none
    python3 humanize.py --list-providers
    python3 humanize.py --print-prompt chat     # the skill as a paste-in system prompt

Standard library only. See human_voice_llm/providers.py for every provider and
the environment variables each one reads.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from human_voice_llm.cli import main  # noqa: E402

if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os._exit(0)
