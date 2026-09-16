# Changelog

All notable changes to the human-voice skill and its linter are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/); versions
track `.claude-plugin/plugin.json`.

## [0.9.0]

### Docs you can start from

The README leads with the evidence now: before and after side by side, the rhythm
chart, the comparison table and a three-path quick start. The detail moved into
`docs/`, which has a getting-started guide (an agent, an API key, or a CI gate
with a GitHub Actions workflow that annotates pull requests), a reorganized
install and usage reference, and an examples gallery. The gallery's scores come
from `docs/assets/make_visuals.py`, which also draws every chart from the
committed eval output. `make visuals-check` fails CI when either goes stale. The
palette moved from orange to indigo.

### Any agent, any model

Until this release the skill assumed Claude Code. The instructions never needed
Claude. The packaging did, and so did three frontmatter fields. This release
removes the assumption and changes none of the rules.

`SKILL.md` now passes the open Agent Skills spec. `when_to_use` merged into
`description`. `argument-hint` moved under `metadata`. `user-invokable` was
misspelled, so no agent ever read it, and it is gone. `skills-ref validate`
rejects unknown top-level fields, and at least one strict loader drops a skill
that fails it. A portability test now holds the frontmatter to the spec, so the
drift cannot come back quietly. The Workflow section also says how to find the
tools when the agent is not Claude Code: the script, then the MCP tools, then the
no-tool checklist.

`install.py` puts the skill where each agent looks: Claude Code, Codex, Gemini
CLI, Cursor, GitHub Copilot, Windsurf, Cline and opencode. Aider has no skill
support, so it gets a conventions file. The installer writes the fewest copies
that cover the request. Five of those agents read `.agents/skills` and three read
`.claude/skills`, and a naive copy per agent made Cursor load the skill twice.
`gemini-extension.json` makes the repository installable as a Gemini CLI
extension, with the MCP server bundled.

`humanize.py` runs the procedure against a model API directly, for CI and batch
jobs with no agent in the loop. It covers Anthropic, OpenAI, Gemini, Vertex AI,
Bedrock, Azure OpenAI, xAI, Mistral, DeepSeek, Cohere, Groq, Together, Fireworks,
OpenRouter, Ollama, LM Studio and any OpenAI-compatible server. That is four wire
formats on the standard library, with SigV4 checked against botocore. The loop
does what the agent would: lint, rewrite, re-lint, feed the report back. The
stopping condition is no longer the model's opinion of its own pass.

The loop adds one gate the agent version leaves to the model's diligence. A
deterministic invariant check compares numbers, versions, links, inline code,
code blocks and citations between the source and every rewrite. A pass that loses
one, or states one the source and `--context` never supplied, is not accepted
however well it scores. Run over the twenty `ai_modern` rewrites and the shipped
examples, it flags six of 29 pairs. Five are real: m13 dropped "March 13", and
four example "afters" carry author-supplied figures their "before" never had,
which is what the gate exists to question. The sixth was an HTML comment, and
comments are now ignored.

`mcp_server.py` serves the skill over MCP (stdio, standard library) with
`lint_prose`, `check_invariants`, `get_skill`, `humanize` and `verify_detector`,
plus every reference file as a resource. `humanize.py --print-prompt chat`
compiles the skill for ChatGPT projects, Gemini Gems and Claude projects.

### What a document spends its words on

Every check before this release read a sentence, a paragraph or the markdown on
the page. None read the document as a plan, which is where an agent-written report
still gives itself away once its sentences are clean. It says its point in the
overview, again in the body, and a third time in the summary. It gives the schema
four hundred words and rollback one line. One section quotes
`min.insync.replicas=2` and the next says the system scales to handle increased
load.

Three new checks in `architecture.py` cover it, all document-level and all
count-gated. `restatement` compares every sentence and list item with the ones in
other sections by stemmed content words and flags two or more near-duplicates at
2.5 per thousand words. Each finding names any number or word the repeat carries
that appears nowhere else in the source, and in that case the suggested fix is a
merge, not a cut. `section_balance` flags hollow stub sections beside a bloated
one, five or more sections of near-identical length, framing sections (overview,
background, summary) over 35% of the words with a recap among them, and four or
more lists all cut to one length. `depth_drift` measures checkable detail per
hundred words by section. It flags a long section built from abstract benefit
words beside a dense one, and beginner explanations in a technical document. A new
`structure:` metrics line reports the numbers behind all three.

The skill gained a matching step. The rewrite procedure now builds a section map
right after stripping the assistant shape, with a column for what each section
alone says. **A structure pass never cuts distinct information without approval.**
A fact, number, name, commitment, decision, caveat or owner that appears once moves
or gets reworded. If it should go, the agent asks, or leaves it and lists it under
the new "Proposed cuts" line in the audit. The hallucination pass restores
anything the architecture step dropped without that approval. The long version is
`references/content-architecture.md`, and `examples/architecture-*.md` walks a
design doc from 48.9 to 0.0 with every distinct claim accounted for. The first
draft of that example deleted a claim and reworded three commitments into
something the author never said, and the notes keep that mistake on the record.

Calibration came from 869 long, sectioned markdown files written by people (the
READMEs and manuals shipped with Homebrew formulae, npm packages, Rust crates and
Python packages). The first thresholds fired on 35% of them. What separated agent
output from human reference docs was specific, and each became a rule. Human
stubs are pointers carrying a link or a command. Human repeats are verbatim notes
or parallel API entries under code-named headings. Human conceptual sections talk
about particular things rather than in benefit words. Changelogs repeat by design.
At the shipped values the checks fire on 6 of the 869 (0.7%), section balance on
none. `eval/structure_eval.py --check` runs in CI over six authored positives and
64 in-repo negatives. `--human-dir` repeats the sweep on any local tree. The main
corpus is single-section, so no existing eval number moved.

Thresholds and weights live in the pattern file like every other knob.
`release_notes` and `ux_microcopy` mute `section_balance` through the new
`fixed_sections_ok` token. `tutorial` doubles the expert bar for explainers rather
than muting it.

### A negative set that was measuring the wrong text

CI had failed on every push since August, in one test: the stdlib-docstring
false-positive sweep. It scored `email` at 34.2 under pytest and 17.7 in a plain
run. The sweep collected every attribute's `__doc__`, and that picked up two kinds
of text the module never wrote. Imported modules contributed their own
docstrings, so the result depended on what happened to be imported first; pytest
imports nine `email` submodules. Constants answered with their type's docstring,
so `int`'s text was scored 172 times inside `sqlite3`. The sweep now reads
function and class docstrings only, each once, and gives the same answer in and
out of pytest on every Python from 3.8 to 3.13.

Honest input exposed a real false positive that the noise had hidden.
`ngram_repetition` owned 49% of all score points on human reference prose, almost
all of it two-word terms of art repeated the way principle 6 asks: "event loop",
"type variables". The check now counts trigrams only. The labeled eval and the
ablation are unchanged to four decimal places, so bigrams were catching nothing
the other checks missed. On clean input the sweep median fell from about 10 to
8.0 and the worst module from 18.6 to 15.3. Two smaller fixes rode along: the
sweep's minimum-length filter now counts the words the linter actually scored,
and `tests/test_llm.py` runs as a script, because `python -m unittest <path>`
fails to import it on Python 3.9.

## [0.8.0]

### What the other hundred tools do, and what survived the measurement

A survey of roughly a hundred overlapping tools and papers: the commercial
humanizer market, the open-source anti-slop projects, the prose linters, the
editing suites, the detectors, the stylometry literature, and Wikipedia's
WikiProject AI Cleanup catalog. The full write-up, with what each contributes and
where this skill is still behind, is
`skills/human-voice/references/competitive-landscape.md`.

The audit against Wikipedia's catalog, which is the best public field guide in
existence and is built from thousands of flagged drafts rather than from
intuition, found fifteen tells the pattern file did not cover. Four new checks
close most of them.

