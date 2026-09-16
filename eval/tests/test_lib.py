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


def test_detector_harness_offline_and_pairs():
    """The harness must run with no key, find the shipped pairs, and dig paths."""
    import detector_harness as dh

    pairs = dh.example_pairs()
    assert pairs, "no before/after example pairs found"
    for stem, before, after in pairs:
        assert before.endswith("-before.md") and after.endswith("-after.md")
        assert stem in dh.PAIR_REGISTER, "pair %r has no register mapping" % stem
    # Every registered detector declares a usable request shape.
    for var, spec in dh.DETECTORS.items():
        assert spec["url"].startswith("https://"), var
        assert isinstance(spec["headers"]("k"), dict)
        assert isinstance(spec["body"]("text"), dict)
        assert spec["path"]
    assert dh._dig_path({"a": [{"b": 0.5}]}, ("a", 0, "b")) == 0.5
    with pytest.raises(KeyError):
        dh._dig_path({"a": 1}, ("a", "b"))
    # No key in the environment => offline path, exit 0, no network.
    saved = {v: os.environ.pop(v) for v in dh.KEY_ENV_VARS if v in os.environ}
    try:
        assert dh.main([]) == 0
    finally:
        os.environ.update(saved)


def test_modern_eval_reports_auc_and_misses():
    labels = lib.load_labels()
    modern = [k for k, v in labels.items() if v["label"] == lib.MODERN_LABEL]
    assert len(modern) >= 10, "the realistic modern-AI class should not be tiny"
    recs = ([{"file": f, "label": lib.MODERN_LABEL, "register": "technical",
              "group": "ai_modern", "score": s, "verdict": "x", "words": 100}
             for f, s in (("m1", 20.0), ("m2", 1.0))]
            + [{"file": "h1", "label": "human", "register": "technical",
                "group": "human", "score": 0.0, "verdict": "clean", "words": 100}])
    out = lib.modern_eval(recs, 5.0)
    assert out["n"] == 2
    assert out["recall"] == 0.5
    assert out["missed"] == ["m2"]
    assert 0.0 <= out["auc_vs_human"] <= 1.0


def test_rewrite_eval_pairs_and_flags_regressions():
    """The paired before/after evaluation must pair by basename, count clean
    verdicts on both sides, and name any file that got worse."""
    def rec(label, name, score, verdict):
        return {"file": "%s/%s" % (label, name), "label": label, "register": "technical",
                "group": label, "score": score, "verdict": verdict, "words": 200}

    records = [
        rec(lib.MODERN_LABEL, "a.md", 20.0, "strong-tell"),
        rec(lib.MODERN_LABEL, "b.md", 8.0, "watch"),
        rec(lib.MODERN_LABEL, "c.md", 1.0, "clean"),
        rec(lib.REWRITTEN_LABEL, "a.md", 0.0, "clean"),
        rec(lib.REWRITTEN_LABEL, "b.md", 2.0, "clean"),
        rec(lib.REWRITTEN_LABEL, "c.md", 4.0, "clean"),   # got worse, still clean
    ]
    out = lib.rewrite_eval(records, 5.0)
    assert out["n"] == 3
    assert out["mean_before"] > out["mean_after"]
    assert out["clean_before"] == 1 and out["clean_after"] == 3
    assert out["flagged_before"] == 2 and out["flagged_after"] == 0
    assert out["improved"] == 2
    assert out["regressed"] == ["c.md"], out["regressed"]
    assert out["unpaired"] == []


def test_rewrite_eval_reports_unpaired_instead_of_averaging():
    def rec(label, name, score):
        return {"file": "%s/%s" % (label, name), "label": label, "register": "technical",
                "group": label, "score": score, "verdict": "clean", "words": 200}
    out = lib.rewrite_eval([rec(lib.MODERN_LABEL, "a.md", 9.0),
                            rec(lib.MODERN_LABEL, "orphan.md", 9.0),
                            rec(lib.REWRITTEN_LABEL, "a.md", 1.0)], 5.0)
    assert out["n"] == 1
    assert out["unpaired"] == ["orphan.md"]


