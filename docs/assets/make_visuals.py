#!/usr/bin/env python3
"""Regenerate the README graphics, and the examples table, from the repository's own data.

Every number in a chart is read from the source it describes: sentence lengths
from the shipped example pair, scores from eval/results.json, detector counts
from eval/detector_local_results.json. A chart cannot drift from the eval, since
rerunning this rebuilds it from the committed results.

    python3 docs/assets/make_visuals.py
    python3 docs/assets/make_visuals.py --check   # exit 1 if a committed chart is stale

Writes a light and a dark variant of each SVG next to this file, and rewrites the
score table in docs/examples.md between its marker comments. Standard library only.
"""
from __future__ import annotations

import json
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(ROOT, "skills", "human-voice", "scripts")
sys.path.insert(0, SCRIPTS)

import human_voice_linter as L  # noqa: E402
from human_voice_llm.providers import PROVIDERS  # noqa: E402

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

THEMES = {
    "light": {"ink": "#1F2328", "muted": "#59636E", "faint": "#D1D9E0", "card": "#F6F8FA",
              "edge": "#E1E6EB", "machine": "#A5AEB8", "human": "#4F46E5", "human_soft": "#EEF0FF",
              "band": "#EDF0F3", "ok": "#1A7F37", "on_accent": "#FFFFFF"},
    "dark": {"ink": "#E6EDF3", "muted": "#9198A1", "faint": "#3D444D", "card": "#151B23",
             "edge": "#262C36", "machine": "#5D6570", "human": "#8B93FF", "human_soft": "#1D1C45",
             "band": "#1C222A", "ok": "#3FB950", "on_accent": "#0D1117"},
}


def text(x, y, s, size=14, fill="ink", weight=400, anchor="start", family=SANS, t=None, extra=""):
    color = t[fill] if t and fill in t else fill
    return ('<text x="%s" y="%s" font-family="%s" font-size="%s" font-weight="%s" fill="%s" '
            'text-anchor="%s"%s>%s</text>' % (x, y, family, size, weight, color, anchor,
                                              extra, escape(s)))


def svg(w, h, body, title):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
            'role="img" aria-label="%s"><title>%s</title>\n%s\n</svg>\n'
            % (w, h, w, h, escape(title), escape(title), "\n".join(body)))


def card(w, h, t):
    return '<rect x="0.5" y="0.5" width="%d" height="%d" rx="14" fill="%s" stroke="%s"/>' % (
        w - 1, h - 1, t["card"], t["edge"])


def wrap(items, width_px, size, sep=" · "):
    """Pack whole items into lines, so no line starts or ends on a separator."""
    per_line = max(8, int(width_px / (size * 0.53)))
    lines, cur = [], ""
    for item in items:
        cand = item if not cur else cur + sep + item
        if cur and len(cand) > per_line:
            lines.append(cur)
            cur = item
        else:
            cur = cand
    return lines + ([cur] if cur else [])


# ---------------------------------------------------------------------------
# Logo: a speech bubble whose waveform starts flat and even, then turns bursty.
# ---------------------------------------------------------------------------

MACHINE_BARS = (34, 34, 34, 34)
HUMAN_BARS = (20, 62, 38, 12, 50)


def mark(t, x=0, y=0, scale=1.0):
    g = ['<g transform="translate(%s %s) scale(%s)">' % (x, y, scale),
         '<path d="M26 0 H118 A26 26 0 0 1 144 26 V86 A26 26 0 0 1 118 112 H52 L26 136 L30 112 '
         'H26 A26 26 0 0 1 0 86 V26 A26 26 0 0 1 26 0 Z" fill="%s" stroke="%s" stroke-width="3"/>'
         % (t["human_soft"], t["human"])]
    bars = [(h, t["machine"]) for h in MACHINE_BARS] + [(h, t["human"]) for h in HUMAN_BARS]
    bw, gap = 8, 6
    x0 = (144 - (len(bars) * bw + (len(bars) - 1) * gap)) / 2
    for i, (h, color) in enumerate(bars):
        g.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="4" fill="%s"/>'
                 % (x0 + i * (bw + gap), 56 - h / 2, bw, h, color))
    g.append("</g>")
    return "\n".join(g)


