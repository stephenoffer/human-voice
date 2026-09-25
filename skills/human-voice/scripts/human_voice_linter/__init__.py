"""human_voice_linter — the deterministic floor of the human-voice skill.

Layout, low layers first:

    core/        Hit, Document, LintContext, and the Check base classes
    text/        markdown normalization, derived prose, tokens, line maps
    config/      defaults, pattern file, .humanvoicerc, registers, directives
    checks/      every tell, one class each, and DEFAULT_CHECKS (the run order)
    scoring/     the floor score, category weights, verdict bands
    reporting/   JSON payload, text report, SARIF
    fixes/       the deterministic autofixers
    cli/         the detect_ai_prose.py command line
    engine.py    Linter / analyze(): run the checks over one document
    api.py       lint(): analyze + score + payload in one call
    detector.py  optional external-detector probe for the verification gate

The names below are the supported public surface; `detect_ai_prose.py` re-exports
them. Anything else is reached by module path.
"""
from __future__ import annotations

from .api import lint
from .checks import DEFAULT_CHECKS
from .cli import build_parser, collect_targets, main, read_input
from .cli.inputs import MAX_CHARS, SKIP_DIRS, TEXT_SUFFIXES
from .config import (
    CATEGORY_WEIGHTS,
    CONFIG_NAME,
    CUES,
    DEFAULT_BANDS,
    DEFAULT_THRESHOLDS,
    DEFAULTS,
    KNOWN_CATEGORIES,
    PATTERNS_FILE,
    REGISTERS,
    Thresholds,
    apply_threshold_overrides,
    as_phrase_list,
    directive_suppresses,
    find_project_config,
    infer_register,
    load_patterns,
    merge_config,
    muted_categories,
    parse_directives,
    threshold_default,
    validate,
)
from .core.check import Check, DensityCheck, Diagnostic, RateCheck
from .core.context import LintContext
from .core.document import Document
from .core.hit import Hit
from .core.log import warn
from .engine import Linter, analyze
from .fixes import CODE_MASK_CHAR, SAFE_FIX_KEYS, autofix, is_substitution
from .reporting import build_payload, line_hotspots, render_sarif, render_text
from .scoring import resolve_bands, resolve_scoring, resolve_weights, score, severity_of, verdict_band
from .text import (
    STOPWORDS,
    WORD_RE,
    LineMap,
    MappedLineMap,
    blank_frontmatter,
    normalize_text,
    prose_for_adjacency,
    prose_for_metrics,
    sentences,
    strip_code,
    strip_inline_markup,
)

__all__ = [
    # entry points
    "lint", "analyze", "Linter", "main", "build_parser",
    # model
    "Hit", "Document", "LintContext", "Check", "Diagnostic", "DensityCheck", "RateCheck",
    "DEFAULT_CHECKS",
    # config
    "DEFAULTS", "DEFAULT_THRESHOLDS", "CATEGORY_WEIGHTS", "KNOWN_CATEGORIES", "REGISTERS",
    "DEFAULT_BANDS", "threshold_default", "PATTERNS_FILE", "load_patterns", "as_phrase_list",
    "CONFIG_NAME", "find_project_config", "merge_config", "apply_threshold_overrides",
    "Thresholds", "muted_categories", "parse_directives", "directive_suppresses",
    "CUES", "infer_register", "validate",
    # scoring and output
    "score", "resolve_scoring", "resolve_weights", "severity_of", "resolve_bands",
    "verdict_band", "build_payload", "render_text", "render_sarif", "line_hotspots",
    # fixes
    "autofix", "is_substitution", "SAFE_FIX_KEYS", "CODE_MASK_CHAR",
    # text
    "normalize_text", "blank_frontmatter", "strip_code", "strip_inline_markup",
    "prose_for_metrics", "prose_for_adjacency", "sentences", "WORD_RE", "STOPWORDS",
    "LineMap", "MappedLineMap",
    # inputs
    "read_input", "collect_targets", "MAX_CHARS", "TEXT_SUFFIXES", "SKIP_DIRS",
    "warn",
]
