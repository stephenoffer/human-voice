#!/usr/bin/env python3
"""Stress / robustness suite for detect_ai_prose.py.

Throws 200+ adversarial inputs at the linter and asserts: (a) it never raises,
(b) metrics stay well-formed, (c) known tells are caught and clean text is clean,
(d) the CLI handles bad input (binary, directories, missing/malformed patterns)
with the right exit codes. Run: python3 tests/stress_test.py
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "human-voice", "scripts", "detect_ai_prose.py")
PATTERNS = os.path.join(ROOT, "skills", "human-voice", "scripts", "ai_prose_patterns.json")
EXAMPLES = os.path.join(ROOT, "skills", "human-voice", "examples")

spec = importlib.util.spec_from_file_location("dap", SCRIPT)
dap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dap)
PAT = dap.load_patterns(PATTERNS)

passed = 0
failed = 0
failures = []


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        failures.append("%s %s" % (name, ("- " + detail) if detail else ""))


def run_analyze(name, text, register="technical", dialect=None):
    """Assert analyze/score/render never raise and return well-formed output."""
    try:
        hits, report, wc = dap.analyze(text, register, dialect, PAT)
        sc = dap.score(hits, wc)
        rendered = dap.render_text(name, register, dialect, hits, report, wc, sc)
        payload = json.dumps({"hits": [h.as_dict() for h in hits],
                              "metrics": report, "score": sc})
        ok = (isinstance(sc, float) and sc >= 0 and isinstance(rendered, str)
              and wc >= 0 and isinstance(payload, str))
        cov = report.get("burstiness_cov")
        ttr = report.get("ttr")
        ok = ok and (cov is None or cov >= 0) and (ttr is None or 0 <= ttr <= 1)
        check("analyze:" + name, ok, "malformed output")
        return hits, report, wc, sc
    except Exception as exc:  # noqa: BLE001 - the whole point is to catch any crash
        check("analyze:" + name, False, "RAISED %r" % exc)
        return [], {}, 0, 0.0


def cats(hits):
    return {h.category for h in hits}


# ---------------------------------------------------------------------------
# 1. Pathological / hostile raw strings (must not crash)
# ---------------------------------------------------------------------------
pathological = {
    "empty": "",
    "single_space": " ",
    "only_newlines": "\n\n\n\n",
    "only_tabs": "\t\t\t",
    "null_bytes": "a\x00b\x00c the model is robust",
    "control_chars": "\x01\x02\x07 text \x1b[31m delve",
    "one_word": "delve",
    "one_char": "x",
    "one_long_word": "a" * 100000,
    "no_spaces": "leveragerobustseamless" * 50,
    "huge_repeat": ("the model is robust and seamless. " * 5000),
    "only_punct": "!!!??? ... ;;; --- ***",
    "only_numbers": "123 456 789 3.14 2.71 1,000,000",
    "only_emoji": "🚀🔥✨💡🎉" * 20,
    "rtl_text": "مرحبا بالعالم this is robust",
    "cjk": "这是一个测试 delve into the 系统",
    "combining": "áéí robust",
    "zero_width": "ro​bust se‌amless",
    "mixed_scripts": "Ωmega δelta robust λeverage",
    "smart_quotes": "“It’s important to note” that we delve—deeply—into this.",
    "em_dash_spam": "a—b—c—d—e—f—g—h—i—j—k—l",
    "en_dash_spam": "a–b–c–d–e–f–g–h–i–j",
    "double_hyphen": "well--known fact--that delve--ing happens",
    "windows_crlf": "Line one.\r\nLine two is robust.\r\nLine three delves in.\r\n",
    "mac_cr": "Line one.\rLine two robust.\rThree.",
    "bom_prefix": "﻿The model is robust and seamless.",
    "trailing_ws": "delve   \n   robust   \n",
    "vertical_tab": "a\x0bb\x0cc robust",
    "very_long_sentence": "word " * 5000 + ".",
    "all_caps": "DELVE INTO THE ROBUST SEAMLESS LANDSCAPE",
    "leetspeak": "d3lv3 r0bust s34mless",
    "html_entities": "&amp; &lt; &gt; delve &nbsp; robust",
    "nested_quotes": '"He said \'delve\' robustly," she noted.',
    "math_symbols": "x² + y² = z² ∑∏∫ robust ≤ ≥ ≠",
    "currency": "$100 €50 £30 ¥1000 robust pricing",
}
for name, text in pathological.items():
    run_analyze("path_" + name, text)

# ---------------------------------------------------------------------------
# 2. Adversarial Markdown (must not be miscounted as prose / must not crash)
# ---------------------------------------------------------------------------
markdown_cases = {
    "unterminated_fence": "Intro text.\n```python\ncode that never closes\ndelve here\n",
    "tilde_fence": "Before.\n~~~\nfenced with tildes, robust\n~~~\nAfter is clean.",
    "indented_code": "Para.\n\n    indented code block robust\n    more code\n\nReal prose here.",
    "inline_code_filler": "Use the `leverage` and `robust` functions; they delve nicely.",
    "headings_only": "# Robust Title\n## Seamless Subtitle\n### Cutting-Edge Section",
    "setext_heading": "Robust Title\n===========\n\nBody text that is fine.",
    "table": "| Name | Value |\n|------|-------|\n| robust | seamless |\n| delve | leverage |",
    "table_no_outer_pipe": "Name | Value\n---|---\nrobust | seamless",
    "blockquote": "> It's important to note that we delve robustly.\n> Moreover, seamless.",
    "nested_list": "- Item one\n  - Sub robust\n    - Deeper seamless\n- Item two",
    "ordered_list": "1. First robust point.\n2. Second seamless point.\n3. Third.",
    "bold_bullets": "- **Performance:** fast\n- **Scale:** big\n- **Security:** safe\n- **Cost:** low",
    "underscore_bold_bullets": "- __Speed:__ fast\n- __Scale:__ big\n- __Safe:__ yes",
    "links": "See [the robust docs](https://example.com/delve--seamless) for more.",
    "bare_url_dashes": "Visit https://foo.com/a--b--c--d and http://x.io/delve-robust now.",
    "image": "![a robust diagram](img/delve--chart.png) follows the text.",
    "footnotes": "Text with a note.[^1]\n\n[^1]: The robust footnote delves here.",
    "html_tags": "<div class='robust'>delve</div> and <span>seamless</span> text.",
    "mixed_md": "# Title\n\n- **A:** x\n- **B:** y\n\n> quote\n\n| t | u |\n|---|---|\n\nProse paragraph that reads fine and naturally varies its length a bit here.",
    "hr_spam": "Para one.\n\n---\n\nPara two.\n\n***\n\nPara three.\n\n___\n\nPara four.",
    "checkbox_list": "- [ ] todo robust\n- [x] done seamless\n- [ ] pending delve",
    "fence_with_lang": "```javascript\nconst leverage = robust;\n```\nClean prose after.",
    "many_fences": "a\n```\nx\n```\nb\n```\ny\n```\nc robust prose.",
    "code_only": "```\nall code\nno prose\nrobust seamless leverage\n```",
    "yaml_frontmatter": "---\ntitle: Robust\ntags: [delve]\n---\n\nActual body prose here.",
}
for name, text in markdown_cases.items():
    run_analyze("md_" + name, text)

# code-only must report no prose words
_, _, wc_code, _ = run_analyze("md_codeonly_wc", "```\ndelve robust leverage seamless\n```")
check("codeonly_zero_words", wc_code == 0, "expected 0 words, got %d" % wc_code)

# bare URL with -- must NOT raise em-dash hits from the URL
h_url, _, _, _ = run_analyze("md_url_no_emdash", "Visit https://foo.com/a--b--c--d--e--f for info. " * 3)
check("url_no_false_emdash", "em_dash" not in cats(h_url), "URL double-hyphens counted as em-dash")

# ---------------------------------------------------------------------------
# 3. Sentence-splitting edge cases (abbreviations / decimals must not split)
# ---------------------------------------------------------------------------
sent_cases = {
    "abbrev_eg": "We tested several things, e.g. latency and throughput, in the lab.",
    "abbrev_ie": "The result, i.e. the final number, was good and stable overall.",
    "abbrev_etc": "We used Python, Go, Rust, etc. and measured each carefully here.",
    "abbrev_titles": "Dr. Smith and Mr. Jones met Mrs. Lee at the U.S. office today.",
    "decimals": "The value was 3.14 and then 2.71 and finally 1.41 in our runs.",
    "ellipsis": "It was good... then better... then best of all in the end.",
    "version": "We shipped v1.2.3 and then v1.2.4 to production last week here.",
    "list_no_periods": "- alpha\n- beta\n- gamma\n- delta\n- epsilon\n- zeta\n- eta",
}
for name, text in sent_cases.items():
    run_analyze("sent_" + name, text)

# decimals should not over-split: one sentence here, not several
_, rep_dec, _, _ = run_analyze("sent_dec_count", "The value was 3.14 today.")
check("decimal_not_split", rep_dec.get("sentence_count", 0) <= 1,
      "got %s sentences" % rep_dec.get("sentence_count"))

# ---------------------------------------------------------------------------
# 4. Lexical detection: each category must fire on a positive and stay quiet on a negative
# ---------------------------------------------------------------------------
positive = {
    "filler": ("We leverage robust seamless solutions to delve into it.", "filler"),
    "transitions": ("Furthermore, moreover, additionally, the result holds.", "transitions"),
    "meta": ("It's important to note that this report aims to explore X.", "meta_commentary"),
    "hedging": ("This may potentially possibly somewhat help to some extent.", "hedging"),
    "puffery": ("It stands as a testament and plays a vital role, world-class.", "puffery"),
    "vague": ("Studies suggest and experts believe it is widely known to work.", "vague_attribution"),
    "redundancy": ("The end result of past history was a new innovation overall.", "redundancy"),
    "self_id": ("As an AI language model, I cannot browse the internet for you.", "self_identifying"),
    "antithesis": ("It's not just a tool, it's a complete robust solution today.", "antithesis"),
    "rule_of_three": ("The system is fast, reliable, and scalable across loads.", "rule_of_three"),
    "jargon": ("We leverage synergies to operationalize best-in-class solutions.", "jargon"),
}
for name, (text, expect) in positive.items():
    h, _, _, _ = run_analyze("lex_" + name, text)
    check("lex_fires_" + name, expect in cats(h), "expected %s in %s" % (expect, cats(h)))

# burstiness must fire on uniform-length sentences and stay quiet on varied prose
uniform = " ".join("The system runs the job here." for _ in range(12))
h_uni, _, _, _ = run_analyze("burst_uniform", uniform)
check("burstiness_fires_uniform", "burstiness" in cats(h_uni))

# arrows / math symbols / stars must NOT count as decorative emoji
h_arrow, rep_arrow, _, _ = run_analyze("emoji_arrows", "Flow: a → b ↔ c ⟶ d. Use ≤ and ≥. Rate ★★★ here.")
check("arrows_not_emoji", "formatting" not in cats(h_arrow), "arrows flagged as emoji")
# a real emoji still counts
h_emoji, _, _, _ = run_analyze("emoji_real", "Launch day 🚀 was great and we shipped it 🎉 today.")
check("real_emoji_flagged", "formatting" in cats(h_emoji))

# YAML front matter must not be scored as prose or as horizontal rules
fm = "---\ntitle: Robust Report\ntags: [delve, seamless]\nauthor: me\n---\n\n" + \
     "We cut the cache layer. Latency fell to nine milliseconds at p99, which is what users feel."
h_fm, rep_fm, _, _ = run_analyze("frontmatter", fm)
check("frontmatter_not_prose", not any(h.text in ("delve", "seamless") for h in h_fm),
      "front-matter values scored as prose")

clean = "We cut the cache layer last quarter. Latency dropped to nine milliseconds at the ninety-ninth percentile, which is what users actually feel when the homepage loads. The tradeoff was memory: we now hold twice the working set. For our traffic that is a fair price, and we would make the same call again."
h_clean, rep_clean, _, sc_clean = run_analyze("lex_clean", clean)
check("clean_low_score", sc_clean < 15.0, "clean text scored %.1f" % sc_clean)

# ---------------------------------------------------------------------------
# 5. Registers and dialects across all combinations (must not crash)
# ---------------------------------------------------------------------------
sample = ("We leverage robust, seamless, world-class solutions. You should delve in. "
          "It's not just a tool, it's a movement. Furthermore, studies suggest gains.")
for reg in dap.REGISTERS:
    for dia in (None, "american", "british"):
        run_analyze("reg_%s_%s" % (reg, dia), sample, register=reg, dialect=dia)

# puffery is the marketing failure mode -> it must stay flagged in EVERY register
puff = "It is world-class and plays a vital role here."
for reg in dap.REGISTERS:
    h_p, _, _, _ = run_analyze("puffery_" + reg, puff, register=reg)
    check("puffery_kept_" + reg, "puffery" in cats(h_p), "muted in %s" % reg)

# academic mutes measured hedging; technical does not
h_acad, _, _, _ = run_analyze("reg_acad_hedge", "This may potentially somewhat help to some extent.", register="academic")
h_tech_h, _, _, _ = run_analyze("reg_tech_hedge", "This may potentially somewhat help to some extent.", register="technical")
check("academic_mutes_hedging", "hedging" not in cats(h_acad))
check("technical_keeps_hedging", "hedging" in cats(h_tech_h))

# creative mutes em-dash; technical does not
emd = "We won—again—and then—surprisingly—we won once more—decisively—too."
h_cre, _, _, _ = run_analyze("reg_creative_emdash", emd, register="creative")
h_tech_e, _, _, _ = run_analyze("reg_tech_emdash", emd, register="technical")
check("creative_mutes_emdash", "em_dash" not in cats(h_cre))
check("technical_keeps_emdash", "em_dash" in cats(h_tech_e))

# dialect drift detection
h_dia, _, _, _ = run_analyze("dia_american", "We optimised the colour and analysed the behaviour whilst organising.", dialect="american")
check("dialect_fires", "dialect" in cats(h_dia))
check("dialect_analysing", any("optimis" in h.text.lower() for h in h_dia))
# no dialect flag when dialect not requested
h_nodia, _, _, _ = run_analyze("dia_off", "We optimised the colour and behaviour whilst organising.")
check("dialect_off_quiet", "dialect" not in cats(h_nodia))

# ---------------------------------------------------------------------------
# 6. Fuzz: many generated documents combining fragments (deterministic, varied)
# ---------------------------------------------------------------------------
fragments = [
    "# A Heading", "## Another", "Some plain prose that is reasonably long here.",
    "- **Bold:** item", "- plain item", "> a quote line", "| a | b |", "|---|---|",
    "```\ncode\n```", "delve robustly", "Furthermore, moreover.", "Short.",
    "It's not X, it's Y.", "Visit https://x.io/a--b now.", "See [link](http://q.co).",
    "3.14 and e.g. this.", "🚀 emoji line", "---", "Studies suggest things.",
    "", "    indented", "[^1]: footnote", "**stray bold**", "fast, reliable, and scalable",
]
for i in range(120):
    # Deterministic pseudo-shuffle: rotate and stride the fragment list.
    sel = [fragments[(i * 7 + j * 13) % len(fragments)] for j in range(1 + i % 9)]
    doc = "\n".join(sel)
    reg = dap.REGISTERS[i % len(dap.REGISTERS)]
    dia = (None, "american", "british")[i % 3]
    run_analyze("fuzz_%03d" % i, doc, register=reg, dialect=dia)

# ---------------------------------------------------------------------------
# 7. CLI behavior + exit codes (subprocess)
# ---------------------------------------------------------------------------

def run_cli(args, stdin=None, expect_code=None):
    proc = subprocess.run([sys.executable, SCRIPT] + args,
                          input=stdin, capture_output=True, timeout=60)
    if expect_code is not None:
        check("cli:" + " ".join(args[:2]), proc.returncode == expect_code,
              "exit %d (wanted %d): %s" % (proc.returncode, expect_code,
                                           proc.stderr[:120].decode("utf-8", "replace")))
    return proc


before = os.path.join(EXAMPLES, "before.md")
after = os.path.join(EXAMPLES, "after.md")

run_cli([before], expect_code=0)
run_cli([after], expect_code=0)
run_cli(["--register", "marketing", before], expect_code=0)
run_cli(["--register", "creative", before], expect_code=0)
run_cli(["--dialect", "american", before], expect_code=0)
run_cli(["--dialect", "british", after], expect_code=0)
run_cli(["-"], stdin=b"We leverage robust seamless delve.", expect_code=0)
run_cli(["-"], stdin=b"", expect_code=0)                       # empty stdin
run_cli(["-"], stdin=b"\xff\xfe\x00\x01binary garbage", expect_code=0)  # binary stdin
run_cli(["/nonexistent/path/file.md"], expect_code=2)
run_cli([ROOT], expect_code=2)                                  # directory input
run_cli(["--patterns", "/no/such/patterns.json", before], expect_code=2)

# --json must emit valid JSON with the expected keys
p = run_cli(["--json", before], expect_code=0)
try:
    obj = json.loads(p.stdout.decode("utf-8", "replace"))
    check("cli_json_keys", set(obj) >= {"input", "register", "score", "metrics", "hits"})
except Exception as exc:  # noqa: BLE001
    check("cli_json_valid", False, repr(exc))

# binary file input must not crash
binf = os.path.join(tempfile.gettempdir(), "hv_binary_test.bin")
with open(binf, "wb") as fh:
    fh.write(bytes(range(256)) * 64)
run_cli([binf], expect_code=0)
os.remove(binf)

# discrimination must hold via the CLI too
jb = json.loads(run_cli(["--json", before]).stdout.decode())
ja = json.loads(run_cli(["--json", after]).stdout.decode())
check("cli_before_worse_than_after", jb["score"] > ja["score"],
      "before %.1f after %.1f" % (jb["score"], ja["score"]))
check("cli_after_clean", ja["score"] == 0.0, "after scored %.1f" % ja["score"])

# ---------------------------------------------------------------------------
# 8. Malformed pattern files (must exit 2 or degrade, never traceback)
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="hv_patterns_")
bad_patterns = {
    "not_json": "this is not json {{{",
    "json_array": "[1, 2, 3]",
    "json_string": "\"just a string\"",
    "json_number": "42",
    "empty_object": "{}",
    "wrong_types": json.dumps({"filler": "should-be-dict-or-list",
                               "thresholds": "should-be-object",
                               "antithesis_patterns": "not-a-list",
                               "register_mutes": [], "dialect": 5}),
    "invalid_regex": json.dumps({"antithesis_patterns": ["(unclosed", "[a-", "*bad"],
                                 "filler": {"delve": "examine"}}),
    "null_values": json.dumps({"filler": {"delve": None, "": "x", "robust": 5},
                               "overused_transitions": [None, "", "moreover", 7]}),
    "bad_thresholds": json.dumps({"thresholds": {"em_dash_per_1k_words": "lots",
                                                 "ngram_sizes": "two", "ttr_floor": None},
                                  "filler": {"delve": "examine"}}),
    "unknown_mute_cat": json.dumps({"filler": {"delve": "x"},
                                    "register_mutes": {"technical": ["foo"]},
                                    "muted_checks": {"foo": ["nonexistent_category"]}}),
}
for name, content in bad_patterns.items():
    pf = os.path.join(tmpdir, name + ".json")
    with open(pf, "w", encoding="utf-8") as fh:
        fh.write(content)
    proc = run_cli(["--patterns", pf, before])
    # not_json / array / string / number must be rejected with exit 2;
    # the rest are valid JSON objects and must run (exit 0) without a traceback.
    if name in ("not_json", "json_array", "json_string", "json_number"):
        check("badpat_reject_" + name, proc.returncode == 2,
              "exit %d" % proc.returncode)
    else:
        no_trace = b"Traceback" not in proc.stderr
        check("badpat_degrade_" + name, proc.returncode == 0 and no_trace,
              "exit %d, stderr=%s" % (proc.returncode, proc.stderr[:120].decode("utf-8", "replace")))
for f in os.listdir(tmpdir):
    os.remove(os.path.join(tmpdir, f))
os.rmdir(tmpdir)

# ---------------------------------------------------------------------------
# 9. Static validation of shipped JSON (manifests + patterns)
# ---------------------------------------------------------------------------
for rel in (".claude-plugin/marketplace.json", ".claude-plugin/plugin.json",
            "skills/human-voice/scripts/ai_prose_patterns.json"):
    path = os.path.join(ROOT, rel)
    try:
        with open(path, encoding="utf-8") as fh:
            json.load(fh)
        check("json_valid_" + rel, True)
    except Exception as exc:  # noqa: BLE001
        check("json_valid_" + rel, False, repr(exc))

# patterns: every muted category must be a real linter category
mc = PAT.get("muted_checks", {})
unknown = {c for cats_ in mc.values() if isinstance(cats_, list) for c in cats_
           if c not in dap.KNOWN_CATEGORIES}
check("patterns_mute_cats_known", not unknown, "unknown: %s" % unknown)

# marketplace plugin source path must exist
with open(os.path.join(ROOT, ".claude-plugin/marketplace.json"), encoding="utf-8") as fh:
    mkt = json.load(fh)
for plug in mkt.get("plugins", []):
    src = plug.get("source")
    if isinstance(src, str):
        check("plugin_source_exists", os.path.isdir(os.path.join(ROOT, src)),
              "missing %s" % src)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = passed + failed
print("ran %d checks: %d passed, %d failed" % (total, passed, failed))
if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("all green")
sys.exit(0)
