<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg">
    <img alt="human-voice: writing that reads like a person wrote it, every fact intact" src="docs/assets/logo-light.svg" width="640">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/stephenoffer/human-voice/actions/workflows/test.yml"><img alt="tests" src="https://github.com/stephenoffer/human-voice/actions/workflows/test.yml/badge.svg"></a>
  <img alt="Python 3.8+" src="https://img.shields.io/badge/python-3.8%2B-blue">
  <img alt="zero dependencies" src="https://img.shields.io/badge/dependencies-0-brightgreen">
  <img alt="any model" src="https://img.shields.io/badge/models-any%20major%20provider-4F46E5">
  <img alt="MIT license" src="https://img.shields.io/badge/license-MIT-green">
</p>

<p align="center">
  <a href="#see-it-work">See it work</a> ·
  <a href="#why-its-different">Why it's different</a> ·
  <a href="#proof">Proof</a> ·
  <a href="#get-started">Get started</a> ·
  <a href="docs/README.md">Docs</a>
</p>

Readers can tell when a machine wrote something. The giveaway stopped being
"delve" a while ago. A current model writes fluent prose with no filler at all,
and it still reads machine-made, because its sentences all land in the same
length band and its documents come out shaped like chat answers.

**human-voice** rewrites for what actually gives AI away. It fixes shape and
rhythm first, substance next, word choice last. Every number, link, code span and
citation gets checked against your source, so a rewrite can't quietly change a
fact. When a draft needs a specific it doesn't have, you get `[SOURCE NEEDED]`,
never an invented one.

It runs where you already work: Claude Code, Codex, Cursor, Copilot, Gemini CLI
and four more agents, or any major model through a plain API key.

## See it work

A paragraph from a real model. No filler, no hedging, not one em-dash, and it
still reads machine-made:

<table>
<tr>
<th width="50%" align="left">Before &nbsp;·&nbsp; <code>15.0 strong-tell</code></th>
<th width="50%" align="left">After &nbsp;·&nbsp; <code>0.0 clean</code></th>
</tr>
<tr>
<td valign="top">For most teams under ten million vectors, pgvector is the right starting point. You already have backups, monitoring, and access control for Postgres. Adding a second stateful system is a real cost that tends to get underestimated during the prototype phase, when the dataset is small and everything is fast.</td>
<td valign="top">Start with pgvector. Under about ten million vectors it wins, and the reason has nothing to do with recall benchmarks: it is the database you already back up, already monitor, already have access control for. A second stateful system is a cost that arrives months after the prototype, when the dataset is small and every query is fast and nobody is thinking about it.</td>
</tr>
</table>

The verdict moved to the front. Nothing was invented. The scores are for the
whole document each excerpt comes from
([before](skills/human-voice/examples/modern-ai-before.md),
[after](skills/human-voice/examples/modern-ai-after.md)), and the change that
earned them is one no word list can see:

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/rhythm-dark.svg">
    <img alt="Sentence lengths of the full example before and after. Before, every sentence falls between 10 and 29 words and 73% sit in the 12 to 26 word band. After, lengths run from 3 to 32 words and 42% are under 9 words." src="docs/assets/rhythm-light.svg" width="100%">
  </picture>
</p>

<details>
<summary><b>Another example: an email with the ask buried in paragraph three</b></summary>
<br>

<!-- human-voice: ignore-start -->

