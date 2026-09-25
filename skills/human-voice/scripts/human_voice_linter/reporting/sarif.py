"""sarif — a minimal SARIF 2.1.0 document for code-scanning UIs."""
from __future__ import annotations


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


__all__ = ["render_sarif"]
