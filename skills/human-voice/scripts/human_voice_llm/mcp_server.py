"""mcp_server — the skill and its tools over the Model Context Protocol (stdio).

Any MCP client gets the same thing Claude Code gets from the skill folder, whatever
model it runs: Cursor, VS Code / Copilot, Windsurf, Cline, Gemini CLI, Codex,
Zed, Claude Desktop, and anything else that speaks MCP.

    tools      lint_prose, check_invariants, get_skill, humanize, verify_detector
    prompts    human-voice (the skill plus a task, ready to send)
    resources  human-voice://SKILL.md and every reference file

The host model does the writing; these tools give it the measurements it cannot
make by reading: the floor score, the invariant diff, the detector verdict.
`humanize` is the exception. It delegates the whole loop to a second model via
the provider layer, for clients whose own model is weak or which want the
rewrite done out of band.

Standard library only: newline-delimited JSON-RPC 2.0 on stdin/stdout. Logs go to
stderr, because anything else on stdout corrupts the protocol stream.
"""
from __future__ import annotations

import json
import os
import sys
import traceback

from . import invariants, prompt
from .loop import humanize, lint_text, load_linter_config

SERVER_INFO = {"name": "human-voice", "version": "0.9.0"}
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

REGISTERS_HINT = ("technical, business, marketing, academic, casual, creative, email, "
                  "release_notes, ux_microcopy, tutorial, or auto")

MCP_ADAPTER = """\
# Running through MCP

You loaded the human-voice skill through its MCP server. The skill below was
written for an agent with a shell. What changes:

- Where it says to run `scripts/detect_ai_prose.py`, call the `lint_prose` tool
  with the text and register. It returns the same report.
- Where it says to diff invariants, call `check_invariants` with the original and
  the rewrite, and restore anything it lists as missing.
- Where it says to run `scripts/verify_detector.py`, call `verify_detector`. It
  reports "unavailable" when no detector key is configured, which is not a pass.
- Where it says to load `references/<name>.md`, call `get_skill` with
  `reference` set to that name, or read the `human-voice://references/<name>.md`
  resource.
- File edits use whatever file tools your client gives you, under the same rule:
  never overwrite a file that is not recoverable without keeping a copy.
"""

TOOLS = [
    {
        "name": "lint_prose",
        "description": "Score prose for AI-writing tells with the human-voice floor linter "
                       "(shape, rhythm, syntax, substance, diction). Lower is better: under 5 "
                       "is clean, 15+ is a strong tell. Deterministic, offline.",
        "inputSchema": {"type": "object", "properties": {
            "text": {"type": "string", "description": "the prose to score"},
            "register": {"type": "string", "description": REGISTERS_HINT, "default": "auto"},
            "dialect": {"type": "string", "enum": ["american", "british"]},
        }, "required": ["text"]},
    },
    {
        "name": "check_invariants",
        "description": "Compare a rewrite against its original and list numbers, code, links "
                       "and citations that were lost or introduced. Run before returning any "
                       "rewrite; a non-empty result means a fact changed.",
        "inputSchema": {"type": "object", "properties": {
            "original": {"type": "string"}, "rewrite": {"type": "string"},
        }, "required": ["original", "rewrite"]},
    },
    {
        "name": "get_skill",
        "description": "Return the human-voice instructions (how to rewrite or generate prose "
                       "that does not read as AI-written), or one reference file. Call this "
                       "first when asked to humanize, de-AI, or de-slop writing.",
        "inputSchema": {"type": "object", "properties": {
            "reference": {"type": "string", "description":
                          "a reference file name, e.g. ai-tells.md; omit for the main skill"},
            "include_references": {"type": "string", "enum": ["none", "core", "all"],
                                   "default": "none"},
        }},
    },
    {
        "name": "humanize",
        "description": "Delegate a full rewrite loop to a configured LLM provider (lint, "
                       "rewrite, re-lint, invariant check, up to N passes). Needs a provider "
                       "API key in the server's environment, or a local model.",
        "inputSchema": {"type": "object", "properties": {
            "text": {"type": "string"},
            "model": {"type": "string", "description": "provider/model, e.g. openai/gpt-5.6; "
                      "omit to use HUMAN_VOICE_MODEL or the first configured provider"},
            "mode": {"type": "string", "enum": ["fix", "generate"], "default": "fix"},
            "register": {"type": "string", "description": REGISTERS_HINT, "default": "auto"},
            "depth": {"type": "string", "enum": ["quick", "standard", "full"], "default": "standard"},
            "context": {"type": "string", "description": "real author material the rewrite may use"},
            "max_passes": {"type": "integer", "default": 3, "minimum": 1, "maximum": 6},
        }, "required": ["text"]},
    },
    {
        "name": "verify_detector",
        "description": "Ask a real external AI detector (GPTZero, Originality, Sapling, or "
                       "Winston, whichever key is configured) whether text still reads as AI.",
        "inputSchema": {"type": "object", "properties": {
            "text": {"type": "string"},
            "max_p_ai": {"type": "number", "default": 0.10},
        }, "required": ["text"]},
    },
]

