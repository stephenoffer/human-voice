# Getting started

[Docs home](README.md) · **Getting started** · [Install](install.md) · [Usage](usage.md) · [Examples](examples.md) · [Evidence](evidence.md) · [Comparison](comparison.md)

Pick the path that matches where your writing happens. Each takes about five
minutes, and all three run the same rules.

| Path | Best for | Needs |
|---|---|---|
| [A. In your coding agent](#a-in-your-coding-agent) | docs, READMEs, PR descriptions, anything you write next to code | Claude Code, Codex, Cursor, Copilot, Gemini CLI, Windsurf, Cline, opencode or Aider |
| [B. With an API key](#b-with-an-api-key) | scripts, batch rewrites, comparing models | Python 3.8+ and a key for any major provider, or a local model |
| [C. As a CI gate](#c-as-a-ci-gate) | catching machine-shaped prose before it merges | Python 3.8+. No model, no key, no network |

## A. In your coding agent

You end up with a `/human-voice` command and an agent that writes in the voice
until you tell it to stop.

1. Install it. In Claude Code:

   ```
   /plugin marketplace add stephenoffer/human-voice
   /plugin install human-voice@human-voice
   ```

   In any other agent, clone the repo and let the installer find what you have:

   ```bash
   git clone https://github.com/stephenoffer/human-voice.git && cd human-voice
   python3 install.py --dry-run     # see the plan
   python3 install.py               # do it
   ```

2. Run it on a draft:

   ```
   /human-voice docs/launch-post.md
   ```

   No slash commands? Ask in plain words: "humanize docs/launch-post.md". To write
   something new, say what it's for:

   ```
   /human-voice generate register: email  "ask the team for 30 minutes to settle Q3 priorities"
   ```

3. Read the audit that comes back with the rewrite. This is the template from
   [SKILL.md](../skills/human-voice/SKILL.md), trimmed:

   ```text
   ## Humanization Audit: docs/launch-post.md
   Register: marketing
   Depth: full
   Score: <before> → <after> [<band>]  (linter floor; not ground truth)
   ...
   Author material added: <specifics taken from the draft or from you, or "none">
   Detector gate: <clear|flagged|not run>
   Invariants preserved: numbers ✓  code ✓  links ✓  claims ✓
   Placeholders left for author: <every [SOURCE NEEDED], or "none">
   Residual risk: <why a skeptical reader might still flag it, or "none">
   Next: <the one thing to do now>
   ```

   Act on two lines. `Placeholders` marks each spot where the draft needed a fact
   nobody gave it. You fill those in, because the skill won't invent one. `Next`
   is the single thing left to do.

4. Keep writing. The voice stays on for the rest of the session, so the next
   document comes out the same way. Say "normal voice" to turn it off.

## B. With an API key

This path needs no agent. A script runs the rewrite loop against the model you
choose and checks every pass.

1. Set a key. The script uses the first one it finds:

   ```bash
   export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
                                  # MISTRAL_API_KEY, DEEPSEEK_API_KEY, OPENROUTER_API_KEY...
   ```

   No key? Run a local model with [Ollama](https://ollama.com) and pass
   `-m ollama/<model> --references none`.

2. Check what it will use:

   ```bash
   python3 skills/human-voice/scripts/humanize.py --which
   python3 skills/human-voice/scripts/humanize.py --list-providers
   ```

3. Rewrite a file:

   ```bash
   python3 skills/human-voice/scripts/humanize.py draft.md -o draft.human.md
   ```

   Progress goes to stderr: the starting score, each pass's score and fact check,
   then `ACCEPTED` or `NOT ACCEPTED (best pass returned)`. The exit code agrees.
   It's 0 when accepted, 1 when the best pass fell short of a gate, and 2 for a
   setup or provider error.

4. Try the variations:

   ```bash
   humanize.py draft.md -m openai/gpt-5.6 --in-place          # overwrite (keeps a .bak if untracked)
   humanize.py draft.md --register marketing --depth full      # force the genre, do everything
   humanize.py brief.md --generate --context notes.md          # draft new copy from real material
   humanize.py draft.md --json > result.json                   # every pass, score and diff
   ```

   `--context` is where specifics come from. The rewrite may use any fact in
   those files. A number, link or citation found in neither the draft nor the
   context fails the fact check, and that pass isn't accepted.

## C. As a CI gate

The linter alone is deterministic and free. It can't rewrite anything, but it
will stop a machine-shaped doc from merging.

1. Run the linter on something:

   ```bash
   python3 skills/human-voice/scripts/detect_ai_prose.py --register technical \
     skills/human-voice/examples/modern-ai-before.md
   ```

   Real output, trimmed:

   ```text
   score: 15.0 floor points  [strong-tell]  (lower is better; a FLOOR, not proof)
   rhythm:  CoV 0.33 (want >=0.40)   short<=8w 0.0 (want >=0.12)   mid-band 0.73 (want <=0.72)   mean 18.7 w

   Tells by category (4 total):
     sentence_shape       2
         only 0% of sentences are <=8 words (floor 12%)  -> cut in a short sentence. Like this one.
         73% of sentences sit in the 12-26 word band  -> push sentences out of the middle: some very short, some long
     burstiness           1
         sentence-length CoV 0.33 (floor 0.40)  -> mix short punches with long sentences
     paragraph_uniformity 1
         paragraph-length CoV 0.21 (floor 0.30)  -> vary paragraph length; AI drafts are suspiciously even
   ```

   Under 5 is clean. From 5 to 15 is worth a look. Anything higher is a strong
   tell.

2. Add a workflow:

   ```yaml
   # .github/workflows/prose.yml
   name: prose
   on: [pull_request]
   jobs:
     human-voice:
       runs-on: ubuntu-latest
       permissions:
         contents: read
         actions: read
         security-events: write      # lets findings appear as PR annotations
       steps:
         - uses: actions/checkout@v4
         - run: git clone --depth 1 https://github.com/stephenoffer/human-voice /tmp/human-voice
         - name: Lint docs
           run: >
             python3 /tmp/human-voice/skills/human-voice/scripts/detect_ai_prose.py
             --register auto --recursive --fail-over 5 --sarif docs/ README.md > prose.sarif
         - name: Show findings on the PR
           if: always()
           uses: github/codeql-action/upload-sarif@v3
           with:
             sarif_file: prose.sarif
   ```

   The job fails when any file scores over 5. The SARIF upload puts each finding
   on the line that caused it.

3. Tune it with a `.humanvoicerc` at the repo root:

   ```json
   {
     "register": "technical",
     "dialect": "american",
     "protected_terms": ["seamless handoff"],
     "thresholds": { "burstiness_cov_floor": 0.35 }
   }
   ```

   Product names and required jargon go in `protected_terms`, which the linter
   never flags. The rest is covered under
   [Configuration](usage.md#configuration).

## Where to next

The [examples](examples.md) show ten before/after pairs with live scores. For
modes, registers, autofix and how scoring works, read [Usage](usage.md). MCP
servers, chat apps, all seventeen providers and the Python API are in
[Install](install.md).
