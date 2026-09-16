"""human_voice_llm — run the human-voice skill on any LLM provider.

Standard library only, like the linter it drives. Three entry points:

    from human_voice_llm import humanize, chat, build_system_prompt

`humanize` runs the full lint -> rewrite -> check loop; `chat` is one call to any
provider; `build_system_prompt` compiles the skill for a model that cannot read
files. The command-line front end is scripts/humanize.py.
"""
from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from .invariants import compare as check_invariants  # noqa: E402
from .loop import humanize, lint_text  # noqa: E402
from .prompt import build_system_prompt, parse_response  # noqa: E402
from .providers import PROVIDERS, Completion, ProviderError, chat, resolve  # noqa: E402

__all__ = ["humanize", "lint_text", "chat", "resolve", "PROVIDERS", "Completion",
           "ProviderError", "build_system_prompt", "parse_response", "check_invariants"]