PROMPTS = [{
    "name": "human-voice",
    "description": "Rewrite a draft (or generate from a brief) so it reads as written by a "
                   "skilled person, without changing any fact.",
    "arguments": [
        {"name": "text", "description": "the draft, or a brief with mode=generate", "required": True},
        {"name": "mode", "description": "fix (default) or generate", "required": False},
        {"name": "register", "description": REGISTERS_HINT, "required": False},
    ],
}]


def _refs():
    d = os.path.join(prompt.SKILL_DIR, "references")
    return sorted(n for n in os.listdir(d) if n.endswith(".md")) if os.path.isdir(d) else []


def _skill_text(include="none"):
    body = prompt.read_skill()
    parts = [MCP_ADAPTER.strip(), "---", body]
    for name, ref in prompt.read_references(prompt.REFERENCE_SETS.get(include, ())):
        parts += ["---", "# Reference: references/%s\n\n%s" % (name, ref)]
    return "\n\n".join(parts)


def _text(payload):
    return {"content": [{"type": "text", "text": payload if isinstance(payload, str)
                         else json.dumps(payload, indent=2)}]}


def call_tool(name, args):
    if name == "lint_prose":
        text = args.get("text") or ""
        register = args.get("register") or "auto"
        patterns, _ = load_linter_config()
        inferred = None
        if register == "auto":
            from human_voice_linter import infer_register
            register, conf, why = infer_register(text)
            inferred = "register inferred: %s (confidence %.2f; %s)" % (
                register, conf, "; ".join(why) or "no cue")
        summary, report = lint_text(text, register, patterns, args.get("dialect"), "text")
        head = (inferred + "\n") if inferred else ""
        return _text("%s%s\n\nsummary: %s" % (head, report, json.dumps(
            {k: summary[k] for k in ("score", "verdict", "words", "categories")})))
    if name == "check_invariants":
        res = invariants.compare(args.get("original") or "", args.get("rewrite") or "")
        lines = invariants.summarize(res)
        return _text("invariants: %s\n%s\n\n%s" % (
            "ok" if res["ok"] else "CHANGED", "\n".join(lines), json.dumps(res, indent=2)))
    if name == "get_skill":
        ref = args.get("reference")
        if ref:
            ref = os.path.basename(ref if ref.endswith(".md") else ref + ".md")
            found = prompt.read_references([ref])
            if not found:
                return dict(_text("no reference %r; available: %s" % (ref, ", ".join(_refs()))),
                            isError=True)
            return _text(found[0][1])
        return _text(_skill_text(args.get("include_references") or "none"))
    if name == "humanize":
        result = humanize(args.get("text") or "", model=args.get("model"),
                          mode=args.get("mode") or "fix", register=args.get("register") or "auto",
                          depth=args.get("depth") or "standard", context=args.get("context"),
                          max_passes=int(args.get("max_passes") or 3))
        summary = {k: result[k] for k in ("provider", "model", "accepted", "register",
                                          "invariants", "best_pass")}
        summary["score_before"] = (result["before"] or {}).get("score")
        summary["score_after"] = result["after"]["score"]
        return _text("%s\n\n---\n%s\n\n---\n%s" % (result["rewrite"], result["audit"],
                                                   json.dumps(summary, indent=2)))
    if name == "verify_detector":
        from human_voice_linter import detector as D
        var, key = D.find_api_key()
        if not key:
            return _text("verification: UNAVAILABLE. No detector key set (%s). This is not a "
                         "pass; report the gate as not run." % ", ".join(D.KEY_ENV_VARS))
        p = D.probe(args.get("text") or "", key, var)
        label, _clear = D.verdict(p, float(args.get("max_p_ai") or D.DEFAULT_MAX_P_AI))
        return _text("verification: %s  p(AI)=%.3f  (%s)" % (label.upper(), p,
                                                             D.DETECTORS[var]["name"]))
    raise KeyError(name)


