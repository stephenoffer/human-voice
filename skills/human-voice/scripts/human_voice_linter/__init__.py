"""human_voice_linter — AI-prose linter (package form of detect_ai_prose.py)."""
from __future__ import annotations

import importlib

# Submodules in dependency order (low layers first).
_MODS = ["util", "defaults", "hit", "patterns", "textutil", "directives", "checks",
         "score", "analyze", "report", "autofix", "config", "schema", "api", "cli"]

# Aggregate the public surface BEFORE the star-imports below clobber package
# attributes. Several names are both a submodule name and a function name
# (score, analyze, autofix); once `from .score import *` runs, the attribute
# `human_voice_linter.score` becomes the function, which would shadow the
# submodule for any later `from . import score`. importlib.import_module reads
# the real module object from sys.modules, sidestepping that shadowing.
__all__ = []
for _name in _MODS:
    _mod = importlib.import_module("." + _name, __name__)
    __all__ += [x for x in getattr(_mod, "__all__", []) if x not in __all__]
del _name, _mod

from .util import *       # noqa: E402,F401,F403
from .defaults import *   # noqa: E402,F401,F403
from .hit import *        # noqa: E402,F401,F403
from .patterns import *   # noqa: E402,F401,F403
from .textutil import *   # noqa: E402,F401,F403
from .directives import *  # noqa: E402,F401,F403
from .checks import *     # noqa: E402,F401,F403
from .score import *      # noqa: E402,F401,F403
from .analyze import *    # noqa: E402,F401,F403
from .report import *     # noqa: E402,F401,F403
from .autofix import *    # noqa: E402,F401,F403
from .config import *     # noqa: E402,F401,F403
from .schema import *     # noqa: E402,F401,F403
from .api import *        # noqa: E402,F401,F403
from .cli import *        # noqa: E402,F401,F403
