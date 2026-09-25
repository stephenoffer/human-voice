"""log — the linter's one channel for recoverable problems."""
from __future__ import annotations

import sys


def warn(msg: str) -> None:
    """Report a recoverable problem on stderr. The lint keeps running."""
    sys.stderr.write("warning: %s\n" % msg)


__all__ = ["warn"]
