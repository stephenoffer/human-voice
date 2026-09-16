# Install

[Docs home](README.md) · [Getting started](getting-started.md) · **Install** · [Usage](usage.md) · [Examples](examples.md) · [Evidence](evidence.md) · [Comparison](comparison.md)

Every route below runs the same [SKILL.md](../skills/human-voice/SKILL.md), so a
rewrite follows the same rules whichever agent or model does the writing.
Everything runs on the Python standard library. There's nothing to `pip install`.

- [Coding agents](#coding-agents)
- [Any model through its API](#any-model-through-its-api)
- [MCP clients](#mcp-clients)
- [Chat apps](#chat-apps)
- [Troubleshooting](#troubleshooting)

## Coding agents

Claude Code installs from its plugin marketplace:

```
/plugin marketplace add stephenoffer/human-voice
/plugin install human-voice@human-voice
```

Every other agent takes the installer, which finds what you have:

```bash
git clone https://github.com/stephenoffer/human-voice.git && cd human-voice
python3 install.py --list              # what it knows about and what it found
python3 install.py                     # every agent it detected, user scope
python3 install.py codex windsurf      # only these
python3 install.py --project ~/my-repo # commit the skill so the whole team gets it
python3 install.py --link              # symlink instead of copy; `git pull` updates it
```

| Agent | User scope | Project scope |
|---|---|---|
| Codex, Gemini CLI, Cursor, Copilot, opencode | `~/.agents/skills/` | `.agents/skills/` |
| Claude Code (also read by Cursor, Copilot, opencode) | `~/.claude/skills/` | `.claude/skills/` |
| Windsurf | `~/.codeium/windsurf/skills/` | `.windsurf/skills/` |
| Cline | `~/.cline/skills/` | `.cline/skills/` |
| Aider (no skill support) | n/a | `CONVENTIONS.human-voice.md`, loaded with `aider --read` |

Several agents read more than one of those folders, and two copies of a skill
load as two skills. So the installer writes the fewest copies that cover what you
asked for. `--exact` puts one copy in each agent's own folder instead. Nothing is
overwritten without `--force`.

To update later, pull and reinstall: `git pull && python3 install.py --force`. If
you installed with `--link`, the pull alone is enough, since the agents read your
checkout directly. Uninstalling means deleting the `human-voice` folder from the
directories above.

**Gemini CLI** can also take the whole repo as an extension, which bundles the
skill and the MCP server:

```bash
gemini extensions install https://github.com/stephenoffer/human-voice
```

## Any model through its API

`humanize.py` runs the skill's procedure when there's no agent to run it. It
lints the draft, sends the skill and the report to the model, then lints the
rewrite and checks every number, link, code span and citation against the source.
A pass that falls short goes back to the model with the numbers. The loop stops
when a pass is clean with its facts intact, after three passes, or when two
passes in a row fail to improve.

```bash
export ANTHROPIC_API_KEY=...
python3 skills/human-voice/scripts/humanize.py draft.md -o draft.human.md
```

With no `-m`, it uses `HUMAN_VOICE_MODEL`, and failing that the first provider it
finds a key for. A bare model id works when its prefix names the vendor
(`claude-*`, `gpt-*`, `gemini-*`, `grok-*`). Anything else takes
`provider/model`.

| Provider | Model string | Needs |
|---|---|---|
| Anthropic | `anthropic/claude-sonnet-5` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai/gpt-5.6` | `OPENAI_API_KEY` |
| Google Gemini | `gemini/gemini-3.8-flash` | `GEMINI_API_KEY` |
| Google Vertex AI | `vertex/gemini-3.8-flash`, `vertex/claude-sonnet-5` | `GOOGLE_CLOUD_PROJECT`, plus gcloud or `VERTEX_ACCESS_TOKEN` |
| Amazon Bedrock | `bedrock/<model or inference profile id>` | AWS keys, `AWS_REGION` |
| Azure OpenAI | `azure/<deployment>` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| xAI | `xai/grok-4.6` | `XAI_API_KEY` |
| Mistral | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| DeepSeek | `deepseek/deepseek-v4-pro` | `DEEPSEEK_API_KEY` |
| Cohere | `cohere/command-a-plus-05-2026` | `COHERE_API_KEY` |
| Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Together | `together/<model>` | `TOGETHER_API_KEY` |
| Fireworks | `fireworks/<model>` | `FIREWORKS_API_KEY` |
| OpenRouter | `openrouter/<vendor>/<model>` | `OPENROUTER_API_KEY` |
| Ollama, LM Studio | `ollama/<model>`, `lmstudio/<model>` | nothing, runs locally |
| vLLM, LiteLLM, TGI or any OpenAI-compatible server | `compat/<model>` with `--base-url` | whatever the server wants |

| Flag | Does |
|---|---|
| `-m provider/model` | pick the model |
| `-o FILE` / `--in-place` | write the rewrite to a file, or over the input (a `.bak` is kept unless git tracks it) |
| `--generate` | draft new copy from a brief instead of rewriting |
| `--context FILE` | real material the rewrite may draw on (repeatable) |
| `--register`, `--depth`, `--dialect` | same meanings as in the skill ([Usage](usage.md)) |
| `--passes N`, `--target SCORE` | loop limit (default 3) and acceptance score (default 5) |
| `--verify` | also gate on an external detector |
| `--json` | every pass's score, invariant diff and token usage |
| `--references none\|core\|all` | how much of the reference material to send (default core) |
| `--print-prompt chat\|api`, `--which`, `--list-providers` | inspect without calling a model |

Exit codes: 0 when a pass met every gate, 1 when the best rewrite came back short
of one (it's still written, and stderr says which gate), 2 for a setup or
provider error.

From Python, import the same loop:

```python
import sys; sys.path.insert(0, "skills/human-voice/scripts")
from human_voice_llm import humanize, chat, lint_text

result = humanize(open("draft.md").read(), model="gemini/gemini-3.8-flash")
print(result["accepted"], result["before"]["score"], "->", result["after"]["score"])
print(result["rewrite"])
```

`chat(model, system, messages)` is one call to any provider, if you only want the
transport.

## MCP clients

`skills/human-voice/scripts/mcp_server.py` serves the skill over the Model
Context Protocol, on stdio. Your client's model does the writing. The server
gives it measurements it can't make by reading.

| Tool | Does |
|---|---|
| `get_skill` | the instructions, or one reference file |
| `lint_prose` | the floor score and every tell, with fixes |
| `check_invariants` | numbers, links, code and citations lost or added by a rewrite |
| `verify_detector` | asks GPTZero, Originality, Sapling or Winston, if a key is set |
| `humanize` | hands the whole loop to a second model through the provider layer |

The installer prints the exact config for your client:

```bash
python3 install.py --mcp cursor
```

Clients: `claude-code`, `claude-desktop`, `cursor`, `vscode`, `windsurf`, `cline`,
`gemini`, `codex`, `opencode`, `zed`. The config points at this checkout, so keep
it where it is. Move the folder and the client can't start the server until you
rerun the command. For Cursor the output looks like this, with
your own path:

```json
{
  "mcpServers": {
    "human-voice": {
      "command": "python3",
      "args": ["/path/to/human-voice/skills/human-voice/scripts/mcp_server.py"]
    }
  }
}
```

## Chat apps

```bash
python3 skills/human-voice/scripts/humanize.py --print-prompt chat > human-voice.md
```

That file is the skill compiled for a model with no tools. Add it to a ChatGPT
project or custom GPT, a Gemini Gem or a Claude project. It follows the same
rules, uses the no-tool checklist where an agent would run the linter, and says
so in its audit rather than inventing a score.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `no model given and no provider key found` | export a key from the table above, or pass `-m ollama/<model>` |
| HTTP 404 from the provider | the default model id went stale. Pass a current one with `-m` or `HUMAN_VOICE_MODEL` |
| A local model returns half a rewrite or ignores the format | its context window is too small for the ~30k-token prompt. Use `--references none`, or raise the context length (Ollama truncates silently) |
| The skill loads twice in Cursor or Copilot | you have copies in both `.agents/skills` and `.claude/skills`. Delete one |
| `python3` not found on Windows | use `py` instead |
