"""registers — what a genre profile changes: muted categories and wider bars."""
from __future__ import annotations

from .defaults import DEFAULTS, threshold_default
from .patterns import safe_float, safe_int_list


def muted_categories(register: str, patterns: dict) -> set:
    """Categories a register switches off, via register_mutes -> muted_checks."""
    mutes = patterns.get("register_mutes", {})
    mutes = mutes.get(register, []) if isinstance(mutes, dict) else []
    muted_map = patterns.get("muted_checks", {})
    if not isinstance(muted_map, dict):
        muted_map = {}
    cats = set()
    for token in mutes if isinstance(mutes, list) else []:
        for c in muted_map.get(token, []) if isinstance(muted_map.get(token), list) else []:
            cats.add(c)
    return cats


class Thresholds:
    """Resolved threshold table for one register.

    Callable: `thresholds("cleft_per_1k")` returns the pattern file's value when
    it is present and numeric, else the canonical default, scaled by the
    register's multiplier.

    Per-register multipliers (DEFAULTS["register_thresholds"]): a register that
    legitimately runs hot on one construction gets a wider bar rather than the
    check switched off, so the signal above that bar is still counted.
    """

    def __init__(self, patterns: dict, register: str) -> None:
        th = patterns.get("thresholds", {})
        self._table = th if isinstance(th, dict) else {}
        rt = patterns.get("register_thresholds")
        if not isinstance(rt, dict):
            rt = DEFAULTS.get("register_thresholds", {})
        mult = rt.get(register)
        self._multipliers: dict = mult if isinstance(mult, dict) else {}

    def __call__(self, key: str) -> float:
        base = safe_float(self._table, key, threshold_default(key))
        mult = self._multipliers.get(key)
        if isinstance(mult, (int, float)) and not isinstance(mult, bool) and mult > 0:
            return base * float(mult)
        return base

    def integer(self, key: str) -> int:
        return int(self(key))

    def int_list(self, key: str) -> list:
        """A list-valued knob (ngram_sizes). Never scaled by a multiplier."""
        return safe_int_list(self._table, key, threshold_default(key))


__all__ = ["muted_categories", "Thresholds"]