`llm_artifact` is the highest-precision check in the file and the only one where a
single instance is proof rather than evidence. It flags the residue a chat product
leaves in its own output: OpenAI citation wrappers and tool-call markers, Gemini
span tags, Grok render calls, Perplexity upload paths, lenticular-bracket
citations, chat-product tracking parameters on a URL, and unfilled template slots.
No writer types any of them. The corpus contains none, so this moves no eval
number and catches the commonest real-world case anyway, which is text pasted from
a chat window without being read.

`heading_structure` catches a skipped heading level, a second H1, a heading whose
whole body is the next heading, and a heading running straight into a bullet list.
`quote_style` catches curly and straight quotes mixed lopsidedly, which is usually
the seam where pasted output meets typed text. `copula_avoidance` is the mirror of
the existing `copula_density`: where 2023-era prose over-used "is", current output
reaches for `serves as`, `stands as`, `represents` or `boasts` instead.

Fifteen era-3 phrases were added to the existing lists, and `WH_CLEFT_RE` now
anchors to a clause boundary rather than a sentence start, so the commonest
narrative form of the pseudo-cleft is caught.

### Registers get a wider bar, not an exemption

The most consequential change, and it fixes a design fault rather than adding a
feature. A register that legitimately runs hot on a construction used to be
handled by muting the check outright, and muting throws away the signal above the
register's genuine tolerance along with the false positives below it. Creative
prose had `cleft` muted, so `m20_creative_arrival.md` could stack clefts at 10.5
per 1,000 words and score 3.3, while the human creative samples in the corpus
carry none at all. `register_thresholds` replaces the mute with a multiplier:
fiction gets 1.3x the bar. Two mute tokens, `cleft_ok` and `long_sentences_ok`,
were retired, and the config validator now checks the new table.

### Measured

On the honest separation number, `ai_modern/` against human, with the
false-positive gates unchanged:

| metric | 0.7.0 | 0.8.0 |
|---|---|---|
| ROC AUC vs human | 0.937 | **0.938** |
| recall @ 5.0 | 0.850 (17 of 20) | **0.900 (18 of 20)** |
| F1 @ 5.0 | 0.919 | **0.947** |
| precision @ 5.0 | 1.000 | 1.000 |
| human-subset FPR | 0.000 | 0.000 |
| ESL/formal-human FPR | 0.000 | 0.000 |
| over-corrected costume recall | 1.000 | 1.000 |
| stdlib-docstring worst score | 17.7 | 17.7 |

### Stylometry ships, read backwards

The strongest technique in the survey, and applying it as the literature writes it
would have made the tool worse. Burrows's Delta over function-word frequencies is
the standard stylometric distance, and the obvious feature is to flag documents
far from a human reference profile. Built from the 29 files in
`eval/corpus/human/` and measured, the order is inverted: the human class averages
0.769 and the modern-AI class 0.690, so model output sits **closer** to the human
centroid than human writing does and the naive rank statistic is 0.188. A check
built the obvious way would have flagged the humans and passed the machines.

A reference profile from thirty authors is the centroid of thirty idiosyncrasies,
and a model writes the centroid. The tell is the absence of distance, not the
distance. Read inverted the signal separates at 0.812, below the floor score's own
0.938, and it runs 0.737 on the ESL/formal human subset, so it stays out of the
score on both counts.

It ships as a diagnostic because it is the only number in the repo that shows the
rewrite procedure working: the twenty paired files in `ai_modern_rewritten/` move
from 0.690 to 0.739 and end closer to the human median in 16 of 20 cases. The
profile is `human_reference_profile.json`, generated by `eval/build_profile.py`
and gated by `make profile-check`. The linter prints it on a new `style:` line
with the human range beside it, and `--baseline` prints the movement and which way
it went.

### Three techniques tested and rejected

The more useful half. **Contraction absence** is the widest single signal in the
published humanizer research and it replicates here at nine to one, 20.3 per 1,000
words in the human class against 2.2 in the modern-AI class. It is not scored and
will not be: gated to the conversational registers with a pronoun floor, it fires
on four of the ten files in `esl_formal/`, careful non-native writers who use no
contractions and are human. Scoring it would reproduce, inside a tool whose whole
argument is that commercial detectors are wrong about that population, the exact
bias Liang et al. measured. It is reported as an unscored diagnostic on the new
`voice:` metrics line instead.

**ProWritingAid's glue index** shows no separation at all: 44.2% in the human
class against 43.5% in the modern-AI class, with the caricature class scoring
*better* than the humans. It is a quality metric, not an AI tell.

