"""settings — resolving flags, project config, and the pattern file into one run's settings."""
from __future__ import annotations

from typing import NamedTuple

from ..config.defaults import KNOWN_CATEGORIES, REGISTERS
from ..config.inference import infer_register
from ..config.patterns import load_patterns
from ..config.project import apply_threshold_overrides, find_project_config, merge_config
from ..config.schema import validate
from ..core.log import warn
from ..scoring.bands import resolve_bands
from ..scoring.weights import resolve_weights


class Settings(NamedTuple):
    patterns: dict
    weights: dict
    bands: tuple


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


def resolve_register(text, register, announce):
    """(register, inferred) for one input; `inferred` is None unless `auto` ran."""
    if register != "auto":
        return register, None
    register, confidence, reasons = infer_register(text)
    if announce:
        warn("register: inferred %s (confidence %.2f) from %s"
             % (register, confidence, "; ".join(reasons) or "no cue"))
    return register, {"register": register, "confidence": round(confidence, 2),
                      "reasons": reasons}


def resolve_config(args):
    """Load patterns, merge .humanvoicerc, resolve register/dialect, validate.

    Mutates args (enable/disable/register/dialect) and returns Settings
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
        pass          # resolved per input, since it reads the text
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

    return Settings(patterns, resolve_weights(patterns), resolve_bands(patterns))


__all__ = [
    "Settings",
    "filter_hits",
    "warn_unknown_categories",
    "resolve_register",
    "resolve_config",
]
