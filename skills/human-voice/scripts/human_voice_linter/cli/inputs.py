"""inputs — reading files and stdin, and expanding directories into targets."""
from __future__ import annotations

import os
import sys

from ..core.log import warn
from ..text.markdown import normalize_text

MAX_CHARS = 5_000_000

TEXT_SUFFIXES = (".md", ".markdown", ".txt", ".mdx", ".rst")

# Directories a prose walk should never descend into: they hold generated output
# and dependencies, not writing, and linting them buries the real findings.
SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "dist", "build",
    "site-packages", ".next", ".cache",
})


def read_input(target):
    """Read a path (or '-' for stdin) as normalized text. Exits 2 on failure."""
    if target == "-":
        try:
            raw = sys.stdin.buffer.read()
        except (AttributeError, OSError):
            raw = sys.stdin.read().encode("utf-8", "replace")
        text = raw.decode("utf-8", "replace")
    else:
        if os.path.isdir(target):
            sys.stderr.write("error: input is a directory, not a file: %s\n" % target)
            sys.exit(2)
        try:
            with open(target, "rb") as fh:
                raw = fh.read()
        except (FileNotFoundError, IsADirectoryError, PermissionError, OSError) as exc:
            sys.stderr.write("error: could not read input %s: %s\n" % (target, exc))
            sys.exit(2)
        text = raw.decode("utf-8", "replace")
    if len(text) > MAX_CHARS:
        warn("input truncated to %d chars (was %d)" % (MAX_CHARS, len(text)))
        text = text[:MAX_CHARS]
    return normalize_text(text)


def collect_targets(inputs, recursive):
    """Expand inputs into a flat list of file paths (or '-'), walking dirs.

    Deduplicates while preserving order, so `lint docs/ docs/intro.md` does not
    analyze and print intro.md twice, and prunes vendor/build directories on a
    recursive walk.
    """
    targets = []
    seen = set()

    def add(path):
        key = path if path == "-" else os.path.normpath(path)
        if key in seen:
            return
        seen.add(key)
        targets.append(path)

    for inp in inputs:
        if inp == "-":
            add(inp)
        elif os.path.isdir(inp):
            for root, dirs, files in os.walk(inp):
                dirs[:] = sorted(d for d in dirs
                                 if d not in SKIP_DIRS and not d.startswith("."))
                for fn in sorted(files):
                    if fn.endswith(TEXT_SUFFIXES):
                        add(os.path.join(root, fn))
                if not recursive:
                    break
        else:
            add(inp)
    return targets


__all__ = ["MAX_CHARS", "TEXT_SUFFIXES", "SKIP_DIRS", "read_input", "collect_targets"]
