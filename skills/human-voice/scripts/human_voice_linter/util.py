"""util — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import sys

MAX_CHARS = 5_000_000

# Category weights feed the single "floor" score. See score.score: document-level
# findings contribute fixed points, instance findings a capped per-1000-word density.
# Structure and substance-adjacent tells weigh more than lone diction hits.
def warn(msg):
    sys.stderr.write("warning: %s\n" % msg)


__all__ = [
    'MAX_CHARS',
    'warn',
]
