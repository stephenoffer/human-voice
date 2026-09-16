"""loop — the skill's rewrite procedure, driven from outside the model.

Inside an agent, the model runs the linter, reads the report, and decides whether
another pass is worth it. Through an API the caller has to do that, and doing it
here has one advantage: the stopping condition stops being the model's opinion of
its own work. Every model gets the same gates:

    lint the source -> ask for a rewrite -> lint it + check invariants
      (+ ask the detector, if one is configured) -> feed the report back -> ...

A pass is accepted when the score is at or under the target, no invariant was
lost or introduced, and the detector (if asked) clears. The loop stops early when
two consecutive passes fail to improve, because the skill says not to grind, and
it returns the best pass it saw rather than the last one.
"""
from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from human_voice_linter import (  # noqa: E402
    REGISTERS,
    analyze,
    find_project_config,
    infer_register,
    load_patterns,
    merge_config,
    render_text,
    resolve_bands,
    resolve_weights,
    score,
    verdict_band,
)

from . import invariants, prompt  # noqa: E402
from .providers import ProviderError, chat  # noqa: E402

DEFAULT_TARGET = 5.0  # the top of the `clean` band


def load_linter_config(path_hint=None):
    patterns = load_patterns()
    cfg = find_project_config(path_hint) if path_hint else None
    if cfg:
        patterns = merge_config(patterns, cfg)
    return patterns, (cfg or {})


def lint_text(text, register, patterns, dialect=None, name="text"):
    """(payload dict, rendered report) for one text."""
    hits, report, words = analyze(text, register, dialect, patterns)
    weights = resolve_weights(patterns)
    floor = score(hits, words, weights)
    band = verdict_band(floor, resolve_bands(patterns))
    rendered = render_text(name, register, dialect, hits, report, words, floor, band,
                           thresholds=patterns.get("thresholds"))
    return {"score": floor, "verdict": band, "words": words, "metrics": report,
            "categories": sorted({h.category for h in hits})}, rendered


def _detector_probe(text, max_p_ai):
    from human_voice_linter import detector as D
    var, key = D.find_api_key()
    if not key:
        return None
    try:
        p = D.probe(text, key, var)
    except Exception as exc:  # the gate did not run; that is reported, not raised
        return {"status": "error", "reason": "%s: %s" % (type(exc).__name__, exc)}
    label, clear = D.verdict(p, max_p_ai)
    return {"status": label, "clear": clear, "p_ai": round(p, 4),
            "detector": D.DETECTORS[var]["name"]}


