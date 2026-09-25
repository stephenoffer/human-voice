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
  <a href="#how-it-works">How it works</a> ·
  <a href="#proof">Proof</a> ·
  <a href="#get-started">Get started</a> ·
  <a href="#why-its-different">Why it's different</a> ·
  <a href="docs/README.md">Docs</a>
</p>

Readers can tell when a machine wrote something. The giveaway stopped being
"delve" a while ago. A current model writes fluent prose with no filler in it at
all, and the writing still reads machine-made, because its sentences all land in
the same length band and its documents come out shaped like chat answers.

**human-voice** goes after the tells that survive a good model. Shape and rhythm
first, substance next, word choice last. Every number, link, code span and
citation gets checked against your source, so a rewrite can't quietly change a
fact. When a draft needs a specific it doesn't have, you get `[SOURCE NEEDED]`,
never an invented one.

It runs where you already work: Claude Code, Codex, Cursor, Copilot, Gemini CLI
and four more agents, or any major model through a plain API key.

## See it work

Start with the version everybody already recognizes. A landing page, drafted by a
model, rocket included:

<!-- human-voice: ignore-start -->

<table>
<tr>
<th width="50%" align="left">Before &nbsp;·&nbsp; <code>105.0 strong-tell</code></th>
<th width="50%" align="left">After &nbsp;·&nbsp; <code>0.0 clean</code></th>
</tr>
<tr>
<td valign="top">
<p><b>Unlock the Power of Effortless Team Collaboration</b></p>
<p>In today's fast-paced digital landscape, teams need a robust, seamless, and scalable solution that empowers them to work smarter, not harder. Our cutting-edge platform stands as a testament to innovation, delivering a comprehensive suite of best-in-class tools designed to move the needle for every stakeholder.</p>
<p>Furthermore, studies suggest that teams using collaborative software are significantly more productive. Moreover, it's worth noting that experts believe the future of work is already here. Additionally, our vibrant ecosystem of integrations leverages synergies to operationalize actionable workflows across the entire organization.</p>
<p>It's not just a tool — it's a complete solution. Whether you're a scrappy startup or a global enterprise, our revolutionary technology unlocks new opportunities and elevates your team to new heights. 🚀</p>
</td>
<td valign="top">
<p><b>Your team's work, in one place</b></p>
<p>The brief is sitting in somebody's email, the files are buried in a chat thread from last week, and the one person who knows which version is current is on holiday. That isn't a discipline problem, it's a handful of apps that can't see each other.</p>
<p>So put it all on one board instead: tasks, files, and the conversation about them, right where everyone is already looking. Move a due date and it moves on the calendar too. If you drop in a new version of a file, the person who was about to open the old one gets yours instead.</p>
<p>You keep what you already use. Slack, Drive and GitHub plug straight in, and the board works the same whether you're a startup or an enterprise.</p>
<p>Try it on one project. If people stop asking each other where things are, keep it.</p>
</td>
</tr>
</table>

<!-- human-voice: ignore-end -->

<!-- human-voice: ignore-start vague_attribution -->
164 words became 145, and the pitch got harder to argue with rather than louder.
Notice what is missing: "studies suggest that teams are significantly more
productive" is gone, not restated with a number attached, because there was no
study. That rule holds everywhere in the rewrite. Full pair:
[before](skills/human-voice/examples/marketing-before.md),
[after](skills/human-voice/examples/marketing-after.md).
<!-- human-voice: ignore-end -->

That one is easy, though. Any word list catches it, and nobody was fooled by it
in the first place. Here is the case that matters, five paragraphs on running
one-on-ones from a current model. No filler in it and not one em-dash, so every
word check in the linter passes. Read the sentence lengths instead. Fifteen
sentences running from nine words to twenty-nine, eleven of them in the middle of
that range, one tempo held for five paragraphs. Nothing lands.

