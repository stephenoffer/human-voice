"""cli — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .analyze import *  # noqa: F401,F403
from .api import *  # noqa: F401,F403
from .autofix import *  # noqa: F401,F403
from .checks import *  # noqa: F401,F403
from .config import *  # noqa: F401,F403
from .defaults import *  # noqa: F401,F403
from .infer import infer_register
from .patterns import *  # noqa: F401,F403
from .report import *  # noqa: F401,F403
from .schema import *  # noqa: F401,F403
from .score import *  # noqa: F401,F403
from .textutil import *  # noqa: F401,F403
from .util import *  # noqa: F401,F403


def filter_hits(hits, enable, disable):
    if enable:
        hits = [h for h in hits if h.category in enable]
    if disable:
        hits = [h for h in hits if h.category not in disable]
    return hits


def warn_unknown_categories(enable, disable):
    """Announce --enable/--disable names that match no category.

    A typo in --enable used to filter every hit away and report a clean document,
    which is the most dangerous failure this tool can have: a false all-clear.
    """
    for flag, names in (("--enable", enable), ("--disable", disable)):
        for name in names or ():
            if name and name not in KNOWN_CATEGORIES:
                warn("%s: unknown category %r (matches nothing). Known categories: %s"
                     % (flag, name, ", ".join(sorted(KNOWN_CATEGORIES))))


def analyze_target(target, args, patterns, weights, bands):
    text = read_input(target)
    register = args.register
    inferred = None
    if register == "auto":
        register, confidence, reasons = infer_register(text)
        inferred = {"register": register, "confidence": round(confidence, 2),
                    "reasons": reasons}
        if not args.quiet and not args.json:
            warn("register: inferred %s (confidence %.2f) from %s"
                 % (register, confidence, "; ".join(reasons) or "no cue"))
    hits, report, words = analyze(text, register, args.dialect, patterns)
    hits = filter_hits(hits, set(args.enable or []), set(args.disable or []))
    floor = score(hits, words, weights)
    payload = {
        "schema_version": 1,
        "input": target,
        "register": register,
        "dialect": args.dialect,
        "words": words,
        "score": floor,
        "verdict": verdict_band(floor, bands),
        "metrics": report,
        "hits": [dict(h.as_dict(), severity=severity_of(h.category, weights)) for h in hits],
    }
    # Additive and OPTIONAL: present only when --register auto actually inferred, so
    # a consumer that never asks for inference sees a byte-identical payload.
    if inferred is not None:
        payload["inferred_register"] = inferred
    return payload, hits, report, words, floor


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


def resolve_config(args):
    """Load patterns, merge .humanvoicerc, resolve register/dialect, validate.

    Mutates args (enable/disable/register/dialect) and returns
    (patterns, weights, bands).
    """
    if args.lang and args.lang.lower() not in ("en", "english"):
        warn("only English ('en') is supported today; patterns are English-only. "
             "Proceeding, but results for %r are not meaningful." % args.lang)

    # normalize category filters
    args.enable = [c.strip() for c in args.enable.split(",")] if args.enable else None
    args.disable = [c.strip() for c in args.disable.split(",")] if args.disable else None

    patterns = load_patterns(args.patterns)
    # Project config (.humanvoicerc) discovered relative to the first real path.
    cfg = None
    if not args.no_config:
        first_path = next((i for i in args.input if i != "-"), None)
        cfg = find_project_config(first_path)
        if cfg:
            patterns = merge_config(patterns, cfg)
    # Resolve register/dialect: explicit flag > project config > built-in default.
    args.register = args.register or (cfg or {}).get("register") or "technical"
    if args.register == "auto":
        pass          # resolved per input in analyze_target, since it reads the text
    elif args.register not in REGISTERS:
        warn("unknown register %r from config; using technical" % args.register)
        args.register = "technical"
    args.dialect = args.dialect or (cfg or {}).get("dialect")
    if args.dialect not in (None, "american", "british"):
        args.dialect = None
    warn_unknown_categories(args.enable, args.disable)
    patterns = apply_threshold_overrides(patterns, args.threshold)
    # Validate the resolved config once and surface any problems on stderr.
    # Non-fatal: the linter still runs (degrading per-key to defaults), but a
    # typo or malformed value is now announced instead of silently swallowed.
    for issue in validate(patterns):
        warn("config: %s" % issue)

    return patterns, resolve_weights(patterns), resolve_bands(patterns)


def main(argv=None):
    args = build_parser().parse_args(argv)
    patterns, weights, bands = resolve_config(args)

    # --- autofix mode (single file) ---
    if args.fix or args.fix_dry_run:
        if len(args.input) != 1 or args.input[0] == "-":
            sys.stderr.write("error: --fix needs exactly one file path\n")
            return 2
        target = args.input[0]
        if os.path.isdir(target):
            sys.stderr.write("error: --fix target is a directory: %s\n" % target)
            return 2
        original = read_input(target)
        # read_input normalizes to LF. Writing that back would rewrite every line
        # ending in a CRLF file, which shows up as a whole-file diff for a
        # three-word fix, so restore whatever the file actually used.
        try:
            with open(target, "rb") as _fh:
                crlf = b"\r\n" in _fh.read(65536)
        except OSError:
            crlf = False
        # read_input truncates at MAX_CHARS. Writing that back would silently
        # delete the tail of a large file, so refuse rather than destroy it.
        try:
            on_disk_size = os.path.getsize(target)
        except OSError:
            on_disk_size = 0
        if args.fix and on_disk_size > MAX_CHARS:
            sys.stderr.write(
                "error: %s is %d bytes, over the %d-char read limit; --fix would "
                "truncate it. Split the file or use --fix-dry-run.\n"
                % (target, on_disk_size, MAX_CHARS))
            return 2
        # An `auto` register must be resolved before the autofixer runs: it gates
        # emoji and dash rewriting on the register, and the literal string "auto"
        # matches no gate, so creative prose lost its em-dashes and its emoji.
        fix_register = args.register
        if fix_register == "auto":
            fix_register, conf, why = infer_register(original)
            if not args.quiet:
                warn("register: inferred %s (confidence %.2f) from %s"
                     % (fix_register, conf, "; ".join(why) or "no cue"))
        fixed, swaps, emoji, dashes = autofix(original, patterns, fix_register)
        if args.fix_dry_run:
            sys.stdout.write(fixed)
            return 0
        if fixed != original:
            # Write through a temp file in the same directory and replace
            # atomically, so an interrupted run cannot leave a half-written draft.
            tmp = target + ".hv-tmp"
            try:
                with open(tmp, "w", encoding="utf-8", newline="") as fh:
                    fh.write(fixed.replace("\n", "\r\n") if crlf else fixed)
                os.replace(tmp, target)
            except OSError as exc:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                sys.stderr.write("error: could not write %s: %s\n" % (target, exc))
                return 2
        sys.stderr.write("autofix: %d swap(s), %d emoji, %d dash(es) in %s\n"
                         % (swaps, emoji, dashes, target))
        return 0

    # --- compare mode (input vs baseline) ---
    if args.baseline:
        if len(args.input) > 1:
            warn("--baseline compares a single file; ignoring %d extra input(s): %s"
                 % (len(args.input) - 1, ", ".join(args.input[1:])))
        base = analyze_target(args.baseline, args, patterns, weights, bands)[0]
        cur = analyze_target(args.input[0], args, patterns, weights, bands)[0]
        delta = round(cur["score"] - base["score"], 1)
        if args.json:
            print(json.dumps({"baseline": base, "current": cur,
                              "score_delta": delta}, indent=2))
        else:
            print("compare: %s [%s %.1f]  ->  %s [%s %.1f]   delta %+.1f" % (
                base["input"], base["verdict"], base["score"],
                cur["input"], cur["verdict"], cur["score"], delta))
            # Function-word movement across the rewrite. The per-document value is
            # a weak signal; the DIRECTION across a pair is the useful part, and
            # this is the only place in the tool where it is visible. Toward the
            # human median is the direction a real edit moves it.
            b_sty = (base.get("metrics") or {}).get("stylometric_delta")
            c_sty = (cur.get("metrics") or {}).get("stylometric_delta")
            med = (cur.get("metrics") or {}).get("human_delta_median")
            if b_sty is not None and c_sty is not None:
                toward = ("toward" if abs(c_sty - (med or 0)) < abs(b_sty - (med or 0))
                          else "away from")
                print("         function-word delta %.3f -> %.3f  (%s the human "
                      "median %s; diagnostic, unscored)" % (b_sty, c_sty, toward, med))
        return 0

    targets = collect_targets(args.input, args.recursive)
    results = []
    worst = 0.0
    for target in targets:
        payload, hits, report, words, floor = analyze_target(
            target, args, patterns, weights, bands)
        results.append(payload)
        worst = max(worst, floor)
        if not (args.json or args.sarif):
            if args.quiet:
                print("%-40s %6.1f  [%s]" % (target, floor, payload["verdict"]))
            else:
                print(render_text(target, payload["register"], args.dialect, hits, report,
                                  words, floor, payload["verdict"],
                                  max_examples=(10**6 if args.explain else args.max_examples),
                                  thresholds=patterns.get("thresholds")))
                if len(targets) > 1:
                    print("")

    if args.sarif:
        print(json.dumps(render_sarif(results), indent=2))
    elif args.json:
        print(json.dumps(results[0] if len(results) == 1 else results, indent=2))

    if args.fail_over is not None and worst > args.fail_over:
        return 1
    return 0


__all__ = [
    'filter_hits',
    'warn_unknown_categories',
    'analyze_target',
    'main',
    'build_parser',
    'resolve_config',
]
