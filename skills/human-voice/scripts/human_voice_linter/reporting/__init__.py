"""reporting — rendering analyzed documents for people and for machines.

    payload  the JSON result dict
    text     the human-readable report
    sarif    SARIF 2.1.0 for code-scanning UIs
"""
from __future__ import annotations

from .payload import SCHEMA_VERSION, build_payload
from .sarif import render_sarif
from .text import line_hotspots, render_text

__all__ = ["SCHEMA_VERSION", "build_payload", "render_sarif", "line_hotspots", "render_text"]