<table>
<tr>
<th width="50%" align="left">Before &nbsp;·&nbsp; <code>15.0 strong-tell</code></th>
<th width="50%" align="left">After &nbsp;·&nbsp; <code>0.0 clean</code></th>
</tr>
<tr>
<td valign="top">
<p>The most common complaint about one-on-ones is that they turn into status meetings, which wastes a slot that both people already agreed to protect. A written update can be read at any time, so asking for it out loud converts a document into a slower document. The conversations that justify the meeting are the ones that would never appear in a written update at all.</p>
<p>Consistency matters more than any particular agenda, because a recurring thirty minutes that never moves builds the expectation that there will be a place to raise something.</p>
</td>
<td valign="top">
<p>Two rules cover most of what goes wrong. Never let it become a status meeting, and never cancel it.</p>
<p>The status version is the easier failure to notice, because you can feel it while it is happening. You are asking somebody to say out loud what they already wrote down, which converts a document into a slower document, and neither of you agreed to protect the slot for that. The conversations that justify the half hour are the ones that would never have appeared in a written update at all.</p>
</td>
</tr>
</table>

The rule moved to the front and a paragraph of fence-sitting went. Note what did
not happen: the rewrite is not written in shorter sentences. Its mean sentence
runs 19.3 words against the original's 19.1. The long ones got longer and the
spread opened up, which is the part a reader hears. Scores are for the whole
document each excerpt comes from
([before](skills/human-voice/examples/modern-ai-before.md),
[after](skills/human-voice/examples/modern-ai-after.md)), and the edit that
earned them is one no word list can see:

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/rhythm-dark.svg">
    <img alt="Sentence lengths of the full example before and after. Before, every sentence falls between 9 and 29 words and 73% sit in the 12 to 26 word band. After, lengths run from 6 to 41 words and only 31% stay in that band." src="docs/assets/rhythm-light.svg" width="100%">
  </picture>
</p>

<details>
<summary><b>A second case: a design doc where the sentences were never the problem</b></summary>
<br>

Ask a model for a design document and it fills an outline. Every heading gets
prose whether or not anything is known about it. You could rewrite every sentence
of this rate-limiter draft and still ship the same broken document, because the
damage is in the shape: nine headings covering two ideas, three of them parked
over six words apiece.

| Section in the draft | Words | What the structure pass did with it |
|---|--:|---|
| Overview | 51 | Folded into the opening. It said what the Summary said. |
| Background | 67 | Promoted to the first paragraph. A reviewer has to believe the problem first. |
| What is Rate Limiting? | 63 | Cut. Anyone reading a Lua sliding-window design knows. |
| Design | 166 | Split by what a reviewer asks next: how a request is counted, then what it costs. |
| Scalability | 124 | Two claims were only here, so they moved. The other 100-odd words say the design scales. |
| Security · Testing · Rollout | 6 each | Kept and flagged. Nobody may invent the plan behind them. |
| Summary | 58 | Cut. It restated the Overview, which restated the title. |

547 words became 304. Every commitment survived, including the three that have
nothing behind them:

> Three commitments have no detail behind them yet. Access to Redis will be
> restricted. The limiter will be tested. Rollout will be gradual. This document
> doesn't yet say how for any of them. `[OWNER NEEDED]`

Deleting those three stubs would have scored exactly as well and thrown away
three things the author promised. A structure pass never makes that call on its
own. The section map and the claim diff are in the
[notes](skills/human-voice/examples/architecture-notes.md), along with the
earlier draft of this rewrite that got it wrong.

</details>

Ten pairs across genres, from landing pages to academic papers, each scored
live: **[docs/examples.md](docs/examples.md)**.

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
distribution. Diction comes last, because swapping "leverage" for "use" barely
moves anything. More in [docs/evidence.md](docs/evidence.md).

Longer documents get a structure pass before a single sentence is touched. An
agent fills an outline to quota, so its overview comes back as the summary, the
easy section runs four hundred words while rollback gets one line, and one
section quotes config keys where the next could describe any system at all. The
pass maps what each section says, merges the repeats, weighs sections by what a
reviewer will ask, and holds one depth throughout. A claim that appears in only
one place is never deleted without asking you first.

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
anywhere. The honest limits: n is small, the corpus has one author, and no tool
can promise a text is undetectable. This one checks instead of promising. Details
and caveats: [docs/evidence.md](docs/evidence.md).

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