def test_every_modern_file_has_a_rewrite():
    """The paired corpus must stay paired, or the headline number is meaningless."""
    labels = lib.load_labels()
    before = {k.split("/")[-1] for k, v in labels.items()
              if v["label"] == lib.MODERN_LABEL}
    after = {k.split("/")[-1] for k, v in labels.items()
             if v["label"] == lib.REWRITTEN_LABEL}
    assert before, "no ai_modern files labeled"
    assert before == after, "unpaired: %s" % sorted(before ^ after)


def test_rewrites_change_nothing_numeric():
    """A rewrite may sharpen wording and must not invent or alter a number.

    Guards the anti-hallucination protocol on the shipped rewrites: every numeric
    token in an after-file must appear in its before-file.
    """
    import re
    labels = lib.load_labels()
    pairs = sorted(k.split("/")[-1] for k, v in labels.items()
                   if v["label"] == lib.REWRITTEN_LABEL)
    # A number ends in a digit or a percent sign. The old pattern `\d[\d,.]*%?`
    # swallowed the sentence punctuation after it, so "…187." read as the number
    # "187." and was reported as invented because the source said "…187 days".
    num = re.compile(r"\d+(?:[.,]\d+)*%?")
    for name in pairs:
        with open(os.path.join(lib.CORPUS, "ai_modern", name), encoding="utf-8") as fh:
            before = fh.read()
        with open(os.path.join(lib.CORPUS, "ai_modern_rewritten", name),
                  encoding="utf-8") as fh:
            after = fh.read()
        b_nums = set(num.findall(before))
        invented = sorted(n for n in num.findall(after) if n not in b_nums)
        assert not invented, "%s invented numbers: %s" % (name, invented)


def test_human_baseline_scores_only_own_prose():
    """The sweep must score a module's own docstrings, not imports or constants.

    Counting module-typed attributes made the result depend on import order: pytest
    imports `email.message` and friends, and `email` then scored 34.2 in CI against
    17.7 in a plain run, which failed the gate on every push.
    """
    import types

    import human_baseline as hb

    fake = types.ModuleType("fake_mod", "Fake module.")
    fake.helper = types.ModuleType("fake_mod.helper", "x " * 300)
    fake.CONSTANT = 42  # int instance: its __doc__ is int's docstring
    fake.func = lambda: None
    fake.func.__doc__ = "own prose " * 30
    fake.alias = fake.func
    sys.modules["fake_mod"] = fake
    try:
        text = hb.module_prose("fake_mod")
    finally:
        del sys.modules["fake_mod"]
    assert text.count("own prose own prose") >= 1
    assert text.count("own prose " * 30) <= 1, "an alias must not double-count prose"
    assert "x x x" not in text
    assert (int.__doc__ or "")[:40] not in text


def test_human_baseline_sweep_runs_and_gates():
    """The independent negative set must run offline and stay inside its ceilings.

    stdlib docstrings are human-written by hundreds of authors who never saw this
    repository, which makes them the only negative set here the corpus author did
    not also write. The gate is loose on purpose: reference documentation is a
    genre of its own, so a breach means "read the new findings", not "the linter
    is broken".
    """
    import human_baseline as hb

    report = hb.sweep()
    assert report["modules"] >= 10, "too few stdlib modules produced prose to score"
    assert report["rows"], "no rows in the sweep"
    problems = hb.gate(report)
    assert not problems, "human-prose false positives regressed: %s" % problems
    # Every row must carry the fields the report and the gate read.
    for row in report["rows"]:
        assert set(row) == {"module", "score", "words", "verdict"}
        assert row["words"] >= hb.MIN_WORDS


def test_human_baseline_render_is_stable():
    """The text report must not crash on a minimal report dict."""
    import human_baseline as hb

    tiny = {"python": "3.12", "modules": 1, "median_score": 0.0, "mean_score": 0.0,
            "worst_score": 0.0, "flagged_at_5": 0, "top_category": None,
            "top_category_share": 0.0, "category_counts": {},
            "rows": [{"module": "x", "score": 0.0, "words": 200, "verdict": "clean"}]}
    text = hb.render(tiny)
    assert "median 0.0" in text and "x" in text