def logo(t):
    body = [mark(t, 8, 22, 1.0),
            '<text x="182" y="104" font-family="%s" font-size="68" font-weight="700" '
            'letter-spacing="-1.5"><tspan fill="%s">human</tspan><tspan fill="%s">-</tspan>'
            '<tspan fill="%s">voice</tspan></text>' % (SANS, t["ink"], t["machine"], t["human"]),
            text(185, 142, "Writing that reads like a person wrote it. Every fact intact.",
                 size=20, fill="muted", t=t)]
    return svg(760, 180, body, "human-voice")


def logo_mark(t):
    return svg(160, 160, [mark(t, 8, 12, 1.0)], "human-voice")


# ---------------------------------------------------------------------------
# Rhythm: sentence lengths of the shipped modern-AI example, before and after.
# ---------------------------------------------------------------------------

def sentence_lengths(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    prose = L.prose_for_metrics(L.strip_code(L.blank_frontmatter(L.normalize_text(raw))))
    lengths = [len(L.WORD_RE.findall(s)) for s in L.sentences(prose)]
    result = L.lint(raw, "technical", None, L.load_patterns())
    return lengths, result


def rhythm(t):
    ex = os.path.join(ROOT, "skills", "human-voice", "examples")
    before, rb = sentence_lengths(os.path.join(ex, "modern-ai-before.md"))
    after, ra = sentence_lengths(os.path.join(ex, "modern-ai-after.md"))
    W, H = 880, 400
    body = [card(W, H, t),
            text(32, 50, "Same facts. Different rhythm.", size=24, weight=700, t=t),
            text(32, 76, "Words per sentence in a paragraph a current model wrote, before and after "
                 "the rewrite. No filler in either.", size=14, fill="muted", t=t)]
    top, plot_h, ymax = 116, 190, 35

    def panel(x0, lengths, res, color, label):
        pw = 380
        out = [text(x0, top - 6, label, size=15, weight=600, t=t)]
        y = lambda v: top + 20 + plot_h - v * plot_h / ymax  # noqa: E731
        out.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s"/>'
                   % (x0, y(26), pw, y(12) - y(26), t["band"]))
        for v in (0, 12, 26):
            out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"%s/>'
                       % (x0, x0 + pw, y(v), y(v), t["faint"],
                          "" if v == 0 else ' stroke-dasharray="3 4"'))
            out.append(text(x0 - 8, y(v) + 4, str(v), size=11, fill="muted", anchor="end", t=t))
        slot = pw / max(len(before), len(after))
        bw = slot * 0.62
        for i, v in enumerate(lengths):
            bx = x0 + i * slot + (slot - bw) / 2
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                       % (bx, y(v), bw, y(0) - y(v), color))
        m = res["metrics"]
        stats = "score %.1f %s  ·  under 9 words %d%%  ·  12 to 26 band %d%%" % (
            res["score"], res["verdict"], round(100 * m["short_sentence_ratio"]),
            round(100 * m["mid_band_ratio"]))
        out.append(text(x0, y(0) + 30, stats, size=12.5, fill="muted", t=t))
        return out

    body += panel(64, before, rb, t["machine"], "Before")
    body += panel(476, after, ra, t["human"], "After")
    body.append(text(W - 32, H - 22, "Shaded: the 12 to 26 word band model prose collapses into. "
                     "Source: skills/human-voice/examples/modern-ai-*.md", size=11.5, fill="muted",
                     anchor="end", t=t))
    return svg(W, H, body, "Sentence lengths before and after a human-voice rewrite")


# ---------------------------------------------------------------------------
# Loop: how a rewrite is gated.
# ---------------------------------------------------------------------------

