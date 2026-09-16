"""report — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

from .defaults import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403
from .score import *  # noqa: F401,F403
from .util import *  # noqa: F401,F403


def render_text(target, register, dialect, hits, report, word_count, floor_score,
                band="n/a", max_examples=6, thresholds=None):
    """Human-readable report.

    `thresholds` is the resolved threshold table. The "want >=" figures used to be
    hardcoded in this format string, so overriding a threshold on the command line
    or in .humanvoicerc changed what fired while the report kept quoting the
    default -- the reader was told to aim at a number the linter was not using.
    """
    th = thresholds if isinstance(thresholds, dict) else DEFAULTS["thresholds"]

    def _t(key):
        v = th.get(key, DEFAULTS["thresholds"].get(key))
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(DEFAULTS["thresholds"][key])

    by_cat = {}
    for h in hits:
        by_cat.setdefault(h.category, []).append(h)

    out = []
    out.append("AI-prose floor report — %s" % target)
    out.append("register: %s%s   words: %d" % (
        register, ("   dialect: " + dialect) if dialect else "", word_count))
    out.append("score: %.1f floor points  [%s]  (lower is better; a FLOOR, not proof)"
               % (floor_score, band))
    def _m(key, fmt="%s"):
        v = report.get(key)
        return "n/a" if v is None else fmt % v
    out.append("rhythm:  CoV %s (want >=%.2f)   short<=%dw %s (want >=%.2f)   "
               "mid-band %s (want <=%.2f)   mean %s w" % (
        _m("burstiness_cov"), _t("burstiness_cov_floor"),
        int(_t("short_sentence_max_words")), _m("short_sentence_ratio"),
        _t("short_sentence_ratio_floor"), _m("mid_band_ratio"),
        _t("mid_band_ratio_max"), _m("mean_sentence_len")))
    out.append("shape:   headings/1k %s   bullet-line ratio %s   bold/1k %s   em-dash/1k %s" % (
        _m("headings_per_1k"), _m("bullet_line_ratio"), _m("bold_spans_per_1k"),
        _m("em_dash_per_1k")))
    out.append("syntax:  clefts %s   ',VERBing' tails %s   copula/1k %s   passive/1k %s" % (
        _m("cleft_count"), _m("participial_tail_count"), _m("copula_per_1k"),
        _m("passive_per_1k")))
    out.append("structure: sections %s   section-length CoV %s   framing share %s   "
               "restated pairs %s   depth %s/100w by section %s" % (
        _m("sections"), _m("section_len_cov"), _m("framing_share"),
        _m("restated_pairs"), _m("depth_per_100"),
        "[" + ", ".join(str(d) for d in report["section_depth"]) + "]"
        if report.get("section_depth") else "n/a"))
    out.append("lexicon: TTR %s   Yule's K %s   copula-avoid/1k %s" % (
        _m("ttr"), _m("yules_k"), _m("copula_avoidance_per_1k")))
    # Reported, never scored: see checks.report_contraction_rate. A conversational
    # register with a contraction rate near zero reads stiff and is worth telling
    # the writer about; scoring it would flag careful non-native writers, which is
    # the exact failure this skill argues detectors make.
    out.append("voice:   contractions/1k %s (diagnostic, unscored)   quotes %s curly / %s straight" % (
        _m("contractions_per_1k"), _m("curly_quotes"), _m("straight_quotes")))
    if report.get("stylometric_delta") is not None:
        out.append("style:   function-word delta %s   (human range %s-%s, median %s)%s" % (
            _m("stylometric_delta"), _m("human_delta_min"), _m("human_delta_max"),
            _m("human_delta_median"),
            "   <- flatter than any human sample; the profile has no fingerprint"
            if report.get("stylometric_flat") else ""))
    out.append("detail:  %s specifics/100w (%s numbers, %s proper nouns)%s" % (
        _m("specifics_per_100"), _m("numbers"), _m("proper_nouns"),
        "   <- nothing checkable in here" if report.get("specifics_thin") else ""))
    out.append("")
    if word_count == 0:
        out.append("No prose found (empty, code-only, or non-text input). Nothing to score.")
        return "\n".join(out)
    if not hits:
        out.append("No surface tells flagged. Now do the skeptical human read — the")
        out.append("linter cannot see vacuity, weak stance, or fabrication.")
        return "\n".join(out)

    out.append("Tells by category (%d total):" % len(hits))
    for cat in sorted(by_cat, key=lambda c: (-len(by_cat[c]), c)):
        items = by_cat[cat]
        out.append("  %-20s %d" % (cat, len(items)))
        for h in items[:max_examples]:
            loc = ("L%d: " % h.line) if h.line else ""
            sug = ("  -> %s" % h.suggestion) if h.suggestion else ""
            out.append("      %s%s%s" % (loc, h.text, sug))
        if len(items) > max_examples:
            out.append("      ... and %d more" % (len(items) - max_examples))
    hotspots = line_hotspots(hits)
    if len(hotspots) > 1 and hotspots[0][1] > 1:
        spots = ", ".join("L%d (%d)" % (ln, n) for ln, n in hotspots if n > 1)
        if spots:
            out.append("")
            out.append("Hotspot lines: %s" % spots)
    out.append("")
    out.append("Floor only. The linter cannot see vacuity, weak stance, terminology")
    out.append("drift, or fabrication. A skeptical human read is the real test.")
    return "\n".join(out)


def render_sarif(results):
    """Minimal SARIF 2.1.0 doc so hits surface inline in code-scanning UIs."""
    sarif_results = []
    rules = {}
    for res in results:
        for h in res["hits"]:
            cat = h["category"]
            rules.setdefault(cat, {"id": cat, "name": cat,
                                   "shortDescription": {"text": "AI-prose tell: %s" % cat}})
            region = {"startLine": max(1, h.get("line") or 1)}
            if h.get("col") is not None:
                region["startColumn"] = h["col"]
            if h.get("end_line") is not None:
                region["endLine"] = max(1, h["end_line"])
            if h.get("end_col") is not None:
                region["endColumn"] = h["end_col"]
            sarif_results.append({
                "ruleId": cat,
                "level": {"high": "error", "medium": "warning", "low": "note"}.get(
                    h.get("severity", "low"), "note"),
                "message": {"text": "%s%s" % (
                    h["text"], "  -> " + h["suggestion"] if h.get("suggestion") else "")},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": res["input"]},
                    "region": region}}],
            })
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {"driver": {"name": "detect_ai_prose", "rules": list(rules.values())}},
            "results": sarif_results,
        }],
    }


__all__ = [
    'render_text',
    'render_sarif',
]