**The comma-anchored analogy tail** (", the way snow lies on a road nobody
drives") separates perfectly here, on two files, which is not evidence. It is
named in the creative-register guidance for the human read rather than scored,
because "She smiled, the way she always did" is ordinary fiction and firing on a
single instance is what principle 2 forbids.

### Also

Thirty-nine new stress-test cases, including false-positive guards for every new
check. One of them found a real division-by-zero in `stylometry.delta` when a
caller passes a profile with a zero-variance feature, which `load_profile`
rejects but a direct call did not. The placeholder pattern was tightened after `[X]` and `[X, Y]` in the
Python stdlib docs turned out to be expectation and generic-parameter notation,
which is exactly what the out-of-repo human baseline exists to catch.

## [0.7.0]

### The rules now outlive the document they were invoked on

Nothing about the analysis changed in this release. The linter, the weights, and
the corpus are untouched. What changed is when the skill applies and how hard it
argues with itself, borrowed in most part from the `i-have-adhd` skill, which
solves a different problem with better operational discipline than this one had.

Four gaps, all of them in the seams around a good rewrite rather than in the
rewrite itself.

The skill used to end when the document did. You would humanize a report, hand it
back inside a paragraph of "Great question! I've now rewritten your document to
remove several AI tells", and then draft the next document in the default voice
because nobody said "humanize" twice. **Scope and persistence** closes both. The
rules hold for the session, they cover the response carrying the artifact, they
reach commit messages and PR descriptions, and they stop when the user says
"normal voice" rather than when the turn ends.

The full procedure is eleven steps plus an intake, a scored critique and a
detector gate. On a two-line Slack message that is absurd, and a procedure too
heavy for the common case is a procedure that gets skipped. **Pick the depth of
the pass** gives three tiers chosen by what it costs to be taken for a machine.
Depth changes how much runs and never how strictly: the invariant guard and the
anti-hallucination protocol hold at `quick` exactly as they hold at `full`.

**When a rule fights the task** answers the complaint the guardrails section
never quite did. Anti-overcorrection was about applying a rule too hard. This is
about seven cases where the rule should not have applied: an API reference wants
a heading per endpoint, "may cause drowsiness" is precise rather than hedged, a
translation request is not an invitation to rewrite, and a system prompt beats
this file. The constraint wins and the shape stays, one rule scoped for a stated
reason that goes in the audit.

**Pre-return check** is the handoff gate. The self-critique loop reads the prose;
this reads what you are about to send. Delete the announcing opener, the recap
closer, the "by the way" sidebar, the hedge carrying no information. Then confirm
four things, and fix rather than caveat when one fails.

### Added
- `Scope and persistence`: session-long application, response text in scope, an
  explicit off-switch, and the two rules (no fabrication, no invariant change)
  that survive turning the voice off.
- `Pick the depth of the pass`: `quick` / `standard` / `full`, with the steps
  that scale down named and the ones that never do held fixed.
- `When a rule fights the task`: seven override cases, each scoping one rule.
- `Pre-return check`: a four-item delete list and a four-item confirm list
  covering fabrication, invariants, audit specificity, and gate honesty.
- Audit template: `Depth:` and `Rules relaxed:` lines. At `quick` depth the audit
  collapses to a line or vanishes, because a Slack message needs no report card.
- Workflow step 1 sets the depth; a new step 10 runs the pre-return check.

### Unchanged by this work
No check, weight, threshold, register profile, reference file or example was
touched to make room for any of it. The four sections add 151 lines to
`SKILL.md` against one line replaced in place, and the eval, ablation and
human-baseline metrics match the committed 0.6.0 baseline exactly.

## [0.6.0]

### The syntactic signature, and the false positives that were noise

The v0.5 audit established that word choice is not what gives current model output
away. This release answers the follow-up question: if not diction, then what,
specifically, in a document that has no filler and no em-dashes?

Four grammatical constructions, measured. `participial_tail` and `cleft` alone are
**30% of the score mass** on the realistic-AI class and 0% on the 2023 caricature.
They are the ", making it easier to…" consequence clause bolted onto sentence
after sentence, and the "What actually mattered was…" cleft that stages a subject
instead of stating it. Both are ordinary English that good writers use, which is
why every new check fires on the *stacking* and never on one instance.

The other half of the release is subtraction. Four checks were flagging human
writing for doing normal things, and each one was a real defect rather than a
threshold that needed nudging. The human false-positive rate went from 0.088 to
**0.000** on a binary corpus that grew from 58 to 63 files (34 to 39 of them
human), and the realistic-AI precision went from 0.750 to **1.000** as a result. Recall rose from 0.750 to
0.850 and AUC from 0.901 to 0.937.

### Added: checks for what a current model actually writes
- `cleft` (weight 1.5): wh-clefts ("What actually consumed the time was…"),
  reversed clefts ("The reason this was hard is that…"), and it-clefts ("It is the
  second call that fails"). Gated on three occurrences AND a per-1k rate, muted in
  `creative` where a staged subject is a narrative device with a long history.
  Unmuted in `casual`, where the human corpus uses none and the model corpus
  stacks them.
- `participial_tail` (weight 2.0): the resultative ", making/allowing/ensuring/
  giving…" tail. Gated on three occurrences. The largest single contributor to the
  realistic-AI score.
- `copula_density` (1.0), `clause_splice` (0.5), `paragraph_openers` (1.5),
  `bullet_openers` (1.0), `noun_chain` (0.5): a paragraph where everything simply
  *is*, a page welded together with ", and it is…", every paragraph opening with
  the same two words, every list item opening with the same -ing verb, and stacked
  "the X of the Y of the Z" noun piles.
- A `syntax:` line in the report and a matching row in the audit template, so a
  writer can see the counts before they trip a threshold.
- 466 new pattern entries across the lexical and regex lists, including 69 new
  `context_exceptions` so the additions do not fire on legitimate technical use
  ("primary key", "critical path", "surface temperature", "first-class function").

### Fixed: false positives that were pushing writers toward over-correction
- **Markdown inside a fenced code block counted as document shape.** A `#` comment
  in a `bash` block was a heading, `- **Flag**: …` in a quoted markdown sample was
  a bold bullet, and an emoji in a code example was decorative. A style guide
  demonstrating the anti-pattern it warns against scored 28.2. The shape checks
  (`heading_case`, `bold_bullets`, `formatting`, `assistant_shape`) now run on the
  code-stripped text, with the raw text still supplying the content-line
  denominator so a code-heavy page is not judged as if the code were absent.
- **`uniform_openers` fired at a 30% repeat rate.** Human and AI files overlap
  completely in the 0.30–0.45 band for `the`, `we`, and `I`, which are the words
  English sentences start with; the check separated nothing and flagged five human
  files. It now needs 0.45 and five sentences for that closed set of
  high-frequency openers, and keeps the low bar for a repeated *distinctive*
  opener, which is the actual templating signal.
- **`burstiness` computed a coefficient of variation from five sentences.** A
  seven-sentence human abstract measured 0.33 and was told its rhythm was flat.
  Minimum raised to eight; no AI file that fires has fewer than ten.
- **The noun-phrase `rule_of_three` could not tell a triad from a clause list.**
  "you paste code into a notebook, the kernel dies, and the last save is gone" was
  flagged as a rule-of-three. Members containing a pronoun or a finite verb, or
  opening with a preposition, are no longer treated as noun phrases.
- **`narrator_distance` is now muted in `casual`.** "Nobody tells you" from a
  first-person writer is their stance, not a lecturer's distance.
- **The em-dash density check needed two dashes.** Two em-dashes in a 220-word
  email scored 15.0, the category cap, and read as `strong-tell`. It needs three
  now; the paired-aside check still fires at two, because "— like this —" is a
  distinct tic rather than a rate.

### Fixed: scoring
- **Short documents were amplified by the density denominator.** Two hits in a
  220-word note scored as "9 per 1000 words" and drove the category straight into
  its cap, so a short human note outscored a 2,000-word document carrying the same
  defect ten times over. The per-1000-word denominator now has a floor of 300
  words (`scoring.density_floor_words`).
- **The display cap was capping the score.** Instance checks emitted at most six or
  eight findings, inlined per check, so a 5,000-word document with fifty em-dashes
  scored the same as one with eight. Replaced with one named bound
  (`MAX_INSTANCE_HITS`); display truncation belongs to the report layer, which
  already prints "… and N more".
- **`superlative_creep` emitted one document-level finding per example.** Six
  line-0 hits for one density signal, worth six times `doc_hit_points` and
  carrying no line number. Collapsed to one finding that lists its examples, and
  `scoring.doc_cap_per_category` now bounds the pattern generally.

### Fixed: data loss and corruption in `--fix`
- **The autofixer rewrote URLs.** `.../delve-into-it` became `.../examine-into-it`
  and a query string's `a--b` became `a, b`. Link destinations, autolinks, bare
  URLs, reference definitions, HTML tags, and footnote refs are now masked
  alongside code.
- **`--fix` on a file over the 5,000,000-character read limit wrote back the
  truncated text.** It now refuses and says why.
- **`--fix` converted every line ending in a CRLF file.** The original ending is
  detected and restored, so a three-word fix is a three-word diff.
- **`--fix --register auto` never resolved the register**, so the literal string
  "auto" matched no gate and creative prose lost its em-dashes and its emoji.
- The write is now atomic (temp file plus `os.replace`), so an interrupted run
  cannot leave a half-written draft.
- **The dash rewrite varies the mark.** Turning every dash into a comma clears the
  em-dash check and installs a new uniform signature, which is the failure
  principle 2 names. A paired aside becomes parentheses, an enumeration takes a
  colon, everything else takes a comma.

### Fixed: sentence segmentation
- **A soft-wrapped list item counted as two sentences.** Markdown wraps bullets
  all the time, and the second line started a fresh block, so "...reduced deploy
  time from 40 minutes to" / "6, allowing engineers to ship the same day" became
  two sentences with a full stop planted mid-clause. That corrupted the sentence
  count, the length distribution that `burstiness` and `sentence_shape` both read,
  and every n-gram across the invented boundary. A continuation line now belongs
  to its bullet.
- **`assistant_shape` flagged a recap section anywhere in the document.** The tell
  is a document wrapping *itself* up, so the heading has to be the last one. A
  "Next steps" section in the middle of a plan is a section.
- **`participial_tail` matched narrative motion.** "turning", "letting",
  "leaving", and "freeing" were in the verb list and are what fiction does
  (", turning toward the door"). The list is now the consequence-clause vocabulary
  only: verbs that assert an effect rather than describe an action.

### Changed: performance
- Analysis of a 36,000-word document went from **6.5s to 2.7s**. The lexical
  lists ran one `\bphrase\b` regex per entry, which with a thousand-plus entries
  meant twelve hundred full scans of the text and 66% of total runtime. Phrases
  are alternated into a handful of combined regexes grouped by word-boundary
  anchoring, and matched text is mapped back to its suggestion by normalization.
  The dialect map got the same treatment. A test asserts the pass has not
  regressed to per-phrase scanning.
- Two entries in one list that cover the same words ("it's worth noting" and
  "worth noting that") are now one finding rather than two. That was a
  double-count, not a feature.

### Fixed: text handling
- **An intraword underscore was treated as markdown emphasis**, so
  `get_user_by_id` became `getuserbyid` and `MAX_RETRY_COUNT` became
  `MAXRETRYCOUNT`, corrupting the word count, the n-grams, and the type-token
  ratio of every technical document naming an identifier outside backticks.
  CommonMark does not treat intraword underscores as emphasis and neither does the
  linter now.
- **`api.lint()` and the CLI disagreed about the same file.** Only `read_input`
  normalized CRLF, the BOM, and control characters, so a library caller got
  different line geometry and a different score. Both call `normalize_text` now.
- **The dialect check skipped every sentence-final word.** `_is_identifier_context`
  treated any trailing `.` as attribute access, so "we optimise." went unflagged
  while "we optimise it." was caught. The dot now has to be followed by an
  identifier character.

### Fixed: CLI and configuration
- `--enable`/`--disable` with a misspelled category silently filtered every hit
  away and reported a clean document, which is the most dangerous failure this
  tool can have. Unknown names now warn and list the real ones.
- `--baseline` silently ignored every input past the first; it says so now.
- `collect_targets` deduplicates (so `lint docs/ docs/intro.md` analyzes the file
  once) and prunes `.git`, `node_modules`, `__pycache__`, and the other vendor and
  build directories on a recursive walk. `.mdx` and `.rst` are recognized.
- An `ignore-start` directive with no matching `ignore-end` suppressed nothing at
  all, silently. It now runs to the end of the document, the way a block comment
  behaves.
- The report's "want >=" figures were hardcoded, so overriding a threshold changed
  what fired while the report kept quoting the default. They read the resolved
  threshold table now.

### Fixed: checks that reported nothing
- `check_parallel_structure` fired once when a streak reached the threshold and
  then went quiet, so three sentences in a row and eight read identically in the
  report. It reports the run's actual length, and records
  `parallel_runs`/`longest_parallel_run`.
- `check_circular_conclusion`, `check_wh_openers`, and `check_svo_monotony`
  returned before writing their metrics, so a document just under a threshold
  looked identical to one with no signal at all.
- `check_five_paragraph_shape` gave up above nine paragraphs. A twelve-paragraph
  report closing on "In conclusion" is still closing on a recap.

### Added: a guard against this tool's own fingerprint
- `over_correction` now catches one-mark punctuation substitution: an unusual
  semicolon rate combined with no dash anywhere means every em-dash was swapped
  for the same replacement, which is a fresh uniform signature in place of the old
  one and exactly what principle 2 forbids. The human maximum on this corpus is
  5.5 semicolons per 1,000 words; the floor is 7.0, with an absolute minimum of
  three so a short note with two semicolons stays quiet.
- `copula_per_1k` lowered from 90.0 to 78.0. The human maximum measured here is
  67.8, so 90 sat far enough above every observed document that the check could
  never fire; 78 clears the human range with margin and reaches genuinely
  glossary-shaped prose.

### Added: a negative set nobody here wrote
- `eval/human_baseline.py` scores the docstrings of 26 Python standard-library
  modules. Hundreds of authors, three decades, no knowledge of this repository,
  and it ships with the interpreter, so the sweep runs offline with no corpus
  file. It is the only negative set in this project that the corpus author did
  not also write, and it is gated in CI on a median ceiling, a worst-case
  ceiling, and a cap on how much of the total any single category may own.
- Pointing the linter at it found five real false-positive bugs, all of which
  also fire on ordinary technical documentation: a setext heading underline read
  as a horizontal rule; an aligned two-column table read as a doubled word; an
  emoticon read as a space before punctuation; ASCII `--` counted in two
  categories at once; and every *copy* of a repeated triad counted separately,
  so one type signature in twenty `pathlib` docstrings was twenty findings.
- Median score on that set: **35.0 to 8.7**. Worst module: 43.5 to 17.7. No
  change to any labeled-corpus metric.
- Two calibrations from the same sweep. Repeated n-grams are a rate, so the
  minimum count scales with document length instead of holding at four for a
  300-word note and a 4,000-word reference alike. And a dash convention used more
  than five times is reported once, as the one find-and-replace it is.
- One tricolon no longer fires at all. Principle 2 says a tricolon in moderation
  is fine, and the check contradicted it; the reflex needs two.

### Changed: the corpus and the eval
- `eval/corpus/` grew from 92 to **113 files**: eight new `ai_modern/` samples with
  their paired rewrites, and five new long-form `human/` hard negatives. The new
  files are longer than the originals (300–450 words), because the count-gated
  checks need a document long enough for a rate to mean anything.
- `EVAL.md` reports the v0.5 numbers beside the v0.6 ones throughout, and states
  the circularity risk plainly: eight `ai_modern/` files and the checks that catch
  them were written in the same pass. The numbers those files cannot inflate are
  called out: the 0.000 human FPR, and recall on the twelve *pre-existing*
  `ai_modern/` files, which went from 9/12 to 11/12 with no threshold change.
- `--register auto` accuracy is 82.3% on 113 files (was 79.3% on 92), against
  18.6% for always-`technical`. Cue scoring is sublinear in the hit count instead
  of tripling on three matches, cues carry an optional `min_hits`, and the tutorial,
  casual, creative, and marketing cue sets are wider. 82% is a measured plateau,
  not a waypoint.
- `make dogfood` lints the repository's own prose. `SKILL.md` had 66 em-dashes in a
  document that tells writers to remove nearly all of them; it now has none.
- The numeric-invariance test on the shipped rewrites was matching sentence
  punctuation as part of the number, so "…187." read as the number `187.` and was
  reported as invented.
- 1,078 stress checks (was 854), covering every new check, every false-positive
  guard, and every `--fix` corruption case above. Two of them are property tests
  rather than fixtures: adversarial markdown must never crash the linter, and
  autofix must never alter a number, a code span, or a URL on any input.
- `ai_prose_patterns.json` carries a version string that must match the plugin
  manifest, and the CHANGELOG must have a section for the current version. Both
  are now asserted, because a stale pattern-file version misleads a user about
  which tell lists they have.

### The audit that produced this release

The linter reported a ROC AUC of 1.000 on its own corpus. That number was close to
meaningless, and finding out why changed the skill's whole theory of what to fix.

The `ai/` class had been authored to carry the exact tells the linter scores, 2023
<!-- human-voice: ignore-start filler,meta_commentary -->
ChatGPT slop, "in today's fast-paced landscape", bold-bullet listicles, "In
conclusion".
<!-- human-voice: ignore-end --> Prose a *current* model writes scored 21.4 against a human class
spanning 0.0–25.4, i.e. squarely inside the human distribution. The perfect
separation was measuring internal consistency and nothing else.

Two published findings reordered the priorities. Base models, pretrained
checkpoints that never went through instruction tuning, are classified human by
commercial detectors more than 96% of the time, so what detectors respond to is
post-training artifacts: markdown formatting preference, response-length and
structural conventions, sycophancy. And the vendor with the strongest numbers on
humanized text reports that *the more fluent a humanizer's output, the more
reliably it is detected*, because the tools that evade do it by damaging the text.
Word choice, which is where most humanizers start and where much of this skill's
weight sat, is at the bottom of the list.

### Added: the class the linter was missing
- `eval/corpus/ai_modern/` (12 files, held out): prose in the register a current
  instruction-tuned model actually produces. Fluent, takes a position, carries
  concrete detail, contains no filler and no em-dashes, and still reads
  machine-written. Every register represented. `lib.modern_eval` scores it against
  the human class and names the files it misses.
- **The honest headline number: AUC 0.901** against that class (recall 0.750 at
  the default boundary), reported beside the legacy 1.000 rather than instead of
  it. The three misses are all casual/creative and score 0.0–3.0; what gives them
  away is that their specifics are plausible and unowned, which no regex reads.
- Ablation now reports score-mass share for **both** AI classes. The divergence is
  the finding: `filler` (11.8%) and `meta_commentary` (11.5%) drive the caricature
  score and contribute **0.0%** to catching modern output, while `sentence_shape`
  (23.3%), `paragraph_uniformity` (13.6%), and `burstiness` (12.9%) drive that one.

### Added: two detector-aligned checks
- **`assistant_shape`** (weight 2.5, Tier A): markdown scaffolding density,
  headings per 1k words, bullet-line ratio, bold spans per 1k, and a closing
  "Key takeaways"/"In conclusion" recap section. Density-based and length-gated, so
  a README's headings are fine and a heading every sixty words is not. Muted for
  `release_notes`, `ux_microcopy`, and `tutorial`, where the format is the genre's.
  This is the single strongest evidenced detector signal and the linter had no
  check for it.
- **`sentence_shape`** (weight 2.0): the sentence-length *distribution*, not just
  its coefficient of variation. CoV is fooled by one long outlier while everything
  else stays uniform, so this measures the tails directly, the fraction of
  sentences at ≤8 words (floor 0.12) and the fraction inside the 12–26 word band
  (ceiling 0.72). Now the largest single driver of the modern-AI score.

### Fixed: the score was length-dependent, which distorted every metric
- Document-level findings were divided by word count. A flat-burstiness finding
  fires once no matter how long the text is, so the same defect was worth ~13
  points in a 150-word note and ~1 point in a 2000-word report, and the corpus
  median is 163 words, so this was skewing every number in `EVAL.md`. Document
  findings now contribute fixed points (`scoring.doc_hit_points`); only instance
  findings are normalized by length. Regression test asserts a 10× length change
  moves the score by under 40%; it used to move it ~13×.
- Per-category density is now capped (`scoring.category_cap`), so one runaway check
  cannot swamp the rest. `ngram_repetition` had emitted 394 positionless hits on an
  840-word document, 82% of a score of 482.
- `ngram_repetition` is an instance check now: findings carry the line of their
  first occurrence and are capped at 8, instead of being unbounded and unlocatable.
- **`casual` and `creative` had no rhythm check at all.** Both muted `burstiness`
  on the grounds that they permit fragments, but the check fires only on *low*
  variance and fragments raise it. Rhythm checks are now universal, no genre is
  served by a metronome, and a test asserts no mute token can silence them.

### Added: a verification gate, so the claim is checked instead of asserted
The skill could not tell you whether a rewrite actually cleared a detector. It
reported a floor score and a caveat saying the floor is not a detector, and left it
there. A document can score 0.0 and be flagged at 0.93; nothing closed that loop.

- **`skills/human-voice/scripts/verify_detector.py`**: probes a configured detector
  and exits **1 while the text is still flagged**, 0 when it clears, 2 when no
  detector is configured. Supports `--before` to report the movement, `--max-p-ai`
  to tighten the gate, and `--json`.
- **`human_voice_linter/detector.py`**: request shapes for GPTZero,
  Originality.ai, Sapling, and Winston (whose 0-100 human score is inverted into
  p(AI)), key discovery, and the probe. It lives in the skill package so a skill
  copied to `~/.claude/skills/` works without the `eval/` directory, and
  `eval/detector_harness.py` imports it instead of keeping a second copy.
- **SKILL.md Workflow step 7 makes it the stopping condition.** While the gate
  returns 1 the pass is not finished and the loop goes back to the rewrite, fixing
  in the measured priority order. The cap rises from 3 passes to 5 when a gate is
  active, and the loop stops early if two consecutive passes cannot move the
  detector without damaging the prose. Grinding past that point is how humanizer
  tools produce the mangled text detectors catch most easily.
- **Exit 2 is not a pass.** The audit template has a `Detector gate:` line that
  records `clear`, `flagged`, or `not run` verbatim, and principle 8 now names three
  instruments with three distinct limits instead of two.
- No network call happens without a key: no default endpoint, no telemetry. A stale
  request shape raises an error naming the missing field rather than returning a
  wrong answer. 21 new checks cover the exit codes, the human-scale inversion, the
  out-of-range rejection, the stale-shape error, and the fact that neither a missing
  key nor a network failure can be reported as a pass.
- `make verify FILE=draft.md BEFORE=original.md`.

### Added: real detector measurement, replacing the vendor citations
The repo quoted other people's detector numbers and disclaimed them, because it had
measured none itself. `eval/detector_local.py` fixes that by running four detectors
locally on open models: no API key, nothing sent to a vendor. Opt-in and dev-only
(`make detector-local`, ~1.5GB of weights), never part of `test` or CI, and nothing in
the skill imports it. The shipped linter stays dependency-free.

Both detector families are covered. **GPT-2 token surprisal** gives real per-token
`-log P(token | context)`, so genuine perplexity, which is what the
statistical/zero-shot family thresholds on. **Binoculars** (gpt2 observer /
distilgpt2 performer) is the strongest published zero-shot method. Two **supervised
classifiers** of different vintages: the 2019 `roberta-base-openai-detector` trained
on GPT-2 output, and the 2023 `Hello-SimpleAI/chatgpt-detector-roberta` trained on
real ChatGPT output. Classifier results are reported as the model's **argmax label**,
not a probability against a threshold somebody chose. Results in
`eval/detector_local_results.json`, written up in `EVAL.md`.

- **Rewritten texts classified AI by any supervised detector run here: 0 of 7.**
  Median perplexity multiplier **x2.14** across the shipped pairs (x2.03 to x4.02),
  Binoculars up in all seven, and every rewritten text inside or above the human
  perplexity range of 26.2-93.3. The `casual` pair is a measured before/after flip on
  a real classifier: flagged AI at 0.993 before, human after.
- **Realistic model output is already indistinguishable from human on all four
  detectors.** Perplexity 46.4 against a human 48.5, Binoculars 0.892 against 0.891,
  and the ChatGPT-trained classifier catches **1 of 12** of it against 9 of 24 for the
  2023-era caricature. The audit's central finding reproduces at the detector level,
  across two families, with a classifier trained on the right generation of model.
  The distributional tells are gone; what remains is structural.
- **The anti-AI costume is caught by Binoculars and missed by perplexity.**
  `over_corrected` scores 94.6 on perplexity, *higher* than genuine human writing,
  because forced lowercase and staccato fragments are unpredictable. Binoculars puts
  it at 0.780, below the human 0.891. Perplexity alone is gameable by making prose
  worse; a better statistical detector is not. Measured justification for treating
  `over_correction` as a tell rather than a fix.
- **Neither classifier flags any of the 34 human files**, 0 of 34 on both, which is
  the false-positive result that matters most given how these tools get used.
- The `over-corrected` pair is the control that shows the tool is not optimizing the
  metric: its "before" is already at perplexity 165.8 and the rewrite brings it *down*
  to 92.7 while raising Binoculars from 0.928 to 0.965.

Reported rather than dropped: no commercial API has been queried from this repository;
the models are small, so the direction of travel is trustworthy and the absolute
values are not; and three "after" texts reach perplexity 111-133, above the human
median, which is a signal to watch in case a future pass starts optimizing perplexity
instead of prose. Binoculars is the guard against that, and it moved the right way in
all seven pairs.

### Added: `--register auto`, because the default was wrong most of the time
The skill documents a register-detection decision tree and the linter never
implemented it, so `--register` defaulted to `technical` no matter what you fed it.
That applied the strictest mute set to fiction and to marketing copy alike: a
novelist's em-dashes and a marketer's "you" were both scored as tells.

`infer.py` implements the tree as a weighted-cue vote over 33 cues. Measured against
the corpus register labels as ground truth:

| | correct |
|---|---|
| old behavior (always `technical`) | 18 of 92 (19.6%) |
| `--register auto` | **73 of 92 (79.3%)** |

The failure mode is designed, not incidental. Of the 19 misses, 10 fall back to
`technical`, which is the strictest profile and the old behavior, so a wrong guess
over-flags rather than silently excusing tells; only 9 of 92 choose a *more*
permissive register than the truth. Guards that came out of measuring rather than
guessing: a document under 30 words gets no inference at all (a one-line note matched
the email greeting cue and was "inferred" as email with full confidence), the
winner must lead proportionally rather than by a fixed margin, and first-person
density only *reinforces* an existing casual signal instead of deciding on its own,
because formal business memos and non-native academic writing both use "I" freely and
that cue was dragging the whole ESL subset into `casual`.

It prints what it chose and why, to stderr, so `--json` stays parseable and `--quiet`
stays one line per file. An explicit `--register` always wins, and the payload gains
`inferred_register` **only** when inference actually ran, so a consumer that never
asks for it sees a byte-identical payload. Two accuracy gates in the test suite fail
if the cue tuning regresses below the status quo or if the misses stop skewing safe.

SKILL.md tells the model to prefer its own judgment over the flag: it has the whole
document and the user's intent, the flag has keyword cues.

### Added: a specificity diagnostic for the tell no regex can see
Vacuity is the tell this skill calls highest and the one it admits it cannot check.
`specifics_per_100` measures what vacuous prose reliably lacks instead: numbers,
dates, and proper nouns a reader could go and verify. The human class runs about 3.0
per 100 words, realistic-AI about 0.6.

It is **reported, never scored**, and that decision came from the measurement. The
ranges overlap completely: plenty of good writing, fiction especially, contains no
number and no proper noun at all, so scoring it would flag exactly the careful and
creative writers detectors already mistreat. What it is good for is branching: a
`specifics_thin` flag fires when a document over 120 words has almost nothing
checkable in it, which is the signal that the author-material intake is mandatory
rather than optional. Cutting tells from a draft with no material in it just produces
clean generic prose, which is the over-correction failure mode.

Measured honestly, it also flags this repo's own shipped rewrites (0.64 per 100 words
against the sources' 0.55): they could not add specifics, because principle 3 forbids
inventing them and the sources had few. That is the limitation the intake exists to
solve, and it needs a real author, not a linter.

### Added: doctrine and consistency gates on the mute table
Principle 5 names a "universal core" of tells that are wrong in every genre. A test
now asserts no register mutes any of them, so the config cannot drift from the
documentation the way `casual` and `creative` did when they silenced the rhythm
checks. Three more gates: every mute token names categories that exist, no token is
defined and unused, and none is used without a definition.

Also verified and left alone: the linter is linear in input size, about 30k words per
second, 34k words in 1.1s.

### Added: the paired after-corpus, and a detector panel with a calibration gate
The detector measurement had one sample that started from realistic modern AI. Now
all twelve do. `eval/corpus/ai_modern_rewritten/` holds every `ai_modern/` sample
after the skill's procedure under the same filename, so before and after are paired
on identical claims, across every register. `lib.rewrite_eval` pairs by basename and
names any file that got worse instead of averaging it away.

On the floor score: **mean 12.9 to 1.2, clean 3/12 to 12/12, flagged at the default
boundary 9 to 0, and nothing regressed.** A pytest case asserts every numeric token
in an after-file appears in its before-file, so the anti-hallucination protocol is
enforced mechanically on the shipped rewrites rather than promised.

The panel grew to five detectors: token surprisal, Binoculars, and three supervised
classifiers of mixed vintage. **One of them flags 34 of 34 hand-written human files
at p(AI)=1.000.** A detector that cannot pass human text tells you nothing about a
rewrite, and counting its verdict would have inflated every number in the report, so
`calibrate()` measures each classifier's false-positive rate on the human class first
and excludes anything above `MAX_HUMAN_FPR` (0.20), printing which and why. That
guard is the most important thing in this section: without it the headline would have
read "12 of 12 still flagged" and meant nothing.

Among the classifiers that *do* pass calibration, one is genuinely discriminating:
0 of 34 human files, 24 of 24 caricature-AI files. With that panel:

| set | flagged before | flagged after |
|---|---|---|
| the 12 realistic modern-AI samples | 3 | **0** |
| the 7 shipped example pairs | 4 | **0** |

Median perplexity multiplier x2.21 on the modern set, with every one of the twelve
rising. `--check` gates the panel like the other evals, failing if more rewrites get
flagged or the perplexity movement shrinks.

### Corrected: a finding from the previous pass did not replicate
An earlier run reported that Binoculars catches the anti-AI costume, scoring
`over_corrected` at 0.780 against a human 0.891. That used a gpt2/distilgpt2 pair.
With gpt2-large/gpt2 the ordering disappears (0.788 against 0.780). The conclusion
was an artifact of the model pair, it is corrected in `EVAL.md` and in the harness
docstring, and the general lesson is recorded there too: a single Binoculars ranking
is pair-dependent until it replicates.

### Fixed: reported line numbers pointed at the wrong lines
`prose_for_metrics` joins soft-wrapped lines so sentences segment correctly, which
collapsed a 75-line document to 12. Every check located against that text reported a
line number from the *reduced* text: a finding on source line 42 was reported as line
8. Two consequences, both real. Readers following a location landed in the wrong
place, and inline `<!-- human-voice: ignore -->` directives could never match those
hits, because directives are keyed on source lines. That silently affected `em_dash`,
`rule_of_three`, `ngram_repetition`, and `colon_summary`.

`prose_for_metrics(..., with_line_map=True)` now returns a segment table, and the new
`MappedLineMap` binary-searches it, so a hit resolves to the exact source line rather
than to the line its paragraph started on. Ten checks cover it, including one that a
directive suppresses its own line while a hit on another line survives, which is what
proves the match is by exact line rather than a blanket category mute.

### Not shipped: a frequency table is not a perplexity proxy (negative result)
The audit named "no surprisal measurement" as a gap and this was the attempt. Bundle
a ~600-word high-frequency list, treat band membership as low surprisal, and measure
both the common-token ratio and its variance across sentences, the latter standing
in for what DetectGPT-family detectors key on.

Measured before wiring it in, and it fails. The ratio separates in the **wrong**
direction (human 0.664, realistic AI 0.611) because the AI samples' latinate filler
is *rarer* vocabulary, not commoner, and the cross-sentence variance does not
separate at all (0.182 against 0.176). A better word list cannot fix it: surprisal
is `P(token | context)` and a context-free frequency band discards exactly the
conditioning that makes perplexity discriminative. "The cat sat on the mat" and "the
mat sat on the cat" have identical unigram statistics.

The module was deleted rather than shipped, because a metric that does not separate
adds noise and false confidence. It is written up in `EVAL.md` so nobody spends the
day twice. A real surprisal measurement needs a model, which means abandoning the
zero-dependency promise, and the shipped alternative is to ask a detector that
already has one.

### Fixed: n-gram repetition flagged the consistency it tells you to keep
- Bigrams now need two content words, so `"the text"`, `"the skill"`, and
  `"the rewrite"` no longer fire. Those are article-plus-defined-term pairs, which
  is precisely the one-term-per-concept consistency principle 6 mandates, and
  flagging them pushed writers toward rotating synonyms, a tell in its own right.
- N-grams are counted **within** sentences. Sliding a window across the whole token
  stream manufactured phrases that straddled a full stop: "...to the client. The
  client retries..." produced the trigram `"client the client"`.
- Together these took the README from 6.6 to 2.6 with no change to class
  separation: human 0.0-11.6, realistic AI 0.0-34.0, AUC 0.901, all unmoved.

### Fixed: four autofix bugs, found by running `--fix` on this repo's own docs
- **`--fix` was deleting inline code.** `_mask_code` blanked code spans to
  *spaces*, and the dash and emoji patterns pad themselves with `[ \t]*`, so in
  "labeled `ai`, balanced" the masked span read as whitespace, the dash match
  extended across it, and splicing the replacement back into the original text
  removed the `` `ai` ``. The README's claim that `--fix` "never touches code" was
  false. Code is now masked with NUL, which no pattern can consume. Four
  regression cases plus a fenced-code case.
- **Guidance suggestions were spliced in as replacements.** The `filler` entry
  `harness → use` is correct for the verb and wrong for the noun, and `--fix`
  turned "evaluation harness" into "evaluation use" in `EVAL.md`. Only literal
  substitutions are auto-applied now (`is_substitution`); an entry containing a
  parenthesis, semicolon, or alternation is treated as advice for a human. A test
  asserts no shipped entry in an auto-fixable category can regress this.
- **A dash opening a wrapped line stranded the comma at that line's start.** Running
  `--fix` on this README produced "...rewritten text\n, a figure about...". The edit
  now reaches back across the newline so the comma ends the previous line, where a
  writer would have put it, while an inline dash keeps its geometry unchanged.
- **A lone dash in a table cell became a comma.** `| n/a |` placeholder cells in
  this README turned into `|, |`. A dash in a table cell is a conventional
  "not applicable" marker rather than a dash-as-pause, so table rows and alignment
  rows are now skipped, while a prose dash on the following line is still fixed.
- Added `Bryan Garner` / `Garner and Pinker` to `context_exceptions`, since the
  surname was matching the `garner` filler verb, and exempted the noun compounds of
  `harness` ("test harness", "evaluation harness", "detector harness"). The verb
  sense that actually is filler, "harness the power of", still fires; a test asserts
  both halves so the exception cannot silently widen.

All four were found by running the tool on this repository's own prose, which is the
argument for dogfooding a linter: none showed up in 510 unit tests, and every one of
them corrupted real text.

### Fixed: the project's own prose
Running the linter on the repo's documentation found it in violation of its own
headline rule. README went from 18.6 (`strong-tell`, 17 em-dashes) to 4.5
(`clean`, none); `references/what-detectors-see.md` from 21.3 to 0.0, which also
meant converting its own bold-lead-in bullet lists to prose. `EVAL.md` and
`CHANGELOG.md` had all 63 em-dashes between them replaced with varied marks. The
remaining flags in those two are the documented confound of a document that
*quotes* the tells it catalogs, now suppressed with the inline
`<!-- human-voice: ignore -->` directives rather than left to look like a pass.

### Result of those fixes, on the same corpus
| metric | before | after |
|---|---|---|
| human false-positive rate @5.0 | 0.294 | **0.088** |
| ESL/formal-human FPR @5.0 | 0.300 | **0.000** |
| F1 @5.0 | 0.828 | **0.941** |
| human score range | 0.0–25.4 | 0.0–11.6 |

The ESL result is the important one: careful non-native and formal-human writing is
the population commercial detectors demonstrably over-flag, and a tool that repeats
that failure is worse than no tool.

### Changed: the skill
- **New section: Author-material intake.** The skill was purely subtractive, and a
  rewrite that can only delete produces clean, generic, unowned prose, which is
  the over-correction failure mode it already warned about. The intake runs *before*
  the subtractive passes and sources real specifics from the draft, the surrounding
  context, or four short questions to the user. Highest-yield question: "what do you
  believe about this that you can't fully defend?" Nothing invented; gaps stay
  `[SOURCE NEEDED]`.
- **New edit move ⓿: strip the assistant shape**, ahead of everything else, with
  concrete instructions per genre.
- Rhythm target changed from "CoV ≥ 0.5" to the distribution: ≥12% of sentences at
  ≤8 words, ≤72% in the 12–26 word band. The self-critique checks the metrics line
  rather than guessing.
- "What detectors actually measure" rewritten as "What detectors actually see" on
  the current evidence, with a per-family table of what a rewrite does and does not
  move. New reference: `references/what-detectors-see.md`.
- "Top tells" was 39 flat bullets, which gives no priority signal and produces
  keyword-avoidance instead of writing. Now tiered: shape and rhythm, then substance
  and stance, then diction, plus a "the costume is not the fix" tier.
- Self-critique gained a fourth reviewer, the **author's colleague**: is there
  anything here only this author could have written?
- Audit template reports shape and rhythm metrics before/after, and lists the
  author material added with its provenance.
- Removed the "Quick reference" section (it restated the Rewrite procedure that
  immediately followed it) and moved the anti-jargon rules to
  `references/anti-jargon.md`.

### Changed: the linter's reporting
- Report prints three metric lines (rhythm / shape / lexicon) with the targets
  inline, instead of one line without them. The score is labeled "floor points",
  since it is no longer a pure per-1000-word density.
- `resolve_scoring()` exposes `doc_hit_points` and `category_cap` for `.humanvoicerc`
  override, with per-key fallback like the other knobs.

### Added: examples and harness
- `examples/modern-ai-before.md` / `-after.md` / `-notes.md`: the hard case, which
  no existing example covered. 19.9 → 0.0, words −16%, no fact changed; sentences
  ≤8 words 0% → 42%, mid-band 73% → 42%, CoV 0.33 → 0.65. The notes record that an
  earlier pass wrote "three or four metadata predicates" where the source said
  "several", and that it was reverted, that is exactly the invented specificity
  principle 3 forbids.
- Every shipped "after" example is now gated on the rhythm targets too, so no
  example can demonstrate a clean score with metronome prose.
- `eval/detector_harness.py`: `call_detector` was a stub that guaranteed the online
  path had never been exercised. Now implemented for GPTZero, Originality.ai, and
  Sapling from their published request shapes, clearly labeled unverified against a
  live API, failing per-file with ERR(...) rather than crashing. New `--pairs` mode
  scores the shipped before/after pairs and reports the mean drop in p(AI), the
  measurement you actually want. Full runs print mean p(AI) per class, so a
  detector that does not separate the corpus is visible as such.
- `make detector` target. 569 stress checks (was 510), 12 pytest cases (was 10).

### Honesty
`EVAL.md` leads with what was wrong with its own previous headline number. The
README states, per detector family, what a rewrite moves and what it does not, and
says plainly that no legitimate method makes text undetectable, against a
classifier trained on humanizer output, published accuracy on rewritten text is
around 97%. The comparison section now covers three separate markets (prose
linters, detectors, humanizers) instead of conflating them, and explains why the
humanizer market's tricks lose on their own terms before the ethics come up.

### Linter: the "second dialect" (v0.4.1 patterns)
- `rule_of_three` now also catches **noun-phrase** triads ("encryption at rest,
  row-level access control, and audit logging") that the single-word pattern
  missed; gated to fire only when a document stacks 2+ (a lone enumeration is
  left alone). Measured 14/24 AI vs 1/34 human on the corpus.
- New `false_agency` pattern for the "[inanimate thing] lives/sits in [place]"
  locative ("a project living in five tools", "the logic lives in the
  controller").
- Documented the second-dialect tells a regex shouldn't chase (the ", and" splice
  rhythm and stacked "[noun] is [noun]" copulas, both too common in careful and
  ESL writing to flag) in `references/structural-craft.md`, and rewrote the
  shipped "after" examples to remove all four (they had become a tidier AI
  dialect: ", and" splices, copular stacks, triads, and a "project living in"
  locative).

### Linter: craft tells (v0.4.1 patterns)
- New `cowardly_passive` category: evasive actor-hiding passives ("it can be seen
  that", "the decision was made to", "mistakes were made"), distinct from the
  passive-voice density check.
- New `whether you're X or Y` antithesis pattern; resumptive connectives ("in
  terms of", "about", "in the context of") added to `soft_filler` at
  Tier-C weight (common in careful/ESL writing, so a whisper not a verdict).
- New `references/structural-craft.md`: the generative companion (vary length and
  density, don't follow the outline, get specific, cowardly passives, emotional
  range, self-correction traces) drawn from `oberskills`' deep-craft material.
- Skill frontmatter: added a `when_to_use` routing field.

### Linter: evidence-based recalibration (v0.4.0 patterns)
- Retiered category weights by what readers **cite** as a tell, not what a
  keyword scanner **matches**. Source: a ~90k-post Reddit study
  (`JCarterJohnson/vibecoded-design-tells`, MIT) plus the `oberskills` write
  skill (`ryanthedev/oberskills`, MIT). The two diverge: generic words
  (`however`/`thus`/`nuanced`/`comprehensive`/`robust`/`when it comes to`) match
  often but are cited ~0% of the time. See `references/cited-vs-matched.md`.
- Split generic high-match/low-cited diction into a new `soft_filler` category at
  weight 0.5 (was weight 1.0 inside `filler`); lowered `transitions` 1.0→0.5.
  Raised the structural/artifact tells readers actually catch: `antithesis`
  1.5→2.0, `bold_bullets` 1.5→2.0; added `sycophancy` and `aidiolect` at 2.0.
- Tightened the em-dash density floor 2.0→1.5 per 1k words (AI uses the em-dash
  at 2–5× the human rate, Pangram Labs).

### Linter: new tell categories
- Lexical: `sycophancy` ("great question!", reflexive "you're absolutely right"),
  `aidiolect` (multi-word phrases overused at 10,000×+: "a testament to", "the
  complex interplay", "faced many challenges"), `cliche_metaphor`
  (foundation/landscape/journey/double-edged-sword frames), `internet_tells` (the
  2025–26 cadence: "load-bearing", "honestly?", "it's giving"),
  `significance_inflation` ("opens new avenues", "cannot be overstated").
- Structural: `five_paragraph_shape` (intro/three-body/"in conclusion" mold),
  `hypophora` (ask-then-immediately-answer), `superlative_creep` (absolutes with
  no number nearby), `svo_monotony` (a long run of Subject-Verb-Object openers),
  `name_selection` (Emily/Sarah/"Dr." defaults; muted outside creative/casual),
  `over_correction` (the anti-AI costume: forced lowercase + sprinkled slang).
- ~165 new lexical entries across the new and existing lists; expanded
  `antithesis_patterns`, `hedging`, `redundancy`, and `vague_attribution`.

### Evaluation, rigor
- New hard-negative classes: `eval/corpus/esl_formal/` (careful non-native and
  formal-human samples, labeled human, that real detectors over-flag) with a
  dedicated **ESL-FPR** metric; `eval/corpus/over_corrected/` (the anti-AI
  costume, held out of the binary AUC and scored on its own recall).
- Cited-ranking correlation test (`eval/tests/test_calibration.py`): the category
  weights must keep a strong rank correlation with the Reddit cited ranking.
- Expanded the balanced corpus and refreshed the golden metrics + `EVAL.md`.

### Documentation
- New references: `cited-vs-matched.md`, `over-correction.md`,
  `discourse-and-structure.md`; extended `ai-tells.md` (Pangram detector entry,
  new BAD→GOOD pairs, rhetoric-calibration rule). New example pairs
  (over-corrected, cliché-metaphor). MIT attribution to both source repos.

### Linter: architecture & quality
- Split the 1700-line `detect_ai_prose.py` monolith into a `human_voice_linter`
  package (util, defaults, hit, patterns, textutil, directives, checks, score,
  analyze, report, autofix, config, schema, api, cli). `detect_ai_prose.py` is now
  a thin entry-point shim, so the documented invocation and the importlib API
  surface are unchanged.
- Single source of truth for thresholds, category weights, and verdict bands
  (`defaults.DEFAULTS`); the shipped JSON mirrors it and a drift guard keeps them
  consistent. Removed the stale code-vs-JSON fallback divergence.
- Added type hints to the public API and the `Hit` model; surfaced previously
  silent regex-compile failures as warnings.
- New `schema.validate()` config validator: malformed `.humanvoicerc`/patterns
  values are reported on stderr (non-fatal) instead of being silently swallowed.

### Linter: new features
- Per-tell column/character spans (`col`/`end_line`/`end_col` on hits, surfaced in
  JSON and SARIF) for checks whose match geometry matches the source; document-level
  findings carry `scope: "document"`.
- Inline ignore directives: `<!-- human-voice: ignore [categories] -->` (trailing,
  next-line, or `ignore-start`/`ignore-end` block); directives inside code fences
  are inert.

### Evaluation
- Extracted shared `eval/lib.py` (loaders, one canonical metrics/auc/sweep,
  per-register breakdown, deterministic bootstrap CIs, regression comparator,
  corpus validation); the three scripts are thin consumers.
- `run_eval.py --check` / `ablation.py --check` regression-gate against the
  committed golden JSON (CI fails on metric drift instead of silently overwriting).
- Expanded the corpus to 36 balanced samples (18/18) covering every register,
  including the previously empty `creative` and human `business` samples.

### Dev tooling
- Added `pyproject.toml` with ruff + mypy + pytest (dev-only extra; runtime stays
  pure stdlib), a `quality` CI job, `make eval-check`/`make quality`, and pytest
  unit tests for the eval math.

### Linter: detection
- New checks: chatbot-scaffold phrases, over-signposting glue, "it depends"
  non-conclusions, multi-word AI openers, "worth noting" family, hook openers,
  passive-voice density, -ly adverb density, nominalization density,
  rhetorical-question density, colon-summary reflex, paired em-dash asides,
  paragraph-length uniformity, list-item uniformity, circular conclusion, and
  parallel-structure runs.
- New report metrics: em/en-dash profile, punctuation profile, Yule's K,
  sentence-opener entropy, paragraph-length CoV, list-item CoV.
- Broadened rule-of-three (optional Oxford comma, `and`/`or`); MATTR moving-window
  type-token ratio; spaced double-hyphen counted as an em-dash.

### Linter: fewer false positives
- Rule-of-three skips proper-noun lists (`Python, Django, and Flask`).
- En-dash number ranges (`2024–2025`) no longer count as em-dashes.
- Dialect drift skips code identifiers (`analyse()`, `Color.RED`, `OPTIMISE_FLAGS`).
- `context_exceptions` protect legitimate fixed phrases (`test harness`,
  `vital signs`); cited attribution (`studies show [1]`) is not flagged as vague;
  redundancy is skipped inside quotes and headings; density checks have a
  minimum-word floor.

### Linter: scoring, API & config
- Category weights, score bands, and thresholds are externalized to
  `ai_prose_patterns.json`; verdict bands (`clean`/`watch`/`strong-tell`) in text
  and JSON; `schema_version` and per-hit `severity` in JSON.
- New flags: `--fail-over` (CI gate), `--baseline`/compare, `--fix` and
  `--fix-dry-run` (autofix safe swaps), `--sarif`, `--enable`/`--disable`,
  `--threshold`, `--quiet`, `--explain`, `--max-examples`, `--recursive`,
  `--no-config`; multiple inputs and directory walking.
- Importable `lint()` library API; auto-discovered `.humanvoicerc` project config;
  project-specific `protected_terms` allowlist.
- Performance: cached regex compilation, `LineMap` bisect for line lookups,
  single-pass abbreviation handling, tokenize-once.
- Four new registers: `email`, `release_notes`, `ux_microcopy`, `tutorial`.

### Methodology & docs
- Catalog expanded with the tells above plus weak intensifiers, gratuitous
  reformulation, hype verbs, over-explaining, parenthetical over-qualification,
  chatbot politeness, and emoji-as-bullet decoration.
- Self-critique loop gains a three-persona review, a 0–2 dimension rubric,
  measurable targets, an A/B-against-original check, and a fixed-point stop rule.
- Anti-hallucination protocol gains a structured four-bucket claim diff
  (added/strengthened/weakened/dropped), a completeness check, quote/citation
  integrity, and an explicit generate-mode path.
- Detector-science section updated: modern detectors (Binoculars, Ghostbuster,
  DNA-GPT, GLTR, RADAR), the ESL false-positive finding (Liang et al. 2023), and
  qualified watermarking/curvature claims.
- New examples per register, a generate-mode example, a refusal-to-fabricate
  example, a restraint case, and an annotated walkthrough.
- Evaluation harness (`eval/`) with a labeled corpus, precision/recall/FPR
  measurement, an ablation script, an offline-safe external-detector scaffold,
  and `EVAL.md`.

## [0.1.0]
- Initial release: skill instructions, AI-tells catalog, style guide, regex
  linter with the patterns file, before/after example pair, and stress test.