def loop(t):
    W, H = 880, 300
    n_checks = len(L.KNOWN_CATEGORIES)
    nodes = [("Draft", "your text or a brief", False),
             ("Lint", "%d checks, shape first" % n_checks, False),
             ("Rewrite", "any model, full skill", True),
             ("Check", "score, facts, detector", False),
             ("Ship", "clean, facts intact", False)]
    bw, bh, gap, x0, y0 = 144, 78, 28, 26, 74
    body = [card(W, H, t),
            text(32, 44, "Every pass has to earn its way out", size=22, weight=700, t=t),
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="%s"/>'
            '</marker></defs>' % t["muted"]]
    centers = []
    for i, (title, sub, accent) in enumerate(nodes):
        x = x0 + i * (bw + gap)
        centers.append(x + bw / 2)
        fill = t["human"] if accent else t["card"]
        stroke = t["human"] if accent else t["faint"]
        body.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="%s" stroke="%s" '
                    'stroke-width="1.5"/>' % (x, y0, bw, bh, fill, stroke))
        body.append(text(x + bw / 2, y0 + 33, title, size=17, weight=700, anchor="middle",
                         fill=t["on_accent"] if accent else t["ink"], t=t))
        body.append(text(x + bw / 2, y0 + 55, sub, size=12, anchor="middle",
                         fill=t["on_accent"] if accent else t["muted"], t=t))
        if i:
            body.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.6" '
                        'marker-end="url(#a)"/>' % (x - gap + 3, y0 + bh / 2, x - 4, y0 + bh / 2,
                                                   t["muted"]))
    # Feedback arc from Check back to Rewrite.
    yb = y0 + bh
    body.append('<path d="M%d %d C %d %d, %d %d, %d %d" fill="none" stroke="%s" stroke-width="1.6" '
                'stroke-dasharray="5 4" marker-end="url(#a)"/>'
                % (centers[3], yb + 4, centers[3], yb + 62, centers[2], yb + 62, centers[2], yb + 6,
                   t["human"]))
    body.append(text((centers[2] + centers[3]) / 2, yb + 80, "not yet: the report goes back to the model",
                     size=13, fill="human", anchor="middle", t=t))
    notes = ["A pass ships only when the score is clean, every number, link, code span and citation",
             "survived, and a configured detector clears. Two passes without progress stop the loop."]
    for i, line in enumerate(notes):
        body.append(text(32, H - 42 + i * 19, line, size=13, fill="muted", t=t))
    return svg(W, H, body, "The human-voice rewrite loop")


# ---------------------------------------------------------------------------
# Results: the measured claims, read from the committed eval output.
# ---------------------------------------------------------------------------

def results(t):
    with open(os.path.join(ROOT, "eval", "results.json"), encoding="utf-8") as fh:
        ev = json.load(fh)
    with open(os.path.join(ROOT, "eval", "detector_local_results.json"), encoding="utf-8") as fh:
        det = json.load(fh)
    rw = ev["modern_ai_rewritten"]
    pairs_before = sum(1 for p in det["pairs"] if _flagged(p["before"], det))
    pairs_after = sum(1 for p in det["pairs"] if _flagged(p["after"], det))
    n_det = len(det["modern_pairs"]) + len(det["pairs"])
    det_before = det["modern_flagged_before"] + pairs_before
    det_after = det["modern_flagged_after"] + pairs_after
    hn = ev["hard_negatives"]["esl_formal"]
    rows = [
        ("Current-model drafts the linter flags", rw["flagged_before"], rw["flagged_after"], rw["n"]),
        ("Documents an independent AI classifier flags", det_before, det_after, n_det),
    ]
    W, H = 880, 380
    body = [card(W, H, t),
            text(32, 48, "Measured on the repo's own eval, not asserted", size=22, weight=700, t=t),
            text(32, 72, "Before and after the rewrite. Lower is better.", size=14, fill="muted", t=t)]
    bar_x, bar_w = 96, 640
    y = 104
    for label, b, a, n in rows:
        body.append(text(32, y + 14, label, size=15, weight=600, t=t))
        for j, (val, color, tag) in enumerate(((b, t["machine"], "before"), (a, t["human"], "after"))):
            yy = y + 28 + j * 26
            w = max(3, bar_w * val / n)
            body.append('<rect x="%d" y="%d" width="%d" height="18" rx="4" fill="%s"/>'
                        % (bar_x, yy, bar_w, t["band"]))
            body.append('<rect x="%d" y="%d" width="%.1f" height="18" rx="4" fill="%s"/>'
                        % (bar_x, yy, w, color))
            body.append(text(bar_x - 10, yy + 14, tag, size=12, fill="muted", anchor="end", t=t))
            body.append(text(bar_x + bar_w + 12, yy + 14, "%d of %d" % (val, n), size=13.5,
                             weight=700 if j else 400, fill="ink" if j else "muted", t=t))
        y += 100
    body.append(text(32, y + 10, "Mean linter score on those drafts: %.1f before, %.1f after." % (
        rw["mean_before"], rw["mean_after"]), size=14, t=t))
    body.append(text(32, y + 34, "Careful non-native writers wrongly flagged: %d of %d. AI detectors "
                     "are known to over-flag them." % (hn["flagged"], hn["n"]), size=14, t=t))
    body.append(text(W - 32, H - 20, "Sources: eval/results.json, eval/detector_local_results.json",
                     size=11.5, fill="muted", anchor="end", t=t))
    return svg(W, H, body, "human-voice evaluation results")


