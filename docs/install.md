# Installing human-voice

[README](../README.md) · [Install](install.md) · [Usage](usage.md) · [Why it works](evidence.md) · [Comparison](comparison.md)

Pick the row that matches how you work. Every path runs the same SKILL.md, so a
rewrite follows the same rules whichever model does the writing.

| You use | Do this |
|---|---|
| Claude Code | `/plugin marketplace add stephenoffer/human-voice`, then `/plugin install human-voice@human-voice` |
| Codex, Cursor, Copilot, Gemini CLI, Windsurf, Cline, opencode | `python3 install.py` (detects them) |
| Gemini CLI, as an extension | `gemini extensions install https://github.com/stephenoffer/human-voice` |
| Aider | `python3 install.py aider --project .`, then `aider --read CONVENTIONS.human-voice.md` |
| Any MCP client | `python3 install.py --mcp <client>` prints the config |
| An API key and no agent | `python3 skills/human-voice/scripts/humanize.py draft.md` |
| ChatGPT, Gemini or Claude in the browser | paste the output of `humanize.py --print-prompt chat` into a project or custom instructions |

## Coding agents

```bash
git clone https://github.com/stephenoffer/human-voice.git
cd human-voice
python3 install.py --list              # what it knows about and what it found
python3 install.py                     # every agent it detected, user scope
python3 install.py codex windsurf      # only these
python3 install.py --project ~/my-repo # commit the skill so the whole team gets it
python3 install.py --link              # symlink instead of copy; `git pull` updates it
```

Most of these agents read a shared directory as well as their own. Codex, Gemini
CLI, Cursor, Copilot and opencode all scan `.agents/skills`. Cursor, Copilot and
opencode also scan `.claude/skills`. So the installer writes the fewest copies
that cover what you asked for, because two copies of one skill load as two
skills. `--exact` puts one copy in each agent's own folder instead. Nothing is
overwritten without `--force`, and `--dry-run` shows the plan first.

Invoke it as `/human-voice` where the agent has slash commands. Everywhere else,
ask for it: "humanize this", "de-slop the README", "draft the launch email in
human-voice".

## Any model through its API

`humanize.py` runs the skill's procedure itself, for when there is no agent to
run it: a CI job, a script, a batch of docs, a model you want to compare. It
lints the draft, sends the skill and the report to the model, then lints the
rewrite and checks every number, link, code span and citation against the source.
Anything that fell short goes back to the model with the numbers. The loop stops
when a pass is clean with its facts intact, after three passes, or when two
passes in a row fail to improve.

```bash
export ANTHROPIC_API_KEY=...          # or any key from the table below
python3 skills/human-voice/scripts/humanize.py draft.md -o draft.human.md
python3 skills/human-voice/scripts/humanize.py draft.md -m openai/gpt-5.6 --in-place
python3 skills/human-voice/scripts/humanize.py brief.md --generate --context notes.md
python3 skills/human-voice/scripts/humanize.py draft.md -m ollama/qwen3:32b --references none
python3 skills/human-voice/scripts/humanize.py --list-providers
```

With no `-m`, it uses `HUMAN_VOICE_MODEL`, and failing that the first provider it
finds a key for. A bare model id works when the prefix gives the vendor away
(`claude-*`, `gpt-*`, `gemini-*`, `grok-*`). Everything else takes a
`provider/model` string.

| Provider | Model string | Needs |
|---|---|---|
| Anthropic | `anthropic/claude-sonnet-5` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai/gpt-5.6` | `OPENAI_API_KEY` |
| Google Gemini | `gemini/gemini-3.8-flash` | `GEMINI_API_KEY` |
| Google Vertex AI | `vertex/gemini-3.8-flash`, `vertex/claude-sonnet-5` | `GOOGLE_CLOUD_PROJECT`, gcloud or `VERTEX_ACCESS_TOKEN` |
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
| Ollama, LM Studio | `ollama/<model>`, `lmstudio/<model>` | nothing; runs locally |
| vLLM, LiteLLM, TGI, any OpenAI-compatible server | `compat/<model>` with `--base-url` | whatever the server wants |

Four request formats cover all of it (OpenAI chat completions, Anthropic
messages, Gemini generateContent, Bedrock Converse), on the standard library and
nothing else. Bedrock requests are signed with SigV4 in about forty lines, checked
against botocore's signature in the tests. Default model ids go stale faster than
anything else in this repo. When one does, the provider's own 404 says so, and
`-m` or `HUMAN_VOICE_MODEL` fixes it without an upgrade.

The exit code tells a script what happened: 0 when a pass met every gate, 1 when
the best rewrite came back short of one (the rewrite is still written, and stderr
says which gate), 2 for a configuration or provider error. `--json` returns every
pass's score, invariant diff and token usage. Add `--verify` to gate on a real
detector too.

The whole skill plus its core references comes to about 30k tokens of system
prompt. Every hosted model above has room for that. A local model running a 4k or
8k context does not, and Ollama truncates without saying so. Use `--references
none` there, or raise the context length.

From Python:

```python
import sys; sys.path.insert(0, "skills/human-voice/scripts")
from human_voice_llm import humanize

result = humanize(open("draft.md").read(), model="gemini/gemini-3.8-flash")
print(result["rewrite"], result["accepted"], result["after"]["score"])
```

## MCP server

`skills/human-voice/scripts/mcp_server.py` puts the skill behind the Model Context
Protocol for any client that speaks it. It is standard-library Python over stdio.
The host model does the writing. The server gives it the measurements it can't
make by reading: `lint_prose`, `check_invariants` and `verify_detector`. It also
serves the skill (`get_skill`, plus every reference file as a resource) and a
`humanize` tool that hands the whole loop to a second model.

```bash
python3 install.py --mcp cursor          # or vscode, windsurf, cline, zed, opencode,
python3 install.py --mcp claude-desktop  # gemini, codex, claude-code
```

## Chat apps

```bash
python3 skills/human-voice/scripts/humanize.py --print-prompt chat > human-voice.md
```

That file is the skill compiled for a model with no tools. Upload it to a ChatGPT
project or custom GPT, a Gemini Gem, or a Claude project, and it follows the same
rules. It uses the no-tool checklist where the agent version would run the
linter, and its audit says so instead of inventing a score.
