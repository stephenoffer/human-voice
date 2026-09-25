"""payload — the JSON result shape shared by lint(), --json, SARIF, and MCP."""
from __future__ import annotations

from ..scoring.bands import verdict_band
from ..scoring.weights import severity_of

SCHEMA_VERSION = 1


def build_payload(hits, report, words, floor, *, register, dialect, weights, bands,
                  input_name=None, inferred_register=None) -> dict:
    """One analyzed document as a JSON-ready dict.

    `input` appears only when a target name is given (the CLI), and
    `inferred_register` only when --register auto actually inferred one, so a
    consumer that asks for neither sees the same keys it always has.
    """
    payload: dict = {"schema_version": SCHEMA_VERSION}
    if input_name is not None:
        payload["input"] = input_name
    payload.update({
        "register": register,
        "dialect": dialect,
        "words": words,
        "score": floor,
        "verdict": verdict_band(floor, bands),
        "metrics": report,
        "hits": [dict(h.as_dict(), severity=severity_of(h.category, weights)) for h in hits],
    })
    if inferred_register is not None:
        payload["inferred_register"] = inferred_register
    return payload


__all__ = ["SCHEMA_VERSION", "build_payload"]
