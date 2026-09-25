"""commands — the three things the CLI does: fix a file, compare two, lint many.

Each is a Command: built from the parsed args and the resolved Settings, run()
returns the process exit code.
"""
from __future__ import annotations

import json
import os
import sys

from ..core.log import warn
from ..engine import analyze
from ..fixes import autofix
from ..reporting.payload import build_payload
from ..reporting.sarif import render_sarif
from ..reporting.text import render_text
from ..scoring.floor import score
from .inputs import MAX_CHARS, collect_targets, read_input
from .settings import filter_hits, resolve_register


def analyze_target(target, args, settings):
    """Read, analyze, filter, and score one input.

    Returns (payload, hits, report, words, floor).
    """
    text = read_input(target)
    register, inferred = resolve_register(text, args.register,
                                          announce=not args.quiet and not args.json)
    hits, report, words = analyze(text, register, args.dialect, settings.patterns)
    hits = filter_hits(hits, set(args.enable or []), set(args.disable or []))
    floor = score(hits, words, settings.weights)
    # `inferred_register` is additive and OPTIONAL: present only when --register
    # auto actually inferred, so a consumer that never asks for inference sees a
    # byte-identical payload.
    payload = build_payload(hits, report, words, floor, register=register,
                            dialect=args.dialect, weights=settings.weights,
                            bands=settings.bands, input_name=target,
                            inferred_register=inferred)
    return payload, hits, report, words, floor


class Command:
    def __init__(self, args, settings):
        self.args = args
        self.settings = settings

    def run(self) -> int:
        raise NotImplementedError


class FixCommand(Command):
    """--fix / --fix-dry-run on exactly one file."""

    def run(self):
        args = self.args
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
            with open(target, "rb") as fh:
                crlf = b"\r\n" in fh.read(65536)
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
        register, _ = resolve_register(original, args.register, announce=not args.quiet)
        fixed, swaps, emoji, dashes = autofix(original, self.settings.patterns, register)
        if args.fix_dry_run:
            sys.stdout.write(fixed)
            return 0
        if fixed != original and not self._write(target, fixed, crlf):
            return 2
        sys.stderr.write("autofix: %d swap(s), %d emoji, %d dash(es) in %s\n"
                         % (swaps, emoji, dashes, target))
        return 0

    @staticmethod
    def _write(target, text, crlf):
        """Write through a temp file in the same directory and replace atomically,
        so an interrupted run cannot leave a half-written draft."""
        tmp = target + ".hv-tmp"
        try:
            with open(tmp, "w", encoding="utf-8", newline="") as fh:
                fh.write(text.replace("\n", "\r\n") if crlf else text)
            os.replace(tmp, target)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            sys.stderr.write("error: could not write %s: %s\n" % (target, exc))
            return False
        return True


class CompareCommand(Command):
    """--baseline: the input's score against a baseline file's."""

    def run(self):
        args = self.args
        if len(args.input) > 1:
            warn("--baseline compares a single file; ignoring %d extra input(s): %s"
                 % (len(args.input) - 1, ", ".join(args.input[1:])))
        base = analyze_target(args.baseline, args, self.settings)[0]
        cur = analyze_target(args.input[0], args, self.settings)[0]
        delta = round(cur["score"] - base["score"], 1)
        if args.json:
            print(json.dumps({"baseline": base, "current": cur,
                              "score_delta": delta}, indent=2))
            return 0
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


class LintCommand(Command):
    """The default: lint every target and print text, JSON, or SARIF."""

    def run(self):
        args = self.args
        targets = collect_targets(args.input, args.recursive)
        results = []
        worst = 0.0
        for target in targets:
            payload, hits, report, words, floor = analyze_target(target, args, self.settings)
            results.append(payload)
            worst = max(worst, floor)
            if args.json or args.sarif:
                continue
            if args.quiet:
                print("%-40s %6.1f  [%s]" % (target, floor, payload["verdict"]))
                continue
            print(render_text(target, payload["register"], args.dialect, hits, report,
                              words, floor, payload["verdict"],
                              max_examples=(10**6 if args.explain else args.max_examples),
                              thresholds=self.settings.patterns.get("thresholds")))
            if len(targets) > 1:
                print("")

        if args.sarif:
            print(json.dumps(render_sarif(results), indent=2))
        elif args.json:
            print(json.dumps(results[0] if len(results) == 1 else results, indent=2))

        if args.fail_over is not None and worst > args.fail_over:
            return 1
        return 0


def command_for(args, settings) -> Command:
    """The command the parsed flags ask for."""
    if args.fix or args.fix_dry_run:
        return FixCommand(args, settings)
    if args.baseline:
        return CompareCommand(args, settings)
    return LintCommand(args, settings)


__all__ = [
    "analyze_target",
    "Command",
    "FixCommand",
    "CompareCommand",
    "LintCommand",
    "command_for",
]
