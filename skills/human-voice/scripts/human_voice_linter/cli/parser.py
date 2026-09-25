"""parser — the command-line interface definition."""
from __future__ import annotations

import argparse

from ..config.defaults import REGISTERS
from ..config.patterns import PATTERNS_FILE


def build_parser():
    """Construct the CLI argument parser (separated out for testability)."""
    ap = argparse.ArgumentParser(description="Detect surface tells of AI-written prose.")
    ap.add_argument("input", nargs="+", help="file path(s) or directory, or - for stdin")
    ap.add_argument("--register", choices=list(REGISTERS) + ["auto"], default=None,
                    help="genre profile (default: technical, or .humanvoicerc)")
    ap.add_argument("--dialect", choices=["american", "british"], default=None,
                    help="enable spelling-consistency check for this dialect")
    ap.add_argument("--no-config", action="store_true", dest="no_config",
                    help="ignore any .humanvoicerc project config")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--sarif", action="store_true", help="SARIF 2.1.0 output for code scanning")
    ap.add_argument("--patterns", default=PATTERNS_FILE, help="patterns JSON path")
    ap.add_argument("--fail-over", type=float, default=None, metavar="SCORE",
                    dest="fail_over",
                    help="exit 1 when any floor score exceeds SCORE (for CI gating)")
    ap.add_argument("--baseline", metavar="FILE",
                    help="compare the input against FILE and print the score delta")
    ap.add_argument("--enable", help="comma-separated categories to keep (drop the rest)")
    ap.add_argument("--disable", help="comma-separated categories to suppress")
    ap.add_argument("--threshold", action="append", metavar="KEY=VALUE",
                    help="override a threshold (repeatable), e.g. --threshold burstiness_cov_floor=0.5")
    ap.add_argument("--max-examples", type=int, default=6, dest="max_examples",
                    help="examples shown per category in text output (default 6)")
    ap.add_argument("--quiet", action="store_true", help="print only the score line per file")
    ap.add_argument("--explain", action="store_true",
                    help="list every hit with line and fix (no per-category cap)")
    ap.add_argument("--recursive", action="store_true",
                    help="recurse into subdirectories when a directory is given")
    ap.add_argument("--lang", default="en",
                    help="language of the input (only 'en' is supported today)")
    ap.add_argument("--fix", action="store_true",
                    help="apply unambiguous 1:1 word swaps in place (files only)")
    ap.add_argument("--fix-dry-run", action="store_true", dest="fix_dry_run",
                    help="print the autofixed text to stdout without writing")
    return ap


__all__ = ["build_parser"]
