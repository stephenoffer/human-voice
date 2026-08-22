#!/usr/bin/env python3
"""Measure real detector signals locally, with open models. Dev-only, opt-in.

Why this exists: every other number in `eval/` measures the regex floor against
itself. Nothing measured what a *detector* does, so the repo quoted third-party
figures and disclaimed them. This closes that, without an API key and without
sending anyone's text to a vendor, by running two open models locally.

    python3 -m venv .detvenv
    .detvenv/bin/pip install torch transformers
    .detvenv/bin/python eval/detector_local.py

It is deliberately NOT part of `make test` or CI: it needs ~1.5GB of model
weights and a heavy dependency tree, and the shipped linter must stay
dependency-free. Nothing here is imported by the skill.

Three signals across the two detector families that behave differently on rewritten
text (see references/what-detectors-see.md):

1. **Token surprisal** -- real per-token -log P(token | context) under the observer
   model, giving genuine perplexity and its variance. This is what the
   statistical/zero-shot family (DetectGPT, FastDetectGPT, Binoculars, most free web
   tools) computes, modulo the size of the proxy model. Low perplexity = predictable
   = machine-looking. Note the direction: raising perplexity by writing more
   specifically is the honest lever, and raising it with mangled synonyms is what
   humanizer tools do and what gets them caught.
2. **Binoculars** -- observer perplexity over observer/performer cross-perplexity,
   the strongest published zero-shot method, here with a small model pair.
   A caution learned the hard way in this repo: with a gpt2/distilgpt2 pair the
   `over_corrected` class scored *below* human (0.780 vs 0.891), which read as
   "Binoculars catches the anti-AI costume". With gpt2-large/gpt2 it does not (0.788
   vs 0.780). That conclusion was an artifact of the pair, so treat any single
   Binoculars ranking as pair-dependent until it replicates.
3. **Supervised classifiers** returning p(AI), of deliberately mixed vintage: a 2019
   model trained on GPT-2 output, a 2023 model trained on ChatGPT output, and newer
   ones. Each is calibrated against the human class first (see MAX_HUMAN_FPR): one
   candidate flags 34 of 34 human files, so its verdict on a rewrite carries no
   information and is excluded from every tally rather than quietly inflating it.

None of them is ground truth. A small proxy model's perplexity is a coarse stand-in
for a large one's, and GPT detectors misclassify non-native-English writing (Liang
et al. 2023). Read the numbers as a measured direction of travel, not a verdict.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CORPUS = os.path.join(HERE, "corpus")
EXAMPLES = os.path.join(REPO, "skills", "human-voice", "examples")

# Observer for perplexity and Binoculars. gpt2-large is a better stand-in for the
# proxy models real statistical detectors use; set HV_CAUSAL_MODEL=gpt2 for a fast run.
CAUSAL_MODEL = os.environ.get("HV_CAUSAL_MODEL", "gpt2-large")
# Binoculars scores a text by the ratio of its perplexity under one model to its
# cross-perplexity against a second, closely-related one. It is the strongest
# published zero-shot method; this is the same statistic computed with a small
# model pair, so read it as directional.
PERFORMER_MODEL = os.environ.get("HV_PERFORMER_MODEL", "gpt2")
# Two supervised classifiers, deliberately of different vintages. The 2019 model
# was trained on GPT-2 output; the 2023 one on real ChatGPT output, which makes it
# the far more relevant test of whether a rewrite clears a *trained* detector.
# (key, repo, label meaning "AI"). Any that fails to load is skipped with a notice,
# so the panel degrades instead of the run dying.
CLASSIFIER_CANDIDATES = (
    ("roberta_openai_2019", "openai-community/roberta-base-openai-detector", "fake"),
    ("chatgpt_detector_2023", "Hello-SimpleAI/chatgpt-detector-roberta", "chatgpt"),
    ("mixed_detector", "andreas122001/roberta-mixed-detector", "machine"),
    ("desklib_2024", "desklib/ai-text-detector-v1.01", "ai"),
    ("fakespot", "fakespot-ai/roberta-base-ai-text-detection-v1", "ai"),
)
CLASSIFIERS: list = []   # filled by load_models with whatever actually loaded


def load_models():
    try:
        import torch
        from transformers import (  # noqa: I001
            AutoModelForCausalLM,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )
    except ImportError:
        print("torch/transformers not installed. This harness is opt-in:")
        print("  python3 -m venv .detvenv")
        print("  .detvenv/bin/pip install torch transformers")
        print("  .detvenv/bin/python eval/detector_local.py")
        return None
    torch.set_grad_enabled(False)
    gt = AutoTokenizer.from_pretrained(CAUSAL_MODEL)
    gm = AutoModelForCausalLM.from_pretrained(CAUSAL_MODEL).eval()
    pm = AutoModelForCausalLM.from_pretrained(PERFORMER_MODEL).eval()
    clfs = []
    for key, name, ai_label in CLASSIFIER_CANDIDATES:
        try:
            tok = AutoTokenizer.from_pretrained(name)
            mod = AutoModelForSequenceClassification.from_pretrained(name).eval()
            idx = [i for i, lab in mod.config.id2label.items()
                   if ai_label in lab.lower()]
            if not idx:
                # Some checkpoints ship LABEL_0/LABEL_1 with no semantics. Guessing
                # which index means AI would silently invert the result, so skip.
                print("skip %s: cannot identify the AI label in %s"
                      % (key, mod.config.id2label), file=sys.stderr)
                continue
            clfs.append((key, tok, mod, idx[0], mod.config.id2label))
            CLASSIFIERS.append((key, name, ai_label))
        except Exception as exc:
            print("skip %s (%s): %s" % (key, name, type(exc).__name__), file=sys.stderr)
    if not clfs:
        print("no supervised classifier loaded; only the statistical signals will run",
              file=sys.stderr)
    return torch, gt, gm, pm, clfs


def surprisal_stats(text, torch, gt, gm, max_len=512, min_tokens=12):
    """Real per-token surprisal: perplexity and its coefficient of variation."""
    ids = gt(text, return_tensors="pt", truncation=True, max_length=max_len).input_ids
    if ids.shape[1] < min_tokens:
        return {}
    logits = gm(ids).logits[0, :-1]
    target = ids[0, 1:]
    logprobs = torch.log_softmax(logits.float(), dim=-1)
    surp = (-logprobs[torch.arange(target.shape[0]), target]).tolist()
    mean = statistics.fmean(surp)
    sd = statistics.pstdev(surp)
    return {"ppl": math.exp(min(mean, 20)), "surprisal_mean": mean,
            "surprisal_cov": (sd / mean) if mean else 0.0, "n_tokens": len(surp)}


def binoculars_score(text, torch, gt, gm, pm, max_len=512, min_tokens=12):
    """Binoculars-style score: observer perplexity / observer-performer
    cross-perplexity. HIGHER means more human-looking. Computed with a small model
    pair, so the ordering is meaningful and the absolute value is not comparable to
    the published thresholds."""
    ids = gt(text, return_tensors="pt", truncation=True, max_length=max_len).input_ids
    if ids.shape[1] < min_tokens:
        return None
    obs = gm(ids).logits[0, :-1].float()
    perf = pm(ids).logits[0, :-1].float()
    target = ids[0, 1:]
    obs_lp = torch.log_softmax(obs, dim=-1)
    ppl = -obs_lp[torch.arange(target.shape[0]), target].mean().item()
    # Cross-perplexity: performer's predicted distribution scored by the observer.
    x_ppl = -(torch.softmax(perf, dim=-1) * obs_lp).sum(dim=-1).mean().item()
    return ppl / x_ppl if x_ppl else None


def classify(text, torch, clfs, max_len=512):
    """{key: {"p_ai", "label", "says_ai"}} for every supervised classifier."""
    out = {}
    for key, tok, mod, ai_idx, id2label in clfs:
        enc = tok(text, return_tensors="pt", truncation=True, max_length=max_len)
        probs = torch.softmax(mod(**enc).logits.float()[0], dim=-1)
        pred = int(probs.argmax().item())
        out[key] = {"p_ai": probs[ai_idx].item(),
                    "label": id2label[pred],
                    "says_ai": pred == ai_idx}
    return out


def measure(text, models):
    torch, gt, gm, pm, clfs = models
    out = surprisal_stats(text, torch, gt, gm)
    out["binoculars"] = binoculars_score(text, torch, gt, gm, pm)
    out["classifiers"] = classify(text, torch, clfs)
    for key, res in out["classifiers"].items():
        out["p_ai_" + key] = res["p_ai"]
        out["says_ai_" + key] = res["says_ai"]
    return out


# A classifier is only counted if it can tell the human class apart. One of the
# candidates flags 34 of 34 human files at p(AI)=1.000, so "it flagged the rewrite
# too" carries no information; including it would have inflated every count in this
# report. Anything above this human false-positive rate is measured, reported, and
# then excluded from the verdict tallies.
MAX_HUMAN_FPR = 0.20


def calibrate(by_label, clf_keys):
    """{key: {"human_fpr", "n_human", "usable"}} measured on the human class."""
    human = by_label.get("human") or []
    out = {}
    for key in clf_keys:
        n = len(human)
        flagged = sum(1 for r in human if r.get("says_ai_" + key))
        fpr = (flagged / n) if n else None
        out[key] = {"human_fpr": fpr, "flagged_human": flagged, "n_human": n,
                    "usable": bool(n) and fpr is not None and fpr <= MAX_HUMAN_FPR}
    return out


def _stats(rows, key):
    vals = sorted(r[key] for r in rows if key in r)
    if not vals:
        return None
    return {"median": statistics.median(vals), "min": vals[0], "max": vals[-1],
            "n": len(vals)}


def run(models, as_json=False):
    labels = json.load(open(os.path.join(CORPUS, "LABELS.json")))["labels"]
    by_label: dict = {}
    for rel, meta in sorted(labels.items()):
        with open(os.path.join(CORPUS, rel), encoding="utf-8") as fh:
            by_label.setdefault(meta["label"], []).append(measure(fh.read(), models))

    calibration = calibrate(by_label, [k for k, _n, _l in CLASSIFIERS])
    usable = [k for k, _n, _l in CLASSIFIERS if calibration[k]["usable"]]

    # The headline comparison: every realistic-modern-AI sample, before and after
    # the skill's rewrite procedure. n=12 across every register, which is a far
    # stronger test than the hand-picked example pairs below.
    modern_pairs = []
    rewritten_dir = os.path.join(CORPUS, "ai_modern_rewritten")
    for bpath in sorted(glob.glob(os.path.join(CORPUS, "ai_modern", "*.md"))):
        apath = os.path.join(rewritten_dir, os.path.basename(bpath))
        if not os.path.isfile(apath):
            continue
        with open(bpath, encoding="utf-8") as fh:
            before = measure(fh.read(), models)
        with open(apath, encoding="utf-8") as fh:
            after = measure(fh.read(), models)
        modern_pairs.append({
            "file": os.path.basename(bpath), "before": before, "after": after,
            "ppl_ratio": (after.get("ppl", 0) / before["ppl"]
                          if before.get("ppl") else None)})

    pairs = []
    for bpath in sorted(glob.glob(os.path.join(EXAMPLES, "*-before.md"))):
        stem = os.path.basename(bpath)[: -len("-before.md")]
        apath = os.path.join(EXAMPLES, stem + "-after.md")
        if not os.path.isfile(apath):
            continue
        with open(bpath, encoding="utf-8") as fh:
            before = measure(fh.read(), models)
        with open(apath, encoding="utf-8") as fh:
            after = measure(fh.read(), models)
        pairs.append({"pair": stem, "before": before, "after": after,
                      "ppl_ratio": (after.get("ppl", 0) / before["ppl"]
                                    if before.get("ppl") else None)})

    report = {
        "causal_model": CAUSAL_MODEL,
        "performer_model": PERFORMER_MODEL,
        "classifiers": {k: n for k, n, _ in CLASSIFIERS},
        "by_class": {lab: {k: _stats(rows, k)
                           for k in (("ppl", "surprisal_cov", "binoculars")
                                     + tuple("p_ai_" + c[0] for c in CLASSIFIERS))}
                     for lab, rows in by_label.items()},
        "calibration": calibration,
        "usable_classifiers": usable,
        "modern_pairs": modern_pairs,
        "pairs": pairs,
        "pair_ppl_ratio_median": statistics.median(
            [p["ppl_ratio"] for p in pairs if p["ppl_ratio"]]) if pairs else None,
    }
    if as_json:
        json.dump(report, sys.stdout, indent=2)
        print()
        return report

    print("Local detector measurement")
    print("  statistical: %s perplexity, Binoculars(%s / %s)"
          % (CAUSAL_MODEL, CAUSAL_MODEL, PERFORMER_MODEL))
    for key, name, _ in CLASSIFIERS:
        print("  classifier:  %-22s %s" % (key, name))
    print("=" * 100)
    print("%-16s %4s | %-11s | %-9s | %s"
          % ("class", "n", "perplexity", "binocs", "supervised classifiers: median p(AI) / n saying AI"))
    print("-" * 100)
    for lab in ("human", "ai", "ai_modern", "over_corrected"):
        rows = by_label.get(lab) or []
        if not rows:
            continue
        c = report["by_class"][lab]
        cells = []
        for key, _n, _l in CLASSIFIERS:
            st = c.get("p_ai_" + key)
            n_ai = sum(1 for r in rows if r.get("says_ai_" + key))
            cells.append("%s %.3f / %d of %d" % (key.split("_")[0], st["median"],
                                                 n_ai, len(rows)))
        bn = c.get("binoculars")
        print("%-16s %4d | med %7.1f | med %.3f | %s"
              % (lab, len(rows), c["ppl"]["median"],
                 bn["median"] if bn else float("nan"), "   ".join(cells)))

    def _says(rec, keys=None):
        keys = usable if keys is None else keys
        hits = [k.split("_")[0] for k in keys if rec.get("says_ai_" + k)]
        return ",".join(hits) if hits else "no"

    print()
    print("Classifier calibration on the human class (a detector that flags humans")
    print("cannot tell you anything about a rewrite, so it is excluded below):")
    for _key, _n, _l in CLASSIFIERS:
        _cal = calibration[_key]
        print("  %-24s human FPR %5.1f%%  (%d of %d)   %s"
              % (_key, 100 * (_cal["human_fpr"] or 0), _cal["flagged_human"],
                 _cal["n_human"], "USABLE" if _cal["usable"] else "EXCLUDED"))
    if not usable:
        print("  none usable: no classifier verdict is reported below")

    if modern_pairs:
        print()
        print("HEADLINE: all %d realistic-modern-AI samples, before -> after the skill."
              % len(modern_pairs))
        print("'says AI' is each classifier's own argmax LABEL, not a chosen threshold.")
        print("%-30s | %-22s | %-15s | %s"
              % ("file", "perplexity", "binoculars", "says AI: before -> after"))
        print("-" * 104)
        n_b = n_a = 0
        for mp in modern_pairs:
            b, a = mp["before"], mp["after"]
            sb, sa = _says(b), _says(a)
            n_b += sb != "no"
            n_a += sa != "no"
            print("%-30s | %6.1f -> %6.1f (x%.2f)| %.3f -> %.3f | %-10s -> %s"
                  % (mp["file"][:28], b.get("ppl", 0), a.get("ppl", 0),
                     mp["ppl_ratio"] or 0, b.get("binoculars") or 0,
                     a.get("binoculars") or 0, sb, sa))
        ratios = [mp["ppl_ratio"] for mp in modern_pairs if mp["ppl_ratio"]]
        print("-" * 104)
        print("median perplexity multiplier: x%.2f      flagged by any classifier: "
              "%d of %d before -> %d of %d after"
              % (statistics.median(ratios) if ratios else 0,
                 n_b, len(modern_pairs), n_a, len(modern_pairs)))
        report["modern_flagged_before"] = n_b
        report["modern_flagged_after"] = n_a
        report["modern_ppl_ratio_median"] = (statistics.median(ratios)
                                            if ratios else None)

    print()
    print("Shipped before/after pairs. 'says AI' is the classifier's argmax LABEL,")
    print("not a threshold anyone chose:")
    print("%-18s | %-20s | %-15s | %s"
          % ("pair", "perplexity", "binoculars", "any classifier says AI?"))
    print("-" * 92)
    for p in pairs:
        b, a = p["before"], p["after"]
        print("%-18s | %6.1f -> %6.1f (x%.2f)| %.3f -> %.3f | before: %-8s after: %s"
              % (p["pair"], b.get("ppl", 0), a.get("ppl", 0), p["ppl_ratio"] or 0,
                 b.get("binoculars") or 0, a.get("binoculars") or 0,
                 _says(b), _says(a)))

    n_after_flagged = sum(
        1 for p in pairs
        if any(p["after"].get("says_ai_" + k) for k in usable))
    print()
    if report["pair_ppl_ratio_median"]:
        print("Median perplexity multiplier across pairs: x%.2f"
              % report["pair_ppl_ratio_median"])
    print("Rewritten texts classified AI by ANY supervised detector run here: %d of %d"
          % (n_after_flagged, len(pairs)))
    report["after_flagged_count"] = n_after_flagged
    report["n_pairs"] = len(pairs)
    print()
    print("Neither family is ground truth. GPT-2 is 124M parameters and the")
    print("Binoculars pair is small, so trust the direction and not the absolute")
    print("values; and GPT detectors misclassify non-native-English writing")
    print("(Liang et al. 2023, Patterns). No commercial API was queried.")
    return report


# Gated metrics: the ones a change must not quietly regress. Kept small and
# outcome-shaped on purpose, because the per-file values move with model versions
# while these should not.
GATED = (
    ("modern_flagged_after", "realistic-AI rewrites flagged by any classifier", "max"),
    ("after_flagged_count", "example-pair rewrites flagged by any classifier", "max"),
    ("modern_ppl_ratio_median", "median perplexity multiplier on the rewrites", "min"),
)

DEFAULT_RESULTS = os.path.join(HERE, "detector_local_results.json")


def check(report, golden_path=DEFAULT_RESULTS, tol=0.05):
    """Compare a fresh report against the committed one. Returns a list of failures.

    'max' metrics must not increase (more flagged is worse); 'min' metrics must not
    fall by more than `tol` relatively. Absolute per-file numbers are NOT gated: they
    shift with model and library versions, and gating them would produce noise
    instead of signal.
    """
    with open(golden_path, encoding="utf-8") as fh:
        golden = json.load(fh)
    problems = []
    for key, label, direction in GATED:
        want, got = golden.get(key), report.get(key)
        if want is None or got is None:
            problems.append("%s: missing (golden=%r live=%r)" % (key, want, got))
            continue
        if direction == "max" and got > want:
            problems.append("%s regressed: %s went %r -> %r" % (key, label, want, got))
        if direction == "min" and got < want * (1.0 - tol):
            problems.append("%s regressed: %s fell %r -> %r (tol %.0f%%)"
                            % (key, label, want, got, tol * 100))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--out", metavar="PATH",
                    help="also write the report JSON to PATH")
    ap.add_argument("--check", action="store_true",
                    help="compare against the committed results and exit 1 on regression")
    ap.add_argument("--tol", type=float, default=0.05,
                    help="relative tolerance for 'higher is better' metrics")
    args = ap.parse_args(argv)
    models = load_models()
    if models is None:
        return 2
    report = run(models, as_json=args.json)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
        print("wrote %s" % args.out, file=sys.stderr)
    if args.check:
        problems = check(report, tol=args.tol)
        if problems:
            print("\ndetector --check: FAIL")
            for pr in problems:
                print("  - %s" % pr)
            return 1
        print("\ndetector --check: OK (no gated metric regressed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
