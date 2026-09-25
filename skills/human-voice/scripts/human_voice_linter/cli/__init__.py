"""cli — the detect_ai_prose.py command line.

    main      entry point: parse, resolve settings, run a command
    parser    the argparse definition
    settings  flags + .humanvoicerc + pattern file -> Settings
    inputs    reading files and stdin; expanding directories
    commands  FixCommand, CompareCommand, LintCommand
"""
from __future__ import annotations

from .commands import CompareCommand, FixCommand, LintCommand, analyze_target, command_for
from .inputs import MAX_CHARS, SKIP_DIRS, TEXT_SUFFIXES, collect_targets, read_input
from .main import main
from .parser import build_parser
from .settings import Settings, filter_hits, resolve_config, warn_unknown_categories

__all__ = [
    "main",
    "build_parser",
    "Settings",
    "resolve_config",
    "filter_hits",
    "warn_unknown_categories",
    "analyze_target",
    "command_for",
    "FixCommand",
    "CompareCommand",
    "LintCommand",
    "MAX_CHARS",
    "SKIP_DIRS",
    "TEXT_SUFFIXES",
    "collect_targets",
    "read_input",
]