def _flagged(doc, det):
    cls = doc.get("classifiers") or {}
    return any((cls.get(name) or {}).get("says_ai") for name in det["usable_classifiers"])


# ---------------------------------------------------------------------------
# Everywhere: one skill, four ways in.
# ---------------------------------------------------------------------------

def everywhere(t):
    W, H = 880, 494
    short = {"anthropic": "Anthropic", "openai": "OpenAI", "azure": "Azure", "gemini": "Gemini",
             "vertex": "Vertex AI", "bedrock": "Bedrock", "mistral": "Mistral", "groq": "Groq",
             "deepseek": "DeepSeek", "xai": "xAI", "openrouter": "OpenRouter",
             "together": "Together", "fireworks": "Fireworks", "cohere": "Cohere",
             "ollama": "Ollama", "lmstudio": "LM Studio", "compat": "any OpenAI-compatible server"}
    missing = set(PROVIDERS) - set(short)
    if missing:
        raise SystemExit("add a short name for provider(s): %s" % ", ".join(sorted(missing)))
    groups = [
        ("Coding agents", ["Claude Code", "Codex", "Gemini CLI", "Cursor", "GitHub Copilot",
                           "Windsurf", "Cline", "opencode", "Aider"], "python3 install.py"),
        ("Model APIs", [short[k] for k in PROVIDERS], "humanize.py draft.md -m <provider/model>"),
        ("MCP clients", ["Cursor", "VS Code", "Windsurf", "Cline", "Zed", "Claude Desktop",
                         "Gemini CLI", "Codex", "opencode"], "install.py --mcp <client>"),
        ("Chat apps", ["ChatGPT projects", "custom GPTs", "Gemini Gems", "Claude projects"],
         "humanize.py --print-prompt chat"),
    ]
    cw, ch = 340, 184
    cx, cy = W / 2, 60 + (H - 60) / 2
    spots = [(28, 70), (W - 28 - cw, 70), (28, H - 28 - ch), (W - 28 - cw, H - 28 - ch)]
    body = [card(W, H, t),
            text(32, 46, "One skill. Every major agent and model.", size=22, weight=700, t=t)]
    for (x, y) in spots:
        ex = x + cw if x < cx else x
        ey = y + ch / 2
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5" '
                    'stroke-dasharray="4 4"/>' % (ex, ey, cx, cy, t["faint"]))
    body.append('<rect x="%.1f" y="%.1f" width="120" height="64" rx="32" fill="%s"/>'
                % (cx - 60, cy - 32, t["human"]))
    body.append(text(cx, cy - 3, "SKILL.md", size=16, weight=700, anchor="middle", family=MONO,
                     fill=t["on_accent"], t=t))
    body.append(text(cx, cy + 17, "one set of rules", size=11.5, anchor="middle",
                     fill=t["on_accent"], t=t))
    for (x, y), (title, names, cmd) in zip(spots, groups):
        body.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="%s" stroke="%s"/>'
                    % (x, y, cw, ch, t["card"], t["faint"]))
        body.append(text(x + 18, y + 30, title, size=16, weight=700, t=t))
        lines = wrap(names, cw - 36, 13)
        if len(lines) > 5:
            raise SystemExit("%s does not fit its card" % title)
        for i, line in enumerate(lines):
            body.append(text(x + 18, y + 54 + i * 19, line, size=13, fill="muted", t=t))
        body.append('<rect x="%d" y="%d" width="%d" height="26" rx="6" fill="%s"/>'
                    % (x + 14, y + ch - 38, cw - 28, t["band"]))
        body.append(text(x + 24, y + ch - 20, cmd, size=12, family=MONO, t=t))
    return svg(W, H, body, "human-voice runs in coding agents, model APIs, MCP clients and chat apps")


