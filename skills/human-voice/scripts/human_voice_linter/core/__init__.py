"""core — the linter's data model and the contract every check implements.

    hit       Hit, the finding every check emits
    document  Document, one input with every view of it a check reads
    context   LintContext, the state of one run (thresholds, hits, metrics)
    check     Check and its reusable shapes (Diagnostic, DensityCheck, RateCheck)
    log       warn(), the channel for recoverable problems

Only the leaf modules are imported here. `document` and `context` depend on
`text` and `config`, which themselves import `core.log`, so importing them from
this package's `__init__` would create a cycle. Import them by module path.
"""
from __future__ import annotations

from .hit import Hit
from .log import warn

__all__ = ["Hit", "warn"]