def humanize(text, model=None, mode="fix", register="auto", depth="standard",
             dialect=None, context=None, max_passes=3, target_score=DEFAULT_TARGET,
             references="core", verify=False, max_p_ai=0.10, max_tokens=None,
             temperature=None, base_url=None, path_hint=None, source_name="pasted text",
             opener=None, env=None, log=None):
    """Run the rewrite loop and return a result dict.

    The dict always carries the best rewrite found, the audit that came with it,
    every pass's numbers, and `accepted`, which is True only when a pass met
    every gate. A result that was not accepted still has a usable rewrite; the
    caller decides whether to ship it, and the numbers say why it fell short.
    """
    say = log or (lambda msg: None)
    patterns, cfg = load_linter_config(path_hint)
    register = register or cfg.get("register") or "auto"
    dialect = dialect or cfg.get("dialect")
    inferred = None
    if register == "auto":
        register, confidence, why = infer_register(text)
        inferred = "%s, confidence %.2f, from %s" % (register, confidence,
                                                     "; ".join(why) or "no cue")
        say("register: %s" % inferred)
    elif register not in REGISTERS:
        raise ValueError("unknown register %r; one of %s" % (register, ", ".join(REGISTERS)))

    before, before_report = (None, None)
    if mode == "fix":
        before, before_report = lint_text(text, register, patterns, dialect, source_name)
        say("before: %.1f [%s], %d words" % (before["score"], before["verdict"], before["words"]))

    system = prompt.build_system_prompt("api", references)
    messages = [{"role": "user", "content": prompt.build_task(
        text, mode, register, depth, context, before_report, inferred, source_name)}]

    passes, best = [], None
    provider = model_id = None
    stalled = 0
    for n in range(1, max_passes + 1):
        say("pass %d/%d: calling model" % (n, max_passes))
        try:
            completion = chat(model, system, messages, max_tokens=max_tokens,
                              temperature=temperature, env=env, opener=opener,
                              base_url=base_url)
        except ProviderError:
            if best is None:
                raise
            say("provider error on pass %d; keeping the best earlier pass" % n)
            break
        provider, model_id = completion.provider, completion.model
        messages.append({"role": "assistant", "content": completion.text})
        rewrite, audit, fmt_err = prompt.parse_response(completion.text, text)

        if fmt_err:
            say("pass %d: %s" % (n, fmt_err))
            passes.append({"pass": n, "error": fmt_err, "truncated": completion.truncated})
            messages.append({"role": "user", "content": prompt.build_feedback(
                n, max_passes, None, None, truncated=completion.truncated,
                format_error=fmt_err)})
            continue

        after, after_report = lint_text(rewrite, register, patterns, dialect, "rewrite")
        if mode == "fix":
            inv = invariants.compare(text, rewrite, context)
        else:
            # A draft need not repeat every number in its brief, but it may not
            # state one that neither the brief nor the context supplied.
            inv = invariants.compare("%s\n\n%s" % (text, context or ""), rewrite)
            inv["missing"] = {}
            inv["ok"] = not inv["added"]
        det = _detector_probe(rewrite, max_p_ai) if verify else None
        det_ok = det is None or det.get("clear") is True or det.get("status") == "error"

        record = {"pass": n, "score": after["score"], "verdict": after["verdict"],
                  "words": after["words"], "invariants_ok": inv["ok"],
                  "missing": inv["missing"], "added": inv["added"],
                  "placeholders": inv["placeholders"], "truncated": completion.truncated,
                  "detector": det, "usage": completion.usage}
        passes.append(record)
        say("pass %d: score %.1f [%s], invariants %s%s%s" % (
            n, after["score"], after["verdict"], "ok" if inv["ok"] else "FAILED",
            ", detector %s" % det["status"] if det else "",
            ", TRUNCATED" if completion.truncated else ""))

        candidate = {"rewrite": rewrite, "audit": audit, "record": record,
                     "metrics": after, "report": after_report}
        rank = (not inv["ok"], completion.truncated, not det_ok, after["score"])
        improved = best is None or rank < best["rank"]
        stalled = 0 if improved else stalled + 1
        if improved:
            best = dict(candidate, rank=rank)

        if (inv["ok"] and not completion.truncated and det_ok
                and after["score"] <= target_score):
            break
        if stalled >= 2:
            say("two passes without improvement; stopping rather than grinding")
            break
        if n < max_passes:
            det_line = None
            if det:
                det_line = ("%s p(AI)=%s against %s (gate %.2f)" % (
                    det["status"], det.get("p_ai"), det.get("detector"), max_p_ai)
                    if det.get("status") != "error" else "error: %s" % det["reason"])
            messages.append({"role": "user", "content": prompt.build_feedback(
                n, max_passes, after_report, invariants.summarize(inv), det_line,
                truncated=completion.truncated)})

    if best is None:
        raise ProviderError("the model never returned a usable <rewrite> section in %d "
                            "pass(es); try a stronger model or --references none for a "
                            "small context window" % max_passes)
    rec = best["record"]
    accepted = (rec["invariants_ok"] and not rec["truncated"]
                and (rec["detector"] is None or rec["detector"].get("clear") is True)
                and rec["score"] <= target_score)
    return {
        "schema_version": 1,
        "provider": provider, "model": model_id,
        "mode": mode, "register": register, "depth": depth,
        "accepted": accepted, "target_score": target_score,
        "before": before, "after": best["metrics"],
        "rewrite": best["rewrite"], "audit": best["audit"],
        "invariants": {k: rec[k] for k in ("invariants_ok", "missing", "added", "placeholders")},
        "detector": rec["detector"] if verify else "not run",
        "passes": passes, "best_pass": rec["pass"],
    }


__all__ = ["DEFAULT_TARGET", "humanize", "lint_text", "load_linter_config"]
