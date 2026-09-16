"""cli — `humanize.py`: the human-voice rewrite loop against any LLM provider."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

from . import prompt
from .loop import DEFAULT_TARGET, humanize
from .providers import PROVIDERS, ProviderError, describe_providers, resolve

EXIT_ACCEPTED, EXIT_NOT_ACCEPTED, EXIT_ERROR = 0, 1, 2

EPILOG = """\
examples:
  humanize.py draft.md                                  # first provider with a key set
  humanize.py draft.md -m anthropic/claude-sonnet-5 -o draft.human.md
  humanize.py draft.md -m openai/gpt-5.6 --in-place
  humanize.py draft.md -m gemini/gemini-3.8-flash --register marketing
  humanize.py draft.md -m ollama/qwen3:32b --references none
  humanize.py brief.txt --generate -m xai/grok-4.6 --context notes.md
  humanize.py --print-prompt chat > human-voice-system-prompt.md
  humanize.py --list-providers

exit: 0 a pass met every gate, 1 best rewrite returned but a gate was missed,
      2 configuration or provider error.
"""


def build_parser():
    ap = argparse.ArgumentParser(
        prog="humanize.py", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Rewrite or generate prose with the human-voice skill on any LLM: "
                    "Anthropic, OpenAI, Gemini, Bedrock, Vertex, Azure, Mistral, xAI, "
                    "DeepSeek, Groq, OpenRouter, Together, Fireworks, Cohere, Ollama, "
                    "LM Studio, or any OpenAI-compatible server.",
        epilog=EPILOG)
    ap.add_argument("input", nargs="?", help="file to rewrite (or a brief with --generate); - for stdin")
    m = ap.add_argument_group("model")
    m.add_argument("-m", "--model", help="provider/model, a bare model id, or omit to use "
                   "HUMAN_VOICE_MODEL or the first provider with a key set")
    m.add_argument("--base-url", help="override the provider endpoint (proxies, gateways, "
                   "self-hosted OpenAI-compatible servers)")
    m.add_argument("--max-tokens", type=int, help="output token budget per call")
    m.add_argument("--temperature", type=float,
                   help="sampling temperature (omitted by default; reasoning models reject it)")
    m.add_argument("--references", choices=sorted(prompt.REFERENCE_SETS), default="core",
                   help="reference files appended to the prompt (default core, ~30k tokens "
                   "total; use none for small local context windows)")
    t = ap.add_argument_group("task")
    t.add_argument("--generate", action="store_true", help="draft new copy from a brief")
    t.add_argument("--register", default=None,
                   help="technical, business, marketing, academic, casual, creative, email, "
                   "release_notes, ux_microcopy, tutorial, or auto (default auto or .humanvoicerc)")
    t.add_argument("--depth", choices=("quick", "standard", "full"), default="standard")
    t.add_argument("--dialect", choices=("american", "british"))
    t.add_argument("--context", action="append", metavar="FILE",
                   help="real author material the rewrite may draw on (repeatable)")
    g = ap.add_argument_group("gates")
    g.add_argument("--passes", type=int, default=3, help="max rewrite passes (default 3)")
    g.add_argument("--target", type=float, default=DEFAULT_TARGET,
                   help="accept at or under this floor score (default %(default)s)")
    g.add_argument("--verify", action="store_true",
                   help="also gate on an external detector (needs GPTZERO_API_KEY or similar)")
    g.add_argument("--max-p-ai", type=float, default=0.10)
    o = ap.add_argument_group("output")
    o.add_argument("-o", "--output", help="write the rewrite here (default stdout)")
    o.add_argument("--in-place", action="store_true",
                   help="overwrite the input file (a .bak is kept unless git tracks it)")
    o.add_argument("--audit", metavar="FILE", help="write the audit here (default stderr)")
    o.add_argument("--json", action="store_true", help="print the full result as JSON")
    o.add_argument("-q", "--quiet", action="store_true", help="no progress lines")
    x = ap.add_argument_group("inspect")
    x.add_argument("--print-prompt", nargs="?", const="chat", choices=("chat", "api"),
                   help="print the compiled system prompt and exit (chat: paste into "
                   "ChatGPT, Gemini, a Claude project; api: what this tool sends)")
    x.add_argument("--list-providers", action="store_true",
                   help="show every provider, its default model, and whether it is configured")
    x.add_argument("--which", action="store_true",
                   help="print the provider/model that would be used, and exit")
    return ap


def _read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _git_tracked(path):
    git = shutil.which("git")
    if not git:
        return False
    d = os.path.dirname(os.path.abspath(path))
    try:
        return subprocess.run([git, "ls-files", "--error-unmatch", os.path.basename(path)],
                              cwd=d, capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def _write(path, text):
    tmp = path + ".hv-tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    os.replace(tmp, path)


def main(argv=None):
    args = build_parser().parse_args(argv)
    err = sys.stderr

    if args.list_providers:
        rows = describe_providers()
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        width = max(len(r["provider"]) for r in rows)
        mw = max(len(r["default_model"]) for r in rows)
        for r in rows:
            print("%-*s  %-*s  %s" % (width, r["provider"], mw, r["default_model"], r["status"]))
        return 0

    if args.print_prompt:
        sys.stdout.write(prompt.build_system_prompt(args.print_prompt, args.references))
        return 0

    try:
        if args.which:
            provider, model = resolve(args.model)
            print("%s/%s" % (provider, model))
            return 0
        if not args.input:
            build_parser().print_usage(err)
            err.write("error: an input file (or -) is required\n")
            return EXIT_ERROR
        if args.in_place and (args.input == "-" or args.generate):
            err.write("error: --in-place needs a file to fix\n")
            return EXIT_ERROR
        text = _read(args.input)
        context = "\n\n".join(_read(p) for p in (args.context or [])) or None
        log = None if args.quiet else (lambda msg: err.write("human-voice: %s\n" % msg))
        if log:
            provider, model = resolve(args.model)
            log("model: %s/%s (%s)" % (provider, model, PROVIDERS[provider]["label"]))
        result = humanize(
            text, model=args.model, mode="generate" if args.generate else "fix",
            register=args.register, depth=args.depth, dialect=args.dialect,
            context=context, max_passes=max(1, args.passes), target_score=args.target,
            references=args.references, verify=args.verify, max_p_ai=args.max_p_ai,
            max_tokens=args.max_tokens, temperature=args.temperature,
            base_url=args.base_url,
            path_hint=None if args.input == "-" else args.input,
            source_name="pasted text" if args.input == "-" else args.input, log=log)
    except (ProviderError, ValueError, OSError) as exc:
        err.write("human-voice: error: %s\n" % exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        return 130

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.in_place:
            if not _git_tracked(args.input):
                shutil.copyfile(args.input, args.input + ".bak")
                if log:
                    log("not tracked by git; original kept at %s.bak" % args.input)
            _write(args.input, result["rewrite"])
        elif args.output:
            _write(args.output, result["rewrite"])
        else:
            sys.stdout.write(result["rewrite"].rstrip("\n") + "\n")
        if args.audit:
            _write(args.audit, result["audit"])
        elif not args.quiet and result["audit"]:
            err.write("\n%s\n" % result["audit"])

    if log:
        before = result["before"]
        after = result["after"]
        inv = result["invariants"]
        log("score %s -> %.1f [%s]   invariants %s   passes %d   %s" % (
            "%.1f" % before["score"] if before else "n/a", after["score"], after["verdict"],
            "ok" if inv["invariants_ok"] else "FAILED", len(result["passes"]),
            "ACCEPTED" if result["accepted"] else "NOT ACCEPTED (best pass returned)"))
        if not inv["invariants_ok"]:
            for kind, items in sorted(inv["missing"].items()):
                log("  missing %s: %s" % (kind, ", ".join(items[:8])))
            for kind, items in sorted(inv["added"].items()):
                log("  introduced %s: %s" % (kind, ", ".join(items[:8])))
        if inv["placeholders"]:
            log("  placeholders for the author: %s" % ", ".join(inv["placeholders"]))
    return EXIT_ACCEPTED if result["accepted"] else EXIT_NOT_ACCEPTED


__all__ = ["main", "build_parser"]
