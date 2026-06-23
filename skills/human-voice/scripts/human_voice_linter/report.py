"""report — part of human_voice_linter (split from detect_ai_prose.py)."""
from __future__ import annotations

import argparse
import bisect
import functools
import json
import math
import os
import re
import sys
from collections import Counter
from .util import *  # noqa: F401,F403
from .hit import *  # noqa: F401,F403
from .defaults import *  # noqa: F401,F403
from .score import *  # noqa: F401,F403


def render_text(target, register, dialect, hits, report, word_count, floor_score,
                band="n/a", max_examples=6):
    by_cat = {}
    for h in hits:
        by_cat.setdefault(h.category, []).append(h)

    out = []
    out.append("AI-prose floor report — %s" % target)
    out.append("register: %s%s   words: %d" % (
        register, ("   dialect: " + dialect) if dialect else "", word_count))
    out.append("score: %.1f weighted tells / 1k words  [%s]  (lower is better; a FLOOR, not proof)"
               % (floor_score, band))
    bcov = report.get("burstiness_cov")
    out.append("burstiness CoV: %s   TTR: %s   em-dash/1k: %s   mean sentence: %s words" % (
        bcov if bcov is not None else "n/a",
        report.get("ttr", "n/a"),
        report.get("em_dash_per_1k", "n/a"),
        report.get("mean_sentence_len", "n/a")))
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
