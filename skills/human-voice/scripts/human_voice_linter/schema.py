"""schema — hand-written validator for the patterns / .humanvoicerc config.

Stdlib only (no jsonschema). `validate(patterns)` returns a list of human-readable
warning strings; it never raises and never mutates. The linter degrades
gracefully on bad config (defaults are substituted per key), but degradation used
to be silent — the CLI now runs this once and prints each issue to stderr so a
typo or a malformed value gets real feedback instead of being swallowed.

Severity model: everything here is a *warning* (recoverable — the linter still
runs). The one hard error, "the file is not a JSON object", is handled earlier in
load_patterns, which exits 2.
"""
from __future__ import annotations

import re

from .defaults import DEFAULTS, KNOWN_CATEGORIES

# Pattern keys whose value is coerced by as_phrase_list (dict | list | str).
_PHRASE_KEYS = (
    "filler", "soft_filler", "jargon", "redundancy", "overused_transitions",
    "meta_commentary", "chatbot_scaffold", "sycophancy", "hedging", "puffery",
    "vague_attribution", "cowardly_passive", "self_identifying",
    "vague_declarative", "narrator_distance", "aidiolect", "cliche_metaphor",
    "internet_tells", "significance_inflation", "protected_terms",
    "context_exceptions",
)
# Pattern keys whose value is a list of regex strings.
_REGEX_LIST_KEYS = (
    "antithesis_patterns", "false_agency_patterns", "negative_listing_patterns",
    "dramatic_fragmentation_patterns",
)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(patterns: dict) -> list:
    """Return a list of warning strings for a (already-merged) patterns dict."""
    issues: list = []
    if not isinstance(patterns, dict):
        return ["patterns config is not a JSON object; ignoring it"]

    # --- thresholds: dict of known knobs -> number (ngram_sizes -> list[int]) ---
    th = patterns.get("thresholds")
    if th is not None:
        if not isinstance(th, dict):
            issues.append("thresholds: expected an object, got %s" % type(th).__name__)
        else:
            for k, v in th.items():
                if k not in DEFAULTS["thresholds"]:
                    issues.append("thresholds: unknown key %r (ignored)" % k)
                elif k == "ngram_sizes":
                    if not (isinstance(v, list) and all(isinstance(n, int) for n in v)):
                        issues.append("thresholds.ngram_sizes: expected a list of ints")
                elif not _is_number(v):
                    issues.append("thresholds.%s: expected a number, got %r" % (k, v))

    # --- category_weights: known category -> number ---
    cw = patterns.get("category_weights")
    if cw is not None:
        if not isinstance(cw, dict):
            issues.append("category_weights: expected an object")
        else:
            for k, v in cw.items():
                if k not in KNOWN_CATEGORIES:
                    issues.append("category_weights: unknown category %r (ignored)" % k)
                elif not _is_number(v):
                    issues.append("category_weights.%s: expected a number, got %r" % (k, v))

    # --- score_bands: label -> number ---
    sb = patterns.get("score_bands")
    if sb is not None:
        if not isinstance(sb, dict):
            issues.append("score_bands: expected an object")
        else:
            for k, v in sb.items():
                if not _is_number(v):
                    issues.append("score_bands.%s: expected a number, got %r" % (k, v))

    # --- muted_checks: token -> list of known categories ---
    mc = patterns.get("muted_checks")
    if mc is not None:
        if not isinstance(mc, dict):
            issues.append("muted_checks: expected an object")
        else:
            for token, cats in mc.items():
                if not isinstance(cats, list):
                    issues.append("muted_checks.%s: expected a list" % token)
                    continue
                for c in cats:
                    if c not in KNOWN_CATEGORIES:
                        issues.append("muted_checks.%s references unknown category %r"
                                      % (token, c))

    # --- register_mutes: register -> list of tokens that exist in muted_checks ---
    rm = patterns.get("register_mutes")
    if rm is not None:
        if not isinstance(rm, dict):
            issues.append("register_mutes: expected an object")
        else:
            known_tokens = set(mc) if isinstance(mc, dict) else set()
            for reg, tokens in rm.items():
                if not isinstance(tokens, list):
                    issues.append("register_mutes.%s: expected a list" % reg)
                    continue
                for t in tokens:
                    if known_tokens and t not in known_tokens:
                        issues.append("register_mutes.%s references token %r not in "
                                      "muted_checks" % (reg, t))

    # --- dialect: name -> {wrong: right} ---
    dia = patterns.get("dialect")
    if dia is not None and not isinstance(dia, dict):
        issues.append("dialect: expected an object")
    elif isinstance(dia, dict):
        for name, mapping in dia.items():
            if not isinstance(mapping, dict):
                issues.append("dialect.%s: expected an object of word->word" % name)

    # --- regex lists: every entry must compile ---
    for key in _REGEX_LIST_KEYS:
        val = patterns.get(key)
        if val is None:
            continue
        if not isinstance(val, list):
            issues.append("%s: expected a list of regex strings" % key)
            continue
        for pat in val:
            if not isinstance(pat, str):
                issues.append("%s: non-string entry %r" % (key, pat))
                continue
            try:
                re.compile(pat)
            except re.error as exc:
                issues.append("%s: invalid regex %r (%s)" % (key, pat, exc))

    # --- phrase maps: must be dict | list | str ---
    for key in _PHRASE_KEYS:
        val = patterns.get(key)
        if val is not None and not isinstance(val, (dict, list, str)):
            issues.append("%s: expected an object, list, or string" % key)

    return issues


__all__ = ["validate"]
