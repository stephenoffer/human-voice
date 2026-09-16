#!/usr/bin/env python3
"""Install the human-voice skill into any AI coding agent, or wire up its MCP server.

The skill is a folder with a SKILL.md, the open Agent Skills format, so for most
agents installing it means copying one directory to the place that agent looks.
This script knows those places, so you do not have to.

    python3 install.py                       # every agent detected on this machine
    python3 install.py codex cursor          # just these (user scope)
    python3 install.py copilot --project .   # into a repo, for everyone who clones it
    python3 install.py --list                # agents, paths, and what is detected
    python3 install.py --mcp cursor          # print the MCP config for a client
    python3 install.py aider --project .     # agents without skills get a rules file

Standard library only. Nothing is overwritten without --force, and --dry-run
prints every action instead of taking it.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILL_SRC = os.path.join(ROOT, "skills", "human-voice")
SCRIPTS = os.path.join(SKILL_SRC, "scripts")
MCP_SCRIPT = os.path.join(SCRIPTS, "mcp_server.py")
HOME = os.path.expanduser("~")

# user: skills dir in $HOME. project: skills dir inside a repo. detect: a path whose
# existence means the agent is installed. Agents without skill support get `rules`.
AGENTS = {
    "claude": {"label": "Claude Code", "user": "~/.claude/skills", "project": ".claude/skills",
               "detect": "~/.claude"},
    "codex": {"label": "OpenAI Codex CLI", "user": "~/.agents/skills", "project": ".agents/skills",
              "detect": "~/.codex"},
    "gemini": {"label": "Google Gemini CLI", "user": "~/.gemini/skills", "project": ".gemini/skills",
               "detect": "~/.gemini"},
    "cursor": {"label": "Cursor", "user": "~/.cursor/skills", "project": ".cursor/skills",
               "detect": "~/.cursor"},
    "copilot": {"label": "GitHub Copilot (VS Code, CLI)", "user": "~/.copilot/skills",
                "project": ".github/skills", "detect": "~/.copilot"},
    "windsurf": {"label": "Windsurf", "user": "~/.codeium/windsurf/skills",
                 "project": ".windsurf/skills", "detect": "~/.codeium/windsurf"},
    "cline": {"label": "Cline", "user": "~/.cline/skills", "project": ".cline/skills",
              "detect": "~/.cline"},
    "opencode": {"label": "opencode", "user": "~/.config/opencode/skills",
                 "project": ".opencode/skills", "detect": "~/.config/opencode"},
    "agents": {"label": "Shared .agents/skills (read by Codex, Gemini CLI, Cursor, Copilot, opencode)",
               "user": "~/.agents/skills", "project": ".agents/skills", "detect": None},
    "aider": {"label": "Aider (no skills: a conventions file loaded with --read)",
              "rules": "CONVENTIONS.human-voice.md", "detect": "~/.aider.conf.yml"},
}

# Which agents scan each shared directory (both scopes). Installing once into a
# shared directory beats one copy per agent: several agents read more than one of
# these, and two copies of a skill load as two skills.
SHARED = (
    ("agents", {"agents", "codex", "gemini", "cursor", "copilot", "opencode"}),
    ("claude", {"claude", "cursor", "copilot", "opencode"}),
)

MCP_CLIENTS = ("claude-code", "claude-desktop", "cursor", "vscode", "windsurf", "cline",
               "gemini", "codex", "opencode", "zed")

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "*.hv-tmp")


def _say(msg):
    sys.stdout.write(msg + "\n")


def detected(name):
    d = AGENTS[name].get("detect")
    return bool(d) and os.path.exists(os.path.expanduser(d))


def plan(names, exact=False):
    """[(install_as, [agents it serves])]: the fewest directories covering `names`."""
    if exact:
        return [(n, [n]) for n in names]
    wanted = list(dict.fromkeys(names))
    steps = []
    for shared, readers in SHARED:
        served = [n for n in wanted if n in readers]
        if served:
            steps.append((shared, served))
            wanted = [n for n in wanted if n not in readers]
    return steps + [(n, [n]) for n in wanted]


def install_skill(name, project=None, force=False, link=False, dry=False):
    info = AGENTS[name]
    if "rules" in info:
        return install_rules(name, project, force, dry)
    base = os.path.join(os.path.abspath(project), info["project"]) if project else \
        os.path.expanduser(info["user"])
    dest = os.path.join(base, "human-voice")
    if os.path.lexists(dest):
        if os.path.realpath(dest) == os.path.realpath(SKILL_SRC):
            _say("  %-9s already linked at %s" % (name, dest))
            return True
        if not force:
            _say("  %-9s exists at %s (use --force to replace)" % (name, dest))
            return False
        _say("  %-9s replacing %s" % (name, dest))
        if not dry:
            if os.path.islink(dest) or os.path.isfile(dest):
                os.unlink(dest)
            else:
                shutil.rmtree(dest)
    verb = "link" if link else "copy"
    _say("  %-9s %s -> %s" % (name, verb, dest))
    if dry:
        return True
    os.makedirs(base, exist_ok=True)
    if link:
        os.symlink(SKILL_SRC, dest, target_is_directory=True)
    else:
        shutil.copytree(SKILL_SRC, dest, ignore=IGNORE)
    return True


def install_rules(name, project, force, dry):
    sys.path.insert(0, SCRIPTS)
    from human_voice_llm.prompt import build_system_prompt
    target_dir = os.path.abspath(project or os.getcwd())
    dest = os.path.join(target_dir, AGENTS[name]["rules"])
    if os.path.exists(dest) and not force:
        _say("  %-9s exists at %s (use --force to replace)" % (name, dest))
        return False
    _say("  %-9s write %s" % (name, dest))
    if not dry:
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(build_system_prompt("chat", "core"))
    if name == "aider":
        _say("            load it with: aider --read %s   (or add `read: [%s]` to "
             ".aider.conf.yml)" % (AGENTS[name]["rules"], AGENTS[name]["rules"]))
    return True


def mcp_config(client, python=None):
    """The exact snippet (or command) that registers the MCP server in `client`."""
    py = python or ("python" if os.name == "nt" else "python3")
    script = MCP_SCRIPT
    std = {"mcpServers": {"human-voice": {"command": py, "args": [script]}}}
    if client == "claude-code":
        return "claude mcp add human-voice -- %s %s" % (py, script)
    if client == "gemini":
        return ("gemini mcp add human-voice %s %s\n\n# or, installing the whole repo as an "
                "extension bundles the skill and the server:\n"
                "gemini extensions install https://github.com/stephenoffer/human-voice"
                % (py, script))
    if client == "codex":
        return ("codex mcp add human-voice -- %s %s\n\n# or in ~/.codex/config.toml:\n"
                "[mcp_servers.human-voice]\ncommand = %s\nargs = [%s]"
                % (py, script, json.dumps(py), json.dumps(script)))
    if client == "vscode":
        return "# .vscode/mcp.json\n" + json.dumps(
            {"servers": {"human-voice": {"type": "stdio", "command": py, "args": [script]}}}, indent=2)
    if client == "opencode":
        return "# opencode.json\n" + json.dumps(
            {"mcp": {"human-voice": {"type": "local", "command": [py, script]}}}, indent=2)
    if client == "zed":
        return "# Zed settings.json\n" + json.dumps(
            {"context_servers": {"human-voice": {"command": py, "args": [script]}}}, indent=2)
    where = {"claude-desktop": "claude_desktop_config.json (Settings > Developer > Edit Config)",
             "cursor": "~/.cursor/mcp.json, or .cursor/mcp.json in a project",
             "windsurf": "~/.codeium/windsurf/mcp_config.json",
             "cline": "cline_mcp_settings.json (MCP Servers > Configure)"}[client]
    return "# %s\n%s" % (where, json.dumps(std, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Install the human-voice skill into AI coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="agents: %s\nmcp clients: %s" % (", ".join(AGENTS), ", ".join(MCP_CLIENTS)))
    ap.add_argument("agents", nargs="*", help="agents to install into (default: every detected one)")
    ap.add_argument("--project", metavar="DIR",
                    help="install into this repo instead of your home directory")
    ap.add_argument("--all", action="store_true", help="every agent, detected or not")
    ap.add_argument("--link", action="store_true",
                    help="symlink to this checkout instead of copying (updates with git pull)")
    ap.add_argument("--force", action="store_true", help="replace an existing install")
    ap.add_argument("--dry-run", action="store_true", help="print actions without taking them")
    ap.add_argument("--exact", action="store_true",
                    help="one copy in each agent's own directory, instead of the fewest "
                    "shared directories that cover them (may load twice in some agents)")
    ap.add_argument("--list", action="store_true", help="show agents, paths and detection")
    ap.add_argument("--mcp", metavar="CLIENT", choices=MCP_CLIENTS,
                    help="print the MCP server config for a client and exit")
    ap.add_argument("--python", help="interpreter to put in MCP configs (default python3)")
    args = ap.parse_args(argv)

    if args.mcp:
        _say(mcp_config(args.mcp, args.python))
        return 0

    if args.list:
        for name, info in AGENTS.items():
            where = info.get("rules") or "%s  |  project: %s" % (info["user"], info["project"])
            _say("%-9s %-4s %s\n          %s" % (name, "yes" if detected(name) else "-",
                                               info["label"], where))
        return 0

    unknown = [a for a in args.agents if a not in AGENTS]
    if unknown:
        ap.error("unknown agent(s): %s. Known: %s" % (", ".join(unknown), ", ".join(AGENTS)))
    names = args.agents or (list(AGENTS) if args.all else
                            [n for n in AGENTS if detected(n) and "rules" not in AGENTS[n]])
    if not names:
        _say("No agents detected. Name one (e.g. `python3 install.py codex`), use --all, or "
             "run --list. Agent-less use: skills/human-voice/scripts/humanize.py.")
        return 1
    _say("human-voice -> %s scope%s" % ("project " + os.path.abspath(args.project) if args.project
                                        else "user", " (dry run)" if args.dry_run else ""))
    results = []
    for target, served in plan(names, args.exact):
        if served != [target]:
            _say("  %-9s serves: %s" % (target, ", ".join(served)))
        results.append(install_skill(target, args.project, args.force, args.link, args.dry_run))
    _say("")
    _say("Invoke it as /human-voice where the agent supports slash commands, or just ask to "
         "\"humanize\" a draft. For the linter as tools in any MCP client: "
         "python3 install.py --mcp <client>.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