<table>
<tr>
<th width="50%" align="left">Before &nbsp;·&nbsp; <code>66.0 strong-tell</code></th>
<th width="50%" align="left">After &nbsp;·&nbsp; <code>0.0 clean</code></th>
</tr>
<tr>
<td valign="top">
<p>Subject: Touching Base re: Synergizing Our Q3 Deliverables</p>
<p>Hi team,</p>
<p>I hope this email finds you well! I wanted to circle back and touch base regarding our ongoing efforts to operationalize the Q3 roadmap. As we navigate this ever-evolving landscape, it's important to note that cross-functional alignment will be crucial to moving the needle on our key deliverables.</p>
<p>Furthermore, I believe we have a real opportunity to leverage our synergies and unlock some low-hanging fruit here. Moreover, it's worth noting that taking a holistic, best-in-class approach to our workflows could really empower the team to deliver actionable, high-impact results that drive value for all stakeholders.</p>
<p>Additionally, I think it would be mission-critical for us to align on next steps. Could we possibly find some time to sync and ideate on a path forward? I'm thinking maybe sometime next week if that works for everyone's schedule, but I'm flexible and happy to work around whatever is most convenient.</p>
<p>Looking forward to connecting and driving this forward together!</p>
<p>Best regards,<br>Jordan</p>
</td>
<td valign="top">
<p>Subject: 30 min next week to lock Q3 priorities?</p>
<p>Hi team,</p>
<p>We still haven't agreed on the top three Q3 deliverables. Engineering needs that list before they can plan sprints. Can we meet for 30 minutes next week to settle it?</p>
<p>I'm free Tuesday or Wednesday afternoon. If neither works, send me a couple of slots and I'll make one fit.</p>
<p>Before the call, it would help if each of you brought your one must-ship item for the quarter. We can sort priority from there.</p>
<p>Thanks,<br>Jordan</p>
</td>
</tr>
</table>

<!-- human-voice: ignore-end -->

The ask moved to the subject line. The rewrite runs 87 words against 169, and it
adds one thing the draft never had: what to bring to the meeting.

</details>

Ten pairs across genres, from landing pages to design docs, each with live scores:
**[docs/examples.md](docs/examples.md)**.

## Why it's different

Three kinds of tool get lumped together here. None of them does this job.

<!-- human-voice: ignore-start formatting -->

| | human-voice | Humanizer apps | Prose linters | AI detectors |
|---|:-:|:-:|:-:|:-:|
| Rewrites the text | ✓ | ✓ | ✗ | ✗ |
| Fixes structure and rhythm, not just words | ✓ | ◐ | ✗ | ✗ |
| Proves numbers, links and citations survived | ✓ | ✗ | ✗ | ✗ |
| Marks a missing fact instead of inventing one | ✓ | ✗ | ✗ | ✗ |
| Never uses homoglyphs, typos or synonym mangling | ✓ | ◐ | ✓ | ✓ |
| Writes to the genre: docs, marketing, email, fiction | ✓ | ◐ | ◐ | ✗ |
| Works with your model and your agent | ✓ | ✗ | ✓ | ✗ |
| Open source, free, runs offline | ✓ | ✗ | ✓ | ✗ |
| Published eval on prose a current model writes | ✓ | ✗ | ✗ | ◐ |

<!-- human-voice: ignore-end -->

✓ yes · ◐ partly or sometimes · ✗ no

**Humanizer apps sell a bypass rate.** When one detector vendor tested 19 of
them, five were caught every time. The ones that slip through do it by damaging
the text: odd synonyms, invisible characters, planted typos. That damage is its
own fingerprint, and the reader pays for it. human-voice has no bypass rate to
sell. It makes the prose better, which is the only version of the goal that lasts.

**Prose linters nitpick sentences.** proselint, write-good, Vale and Hemingway
catch weak words and long sentences. None has a theory of what gives a model
away, and none rewrites. human-voice ships a linter too (68 checks, zero
dependencies, ready for CI), but the linter is the floor, not the product.

**Detectors only judge.** They can't fix anything, and they misfire on careful
non-native writers. human-voice treats a detector as a gate, never as ground
truth. Point it at GPTZero, Originality, Sapling or Winston and the rewrite loops
until the text clears or stops improving.

The full survey covers about a hundred tools and papers, including what got
tested and thrown out: [docs/comparison.md](docs/comparison.md).

## How it works

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/loop-dark.svg">
    <img alt="The rewrite loop: draft, lint, rewrite with any model, then check score, facts and detector. A pass that falls short sends its report back to the model." src="docs/assets/loop-light.svg" width="100%">
  </picture>
</p>

The order comes from the evidence. Detectors respond to what instruction tuning
leaves behind, which is formatting habits and reply-shaped structure. Base models
that never went through it pass as human more than 96% of the time. So the
rewrite strips the assistant shape first: the heading every eighty words, the
bulleted answer, the "Key takeaways" close. Then it fixes the sentence-length
distribution. Diction comes last, because swapping "delve" for "explore" barely
moves anything. More in [docs/evidence.md](docs/evidence.md).

