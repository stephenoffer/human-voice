"""config — everything that decides how strict a lint is.

    defaults    canonical thresholds, category weights, verdict bands
    patterns    loading the pattern file; defensive value readers
    project     .humanvoicerc discovery and command-line overrides
    registers   register mutes and the resolved Thresholds table
    inference   guessing the register from the text (--register auto)
    directives  inline <!-- human-voice: ignore --> comments
    schema      validation warnings for a merged config
"""
from __future__ import annotations

from .defaults import (
    CATEGORY_WEIGHTS,
    DEFAULT_BANDS,
    DEFAULT_THRESHOLDS,
    DEFAULTS,
    KNOWN_CATEGORIES,
    REGISTERS,
    threshold_default,
)
from .directives import DIRECTIVE_RE, directive_suppresses, parse_directives
from .inference import CUES, MIN_MARGIN, MIN_WINNING_SCORE, MIN_WORDS_FOR_INFERENCE, infer_register
from .patterns import PATTERNS_FILE, as_phrase_list, load_patterns, safe_float, safe_int_list
from .project import CONFIG_NAME, apply_threshold_overrides, find_project_config, merge_config
from .registers import Thresholds, muted_categories
from .schema import validate

__all__ = [
    "CATEGORY_WEIGHTS", "DEFAULT_BANDS", "DEFAULT_THRESHOLDS", "DEFAULTS",
    "KNOWN_CATEGORIES", "REGISTERS", "threshold_default",
    "DIRECTIVE_RE", "directive_suppresses", "parse_directives",
    "CUES", "MIN_MARGIN", "MIN_WINNING_SCORE", "MIN_WORDS_FOR_INFERENCE", "infer_register",
    "PATTERNS_FILE", "as_phrase_list", "load_patterns", "safe_float", "safe_int_list",
    "CONFIG_NAME", "apply_threshold_overrides", "find_project_config", "merge_config",
    "Thresholds", "muted_categories",
    "validate",
]