def test_detector_local_check_gates_regressions():
    """The detector panel needs the same regression gate as the other evals: more
    rewrites flagged, or a smaller perplexity movement, must fail loudly."""
    import json as _json
    import tempfile

    import detector_local as dl

    golden = {"modern_flagged_after": 0, "after_flagged_count": 0,
              "modern_ppl_ratio_median": 2.0}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        _json.dump(golden, fh)
        path = fh.name
    try:
        assert dl.check(dict(golden), path) == []
        assert dl.check(dict(golden, modern_flagged_after=1), path), \
            "an extra flagged rewrite must be reported"
        assert dl.check(dict(golden, modern_ppl_ratio_median=1.5), path), \
            "a large drop in the perplexity multiplier must be reported"
        assert dl.check(dict(golden, modern_ppl_ratio_median=1.95), path) == [], \
            "a change inside tolerance must pass"
        assert dl.check({"modern_flagged_after": 0}, path), \
            "missing gated keys must be reported, not silently skipped"
    finally:
        os.unlink(path)


def test_detector_local_declares_both_families():
    """The panel must keep at least one statistical and one supervised detector, or
    it stops covering the two families that behave differently on rewrites."""
    import detector_local as dl
    assert dl.CAUSAL_MODEL and dl.PERFORMER_MODEL
    assert len(dl.CLASSIFIER_CANDIDATES) >= 2
    for key, repo, ai_label in dl.CLASSIFIER_CANDIDATES:
        assert key and "/" in repo and ai_label


def _infer_accuracy():
    """(correct, total, safe_fallbacks, unsafe) over the labeled corpus."""
    sys.path.insert(0, lib.SKILL_DIR)
    from human_voice_linter.infer import infer_register

    labels = lib.load_labels()
    correct = safe = unsafe = 0
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(lib.CORPUS, rel), encoding="utf-8") as fh:
            got, _conf, _why = infer_register(fh.read())
        if got == meta["register"]:
            correct += 1
        elif got == "technical":
            safe += 1          # fell back to the strictest profile
        else:
            unsafe += 1        # chose a MORE permissive profile than the truth
    return correct, len(labels), safe, unsafe


def test_register_inference_beats_the_status_quo():
    """`--register auto` must beat the old behavior of always assuming technical.

    The corpus register labels are ground truth here. The bar is deliberately the
    status quo, because that is what the feature replaces: before this, every
    document was scored with the `technical` mute set no matter what it was.
    """
    correct, total, _safe, _unsafe = _infer_accuracy()
    labels = lib.load_labels()
    status_quo = sum(1 for m in labels.values() if m["register"] == "technical")
    assert correct > status_quo * 2, (
        "inference %d/%d is not clearly better than always-technical %d/%d"
        % (correct, total, status_quo, total))
    assert correct / total >= 0.75, "inference accuracy fell to %.1f%%" % (
        100 * correct / total)


def test_register_inference_fails_safe():
    """When it is wrong it should usually fall back to the strictest profile.

    Guessing a permissive register silently excuses real tells (creative mutes the
    dash checks, casual mutes the costume check), so a wrong guess toward `technical`
    is much cheaper than a wrong guess away from it.
    """
    _correct, total, safe, unsafe = _infer_accuracy()
    assert unsafe / total <= 0.15, (
        "%d of %d guesses chose a more permissive register than the truth" % (unsafe, total))
    assert safe >= unsafe, (
        "misses should skew toward the strict fallback: %d safe vs %d unsafe"
        % (safe, unsafe))


def test_register_inference_is_deterministic_and_explains_itself():
    sys.path.insert(0, lib.SKILL_DIR)
    from human_voice_linter.infer import infer_register

    text = ("Subject: Q3 numbers\n\nHi team,\n\nRetention moved from 71% to 76% "
            "this quarter and churn in mid-market is still twice enterprise.\n\n"
            "Thanks,\nPriya\n")
    a = infer_register(text)
    b = infer_register(text)
    assert a == b, "inference must be deterministic"
    reg, conf, why = a
    assert reg in lib.load_detector().REGISTERS
    assert 0.0 <= conf <= 1.0
    assert why, "inference must report why it chose"


def test_register_inference_empty_and_tiny_inputs():
    sys.path.insert(0, lib.SKILL_DIR)
    from human_voice_linter.infer import infer_register

    for text in ("", "   \n\n", "Hello.", "x"):
        reg, conf, why = infer_register(text)
        assert reg == "technical", "empty/tiny input should fall back, got %r" % reg
        assert why
