"""Calibration anchor: the linter's category weights must track what readers
actually CITE as an AI tell.

The ~90k-post Reddit study (JCarterJohnson/vibecoded-design-tells, MIT) ranked
tells by how often audited posts name them. We digitize that ranking here and
assert a strong positive rank correlation with the shipped category weights, so
a future weight edit that drifts away from the evidence fails loudly. The exact
percentages are noisy; the ORDER is the signal, which is why this is a Spearman
(rank) correlation, not a fit to the numbers.

Stdlib + pytest only. See references/cited-vs-matched.md for the full rationale.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "..", "skills", "human-voice", "scripts"))
from human_voice_linter import CATEGORY_WEIGHTS  # noqa: E402

# Higher cited_rank = more frequently cited by readers as a tell. Mapped from the
# study's ranking onto the linter categories that represent each tell. Generic
# diction that the study found matches often but is cited ~0% (soft_filler,
# transitions) sits at the bottom on purpose.
CITED_RANK = {
    "em_dash": 8,               # the single most-cited tell (~7.1%)
    "burstiness": 7,            # flat, uniform sentence rhythm (~4.0%)
    "antithesis": 6,            # "not just X, it's Y" (~2.8%)
    "five_paragraph_shape": 5,  # the essay mold + "in conclusion" (~2.5%)
    "sycophancy": 5,            # "great question!", reflexive agreement
    "aidiolect": 4,             # high-overuse multi-word phrases
    "self_identifying": 4,      # "as an AI language model" boilerplate (~1.2%)
    "filler": 3,                # the diction cluster (delve/tapestry...) (~1.3%)
    "meta_commentary": 2,       # hollow scene-setting openers (~0.7%)
    "soft_filler": 1,           # generic words: matched often, cited ~0%
    "transitions": 1,           # however/thus/moreover: matched often, cited ~0%
}


def _ranks(values):
    """Fractional (average-tie) ranks, smallest value gets rank 1."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # average of the 1-based positions
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(xs, ys):
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(xs)
    mx = sum(rx) / n
    my = sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy)


def test_every_cited_category_exists():
    # Guard against a rename silently dropping a category from the anchor.
    missing = [c for c in CITED_RANK if c not in CATEGORY_WEIGHTS]
    assert not missing, "cited-anchor categories not in CATEGORY_WEIGHTS: %s" % missing


def test_weights_track_cited_ranking():
    cats = sorted(CITED_RANK)
    cited = [CITED_RANK[c] for c in cats]
    weights = [CATEGORY_WEIGHTS[c] for c in cats]
    rho = _spearman(cited, weights)
    assert rho >= 0.55, (
        "category weights have drifted from the cited ranking (Spearman rho=%.3f < 0.55). "
        "Re-justify against references/cited-vs-matched.md before changing weights." % rho)


def test_generic_diction_outweighed_by_structure():
    # The core recalibration: generic high-match/low-cited diction must weigh
    # less than the structural/artifact tells readers actually cite.
    generic = max(CATEGORY_WEIGHTS["soft_filler"], CATEGORY_WEIGHTS["transitions"])
    for structural in ("antithesis", "sycophancy", "burstiness", "em_dash",
                       "five_paragraph_shape", "aidiolect", "self_identifying"):
        assert CATEGORY_WEIGHTS[structural] > generic, (
            "%s (%.1f) should outweigh generic diction (%.1f)"
            % (structural, CATEGORY_WEIGHTS[structural], generic))