def handle(msg):
    """Response dict for one JSON-RPC message, or None for a notification."""
    method = msg.get("method")
    mid = msg.get("id")
    params = msg.get("params") or {}
    if mid is None:
        return None  # notifications (initialized, cancelled, ...) need no reply

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def fail(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    try:
        if method == "initialize":
            asked = params.get("protocolVersion")
            return ok({"protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                       "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                       "serverInfo": SERVER_INFO,
                       "instructions": "Use get_skill before rewriting or drafting prose that "
                                       "must not read as AI-written; use lint_prose and "
                                       "check_invariants on every rewrite."})
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": TOOLS})
        if method == "tools/call":
            name = params.get("name")
            if name not in {t["name"] for t in TOOLS}:
                return fail(-32602, "unknown tool %r" % name)
            try:
                return ok(call_tool(name, params.get("arguments") or {}))
            except Exception as exc:  # tool failures are results, not protocol errors
                return ok(dict(_text("%s: %s" % (type(exc).__name__, exc)), isError=True))
        if method == "prompts/list":
            return ok({"prompts": PROMPTS})
        if method == "prompts/get":
            if params.get("name") != "human-voice":
                return fail(-32602, "unknown prompt %r" % params.get("name"))
            a = params.get("arguments") or {}
            task = prompt.build_task(a.get("text", ""), a.get("mode") or "fix",
                                     a.get("register") or "auto")
            return ok({"description": PROMPTS[0]["description"], "messages": [
                {"role": "user", "content": {"type": "text", "text": "%s\n\n---\n\n%s" % (
                    _skill_text("none"), task)}}]})
        if method == "resources/list":
            res = [{"uri": "human-voice://SKILL.md", "name": "SKILL.md",
                    "mimeType": "text/markdown", "description": "the human-voice skill"}]
            res += [{"uri": "human-voice://references/%s" % n, "name": n,
                     "mimeType": "text/markdown"} for n in _refs()]
            return ok({"resources": res})
        if method == "resources/read":
            uri = params.get("uri", "")
            if uri == "human-voice://SKILL.md":
                text = prompt.read_skill()
            elif uri.startswith("human-voice://references/"):
                name = os.path.basename(uri)
                found = prompt.read_references([name]) if name in _refs() else []
                if not found:
                    return fail(-32002, "resource not found: %s" % uri)
                text = found[0][1]
            else:
                return fail(-32002, "resource not found: %s" % uri)
            return ok({"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]})
        return fail(-32601, "method not found: %s" % method)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        return fail(-32603, "%s: %s" % (type(exc).__name__, exc))


def serve(stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32700, "message": "parse error"}}
        else:
            if isinstance(msg, list):  # batches (2025-03-26)
                replies = [r for r in (handle(m) for m in msg if isinstance(m, dict)) if r]
                reply = replies or None
            else:
                reply = handle(msg) if isinstance(msg, dict) else None
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


def main():
    try:
        serve()
    except KeyboardInterrupt:
        pass
    return 0


__all__ = ["TOOLS", "PROMPTS", "handle", "call_tool", "serve", "main"]