Longer documents get a structure pass before any sentence is touched. An agent
fills an outline to quota, so its overview comes back as the summary, the easy
section runs four hundred words while rollback gets one line, and one section
quotes config keys while the next could describe any system. The pass maps what
each section says, merges repeats, weighs sections by what a reviewer will ask,
and holds one depth throughout. It never deletes a claim that appears only once
without asking you first.

Genre comes first too. A technical report stays professional and a landing page
talks to "you". Ten register profiles share one core of tells that get fixed
everywhere.

## Proof

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/results-dark.svg">
    <img alt="Evaluation results. Current-model drafts flagged by the linter: 18 of 20 before, 0 of 20 after. Documents flagged by an independent AI classifier: 7 of 19 before, 0 of 19 after. Mean score 17.3 before, 1.3 after. Non-native writers wrongly flagged: 0 of 10." src="docs/assets/results-light.svg" width="100%">
  </picture>
</p>

The chart is generated from the committed eval output, and CI fails if those
metrics drift. The classifiers run locally on open models, with nothing sent
anywhere. The honest limits: n is small, the corpus has one author,
and no tool can promise a text is undetectable. This one checks instead of
promising. Details and caveats: [docs/evidence.md](docs/evidence.md).

## Get started

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/everywhere-dark.svg">
    <img alt="One SKILL.md reaches coding agents, model APIs, MCP clients and chat apps." src="docs/assets/everywhere-light.svg" width="100%">
  </picture>
</p>

**1. In your coding agent.** For Claude Code:

```
/plugin marketplace add stephenoffer/human-voice
/plugin install human-voice@human-voice
```

For Codex, Cursor, Copilot, Gemini CLI, Windsurf, Cline, opencode or Aider:

```bash
git clone https://github.com/stephenoffer/human-voice.git && cd human-voice
python3 install.py
```

Then point it at a draft, or just ask it to humanize something:

```
/human-voice docs/launch-post.md
```

You get the rewrite and an audit listing what changed, what it couldn't verify
and anything left for you to fill in. It stays on for the rest of the session.

**2. With any model's API.** No agent needed, which suits scripts and batch jobs.

```bash
export ANTHROPIC_API_KEY=...   # or OpenAI, Gemini, Bedrock, Mistral, xAI, a local Ollama...
python3 skills/human-voice/scripts/humanize.py draft.md -o draft.human.md
```

**3. As a CI gate.** No model, no key, no network.

```bash
python3 skills/human-voice/scripts/detect_ai_prose.py --register auto --recursive --fail-over 5 docs/
```

**[The getting-started guide](docs/getting-started.md)** walks through all three,
including a GitHub Actions workflow that annotates pull requests. MCP clients,
chat apps and all seventeen providers are in [docs/install.md](docs/install.md).

## What it won't do

It improves writing. It does not disguise machine text. No Unicode homoglyphs, no
zero-width characters, no deliberate typos, no synonym swaps that degrade meaning.
It never invents a fact or fakes a quote to seem human. Passing a detector is a
side effect of good writing, not the objective.

## Docs

| | |
|---|---|
| [Getting started](docs/getting-started.md) | three paths, five minutes each |
| [Examples](docs/examples.md) | ten before/after pairs with live scores |
| [Install](docs/install.md) | every agent, every provider, MCP, chat apps, Python |
| [Usage](docs/usage.md) | modes, registers, the linter, autofix, detector gate, scoring |
| [Evidence](docs/evidence.md) | what detectors respond to, and the measured results |
| [Comparison](docs/comparison.md) | humanizers, linters, detectors, and the full survey |
| [SKILL.md](skills/human-voice/SKILL.md) | the rules themselves |
| [Eval](eval/EVAL.md) | corpus, method, and every number |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Run
`make test`. The suite runs on Python 3.8 through 3.13 in CI. Regenerate the charts
with `python3 docs/assets/make_visuals.py`.

The v0.4 recalibration ranks tells by what readers *cite* as AI rather than what a
scanner *matches*. It draws on two MIT-licensed projects,
[vibecoded-design-tells](https://github.com/JCarterJohnson/vibecoded-design-tells)
and [oberskills](https://github.com/ryanthedev/oberskills), plus the ~90k-post
study behind them.

MIT licensed. See [LICENSE](LICENSE).
