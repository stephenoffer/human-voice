"""Unit tests for eval/lib.py metric math (dev-only; needs pytest).

These verify the extracted metric functions against hand-computed inputs, so the
math is checked independently of the corpus. The eval scripts themselves stay
runnable with the bare standard library; pytest is only a dev-time safety net.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib  # noqa: E402


def _recs(pairs):
    """Build minimal records from (label, score) pairs."""
    return [{"label": lbl, "score": s, "register": "technical"} for lbl, s in pairs]


def test_metrics_known_values():
    # tp=3, fp=1, tn=4, fn=2
    m = lib.metrics(3, 1, 4, 2)
    assert m["precision"] == pytest.approx(0.75)
    assert m["recall"] == pytest.approx(0.6)
    assert m["f1"] == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6), abs=1e-4)
    assert m["accuracy"] == pytest.approx(7 / 10)
    assert m["human_subset_false_positive_rate"] == pytest.approx(1 / 5)
    assert m["confusion"] == {"tp": 3, "fp": 1, "tn": 4, "fn": 2}


def test_confusion_threshold():
    recs = _recs([("ai", 10), ("ai", 2), ("human", 1), ("human", 8)])
    assert lib.confusion(recs, 5) == (1, 1, 1, 1)  # ai>=5: one tp, one fn; human>=5: one fp


def test_auc_perfect_and_reversed_and_tie():
    assert lib.auc(_recs([("ai", 9), ("ai", 8), ("human", 1)])) == 1.0
    assert lib.auc(_recs([("ai", 1), ("human", 9)])) == 0.0
    assert lib.auc(_recs([("ai", 5), ("human", 5)])) == 0.5  # tie counts 0.5
    assert lib.auc(_recs([("ai", 5)])) is None  # one class -> undefined


def test_sweep_finds_separating_threshold():
    recs = _recs([("human", 0), ("human", 1), ("ai", 50), ("ai", 60)])
    best_th, best_m, _rows = lib.sweep(recs)
    assert best_m["f1"] == 1.0
    assert 1 < best_th <= 50


def test_bootstrap_is_deterministic_and_brackets_point():
    recs = _recs([("ai", 50), ("ai", 60), ("ai", 70),
                  ("human", 0), ("human", 1), ("human", 8)])
    a = lib.bootstrap_ci(recs, lib.auc)
    b = lib.bootstrap_ci(recs, lib.auc)
    assert a == b  # same seed -> identical bounds
    assert a["lo"] <= a["point"] <= a["hi"]
    assert a["seed"] == lib.BOOTSTRAP_SEED


def test_compare_results_pass_and_fail():
    golden = {"corpus_size": 10, "n_human": 5, "n_ai": 5, "best_threshold": 40.0,
              "roc_auc": 1.0,
              "default": {"f1": 0.9, "accuracy": 0.9,
                          "human_subset_false_positive_rate": 0.2,
                          "confusion": {"tp": 5, "fp": 1, "tn": 4, "fn": 0}},
              "best": {"f1": 1.0}}
    assert lib.compare_results(golden, golden) == []
    drifted = dict(golden, roc_auc=0.5)
    diffs = lib.compare_results(drifted, golden)
    assert any("roc_auc" in d for d in diffs)
    # exact-gated confusion change is caught
    live = {**golden, "default": {**golden["default"],
            "confusion": {"tp": 4, "fp": 1, "tn": 4, "fn": 1}}}
    assert any("confusion" in d for d in lib.compare_results(live, golden))


def test_metrics_by_register_marks_single_class():
    recs = (_recs([("ai", 50), ("human", 0)]) +
            [{"label": "ai", "score": 60, "register": "business"}])
    by = lib.metrics_by_register(recs, lib.DEFAULT_THRESHOLD)
    assert by["business"]["single_class"] is True
    assert by["technical"]["single_class"] is False
