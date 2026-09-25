"""checks — every tell the linter measures, and the order they run in.

    lexical         phrase and regex lists from the pattern file; dialect drift
    punctuation     em-dashes, dash style, quotes, doubled words, mechanics
    markdown_shape  headings, bullets, bold, rules, emoji, assistant shape
    rhythm          sentence length and sentence openers
    diction         vocabulary range, n-gram repetition, passive/adverb/nominal rates
    syntax          clefts, participial tails, splices, copulas, noun chains
    rhetoric        triads, rhetorical questions, superlatives, names, costume
    paragraphs      paragraph and list-item length and openers, essay shape
    artifacts       chat-product residue and unfilled placeholders
    diagnostics     report-only metrics (specificity, contractions, stylometry)
    stylometry      the function-word profile behind the stylometric delta
    architecture/   restatement, section balance, depth drift

To add a check: subclass `core.check.Check` (or one of its shapes), give it a
`category`, add the category's weight to config/defaults.py, and add an instance
to DEFAULT_CHECKS below.
"""
from __future__ import annotations

from .architecture import ARCHITECTURE_CHECKS
from .artifacts import LlmArtifactCheck
from .diagnostics import ContractionRate, PunctuationProfile, Specificity, Stylometry
from .diction import (
    AdverbCheck,
    LexicalDiversityCheck,
    NgramRepetitionCheck,
    NominalizationCheck,
    PassiveVoiceCheck,
)
from .lexical import PATTERN_LIST_CHECKS, PHRASE_LIST_CHECKS, DialectCheck
from .markdown_shape import (
    AssistantShapeCheck,
    BoldBulletsCheck,
    FormattingCheck,
    HeadingCaseCheck,
    HeadingStructureCheck,
)
from .paragraphs import (
    BulletOpenersCheck,
    CircularConclusionCheck,
    FiveParagraphShapeCheck,
    ListUniformityCheck,
    ParagraphOpenersCheck,
    ParagraphUniformityCheck,
)
from .punctuation import (
    DashStyleCheck,
    DoubledWordCheck,
    EmDashCheck,
    MechanicsCheck,
    PunctuationSubstitutionCheck,
    QuoteStyleCheck,
)
from .rhetoric import (
    HypophoraCheck,
    NameSelectionCheck,
    OverCorrectionCheck,
    RhetoricalQuestionCheck,
    RuleOfThreeCheck,
    SuperlativeCreepCheck,
)
from .rhythm import (
    BurstinessCheck,
    ParallelStructureCheck,
    SentenceShapeCheck,
    SvoMonotonyCheck,
    UniformOpenersCheck,
    WhOpenersCheck,
)
from .syntax import (
    ClauseSpliceCheck,
    CleftCheck,
    ColonSummaryCheck,
    CopulaAvoidanceCheck,
    CopulaDensityCheck,
    NounChainCheck,
    ParticipialTailCheck,
)

# Run order is part of the output: hits are reported in the order checks emit
# them, and the phrase lists share a seen-span table, so the first list to claim a
# span keeps it. Change the order and the JSON changes.
DEFAULT_CHECKS: tuple = (
    *PHRASE_LIST_CHECKS,
    *PATTERN_LIST_CHECKS,
    EmDashCheck(),
    BoldBulletsCheck(),
    RuleOfThreeCheck(),
    UniformOpenersCheck(),
    WhOpenersCheck(),
    FormattingCheck(),
    BurstinessCheck(),
    LexicalDiversityCheck(),
    NgramRepetitionCheck(),
    HeadingCaseCheck(),
    HeadingStructureCheck(),
    # Precision checks: residue rather than style.
    LlmArtifactCheck(),
    QuoteStyleCheck(),
    # Density and structural checks. Conservative thresholds keep clean human
    # prose clean; several are muted by register (see register_mutes).
    ColonSummaryCheck(),
    PassiveVoiceCheck(),
    AdverbCheck(),
    NominalizationCheck(),
    RhetoricalQuestionCheck(),
    ParagraphUniformityCheck(),
    ListUniformityCheck(),
    CircularConclusionCheck(),
    ParallelStructureCheck(),
    FiveParagraphShapeCheck(),
    HypophoraCheck(),
    SuperlativeCreepCheck(),
    SvoMonotonyCheck(),
    NameSelectionCheck(),
    # Modern instruction-tuned signature: syntactic, not lexical. All count-gated.
    CleftCheck(),
    ParticipialTailCheck(),
    CopulaDensityCheck(),
    ClauseSpliceCheck(),
    CopulaAvoidanceCheck(),
    ParagraphOpenersCheck(),
    BulletOpenersCheck(),
    NounChainCheck(),
    OverCorrectionCheck(),
    PunctuationSubstitutionCheck(),
    # Detector-aligned shape: the markdown/assistant signature and the
    # sentence-length distribution.
    AssistantShapeCheck(),
    SentenceShapeCheck(),
    # Content architecture: restated points, section balance, depth drift.
    *ARCHITECTURE_CHECKS,
    # Adjacency checks read the placeholder-substituted prose.
    DashStyleCheck(),
    DoubledWordCheck(),
    MechanicsCheck(),
    # Reported, never scored.
    PunctuationProfile(),
    Specificity(),
    ContractionRate(),
    Stylometry(),
    # Only fires when a dialect was requested.
    DialectCheck(),
)


def emitted_categories(checks=DEFAULT_CHECKS) -> frozenset:
    """Every category the given checks can emit."""
    return frozenset(c.category for c in checks if c.category)


__all__ = ["DEFAULT_CHECKS", "emitted_categories"]