# ---------------------------------------------------------------------------
# Examples gallery: live scores for every shipped pair, never typed by hand.
# ---------------------------------------------------------------------------

EXAMPLES_DOC = os.path.join(ROOT, "docs", "examples.md")
TABLE_START, TABLE_END = "<!-- examples-table:start -->", "<!-- examples-table:end -->"
# (stem, register, what the pair shows, annotation file or None)
PAIRS = (
    ("modern-ai", "technical", "Fluent prose a current model writes, with no filler at all",
     "modern-ai-notes.md"),
    ("syntax-signature", "technical", "No filler, no em-dashes; machine-made through its grammar",
     "syntax-signature-notes.md"),
    ("architecture", "technical", "A design doc whose plan gives it away", "architecture-notes.md"),
    ("", "technical", "2023-era slop in a technical report", "annotated-walkthrough.md"),
    ("marketing", "marketing", "Puffery, hype and fake attribution on a landing page", None),
    ("email", "email", "Jargon, padding and a buried ask", None),
    ("academic", "academic", "Vague attribution, stacked hedges, no commitment", None),
    ("casual", "casual", "Listicle padding and meta-commentary in a blog post", None),
    ("cliche-metaphor", "business", "Metaphor frames doing the work of concrete language", None),
    ("over-corrected", "technical", "The anti-AI costume: forced lowercase, slang, fragments", None),
)


TITLES = {"modern-ai": "Modern AI", "syntax-signature": "Syntax signature",
          "architecture": "Design doc", "": "Technical report", "marketing": "Landing page",
          "email": "Email", "academic": "Academic", "casual": "Blog post",
          "cliche-metaphor": "Cliché metaphors", "over-corrected": "Over-corrected"}


def examples_table():
    ex = os.path.join(ROOT, "skills", "human-voice", "examples")
    patterns = L.load_patterns()
    link = "../skills/human-voice/examples/"
    rows = ["| Pair | Register | Before | After | What it shows |", "|---|---|--:|--:|---|"]
    for stem, register, what, notes in PAIRS:
        names = [("%s-%s.md" % (stem, half)) if stem else "%s.md" % half
                 for half in ("before", "after")]
        scores = []
        for name in names:
            with open(os.path.join(ex, name), encoding="utf-8") as fh:
                res = L.lint(fh.read(), register, None, patterns)
            scores.append("%.1f" % res["score"])
        title = TITLES.get(stem, stem.replace("-", " "))
        cell = "[%s](%s%s) → [after](%s%s)" % (title, link, names[0], link, names[1])
        if notes:
            cell += " · [notes](%s%s)" % (link, notes)
        rows.append("| %s | `%s` | %s | %s | %s |" % (cell, register, scores[0], scores[1], what))
    return "\n".join(rows)


def render_examples_doc():
    with open(EXAMPLES_DOC, encoding="utf-8") as fh:
        doc = fh.read()
    head, rest = doc.split(TABLE_START, 1)
    _, tail = rest.split(TABLE_END, 1)
    return "%s%s\n%s\n%s%s" % (head, TABLE_START, examples_table(), TABLE_END, tail)


def main(argv=None):
    check = "--check" in (sys.argv[1:] if argv is None else argv)
    stale = []
    for name, fn in (("logo", logo), ("logo-mark", logo_mark), ("rhythm", rhythm), ("loop", loop),
                     ("results", results), ("everywhere", everywhere)):
        for theme, palette in THEMES.items():
            path = os.path.join(HERE, "%s-%s.svg" % (name, theme))
            content = fn(palette)
            rel = os.path.relpath(path, ROOT)
            if check:
                try:
                    with open(path, encoding="utf-8") as fh:
                        if fh.read() != content:
                            stale.append(rel)
                except OSError:
                    stale.append(rel)
                continue
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(rel)
    rel = os.path.relpath(EXAMPLES_DOC, ROOT)
    content = render_examples_doc()
    if check:
        with open(EXAMPLES_DOC, encoding="utf-8") as fh:
            if fh.read() != content:
                stale.append(rel)
    else:
        with open(EXAMPLES_DOC, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(rel)
    if stale:
        print("stale charts (run python3 docs/assets/make_visuals.py):\n  " + "\n  ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
