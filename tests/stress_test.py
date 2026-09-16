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
import random as _random
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "human-voice", "scripts", "detect_ai_prose.py")
PATTERNS = os.path.join(ROOT, "skills", "human-voice", "scripts", "ai_prose_patterns.json")
EXAMPLES = os.path.join(ROOT, "skills", "human-voice", "examples")
SCRIPTS = os.path.join(ROOT, "skills", "human-voice", "scripts")

spec = importlib.util.spec_from_file_location("dap", SCRIPT)
dap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dap)
PAT = dap.load_patterns(PATTERNS)

passed = 0
failed = 0
failures = []


def _raises(exc_type, fn):
    """True when fn() raises exc_type. Used by the verification-gate checks."""
    try:
        fn()
    except exc_type:
        return True
    except Exception:
        return False
    return False


def _capture_stdout(fn):
    """(return_value, captured_stdout) for a callable that prints."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rv = fn()
    return rv, buf.getvalue()


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
    "rule_of_three": ("The system is fast, reliable, and scalable across loads. "
                      "The rollout was quick, painless, and cheap for the team.",
                      "rule_of_three"),
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
# 4b. False-positive regressions + new tells (HV-015/016/017/018, HV-065/066)
# Each known false-positive class has a negative case (must stay quiet) paired
# with a positive case (the real tell must still fire).
# ---------------------------------------------------------------------------
# proper-noun triad must NOT fire rule_of_three; adjective triad must
h_pn, _, _, _ = run_analyze("fp_proper_noun_triad", "We shipped with Python, Django, and Flask in production this year here.")
check("fp_proper_noun_no_rule3", "rule_of_three" not in cats(h_pn))
# Two triads, because one tricolon is a rhetorical figure principle 2 allows.
h_adj, _, _, _ = run_analyze(
    "tp_adjective_triad",
    "The system is fast, reliable, and scalable across every workload here. "
    "The rollout was quick, painless, and cheap for everyone involved here.")
check("tp_adjective_rule3", "rule_of_three" in cats(h_adj))
h_one, _, _, _ = run_analyze(
    "fp_single_triad", "It handles tuples, lists, and dicts without special cases.")
check("fp_single_triad_does_not_fire", "rule_of_three" not in cats(h_one),
      "one genuine enumeration of three is not the rule-of-three reflex")

# noun-PHRASE triads: a lone one is a legitimate enumeration (no flag); two or
# more is the reflexive triadic-prose tell (flag).
h_np1, _, _, _ = run_analyze("fp_single_noun_triad",
    "The schema needs encryption at rest, row-level access control, and audit logging here.")
check("fp_single_noun_triad_quiet", "rule_of_three" not in cats(h_np1))
h_np2, _, _, _ = run_analyze("tp_stacked_noun_triads",
    "It needs encryption at rest, row-level access control, and audit logging. "
    "We value clean code, fast reviews, and honest estimates every single day.")
check("tp_stacked_noun_triads_fire", "rule_of_three" in cats(h_np2))
h_npn, _, _, _ = run_analyze("fp_proper_noun_phrase_triad",
    "We deploy on Amazon Web Services, Google Cloud Platform, and Microsoft Azure. "
    "We use New York, San Francisco, and Los Angeles offices for this work today.")
check("fp_proper_noun_phrase_quiet", "rule_of_three" not in cats(h_npn))

# the "[inanimate thing] lives in [place]" locative is a false_agency tell
h_loc, _, _, _ = run_analyze("tp_locative_false_agency",
    "The business logic lives in the controller and the config lives in a YAML file.")
check("tp_locative_fires", "false_agency" in cats(h_loc))
h_locfp, _, _, _ = run_analyze("fp_person_lives_quiet",
    "Maria lives in Lisbon now, and her brother lives in Porto near the river.")
check("fp_person_lives_quiet", "false_agency" not in cats(h_locfp))

# numeric en-dash range must NOT count as em-dash; real em-dash overuse must
h_rng, _, _, _ = run_analyze("fp_numeric_range", "Revenue rose across 2024–2025, 2025–2026, and 2026–2027 in our books.")
check("fp_range_no_emdash", "em_dash" not in cats(h_rng))
h_emd, _, _, _ = run_analyze("tp_emdash", "We won—again—and then—surprisingly—we won—once more—decisively—too here.")
check("tp_emdash_fires", "em_dash" in cats(h_emd))

# dialect must skip code identifiers but catch prose drift
h_id, _, _, _ = run_analyze("fp_dialect_identifier", "Call analyse() and read Color.RED from OPTIMISE_FLAGS in the module here.", dialect="american")
check("fp_dialect_identifier_quiet", "dialect" not in cats(h_id))
h_drift, _, _, _ = run_analyze("tp_dialect_prose", "We optimised the colour and analysed the behaviour whilst organising it.", dialect="american")
check("tp_dialect_prose_fires", "dialect" in cats(h_drift))

# context exception protects a legitimate fixed phrase; bare uses still flag
h_ex, _, _, _ = run_analyze("fp_context_exception", "We built a test harness and watched the vital signs in landscape mode here.")
check("fp_context_exception_quiet",
      not any(h.category == "filler" and h.text.lower() in ("harness", "vital", "landscape") for h in h_ex))
h_filler, _, _, _ = run_analyze("tp_filler_bare", "We must harness the landscape and use the vital realm of the tapestry here.")
check("tp_filler_bare_fires", "filler" in cats(h_filler))

# chatbot scaffolding fires as its own category
h_cb, _, _, _ = run_analyze("tp_chatbot", "Sure! Here's the thing. Great question — let me explain. Hope this helps!")
check("tp_chatbot_fires", "chatbot_scaffold" in cats(h_cb))

# ---------------------------------------------------------------------------
# 4c. Scoring model: weights, bands, threshold sensitivity (HV-037/038/129/131)
# ---------------------------------------------------------------------------
check("band_clean", dap.verdict_band(2.0, dap.DEFAULT_BANDS) == "clean")
check("band_watch", dap.verdict_band(9.0, dap.DEFAULT_BANDS) == "watch")
check("band_strong", dap.verdict_band(99.0, dap.DEFAULT_BANDS) == "strong-tell")
# bands resolved from the shipped patterns file behave the same
check("band_from_patterns", dap.verdict_band(99.0, dap.resolve_bands(PAT)) == "strong-tell")

w = dap.resolve_weights(PAT)
check("weights_self_id_high", w.get("self_identifying", 0) > w.get("filler", 0))
check("weights_fallback_default", dap.resolve_weights({}).get("burstiness") == dap.CATEGORY_WEIGHTS["burstiness"])
# weight ordering: one self_identifying hit outscores one filler hit
sc_self = dap.score([dap.Hit("self_identifying", 1, "x")], 100, w)
sc_fill = dap.score([dap.Hit("filler", 1, "x")], 100, w)
check("weight_ordering", sc_self > sc_fill)
# adding a tell raises the score (monotonic)
check("score_monotonic", dap.score([dap.Hit("filler", 1, "x")] * 3, 100, w) > sc_fill)

# threshold sensitivity: an absurdly high burstiness floor makes even varied prose fire
pat_hi = json.loads(json.dumps(PAT))
pat_hi.setdefault("thresholds", {})["burstiness_cov_floor"] = 5.0
varied = ("Short. This sentence is considerably longer and carries far more clauses "
          "than the first one does here today. Tiny. Another long stretch of words "
          "that deliberately runs on for a while to vary the cadence quite a lot. "
          "Brief again. And one final long clause to push the sentence count well "
          "past the minimum the burstiness check needs to run here. Two more now. "
          "The check wants eight sentences before it will trust a coefficient of "
          "variation, because five is sampling noise rather than rhythm. Done.")
h_thr, _, _ = dap.analyze(varied, "technical", None, pat_hi)
check("threshold_sensitivity", "burstiness" in {h.category for h in h_thr})

# ---------------------------------------------------------------------------
# 4d. New structural / density checks (HV-002/003/005/006/009/010/011)
# ---------------------------------------------------------------------------
# parallel structure: 3+ sentences sharing their opening two words
h_par, _, _, _ = run_analyze("tp_parallel",
    "The system handles ingestion. The system handles indexing. The system handles queries.")
check("tp_parallel_fires", "parallel_structure" in cats(h_par))

# colon-summary reflex
h_col, _, _, _ = run_analyze("tp_colon",
    "The key takeaway is: speed. The bottom line is: cost. The answer is: scale here.")
check("tp_colon_fires", "colon_summary" in cats(h_col))

# paragraph + list uniformity on perfectly even blocks
h_pu, _, _, _ = run_analyze("tp_para_uniform", "\n\n".join(["This paragraph holds exactly six words."] * 5))
check("tp_para_uniform_fires", "paragraph_uniformity" in cats(h_pu))
h_lu, _, _, _ = run_analyze("tp_list_uniform", "\n".join(["- item with five words here"] * 6))
check("tp_list_uniform_fires", "list_uniformity" in cats(h_lu))

# paired em-dash asides fire even below the density floor
h_pd, _, _, _ = run_analyze("tp_paired_dash",
    "We shipped it—finally—after review. The result—surprisingly—held up well in practice.")
check("tp_paired_dash_fires", "em_dash" in cats(h_pd))

# passive/adverb density fire on a heavy sample (>150 words) but not on clean prose
heavy = ("The report was written by the team and was reviewed carefully. The data was collected "
         "slowly and was analyzed thoroughly. The results were shown clearly and were presented "
         "formally. ") * 6
h_pv, _, _, _ = run_analyze("tp_passive", heavy)
check("tp_passive_fires", "passive_voice" in cats(h_pv))
check("tp_adverb_fires", "adverbs" in cats(h_pv))
# academic register mutes passive voice; technical keeps it
h_pv_ac, _, _, _ = run_analyze("tp_passive_academic", heavy, register="academic")
check("academic_mutes_passive", "passive_voice" not in cats(h_pv_ac))

# rhetorical-question density: muted for marketing, kept for technical
rhet = ("Why does this matter to your team? What happens when traffic spikes hard? "
        "How do you know it scales well? Where does the bottleneck actually live here? "
        "When should you reach for a queue? Which store fits a write-heavy load best? ") * 5
h_rh_tech, _, _, _ = run_analyze("tp_rhetorical_tech", rhet)
h_rh_mkt, _, _, _ = run_analyze("tp_rhetorical_mkt", rhet, register="marketing")
check("technical_keeps_rhetorical", "rhetorical" in cats(h_rh_tech))
check("marketing_mutes_rhetorical", "rhetorical" not in cats(h_rh_mkt))

# tiny-doc guard: density checks stay silent under the minimum word floor
h_tiny, _, _, _ = run_analyze("fp_tiny_doc", "It was written slowly. It was read slowly here.")
check("tiny_doc_no_density", not ({"passive_voice", "adverbs", "rhetorical"} & cats(h_tiny)))

# ---------------------------------------------------------------------------
# 4e. B2 refinements: cited attribution, Oxford-less triad, wordiness, metrics
# ---------------------------------------------------------------------------
# vague attribution that is immediately sourced must NOT flag; bare must
h_cite, _, _, _ = run_analyze("fp_cited_attribution",
    "Studies show [1] that latency dominates. Research suggests (Smith 2024) the same here.")
check("fp_cited_attribution_quiet", "vague_attribution" not in cats(h_cite))
h_bare, _, _, _ = run_analyze("tp_bare_attribution",
    "Studies show that latency dominates. Research suggests the very same thing here today.")
check("tp_bare_attribution_fires", "vague_attribution" in cats(h_bare))

# Oxford-comma-less triad still fires (HV-024)
h_ox, _, _, _ = run_analyze("tp_oxfordless_triad",
    "The platform is fast, reliable and scalable across all of the workloads here today. "
    "The rollout stayed quick, painless and cheap for every team involved here.")
check("tp_oxfordless_triad_fires", "rule_of_three" in cats(h_ox))

# wordiness padding flags as redundancy (HV-025)
h_word, _, _, _ = run_analyze("tp_wordiness",
    "In order to win, due to the fact that the majority of users wait, we act now.")
check("tp_wordiness_fires", "redundancy" in cats(h_word))

# A spaced double-hyphen is `dash_style`, not `em_dash`. Counting it in both made
# one double-hyphen worth two hits in two categories.
h_sdh, _, _, _ = run_analyze("tp_spaced_double_hyphen",
    "We shipped it -- finally -- after review and it held -- surprisingly -- up well here.")
check("tp_spaced_double_hyphen", "dash_style" in cats(h_sdh))
check("ascii_dash_not_double_counted", "em_dash" not in cats(h_sdh),
      "ASCII `--` was counted as an em-dash as well as a dash-style error")

# dash_style: ASCII "--" as a dash fires; spaced hyphen as a dash fires (HV-030)
h_ds, _, _, _ = run_analyze("tp_dash_style",
    "The plan was risky--we staged it. The result - in short - held up under load.")
check("tp_dash_style_fires", "dash_style" in cats(h_ds))

# dash_style: mixed em-dash spacing flagged (HV-031)
h_dm, _, _, _ = run_analyze("tp_dash_mixed",
    "We won—again—and then we paused — briefly — before the next release here.")
check("tp_dash_mixed_fires", "dash_style" in cats(h_dm))

# dash_style is muted in the creative register (dashes are its tool) (HV-032)
h_dc, _, _, _ = run_analyze("tp_dash_creative",
    "The plan was risky--we staged it. The result - in short - held.", register="creative")
check("creative_mutes_dash_style", "dash_style" not in cats(h_dc))

# doubled_word: a real doubling fires; a legit "that that" / boundary does not (HV-033)
h_dw, _, _, _ = run_analyze("tp_doubled_word",
    "We we shipped the the release after the review wrapped up late on Friday night.")
check("tp_doubled_word_fires", "doubled_word" in cats(h_dw))
h_dwok, _, _, _ = run_analyze("fp_doubled_word_ok",
    "I know that that release shipped, and they had had trouble with it before then.")
check("fp_doubled_word_quiet", "doubled_word" not in cats(h_dwok))

# doubled_word must not fire across a heading/line boundary (the "...it\n\nIt..." FP) (HV-034)
h_dwb, _, _, _ = run_analyze("fp_doubled_word_boundary",
    "# Why use it\n\nIt fixes the tells that give writing away across many genres here.")
check("fp_doubled_word_boundary_quiet", "doubled_word" not in cats(h_dwb))

# mechanics: space before punctuation and repeated terminal marks fire (HV-035)
h_mech, _, _, _ = run_analyze("tp_mechanics",
    "We shipped it , finally ; and it worked !! Did it really ?? Yes, it did, mostly.")
check("tp_mechanics_fires", "mechanics" in cats(h_mech))

# mechanics must NOT false-positive on inline code stripped before punctuation (HV-036)
h_mok, _, _, _ = run_analyze("fp_mechanics_inline_code",
    "Use the `--fail-over` flag, then run `run_eval.py`; both exit cleanly for you.")
check("fp_mechanics_inline_code_quiet", "mechanics" not in cats(h_mok))

# new report metrics are populated
_, rep_m, _, _ = run_analyze("metrics_present", clean)
check("metric_dash_counts", "dash_ascii_double" in rep_m and "doubled_words" in rep_m)
check("metric_yules_k", rep_m.get("yules_k") is not None)
check("metric_opener_entropy", rep_m.get("opener_entropy") is not None)
check("metric_punctuation", "semicolon_per_1k" in rep_m and "colon_per_1k" in rep_m)
check("metric_paragraph_cov", "paragraph_len_cov" in rep_m)

# ---------------------------------------------------------------------------
# 4f. Stop-slop-derived tells: false agency, narrator-from-a-distance,
# Wh-opener crutch, vague declarative, negative listing, dramatic
# fragmentation. Each fires on a positive case and is muted/quiet where the
# register or the content makes the pattern legitimate.
# ---------------------------------------------------------------------------
# false agency: abstract subject + human verb fires (technical); muted academic
h_fa, _, _, _ = run_analyze("tp_false_agency",
    "The complaint becomes a fix overnight. The data tells us where to invest, and the market rewards the fast.")
check("tp_false_agency_fires", "false_agency" in cats(h_fa))
h_fa_ac, _, _, _ = run_analyze("fp_false_agency_academic",
    "The complaint becomes a fix overnight. The data tells us where to invest, and the market rewards the fast.",
    register="academic")
check("academic_mutes_false_agency", "false_agency" not in cats(h_fa_ac))
# concrete human actor must NOT trip false_agency
h_fa_ok, _, _, _ = run_analyze("fp_false_agency_named",
    "The on-call engineer shipped the fix that week. We read the logs and found the drop-off here.")
check("fp_false_agency_named_quiet", "false_agency" not in cats(h_fa_ok))

# narrator-from-a-distance: lecturer voice fires (technical); muted academic and
# casual, where a first-person writer saying "nobody tells you" is stating their own
# stance rather than lecturing from above.
h_nd, _, _, _ = run_analyze("tp_narrator_distance",
    "Nobody designed this. People tend to follow the path of least resistance, and humans are wired to coast.",
    register="technical")
h_nd_cas, _, _, _ = run_analyze("fp_narrator_distance_casual",
    "Nobody designed this. People tend to follow the path of least resistance, and humans are wired to coast.",
    register="casual")
check("fp_narrator_distance_muted_casual", "narrator_distance" not in cats(h_nd_cas))
check("tp_narrator_distance_fires", "narrator_distance" in cats(h_nd))
h_nd_ac, _, _, _ = run_analyze("fp_narrator_distance_academic",
    "Nobody designed this. People tend to follow the path of least resistance, and humans are wired to coast.",
    register="academic")
check("academic_mutes_narrator_distance", "narrator_distance" not in cats(h_nd_ac))

# Wh-opener crutch: a run of what/why/how openers fires; varied prose stays quiet
h_wh, _, _, _ = run_analyze("tp_wh_openers",
    "What makes this hard is scale. Why does that matter so much? How do you even know it works at all? "
    "We shipped it on Friday anyway.")
check("tp_wh_openers_fires", "wh_opener" in cats(h_wh))
h_wh_ok, _, _, _ = run_analyze("fp_wh_openers_quiet",
    "Scale is the hard part. The index can't keep up past fifty thousand writes. We sharded it instead here.")
check("fp_wh_openers_quiet", "wh_opener" not in cats(h_wh_ok))

# vague declarative: announce-the-weight phrasing fires
h_vd, _, _, _ = run_analyze("tp_vague_declarative",
    "The implications are significant. The reasons are structural. This is genuinely hard to get right here.")
check("tp_vague_declarative_fires", "vague_declarative" in cats(h_vd))

# negative listing: multi-item striptease fires (contraction + 'were' forms)
h_nl, _, _, _ = run_analyze("tp_negative_listing",
    "It wasn't a tooling problem. It wasn't a staffing problem. It was a priorities problem all along here.")
check("tp_negative_listing_fires", "negative_listing" in cats(h_nl))

# dramatic fragmentation: performative simplicity fires in exposition,
# but is muted where fragments are legitimate craft (casual/creative)
h_df, _, _, _ = run_analyze("tp_dramatic_fragmentation",
    "You can only pick two. That's it. That's the tradeoff every team eventually has to make here.")
check("tp_dramatic_fragmentation_fires", "dramatic_fragmentation" in cats(h_df))
h_df_cas, _, _, _ = run_analyze("fp_dramatic_fragmentation_casual",
    "You can only pick two. That's it. That's the tradeoff every team eventually has to make here.",
    register="casual")
check("casual_mutes_dramatic_fragmentation", "dramatic_fragmentation" not in cats(h_df_cas))

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
run_cli([EXAMPLES], expect_code=0)            # directory input now walks markdown
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

# golden bands + margin: the AI-sounding example must land in the top band by a
# wide margin; the rewrite must read clean. Guards both example files and the
# scoring against silent regression.
check("golden_before_strong_band", jb.get("verdict") == "strong-tell",
      "before verdict %s" % jb.get("verdict"))
check("golden_after_clean_band", ja.get("verdict") == "clean",
      "after verdict %s" % ja.get("verdict"))
check("golden_before_margin", jb["score"] >= 50.0, "before %.1f" % jb["score"])

# strict JSON schema: exact key set + value types (HV-130). `inferred_register` is
# additive and optional -- it appears ONLY when --register auto ran, so a consumer
# that never asks for inference keeps a byte-identical payload.
expected_keys = {"schema_version", "input", "register", "dialect", "words",
                 "score", "verdict", "metrics", "hits"}
check("json_strict_keys", set(jb) == expected_keys, "got %s" % sorted(set(jb)))
_ja_auto = json.loads(run_cli(["--register", "auto", "--json", before]).stdout.decode())
check("json_auto_adds_only_inferred_register",
      set(_ja_auto) == expected_keys | {"inferred_register"},
      "auto payload keys: %s" % sorted(set(_ja_auto)))
check("json_auto_inferred_shape",
      set(_ja_auto["inferred_register"]) == {"register", "confidence", "reasons"},
      "inferred_register shape: %s" % sorted(_ja_auto["inferred_register"]))
check("json_schema_version", jb.get("schema_version") == 1)
check("json_value_types",
      isinstance(jb["score"], (int, float)) and isinstance(jb["verdict"], str)
      and isinstance(jb["words"], int) and isinstance(jb["hits"], list)
      and isinstance(jb["metrics"], dict))

# score-gated exit code (HV-039): over the bar exits 1, under exits 0
run_cli(["--fail-over", "10", before], expect_code=1)
run_cli(["--fail-over", "10", after], expect_code=0)

# ---------------------------------------------------------------------------
# 7b. B3 API/UX features: compare, autofix, sarif, filters, library, multi-file
# ---------------------------------------------------------------------------
# library API mirrors the JSON payload
libr = dap.lint("We leverage robust seamless solutions to delve into it here today.")
check("lib_lint_keys", {"score", "verdict", "hits", "metrics", "words"} <= set(libr))
check("lib_lint_severity", all("severity" in h for h in libr["hits"]))

# per-hit severity in CLI JSON
check("json_hit_severity", all("severity" in h for h in jb["hits"]))

# compare mode prints a delta and exits 0
pc = run_cli(["--baseline", after, before], expect_code=0)
check("compare_runs", b"delta" in pc.stdout.lower())
pcj = json.loads(run_cli(["--baseline", after, "--json", before]).stdout.decode())
check("compare_json", "score_delta" in pcj and pcj["current"]["score"] > pcj["baseline"]["score"])

# --enable keeps only listed categories; --disable drops them
je = json.loads(run_cli(["--enable", "filler", "--json", before]).stdout.decode())
check("enable_filter", je["hits"] and all(h["category"] == "filler" for h in je["hits"]))
jd = json.loads(run_cli(["--disable", "filler", "--json", before]).stdout.decode())
check("disable_filter", all(h["category"] != "filler" for h in jd["hits"]))

# --threshold override changes behavior (impossible-high em-dash floor => no em_dash hits)
jt = json.loads(run_cli(["--threshold", "em_dash_per_1k_words=100000", "--json", before]).stdout.decode())
check("threshold_override", all(h["category"] != "em_dash" for h in jt["hits"]))

# SARIF output is well-formed
js = json.loads(run_cli(["--sarif", before]).stdout.decode())
check("sarif_shape", js.get("version") == "2.1.0" and "runs" in js and js["runs"][0]["results"])

# multi-file JSON returns a list; --quiet prints one line per file
jm = json.loads(run_cli(["--json", before, after]).stdout.decode())
check("multifile_list", isinstance(jm, list) and len(jm) == 2)
pq = run_cli(["--quiet", before, after], expect_code=0)
check("quiet_lines", len(pq.stdout.decode().strip().splitlines()) == 2)

# autofix dry-run swaps known filler and never empties the doc
pf = run_cli(["--fix-dry-run", before]).stdout.decode()
check("autofix_swaps", "utilize" not in pf.lower() and len(pf) > 50)

# autofix on a temp copy actually rewrites and lowers the score
_fixsrc = os.path.join(tempfile.gettempdir(), "hv_fix_test.md")
with open(_fixsrc, "w", encoding="utf-8") as fh:
    fh.write("We utilize and leverage robust solutions to delve into the synergy here today.")
run_cli(["--fix", _fixsrc], expect_code=0)
with open(_fixsrc, encoding="utf-8") as fh:
    fixed_text = fh.read()
check("autofix_applied", "utilize" not in fixed_text and "use" in fixed_text)
os.remove(_fixsrc)

# autofix structural fixes: emoji stripped, dashes -> comma, ranges/compounds/code kept
_dtext = ("Fast 🚀 — really fast -- and clean - mostly. Range 10–20 ok. A well-known case.\n"
          "Use `a--b` inline.\n\n```\nx -- y\n```\n")
_dfix, _sw, _em, _da = dap.autofix(_dtext, PAT, "technical")
check("autofix_emoji_stripped", "🚀" not in _dfix and _em == 1)
check("autofix_em_dash_to_comma", "—" not in _dfix and "Fast, really" in _dfix)
check("autofix_ascii_dash_to_comma", "really fast, and clean" in _dfix)
check("autofix_spaced_hyphen_to_comma", "clean, mostly" in _dfix)
check("autofix_dash_count", _da == 3, "dashes replaced: %d" % _da)
check("autofix_keeps_numeric_range", "10–20" in _dfix)
check("autofix_keeps_compound_hyphen", "well-known" in _dfix)
check("autofix_never_touches_code", "`a--b`" in _dfix and "x -- y" in _dfix)

# emoji removal never leaves a doubled or dangling space
_efix, _, _en, _ = dap.autofix("Fast 🚀 Reliable and 🎉 done.", PAT, "technical")
check("autofix_emoji_no_double_space",
      "Fast Reliable" in _efix and "  " not in _efix and _en == 2)

# register gating: creative keeps dashes + emoji; casual keeps emoji but fixes dashes
_cfix, _, _cem, _cda = dap.autofix(_dtext, PAT, "creative")
check("autofix_creative_untouched", "🚀" in _cfix and "—" in _cfix and _cem == 0 and _cda == 0)
_kfix, _, _kem, _kda = dap.autofix(_dtext, PAT, "casual")
check("autofix_casual_keeps_emoji", "🚀" in _kfix and _kem == 0)
check("autofix_casual_fixes_dashes", "—" not in _kfix and _kda == 3)

# --fix-dry-run integration: structural fixes flow through the CLI too
_dfile = os.path.join(tempfile.gettempdir(), "hv_dash_test.md")
with open(_dfile, "w", encoding="utf-8") as fh:
    fh.write("We won — again — here. ✨\n")
_pf = run_cli(["--fix-dry-run", _dfile]).stdout.decode()
# A paired dashed aside becomes parentheses, not two commas: varying the
# replacement is the point (principle 2), and parentheses are what a person writes.
check("cli_fix_strips_dash_emoji", "—" not in _pf and "✨" not in _pf and "won (again) here" in _pf,
      "autofix output was %r" % _pf)
os.remove(_dfile)

# Em-dash density needs THREE. Two is what a person who likes em-dashes writes in
# a short note, and firing at two made a 220-word human email score "strong-tell".
h_lowdash, _, _, _ = run_analyze("tp_three_em_dashes",
    "The result surprised us — it held — and we shipped it — the next morning here.")
check("low_threshold_flags_three_em_dashes", "em_dash" in cats(h_lowdash))
# The paired aside is a distinct tic, so it still fires at two even below the rate.
h_paired, _, _, _ = run_analyze("tp_paired_asides",
    "The result — surprisingly — held. " + ("Plain filler sentence to dilute it. " * 30)
    + "We shipped it — eventually — the next morning.")
check("paired_dash_asides_fire_at_two", "em_dash" in cats(h_paired),
      "two paired dashed asides should fire regardless of density")

# ---------------------------------------------------------------------------
# 7c. B4 project config + protected terms (HV-166/167)
# ---------------------------------------------------------------------------
# protected_terms suppress lexical hits on those exact terms (analyze-level)
pat_prot = json.loads(json.dumps(PAT))
pat_prot["protected_terms"] = ["Robust Analytics"]
h_prot, _, _ = dap.analyze("Our Robust Analytics suite is robust and seamless here today.", "technical", None, pat_prot)
prot_filler = [h.text.lower() for h in h_prot if h.category == "filler"]
check("protected_term_suppressed", "robust analytics" not in " ".join(prot_filler))
check("protected_unprotected_still_flags", any("robust" == t for t in prot_filler) or any("seamless" == t for t in prot_filler))

# .humanvoicerc is discovered, sets register, and extends protected terms
cfgdir = tempfile.mkdtemp(prefix="hv_cfg_")
with open(os.path.join(cfgdir, ".humanvoicerc"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"register": "marketing", "protected_terms": ["Synergy Platform"]}))
with open(os.path.join(cfgdir, "doc.md"), "w", encoding="utf-8") as fh:
    fh.write("We leverage the Synergy Platform to delve into analytics here today now.")
jc = json.loads(run_cli(["--json", os.path.join(cfgdir, "doc.md")]).stdout.decode())
check("config_register_applied", jc["register"] == "marketing")
check("config_protected_term", not any("synergy platform" in h["text"].lower() for h in jc["hits"]))
jnc = json.loads(run_cli(["--no-config", "--json", os.path.join(cfgdir, "doc.md")]).stdout.decode())
check("no_config_reverts_register", jnc["register"] == "technical")
for f in os.listdir(cfgdir):
    os.remove(os.path.join(cfgdir, f))
os.rmdir(cfgdir)

# rich object-form suggestion is accepted by as_phrase_list
check("rich_suggestion_form",
      ("foo", "bar") in dap.as_phrase_list({"foo": {"suggestion": "bar"}}))

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

# drift guard (Phase 2): the shipped JSON must stay consistent with DEFAULTS so
# the code fallbacks and the user-editable file can never silently diverge.
_D = dap.DEFAULTS
for _sect in ("thresholds", "category_weights", "score_bands", "scoring"):
    _json_sect = PAT.get(_sect, {})
    _drift = {k: (v, _json_sect.get(k)) for k, v in _D[_sect].items()
              if _json_sect.get(k) != v}
    check("defaults_drift_" + _sect, not _drift, "JSON vs DEFAULTS: %s" % _drift)
# every category in DEFAULTS["category_weights"] is a known category and vice versa
check("defaults_weights_cover_categories",
      set(_D["category_weights"]) == set(dap.KNOWN_CATEGORIES),
      "mismatch: %s" % (set(_D["category_weights"]) ^ set(dap.KNOWN_CATEGORIES)))

# schema validator (Phase 4): the shipped patterns file is clean; bad config is
# flagged but never fatal.
check("schema_shipped_clean", dap.validate(PAT) == [], "issues: %s" % dap.validate(PAT))
_bad = dap.validate({"thresholds": {"ttr_floor": "x", "nope": 1},
                     "category_weights": {"ghost": 2.0},
                     "muted_checks": {"t": ["not_a_cat"]},
                     "antithesis_patterns": ["(unclosed"]})
check("schema_flags_bad_threshold", any("ttr_floor" in m for m in _bad))
check("schema_flags_unknown_category", any("ghost" in m for m in _bad))
check("schema_flags_bad_regex", any("unclosed" in m for m in _bad))
check("schema_flags_unknown_mute_cat", any("not_a_cat" in m for m in _bad))

# span offsets (Phase 5): column-accurate checks point at the real characters.
_span_txt = "We leverage robust synergy here."
_span_res = dap.lint(_span_txt, register="marketing")
_fill = next((h for h in _span_res["hits"]
              if h["category"] == "filler" and h.get("col")), None)
check("span_columns_present", _fill is not None)
if _fill:
    check("span_columns_correct",
          _span_txt[_fill["col"] - 1:_fill["end_col"] - 1] == _fill["text"],
          "got %r" % _span_txt[_fill["col"] - 1:_fill["end_col"] - 1])
# document-level findings (low burstiness on uniform sentences) carry scope.
_doc = ("The cat sat here. The dog ran fast. The bird flew high. "
        "The fish swam deep. The fox hid low. The owl woke late.")
_doc_hits = dap.lint(_doc, register="technical")["hits"]
check("span_document_scope",
      all(h.get("scope") == "document" for h in _doc_hits if h.get("line") == 0))

# inline ignore directives (Phase 6).
_dbase = "We leverage seamless synergy."
_dn = len(dap.lint(_dbase)["hits"])
check("directive_baseline", _dn == 3)
check("directive_ignore_one",
      {h["category"] for h in dap.lint(_dbase + "  <!-- human-voice: ignore filler -->")["hits"]} == {"jargon"})
check("directive_ignore_all",
      dap.lint(_dbase + "  <!-- human-voice: ignore -->")["hits"] == [])
check("directive_next_line",
      dap.lint("<!-- human-voice: ignore -->\n" + _dbase)["hits"] == [])
check("directive_inert_in_fence",
      len(dap.lint("```\n<!-- human-voice: ignore -->\n```\n" + _dbase)["hits"]) == 3)
check("directive_block",
      dap.lint("<!-- human-voice: ignore-start -->\n" + _dbase +
               "\n<!-- human-voice: ignore-end -->")["hits"] == [])

# marketplace plugin source path must exist
with open(os.path.join(ROOT, ".claude-plugin/marketplace.json"), encoding="utf-8") as fh:
    mkt = json.load(fh)
for plug in mkt.get("plugins", []):
    src = plug.get("source")
    if isinstance(src, str):
        check("plugin_source_exists", os.path.isdir(os.path.join(ROOT, src)),
              "missing %s" % src)

# version-drift guard (HV-146): plugin.json and the marketplace plugin entry
# duplicate the version string; they must never disagree.
with open(os.path.join(ROOT, ".claude-plugin/plugin.json"), encoding="utf-8") as fh:
    plug_manifest = json.load(fh)
mkt_versions = {p.get("name"): p.get("version") for p in mkt.get("plugins", [])}
check("version_drift_guard",
      mkt_versions.get(plug_manifest.get("name")) == plug_manifest.get("version"),
      "plugin.json=%s marketplace=%s" % (plug_manifest.get("version"),
                                         mkt_versions.get(plug_manifest.get("name"))))

# The pattern file carries its own version string. It ships inside the plugin and
# is the thing a user edits, so a stale value there is a real signal about which
# tell lists they have. Keep it in step with the plugin manifest.
with open(os.path.join(ROOT, "skills/human-voice/scripts/ai_prose_patterns.json"),
          encoding="utf-8") as fh:
    _pat_manifest = json.load(fh)
check("patterns_version_matches_plugin",
      _pat_manifest.get("version") == plug_manifest.get("version"),
      "ai_prose_patterns.json says %r, plugin.json says %r"
      % (_pat_manifest.get("version"), plug_manifest.get("version")))
check("changelog_documents_current_version",
      ("## [%s]" % plug_manifest.get("version")) in
      open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read(),
      "CHANGELOG.md has no section for version %r" % plug_manifest.get("version"))


# ---------------------------------------------------------------------------
# 10. Metric golden values, determinism, examples-in-sync (HV-128/134/135)
# ---------------------------------------------------------------------------
# Golden metric values on hand-built inputs lock the math against silent drift.
uniform12 = " ".join("The system runs the daily job." for _ in range(12))
_, rep_u, _, _ = run_analyze("golden_uniform_cov", uniform12)
check("golden_cov_zero", rep_u.get("burstiness_cov") == 0.0,
      "uniform sentences should have CoV 0.0, got %s" % rep_u.get("burstiness_cov"))

allunique = " ".join(chr(97 + i // 26) + chr(97 + i % 26) for i in range(60))  # aa..ch, distinct
_, rep_t, _, _ = run_analyze("golden_ttr", allunique)
check("golden_ttr_one", rep_t.get("ttr") == 1.0,
      "all-unique tokens should give TTR 1.0, got %s" % rep_t.get("ttr"))

# Determinism: same input yields byte-identical JSON across runs.
d1 = run_cli(["--json", before]).stdout
d2 = run_cli(["--json", before]).stdout
check("determinism_json_identical", d1 == d2, "JSON output not reproducible")

# Examples in sync: every shipped before/after pair still separates, and each
# "after" stays in the clean band under its register.
REGISTER_BY_PREFIX = {"marketing": "marketing", "casual": "casual",
                      "academic": "academic", "email": "email",
                      "modern-ai": "technical"}
for prefix, reg in REGISTER_BY_PREFIX.items():
    bpath = os.path.join(EXAMPLES, "%s-before.md" % prefix)
    apath = os.path.join(EXAMPLES, "%s-after.md" % prefix)
    if not (os.path.isfile(bpath) and os.path.isfile(apath)):
        continue
    jb_ex = json.loads(run_cli(["--register", reg, "--json", bpath]).stdout.decode())
    ja_ex = json.loads(run_cli(["--register", reg, "--json", apath]).stdout.decode())
    check("example_pair_separates_%s" % prefix, jb_ex["score"] > ja_ex["score"],
          "%s before %.1f after %.1f" % (prefix, jb_ex["score"], ja_ex["score"]))
    check("example_after_clean_%s" % prefix, ja_ex["verdict"] == "clean",
          "%s-after verdict %s (%.1f)" % (prefix, ja_ex["verdict"], ja_ex["score"]))
    # Every shipped "after" must also clear the rhythm targets the skill sets, so
    # an example can never demonstrate a clean score with metronome prose.
    _am = ja_ex.get("metrics", {})
    _short, _mid = _am.get("short_sentence_ratio"), _am.get("mid_band_ratio")
    if _short is not None:
        check("example_after_short_ratio_%s" % prefix, _short >= 0.12,
              "%s-after short-sentence ratio %.2f < 0.12" % (prefix, _short))
    if _mid is not None:
        check("example_after_mid_band_%s" % prefix, _mid <= 0.72,
              "%s-after mid-band ratio %.2f > 0.72" % (prefix, _mid))

# ---------------------------------------------------------------------------
# 10b. Autofix must never damage code or splice guidance in as a replacement
# ---------------------------------------------------------------------------
# Both of these were real bugs found by running --fix on this repo's own EVAL.md.
_pat_fix = dap.load_patterns()

# Data loss: code was masked to SPACES, and the dash pattern pads itself with
# `[ \t]*`, so the masked span read as whitespace, the match extended across it,
# and splicing the replacement back deleted the code.
for _src, _must_keep in (
        ("The set is 24 labeled `ai` \u2014 balanced across registers.", "`ai`"),
        ("It misses `m12_casual_review.md` \u2014 all casual or creative.",
         "`m12_casual_review.md`"),
        ("Use `foo` \u2014 then `bar` \u2014 and done.", "`bar`"),
        ("Call `f(x, y)` \u2014 twice.", "`f(x, y)`")):
    _out, _sw, _em, _da = dap.autofix(_src, _pat_fix, "technical")
    check("autofix_preserves_inline_code_%d" % len(_must_keep),
          _must_keep in _out,
          "autofix dropped %s: %r -> %r" % (_must_keep, _src, _out))
    check("autofix_still_fixed_dash_%d" % len(_must_keep), "\u2014" not in _out,
          "the dash should still have been normalized: %r" % _out)

# Fenced code is untouched even when it contains a dash.
_fenced = "```\ncode \u2014 here\n```\nprose \u2014 here\n"
_out_f, _, _, _ = dap.autofix(_fenced, _pat_fix, "technical")
check("autofix_leaves_fenced_code", "code \u2014 here" in _out_f,
      "fenced code was modified: %r" % _out_f)
check("autofix_fixes_prose_after_fence", "prose, here" in _out_f,
      "prose after the fence was not fixed: %r" % _out_f)
check("autofix_code_mask_char_absent", dap.CODE_MASK_CHAR not in _out_f,
      "the code mask character leaked into the output")

# A lone dash in a table cell is a conventional "not applicable" marker, not a
# dash-as-pause. Rewriting it produced `|, |` cells in this repo's own README.
_tbl = ("| metric | before | after |\n|---|---|---|\n"
        "| perplexity | \u2014 | 2.46 |\n\nProse after it \u2014 with a real dash.\n")
_out_t, _, _, _dash_t = dap.autofix(_tbl, _pat_fix, "technical")
check("autofix_spares_table_placeholder_dash",
      "| perplexity | \u2014 | 2.46 |" in _out_t,
      "a table-cell dash was rewritten: %r" % _out_t)
check("autofix_spares_table_alignment_row", "|---|---|---|" in _out_t,
      "the alignment row was damaged: %r" % _out_t)
check("autofix_still_fixes_prose_dash_outside_table",
      "Prose after it, with a real dash." in _out_t,
      "the prose dash outside the table should still be fixed: %r" % _out_t)
check("autofix_table_dash_not_counted", _dash_t == 1,
      "only the prose dash should be counted, got %d" % _dash_t)

# A dash that opens a wrapped line must not leave the comma stranded at the start of
# that line. Found by running --fix on this repo's own README, which produced
# "...rewritten text\n, a figure about...".
for _src in ("vendor at ~97% on rewritten text\n\u2014 a figure about other tools.\n",
             "It works well\n\u2014 mostly.\n",
             "trailing dash at end \u2014\nnext line.\n"):
    _out, _, _, _ = dap.autofix(_src, _pat_fix, "technical")
    check("autofix_no_stranded_mark_%d" % len(_src),
          not any(ln.lstrip().startswith((",", ";", ":"))
                  for ln in _out.split("\n")),
          "stranded mark at a line start: %r -> %r" % (_src, _out))
    check("autofix_line_open_dash_fixed_%d" % len(_src), "\u2014" not in _out,
          "the dash should still have been replaced: %r" % _out)
_inline, _, _, _ = dap.autofix("inline dash \u2014 here stays inline.\n",
                               _pat_fix, "technical")
check("autofix_inline_dash_unchanged_geometry",
      _inline == "inline dash, here stays inline.\n",
      "an inline dash should not gain a newline: %r" % _inline)

# Guidance-shaped suggestions must not be spliced in literally. This turned
# "evaluation harness" into "evaluation use" before the fix.
_out_h, _sw_h, _, _ = dap.autofix("an offline evaluation harness for the linter",
                                  _pat_fix, "technical")
check("autofix_skips_guidance_suggestion", _out_h == "an offline evaluation harness for the linter",
      "a guidance suggestion was applied literally: %r" % _out_h)
check("autofix_still_applies_real_swaps",
      dap.autofix("We should leverage the cache.", _pat_fix, "technical")[0]
      == "We should use the cache.",
      "a genuine 1:1 swap stopped working")
check("is_substitution_classifies",
      dap.is_substitution("use") and dap.is_substitution("if")
      and not dap.is_substitution("cut")
      and not dap.is_substitution("use (verb only)")
      and not dap.is_substitution("x or y"),
      "is_substitution misclassified a suggestion")
# And no shipped suggestion in an auto-fixable category is guidance-shaped
# *without* being skipped, which would silently reintroduce the bug.
for _key in dap.SAFE_FIX_KEYS:
    for _phrase, _sug in dap.as_phrase_list(_pat_fix.get(_key)):
        if _sug and _sug != "cut" and not dap.is_substitution(_sug):
            check("autofix_guidance_entry_skipped_%s_%s" % (_key, _phrase.replace(" ", "_")),
                  _phrase not in dap.autofix(_phrase, _pat_fix, "technical")[0]
                  or dap.autofix(_phrase, _pat_fix, "technical")[1] == 0,
                  "%r/%r is guidance but was applied" % (_key, _phrase))

# ---------------------------------------------------------------------------
# 11. Length-stable scoring and the detector-aligned shape checks (v0.5)
# ---------------------------------------------------------------------------
# The bug this locks: document-level findings used to be divided by word count,
# so the SAME defect scored ~13 points in a 150-word note and ~1 point in a
# 2000-word report. Build two documents with identical document-level defects at
# very different lengths and assert the scores stay close.
_MONO = ("The service reads the queue and writes the result to the store. "
         "The worker polls the queue and updates the record in the table. "
         "The handler parses the payload and returns the response to the client. "
         "The client retries the request and logs the failure to the file. ")
_short_doc = _MONO * 2      # ~ 110 words
_long_doc = _MONO * 20      # ~1100 words
_h_s, _r_s, _w_s, _ = run_analyze("len_stable_short", _short_doc)
_h_l, _r_l, _w_l, _ = run_analyze("len_stable_long", _long_doc)
_sc_s = dap.score(_h_s, _w_s, dap.CATEGORY_WEIGHTS)
_sc_l = dap.score(_h_l, _w_l, dap.CATEGORY_WEIGHTS)
check("len_stable_word_counts_differ", _w_l > 8 * _w_s,
      "long doc should be ~10x the short one (%d vs %d)" % (_w_l, _w_s))
check("len_stable_same_band",
      dap.verdict_band(_sc_s, dap.DEFAULT_BANDS) == dap.verdict_band(_sc_l, dap.DEFAULT_BANDS),
      "same defects, different lengths landed in different bands: %.1f vs %.1f"
      % (_sc_s, _sc_l))
# Numeric stability of the part that was broken. The long fixture legitimately
# repeats more n-grams than the short one, so the totals may differ; what must
# NOT differ is the document-scope contribution, which used to scale as 1/words
# and made an identical defect worth ~13x more in a short file.
def _doc_points(hits):
    return dap.score([h for h in hits if h.line == 0], 1000, dap.CATEGORY_WEIGHTS)


_dp_s, _dp_l = _doc_points(_h_s), _doc_points(_h_l)
check("len_stable_doc_points_identical", abs(_dp_s - _dp_l) < 1e-9,
      "document-scope points moved with length: %.1f vs %.1f" % (_dp_s, _dp_l))
check("len_stable_doc_points_nonzero", _dp_s > 0,
      "the fixture should trip document-level checks, else this proves nothing")
# And the old formula, computed on the same hits, must show the drift the new one
# removes -- so this test fails loudly if someone reverts the fix.
_old_s = sum(dap.CATEGORY_WEIGHTS.get(h.category, 1.0) for h in _h_s) / _w_s * 1000
_old_l = sum(dap.CATEGORY_WEIGHTS.get(h.category, 1.0) for h in _h_l) / _w_l * 1000
check("len_stable_beats_old_formula",
      abs(_dp_s - _dp_l) < abs(_old_s - _old_l),
      "the new scoring is no more length-stable than the old one it replaced")
# No document-scope category may emit an unbounded number of findings, or it
# silently reverts to length-dependent scoring.
_doc_s = {}
for _h in _h_s:
    if _h.line == 0:
        _doc_s[_h.category] = _doc_s.get(_h.category, 0) + 1
_doc_l = {}
for _h in _h_l:
    if _h.line == 0:
        _doc_l[_h.category] = _doc_l.get(_h.category, 0) + 1
check("doc_scope_hits_bounded", _doc_s == _doc_l,
      "document-scope hit counts changed with length: %s vs %s" % (_doc_s, _doc_l))
check("doc_scope_hits_small", all(v <= 4 for v in _doc_l.values()),
      "a document-scope category emitted more than 4 findings: %s" % _doc_l)
# ngram_repetition is an instance check now: it must carry a real line and stay
# capped rather than emitting one positionless hit per repeated gram.
_ng_l = [h for h in _h_l if h.category == "ngram_repetition"]
check("ngram_hits_capped", len(_ng_l) <= 8,
      "ngram_repetition emitted %d hits; expected <= 8" % len(_ng_l))
check("ngram_hits_located", all(h.line > 0 for h in _ng_l),
      "ngram_repetition findings must carry a line number")
# Article-plus-defined-term bigrams are the terminology consistency principle 6
# tells you to HOLD, so the check must not flag them and push you toward rotating
# synonyms. Repeated content phrases still fire.
_terms = ("The skill reads the draft. " * 6) + "The skill scores the draft. "
_h_terms, _, _, _ = run_analyze("ngram_keeps_terminology", _terms)
_ng_terms = [h.text for h in _h_terms if h.category == "ngram_repetition"]
_ng_bigrams = [t for t in _ng_terms if len(t.split('"')[1].split()) == 2]
check("ngram_skips_article_term_bigrams",
      not any(t.split('"')[1].split()[0] in dap.STOPWORDS for t in _ng_bigrams),
      "flagged an article+term bigram: %s" % _ng_bigrams)
check("ngram_still_catches_content_phrases",
      any("reads the draft" in t or "skill reads" in t for t in _ng_terms),
      "a repeated content phrase should still fire: %s" % _ng_terms)

# A single category can no longer swamp the score: the per-category density is
# capped, so a pathologically repetitive document stays bounded.
_repetitive = "Alpha beta gamma delta epsilon zeta. " * 200
_h_rep, _, _w_rep, _ = run_analyze("category_cap", _repetitive)
_by_cat = {}
for _h in _h_rep:
    if _h.line != 0:
        _by_cat[_h.category] = _by_cat.get(_h.category, 0.0) + dap.CATEGORY_WEIGHTS.get(_h.category, 1.0)
_cap = dap.DEFAULTS["scoring"]["category_cap"]
_uncapped = sum(v / _w_rep * 1000 for v in _by_cat.values()) if _w_rep else 0.0
_capped = sum(min(v / _w_rep * 1000, _cap) for v in _by_cat.values()) if _w_rep else 0.0
check("category_cap_bounds_runaway", _capped <= _uncapped + 1e-9,
      "capped density must not exceed the uncapped sum")
check("category_cap_respected",
      all(min(v / _w_rep * 1000, _cap) <= _cap + 1e-9 for v in _by_cat.values()),
      "a category exceeded the cap")

# resolve_scoring honors JSON overrides and falls back per key.
check("resolve_scoring_defaults",
      dap.resolve_scoring({}) == (dap.DEFAULTS["scoring"]["doc_hit_points"],
                                  dap.DEFAULTS["scoring"]["category_cap"],
                                  dap.DEFAULTS["scoring"]["doc_cap_per_category"]))
check("resolve_scoring_doc_cap_override",
      dap.resolve_scoring({"scoring": {"doc_cap_per_category": 2}})[2] == 2.0)
# A check that emits one line-0 hit per example must not be worth N findings.
_many_doc = [dap.Hit("superlative_creep", 0, "x") for _ in range(9)]
check("score_doc_cap_per_category",
      dap.score(_many_doc, 500) == dap.score(
          _many_doc[:int(dap.DEFAULTS["scoring"]["doc_cap_per_category"])], 500),
      "document findings beyond the cap still scored")
check("resolve_scoring_override",
      dap.resolve_scoring({"scoring": {"doc_hit_points": 3.5}})[0] == 3.5)
check("resolve_scoring_bad_value_falls_back",
      dap.resolve_scoring({"scoring": {"category_cap": "lots"}})[1]
      == dap.DEFAULTS["scoring"]["category_cap"])

# assistant_shape: a bulleted, heading-dense, bold-heavy answer fires; ordinary
# prose with a couple of real section headings does not.
_chatty = "\n".join(
    ["# Overview", "", "Some framing text about the topic that runs on for a while so the",
     "word count clears the minimum threshold for the density checks to apply.", ""] +
    sum(([("## Section %d" % i), "",
          "- **Point one:** a claim about the section that adds detail here.",
          "- **Point two:** another claim about the section with more detail.",
          "- **Point three:** a third claim rounding out the section nicely.", ""]
         for i in range(1, 6)), []) +
    ["## Key Takeaways", "", "The material above covered several important areas of concern."])
_h_chat, _r_chat, _, _ = run_analyze("assistant_shape_fires", _chatty)
check("assistant_shape_fires", "assistant_shape" in cats(_h_chat),
      "heading/bullet/bold-dense answer should fire assistant_shape; got %s" % cats(_h_chat))
check("assistant_shape_summary_section",
      any("Key Takeaways" in h.text for h in _h_chat if h.category == "assistant_shape"),
      "the recap section should be called out")
check("assistant_shape_metrics_reported",
      _r_chat.get("headings_per_1k") is not None
      and _r_chat.get("bullet_line_ratio") is not None
      and _r_chat.get("bold_spans_per_1k") is not None,
      "assistant-shape metrics missing from the report")

_plain = ("# Why the retry loop broke\n\n" + _MONO * 3 +
          "\n\nThe fix took three lines. We only retry on 5xx now, and the graph "
          "screams before the queue does. That is the whole change.\n")
_h_plain, _, _, _ = run_analyze("assistant_shape_quiet", _plain)
check("assistant_shape_quiet_on_prose", "assistant_shape" not in cats(_h_plain),
      "prose with one heading must not fire assistant_shape; got %s" % cats(_h_plain))
check("assistant_shape_muted_in_release_notes",
      "assistant_shape" not in cats(run_analyze("as_rn", _chatty, register="release_notes")[0]),
      "release_notes should mute assistant_shape")

# sentence_shape: flat mid-band prose fires both sub-checks; prose that reaches
# past both ends fires neither.
_flat = " ".join(
    "The %s service reads the queue and writes each result to the primary store." % w
    for w in "alpha bravo charlie delta echo foxtrot golf hotel india juliet".split())
_h_flat, _r_flat, _, _ = run_analyze("sentence_shape_fires", _flat)
check("sentence_shape_fires", "sentence_shape" in cats(_h_flat),
      "uniform mid-band sentences should fire sentence_shape; got %s" % cats(_h_flat))
check("sentence_shape_no_short", _r_flat.get("short_sentence_ratio") == 0.0,
      "no short sentences expected, got %s" % _r_flat.get("short_sentence_ratio"))

_bursty = ("It broke. At 14:07 the payments worker stopped draining its queue and "
           "nobody noticed for eleven minutes, because the dashboard averages over "
           "a five-minute window and the spike looked like ordinary jitter until it "
           "very much did not. The cause was dumb. We had shipped a retry loop that "
           "retried on a 4xx, and Stripe returns 402 when a card is declined, so "
           "every decline became sixteen doomed attempts spaced two seconds apart. "
           "Three lines fixed it. Retry on 5xx and 429, nothing else. "
           "I added a metric for retries per request. Next time the graph screams "
           "first.")
_h_bursty, _r_bursty, _, _ = run_analyze("sentence_shape_quiet", _bursty)
check("sentence_shape_quiet_on_bursty", "sentence_shape" not in cats(_h_bursty),
      "varied prose must not fire sentence_shape; got %s (short=%s mid=%s)"
      % (cats(_h_bursty), _r_bursty.get("short_sentence_ratio"),
         _r_bursty.get("mid_band_ratio")))

# Rhythm checks are deliberately universal: no register mute may silence them,
# because they fire only on LOW variance and no genre is served by a metronome.
_pat_all = dap.load_patterns()
for _tok, _cats in (_pat_all.get("muted_checks") or {}).items():
    check("rhythm_never_muted_%s" % _tok,
          not ({"burstiness", "sentence_shape"} & set(_cats or [])),
          "mute token %r silences a rhythm check: %s" % (_tok, _cats))

# "harness" is filler as a verb and ordinary technical English as a noun. The noun
# compounds are exempted; the verb sense must still fire, or the exception is too wide.
for _txt, _want in (("an offline evaluation harness for the linter", False),
                    ("the detector harness runs offline", False),
                    ("a test harness covers it", False),
                    ("we harness the power of data", True),
                    ("harness this capability today", True)):
    _h_hn, _, _, _ = run_analyze("harness_sense_%d" % len(_txt), _txt)
    _fired = "filler" in cats(_h_hn)
    check("harness_%s_%d" % ("verb_fires" if _want else "noun_exempt", len(_txt)),
          _fired == _want,
          "%r: filler fired=%s, expected %s" % (_txt, _fired, _want))

# ---------------------------------------------------------------------------
# 10c. --register auto
# ---------------------------------------------------------------------------
# Before this, every document was scored with the `technical` mute set regardless of
# what it was, so a novelist's em-dashes and a marketer's "you" were both tells.
_mk = os.path.join(EXAMPLES, "marketing-after.md")
_em_ex = os.path.join(EXAMPLES, "email-after.md")

_auto_mk = json.loads(run_cli(["--register", "auto", "--json", _mk]).stdout.decode())
check("auto_infers_marketing", _auto_mk["register"] == "marketing",
      "expected marketing, got %r" % _auto_mk["register"])
check("auto_reports_its_reasoning",
      bool((_auto_mk.get("inferred_register") or {}).get("reasons")),
      "the payload must record why the register was chosen")
check("auto_reports_confidence",
      0.0 <= (_auto_mk.get("inferred_register") or {}).get("confidence", -1) <= 1.0,
      "confidence must be a fraction")

_auto_em = json.loads(run_cli(["--register", "auto", "--json", _em_ex]).stdout.decode())
check("auto_infers_email", _auto_em["register"] == "email",
      "expected email, got %r" % _auto_em["register"])

# An explicit register always wins, and the payload records no inference.
_explicit = json.loads(run_cli(["--register", "creative", "--json", _mk]).stdout.decode())
check("explicit_register_wins", _explicit["register"] == "creative")
check("explicit_register_records_no_inference",
      _explicit.get("inferred_register") is None,
      "an explicit register must not be reported as inferred")

# The reasoning goes to stderr, so --json stays parseable and --quiet stays a table.
_res_auto = run_cli(["--register", "auto", "--json", _mk])
check("auto_json_stays_clean_on_stdout",
      _res_auto.stdout.decode().lstrip().startswith(("{", "[")),
      "stdout must stay valid JSON with --register auto")
_res_quiet = run_cli(["--register", "auto", "--quiet", _mk])
check("auto_quiet_stays_one_line",
      len([ln for ln in _res_quiet.stdout.decode().strip().split("\n") if ln]) == 1,
      "--quiet must stay one line per file: %r" % _res_quiet.stdout.decode())

# Inference must be deterministic and must fail safe on short or empty input.
_t1 = dap.infer_register(open(_mk, encoding="utf-8").read())
_t2 = dap.infer_register(open(_mk, encoding="utf-8").read())
check("auto_deterministic", _t1 == _t2, "inference is not deterministic")
for _tiny in ("", "   \n", "Hello.", "Hi there, thanks!"):
    _reg, _c, _why = dap.infer_register(_tiny)
    check("auto_tiny_falls_back_%d" % len(_tiny), _reg == "technical",
          "%r inferred %r; short input has no register signal" % (_tiny, _reg))
    check("auto_tiny_explains_%d" % len(_tiny), bool(_why),
          "a fallback must still say why")

# Every cue must name a real register, or the vote can never be applied. The
# tuple carries an optional fifth element (min_hits), so unpack defensively.
for _ci, _cue in enumerate(dap.CUES):
    _reg, _w, _pat, _why = _cue[:4]
    _min_hits = _cue[4] if len(_cue) > 4 else 1
    check("auto_cue_register_valid_%d_%s" % (_ci, _reg), _reg in dap.REGISTERS,
          "cue names unknown register %r" % _reg)
    check("auto_cue_weight_positive_%d_%s" % (_ci, _reg), _w > 0)
    check("auto_cue_min_hits_valid_%d_%s" % (_ci, _reg),
          isinstance(_min_hits, int) and _min_hits >= 1,
          "cue %r has a bad min_hits %r" % (_why, _min_hits))
    check("auto_cue_reason_present_%d_%s" % (_ci, _reg), bool(_why and _why.strip()),
          "every cue must carry a human-readable reason")

# ---------------------------------------------------------------------------
# 11a. The mute table may not contradict the skill's own doctrine
# ---------------------------------------------------------------------------
# SKILL.md principle 5 names a "universal core" of tells that are wrong in EVERY
# genre. If a register mutes one of them, the config contradicts the documentation
# and a whole class of tells goes unchecked in that genre -- which is exactly how
# `casual` and `creative` ended up with no rhythm check at all until v0.5.
UNIVERSAL_CORE = {
    "rule-of-three": ("rule_of_three",),
    "bold-bullet listicles": ("bold_bullets",),
    "puffery": ("puffery",),
    "vague attribution": ("vague_attribution",),
    "low burstiness": ("burstiness", "sentence_shape"),
    "restatement": ("circular_conclusion", "ngram_repetition"),
    "not-X-but-Y": ("antithesis",),
    "consistency drift": ("dialect", "heading_case"),
}
_pat_mutes = dap.load_patterns()
for _reg in dap.REGISTERS:
    _muted = dap.muted_categories(_reg, _pat_mutes)
    for _name, _cats in UNIVERSAL_CORE.items():
        _hit = sorted(set(_cats) & _muted)
        check("universal_core_%s_not_muted_in_%s" % (_name.replace(" ", "_"), _reg),
              not _hit,
              "register %r mutes %s, which principle 5 calls universal" % (_reg, _hit))

# The mute table itself must be internally consistent: no token naming a category
# that does not exist, no dead tokens, no token used without a definition.
_mc = _pat_mutes.get("muted_checks") or {}
for _tok, _cats in _mc.items():
    _bogus = [c for c in (_cats or []) if c not in dap.KNOWN_CATEGORIES]
    check("mute_token_categories_exist_%s" % _tok, not _bogus,
          "mute token %r names unknown categories %s" % (_tok, _bogus))
_used = set()
for _reg in dap.REGISTERS:
    _used |= set((_pat_mutes.get("register_mutes") or {}).get(_reg, []))
check("mute_tokens_all_defined", not (_used - set(_mc)),
      "register_mutes uses undefined tokens: %s" % sorted(_used - set(_mc)))
check("mute_tokens_none_dead", not (set(_mc) - _used),
      "muted_checks defines tokens no register uses: %s" % sorted(set(_mc) - _used))

# Specificity is REPORTED, never scored: it fires on legitimate human writing that
# happens to contain no number or proper noun (fiction, most obviously), and scoring
# it would penalize exactly the writers detectors already mistreat.
check("specificity_is_not_a_category",
      "specificity" not in dap.KNOWN_CATEGORIES
      and "specifics" not in dap.KNOWN_CATEGORIES,
      "specificity became a scored category; it must stay a diagnostic")
_h_spec, _rep_spec, _, _ = run_analyze(
    "specificity_metric",
    "At 14:07 the Stripe webhook failed 16 times. Priya shipped the fix on Tuesday. "
    * 4)
check("specificity_counts_numbers", (_rep_spec.get("numbers") or 0) >= 4,
      "expected numbers to be counted, got %s" % _rep_spec.get("numbers"))
check("specificity_counts_proper_nouns", (_rep_spec.get("proper_nouns") or 0) >= 4,
      "expected proper nouns to be counted, got %s" % _rep_spec.get("proper_nouns"))
check("specificity_not_thin_when_detailed", _rep_spec.get("specifics_thin") is False,
      "a document full of names and numbers must not read as thin")
_h_vague, _rep_vague, _, _ = run_analyze(
    "specificity_thin",
    ("The implications are significant and the underlying reasons are structural. "
     "Organizations must consider the broader context of their operational posture. ")
    * 8)
check("specificity_thin_when_vacuous", _rep_vague.get("specifics_thin") is True,
      "abstract prose with nothing checkable should read as thin: %s per 100w over %s words"
      % (_rep_vague.get("specifics_per_100"), _rep_vague.get("word_count")))
# Short inputs are never judged thin: a two-line note legitimately has no numbers.
_h_short, _rep_short, _, _ = run_analyze(
    "specificity_short_not_judged", "The reasons are structural. Consider the context.")
check("specificity_short_not_judged", _rep_short.get("specifics_thin") is False,
      "a very short input must not be called thin")

# ---------------------------------------------------------------------------
# 11b. Hit line numbers must point at the SOURCE line
# ---------------------------------------------------------------------------
# prose_for_metrics joins soft-wrapped lines, so a 75-line document collapses to 12.
# Before MappedLineMap, every check located against that text reported a line from
# the reduced text -- a finding on source line 42 was reported as line 8, which sent
# readers to the wrong place and made inline ignore directives unable to match.
_doc_lines = [
    "# A heading",
    "",
    "First paragraph, soft-wrapped across",
    "two source lines with nothing to flag.",
    "",
    "## Another heading",
    "",
    "Some more filler text here that carries no tell at all,",
    "also wrapped, still nothing.",
    "",
    "This line has a real tell \u2014 an em-dash sitting right here.",
    "",
    "And a second one \u2014 because one dash alone is not a tell.",
    "",
    "And a third \u2014 which is what the density gate now requires.",
    "",
    "- a list item with fast, cheap, and good in it",
    "- another item with quick, cheap, and simple in it",
]
_doc = "\n".join(_doc_lines) + "\n"
_h_loc, _, _, _ = run_analyze("line_map_source_lines", _doc)
_em = [h for h in _h_loc if h.category == "em_dash"]
_r3 = [h for h in _h_loc if h.category == "rule_of_three"]
check("line_map_em_dash_found", bool(_em), "the em-dash fixture should fire")
if _em:
    _em_lines = sorted(h.line for h in _em)
    check("line_map_em_dash_exact_lines", _em_lines == [11, 13, 15],
          "em-dashes are on source lines 11, 13 and 15, reported %s" % _em_lines)
check("line_map_triad_found", bool(_r3), "the triad fixture should fire")
if _r3:
    check("line_map_triad_exact_line", _r3[0].line == 17,
          "triad is on source line 17, reported %d" % _r3[0].line)
_max_line = len(_doc_lines)
check("line_map_no_line_beyond_source",
      all(h.line <= _max_line for h in _h_loc),
      "a hit reported a line past the end of a %d-line document: %s"
      % (_max_line, [(h.category, h.line) for h in _h_loc if h.line > _max_line]))

# Because the lines are right, an inline directive can now suppress those hits.
_doc_ignored = _doc.replace(
    "This line has a real tell \u2014 an em-dash sitting right here.",
    "This line has a real tell \u2014 an em-dash sitting right here."
    "  <!-- human-voice: ignore em_dash -->")
_h_ign, _, _, _ = run_analyze("line_map_directive_matches", _doc_ignored)
_ign_em = sorted(h.line for h in _h_ign if h.category == "em_dash")
# Line 11 carries the directive and must go; line 13 has no directive and must stay.
# That the OTHER one survives is the point: it proves the directive matched by exact
# source line rather than blanket-suppressing the category.
check("line_map_directive_suppresses_its_line", 11 not in _ign_em,
      "the directive on line 11 did not suppress that hit: %s" % _ign_em)
check("line_map_directive_spares_other_lines", 13 in _ign_em,
      "the undirected hit on line 13 should survive: %s" % _ign_em)

# The segment table itself: offsets ascending, every line within range.
_txt, _segs = dap.prose_for_metrics(dap.strip_code(_doc), with_line_map=True)
check("line_map_segments_sorted",
      all(_segs[i][0] <= _segs[i + 1][0] for i in range(len(_segs) - 1)),
      "segment offsets must be ascending: %s" % _segs)
check("line_map_segments_in_range",
      all(1 <= ln <= _max_line for _off, ln in _segs),
      "a segment points outside the document: %s" % _segs)
check("line_map_backward_compatible",
      isinstance(dap.prose_for_metrics(dap.strip_code(_doc)), str),
      "prose_for_metrics must still return a bare string by default")

# ---------------------------------------------------------------------------
# 12. The verification gate must never report a pass it did not earn
# ---------------------------------------------------------------------------
sys.path.insert(0, SCRIPTS)
import verify_detector as _V  # noqa: E402
from human_voice_linter import detector as _D  # noqa: E402

_target = os.path.join(EXAMPLES, "modern-ai-after.md")

# Every registered detector declares a usable request shape.
for _var, _spec in _D.DETECTORS.items():
    check("detector_shape_https_%s" % _var, _spec["url"].startswith("https://"))
    check("detector_shape_headers_%s" % _var, isinstance(_spec["headers"]("k"), dict))
    check("detector_shape_body_%s" % _var, isinstance(_spec["body"]("t"), dict))
    check("detector_shape_path_%s" % _var, bool(_spec["path"]))

# No key configured => exit 2 (unavailable), never 0. A gate that could not run
# must not be reportable as a pass.
_saved_keys = {v: os.environ.pop(v) for v in _D.KEY_ENV_VARS if v in os.environ}
try:
    check("detector_no_key_raises",
          _raises(_D.DetectorUnavailable, lambda: _D.probe("x")),
          "probe should raise DetectorUnavailable with no key")
    _out = _capture_stdout(lambda: _V.main([_target]))
    check("gate_no_key_exit_2", _out[0] == 2,
          "no-key gate returned %r, expected 2" % (_out[0],))
    check("gate_no_key_says_unavailable", "UNAVAILABLE" in _out[1],
          "no-key gate must say UNAVAILABLE: %r" % _out[1][:80])
    check("gate_no_key_disclaims_pass", "not run" in _out[1],
          "no-key gate must say the gate was not run")
finally:
    os.environ.update(_saved_keys)

# Probability plumbing, including the 0-100 human-scale inversion.
_p = _D.probe("t", "k", "GPTZERO_API_KEY",
              opener=lambda u, d, h, t: {"documents": [{"completely_generated_prob": 0.87}]})
check("detector_probe_reads_probability", abs(_p - 0.87) < 1e-9, "got %r" % _p)
_pw = _D.probe("t", "k", "WINSTON_API_KEY", opener=lambda u, d, h, t: {"score": 96})
check("detector_probe_inverts_human_scale", abs(_pw - 0.04) < 1e-9,
      "a 0-100 human score should invert to p(AI); got %r" % _pw)
check("detector_probe_rejects_non_probability",
      _raises(ValueError, lambda: _D.probe(
          "t", "k", "GPTZERO_API_KEY",
          opener=lambda u, d, h, t: {"documents": [{"completely_generated_prob": 7}]})),
      "a value outside [0,1] must be rejected, not returned")
check("detector_probe_names_stale_field",
      _raises(KeyError, lambda: _D.probe("t", "k", "GPTZERO_API_KEY",
                                         opener=lambda u, d, h, t: {"nope": 1})),
      "a stale response shape must raise, naming the missing field")
check("detector_verdict_thresholds",
      _D.verdict(0.02)[1] and not _D.verdict(0.93)[1]
      and not _D.verdict(0.06, max_p_ai=0.05)[1],
      "verdict() mis-thresholded")

# The CLI's exit code is the stopping condition, so it must track the verdict.
_orig_probe = _V.D.probe
try:
    os.environ["GPTZERO_API_KEY"] = "test-key"
    for _pv, _want_rc, _want_word in ((0.93, 1, "FLAGGED"), (0.02, 0, "CLEAR")):
        _V.D.probe = (lambda text, k, kv, timeout=30, _x=_pv: _x)
        _rc, _txt = _capture_stdout(lambda: _V.main([_target]))
        check("gate_exit_%s" % _want_word.lower(), _rc == _want_rc,
              "p=%.2f gave exit %r, expected %d" % (_pv, _rc, _want_rc))
        check("gate_says_%s" % _want_word.lower(), _want_word in _txt,
              "expected %s in output: %r" % (_want_word, _txt[:90]))
    # A flagged verdict must point at shape/rhythm and must refuse the tricks.
    _V.D.probe = (lambda text, k, kv, timeout=30: 0.93)
    _, _txt = _capture_stdout(lambda: _V.main([_target]))
    check("gate_flagged_gives_priority_order",
          "shape first" in _txt and "distribution" in _txt,
          "a flagged gate should name the fix order")
    check("gate_flagged_refuses_tricks",
          "Unicode" in _txt and "typos" in _txt,
          "a flagged gate must warn off the evasion tricks")
    # A detector error is not a pass either.
    def _boom(*a, **k):
        raise RuntimeError("connection reset")
    _V.D.probe = _boom
    _rc, _txt = _capture_stdout(lambda: _V.main([_target]))
    check("gate_error_is_not_a_pass", _rc == 2 and "NOT verified" in _txt,
          "a detector error gave exit %r: %r" % (_rc, _txt[:90]))
    # --json stays machine-readable and carries the floor score alongside.
    _V.D.probe = (lambda text, k, kv, timeout=30: 0.4)
    _rc, _txt = _capture_stdout(lambda: _V.main(["--json", _target]))
    _payload = json.loads(_txt)
    check("gate_json_shape",
          _payload["status"] == "flagged" and _payload["p_ai"] == 0.4
          and "floor_score" in _payload and "detector" in _payload,
          "unexpected --json payload: %r" % _payload)
finally:
    _V.D.probe = _orig_probe
    os.environ.pop("GPTZERO_API_KEY", None)
    os.environ.update(_saved_keys)

# ---------------------------------------------------------------------------
# v0.6: the modern syntactic signature, and the false positives it must not have
# ---------------------------------------------------------------------------

_PAD = ("The team shipped the change on Tuesday and watched the graphs. "
        "Nothing moved for an hour. Then the queue drained. " * 6)

# Clefts: stacked, they fire; one on its own does not.
_cleft_text = (
    "What actually consumed the time was the reconciliation step. "
    "The reason the migration was hard is that the tuning had drifted. "
    "What we would do differently is start with the differ. " + _PAD)
_h_cleft, _r_cleft, _, _ = run_analyze("cleft_stacked", _cleft_text)
check("cleft_stacking_fires", "cleft" in cats(_h_cleft),
      "three clefts in one document should fire; got %s" % sorted(cats(_h_cleft)))
check("cleft_count_reported", (_r_cleft.get("cleft_count") or 0) >= 3,
      "cleft_count was %s" % _r_cleft.get("cleft_count"))
_h_cleft1, _, _, _ = run_analyze(
    "cleft_single", "What matters here is the p99 latency. " + _PAD)
check("cleft_single_does_not_fire", "cleft" not in cats(_h_cleft1),
      "one cleft is ordinary English and must not fire")
# Mid-sentence noun phrases that merely contain a cleft head word are not clefts.
_h_cleft_fp, _, _, _ = run_analyze(
    "cleft_false_positive",
    "We fixed the problem and the answer was obvious to everyone. "
    "She solved the question of whether the pipeline could scale. "
    "The difference between the two teams showed up in the retro. " + _PAD)
check("cleft_no_false_positive", "cleft" not in cats(_h_cleft_fp),
      "non-cleft uses of problem/question/answer fired: %s" % sorted(cats(_h_cleft_fp)))
# Creative narration gets a WIDER bar for clefts, not an exemption. The check
# used to be muted outright in that register, which meant a fiction sample could
# stack them at any rate and score zero; two of the three files the floor missed
# on the modern-AI class were exactly that. register_thresholds scales the bar
# 1.3x instead, so a moderate rate passes in creative and fails in technical,
# and a heavy stack fails in both.
_cleft_moderate = _cleft_text.replace(_PAD, "") + (
    "The team shipped the change on Tuesday and watched the graphs. "
    "Nothing moved for an hour. Then the queue drained. " * 18)
_h_cleft_mod_tech, _, _, _ = run_analyze("cleft_moderate_tech", _cleft_moderate)
_h_cleft_mod_cre, _, _, _ = run_analyze("cleft_moderate_creative", _cleft_moderate,
                                        register="creative")
check("cleft_moderate_fires_in_technical", "cleft" in cats(_h_cleft_mod_tech),
      "a moderate cleft rate should still fire in the strictest register")
check("cleft_moderate_passes_in_creative", "cleft" not in cats(_h_cleft_mod_cre),
      "creative tolerates 1.3x the cleft rate; got %s" % sorted(cats(_h_cleft_mod_cre)))
_h_cleft_cre, _, _, _ = run_analyze("cleft_creative", _cleft_text, register="creative")
check("cleft_stacking_fires_in_creative", "cleft" in cats(_h_cleft_cre),
      "a heavy stack is a tell in fiction too; the bar is wider, not absent")
_h_cleft_cas, _, _, _ = run_analyze("cleft_casual", _cleft_text, register="casual")
check("cleft_fires_in_casual", "cleft" in cats(_h_cleft_cas),
      "casual prose stacks clefts the same way an assistant answer does")

# Resultative participial tails.
_tail_text = (
    "The cluster reindexes nightly, allowing the team to treat staleness as fine. "
    "The new path streams updates, ensuring that a document is searchable fast. "
    "We wrote a differ, giving us a concrete list of disagreements. " + _PAD)
_h_tail, _r_tail, _, _ = run_analyze("participial_tail", _tail_text)
check("participial_tail_fires", "participial_tail" in cats(_h_tail),
      "got %s" % sorted(cats(_h_tail)))
check("participial_tail_counted", (_r_tail.get("participial_tail_count") or 0) >= 3)
_h_tail1, _, _, _ = run_analyze(
    "participial_tail_single", "We shipped the differ, giving us a list. " + _PAD)
check("participial_tail_single_ok", "participial_tail" not in cats(_h_tail1))

# Copula density and clause welding are reported even when they do not fire.
_h_cop, _r_cop, _, _ = run_analyze("copula_metric", _PAD)
check("copula_metric_reported", _r_cop.get("copula_per_1k") is not None)
check("clause_splice_metric_reported", _r_cop.get("clause_splice_count") is not None)

# Paragraph openers key on the first TWO words, so three paragraphs starting
# "The" with different second words is not a finding.
_paras_ok = "\n\n".join([
    "The math is simple enough to check by hand in a minute.",
    "The real win is not the money, though the money helps a little.",
    "The warehouse lease runs about seven thousand dollars a month.",
    "Last Black Friday the dock was slammed and we ate the refunds.",
    "We break even somewhere around month five on current volume.",
])
_h_po_ok, _, _, _ = run_analyze("paragraph_openers_ok", _paras_ok)
check("paragraph_openers_no_article_fp", "paragraph_openers" not in cats(_h_po_ok),
      "three paragraphs starting with 'The' is not a templated opening")
_paras_bad = "\n\n".join(["The system handles the write path and the read path."] * 3
                         + ["A different opening sentence entirely here.",
                            "Another different opening sentence here too."])
_h_po_bad, _, _, _ = run_analyze("paragraph_openers_bad", _paras_bad)
check("paragraph_openers_fires", "paragraph_openers" in cats(_h_po_bad),
      "got %s" % sorted(cats(_h_po_bad)))

# Bullet openers.
_bullets = "\n".join(["- Improve the ingestion throughput on the hot path",
                      "- Improve the retry budget for the write path",
                      "- Improve the alerting on queue depth",
                      "- Reduce the reindex window to under an hour"])
_h_bo, _, _, _ = run_analyze("bullet_openers", _bullets)
check("bullet_openers_fires", "bullet_openers" in cats(_h_bo),
      "got %s" % sorted(cats(_h_bo)))

# Noun chains.
# Three links, not two: "a copy of the report in the archive" is ordinary English.
_h_nc, _, _, _ = run_analyze(
    "noun_chains",
    "The reduction of the complexity of the design of the interface mattered. "
    "The evaluation of the quality of the output of the model came later. " + _PAD)
check("noun_chain_fires", "noun_chain" in cats(_h_nc), "got %s" % sorted(cats(_h_nc)))

# --- Code fences must not contribute markdown shape ---------------------------
_fenced = (
    "# A readme\n\nSome real prose lives out here in the document body.\n\n"
    "```bash\n# Install The Dependencies\npip install foo\n```\n\n"
    "```markdown\n- **Performance**: fast\n- **Reliability**: up\n- **Security**: safe\n"
    "\n---\n\nSome \U0001F680 emoji copy.\n```\n\n"
    "More prose after the fence, enough of it to make the document measurable.\n")
_h_fence, _r_fence, _, _ = run_analyze("code_fence_shape", _fenced)
for _cat in ("heading_case", "bold_bullets", "formatting"):
    check("fence_no_%s" % _cat, _cat not in cats(_h_fence),
          "%s fired on content inside a code fence" % _cat)
check("fence_bold_spans_zero", (_r_fence.get("bold_spans") or 0) == 0,
      "bold spans inside a fence were counted: %s" % _r_fence.get("bold_spans"))

# --- Dialect: a word ending a sentence is not an identifier -------------------
_h_dia_end, _, _, _ = run_analyze(
    "dialect_sentence_final", "We had to optimise. The colour was wrong.",
    dialect="american")
check("dialect_catches_sentence_final",
      sorted(h.text.lower() for h in _h_dia_end if h.category == "dialect")
      == ["colour", "optimise"],
      "sentence-final 'optimise.' was skipped as an identifier")
_h_dia_attr, _, _, _ = run_analyze(
    "dialect_attribute_access", "Call theme.colour and Palette.colour here.",
    dialect="american")
check("dialect_skips_attribute_access",
      not [h for h in _h_dia_attr if h.category == "dialect"],
      "attribute access should still be skipped")

# --- superlative_creep is ONE document finding, not one per example -----------
_sup = ("The best tool. The fastest path. The most complete answer. "
        "The ultimate guide. A perfect fit. The greatest win. ") * 4 + _PAD
_h_sup, _, _, _ = run_analyze("superlative_one_finding", _sup)
_sups = [h for h in _h_sup if h.category == "superlative_creep"]
check("superlative_single_document_finding", len(_sups) <= 1,
      "superlative_creep emitted %d findings for one density signal" % len(_sups))

# --- Underscored identifiers survive markup stripping -------------------------
check("underscore_identifier_survives",
      dap.strip_inline_markup("Call get_user_by_id and MAX_RETRY_COUNT.")
      == "Call get_user_by_id and MAX_RETRY_COUNT.")
check("underscore_emphasis_still_stripped",
      dap.strip_inline_markup("A _word_ and __bold__ here.") == "A word and bold here.")

# --- Instance checks are not silently capped at their display limit -----------
_many_dashes = " ".join("Clause %d — with an aside attached to it." % i
                        for i in range(30))
_h_many, _r_many, _, _ = run_analyze("uncapped_instance_hits", _many_dashes)
check("instance_hits_not_capped_at_eight",
      len([h for h in _h_many if h.category == "em_dash"]) > 8,
      "em_dash hits were capped at the old display limit")

# --- Short documents are not amplified by the density denominator -------------
_two_hits = dap.score([dap.Hit("em_dash", 3, "x"), dap.Hit("em_dash", 5, "x")], 220)
check("density_floor_bounds_short_docs", _two_hits < 15.0,
      "two hits in a 220-word note scored %.1f, the category cap" % _two_hits)

# --- collect_targets dedupes and prunes ---------------------------------------
_ct = dap.collect_targets(["eval/corpus/human", "eval/corpus/human/h01_technical_postmortem.md"],
                          recursive=False)
check("collect_targets_dedupes", len(_ct) == len(set(os.path.normpath(p) for p in _ct)),
      "collect_targets returned duplicates")

# --- A soft-wrapped list item is ONE sentence -------------------------------
_wrapped = ("- **Deployment tooling**: A new pipeline reduced deploy time from 40 minutes to\n"
            "  6, allowing engineers to ship changes the same day they write them.\n"
            "- Second item that is short\n"
            "- Third item ends with a period.\n\n"
            "Ordinary paragraph that wraps\nacross two lines here.\n")
_wrapped_sents = dap.sentences(dap.prose_for_metrics(dap.strip_code(_wrapped)))
check("wrapped_list_item_is_one_sentence", len(_wrapped_sents) == 4,
      "expected 4 sentences, got %d: %s" % (len(_wrapped_sents), _wrapped_sents))
check("wrapped_list_item_not_split_mid_clause",
      not any(s.rstrip().endswith("to.") for s in _wrapped_sents),
      "a wrapped bullet was cut mid-clause: %s" % _wrapped_sents)
check("list_items_still_terminated",
      all(s.rstrip()[-1] in ".!?" for s in _wrapped_sents),
      "every emitted block should end in terminal punctuation: %s" % _wrapped_sents)
# The source-line map must survive the join.
_wrapped_text, _wrapped_segs = dap.prose_for_metrics(
    dap.strip_code(_wrapped), with_line_map=True)
check("wrapped_list_segments_in_range",
      all(1 <= ln <= _wrapped.count("\n") + 1 for _off, ln in _wrapped_segs),
      "a segment pointed outside the document: %s" % _wrapped_segs)

# --- The humanizer's own fingerprint: one mark substituted for every dash ------
_SEMI_SWAPPED = (
    "The migration took three weeks; the surprise was how little of it was the "
    "migration. Reconciliation ate the time; nobody had characterized the corpus. "
    "We ran a single cluster with nightly reindexing; staleness was acceptable. "
    "The new path streams updates; a document is searchable in seconds. "
    "Relevance tuning had drifted; a recency boost from 2022 was undocumented. "
    "We built a differ and replayed a week of queries; eleven disagreed. ") * 4
_h_semi, _r_semi, _, _ = run_analyze("punctuation_substitution", _SEMI_SWAPPED)
check("punctuation_substitution_fires",
      any(h.category == "over_correction" and "semicolon" in h.text for h in _h_semi),
      "a document with 88 semicolons per 1k words and no dash at all should fire")
check("semicolon_metric_reported", _r_semi.get("semicolon_per_1k") is not None)
# A writer who uses a few semicolons AND dashes is just punctuating.
_h_mix, _, _, _ = run_analyze(
    "mixed_punctuation_ok",
    "The migration took three weeks; reconciliation ate most of it. "
    "We ran one cluster — nightly reindexing, acceptable staleness — until March. "
    "Relevance tuning had drifted. A recency boost from 2022 was undocumented. "
    + "Some further prose to carry the document past the length floor. " * 20)
check("mixed_punctuation_not_over_correction",
      not [h for h in _h_mix if h.category == "over_correction" and "semicolon" in h.text],
      "a document that uses both marks is not a mechanical substitution")
# Two semicolons in a short note is not a signature.
_h_few, _, _, _ = run_analyze(
    "few_semicolons_ok",
    "We shipped it; the graphs held. Nothing else changed; nobody paged. "
    + "Ordinary prose continues here without further punctuation games. " * 20)
check("few_semicolons_not_flagged",
      not [h for h in _h_few if h.category == "over_correction" and "semicolon" in h.text])

# --- Autofix never edits inside a URL -----------------------------------------
_url_src = "See [docs](https://example.com/delve-into-it?a--b) and https://x.io/leverage-guide now."
_url_fixed, _, _, _ = dap.autofix(_url_src, PAT, "technical")
check("autofix_preserves_link_destination",
      "https://example.com/delve-into-it?a--b" in _url_fixed
      and "https://x.io/leverage-guide" in _url_fixed,
      "autofix rewrote a URL: %r" % _url_fixed)

# --- Autofix varies the replacement mark --------------------------------------
_varied, _, _, _ = dap.autofix(
    "The result — surprisingly — held. We shipped three things — speed, cost, and risk.",
    PAT, "technical")
check("autofix_paired_aside_to_parens", "(surprisingly)" in _varied,
      "paired aside should become parentheses: %r" % _varied)
check("autofix_enumeration_to_colon", "three things: speed" in _varied,
      "an enumeration should take a colon: %r" % _varied)

# --- An unterminated ignore-start runs to end of document ---------------------
_unterminated = ("<!-- human-voice: ignore-start filler -->\n"
                 "We delve into the topic here.\n\nWe delve again down here.\n")
_h_unterm, _, _, _ = run_analyze("unterminated_ignore_start", _unterminated)
check("unterminated_ignore_start_applies",
      "filler" not in cats(_h_unterm),
      "an unterminated ignore-start suppressed nothing: %s" % sorted(cats(_h_unterm)))

# --- CRLF input scores the same as LF -----------------------------------------
_lf = "---\ntitle: x\n---\n\nSome prose here that reads fine.\n"
_h_lf, _, _w_lf = dap.analyze(_lf, "technical", None, PAT)
_h_crlf, _, _w_crlf = dap.analyze(_lf.replace("\n", "\r\n"), "technical", None, PAT)
check("crlf_matches_lf", _w_lf == _w_crlf,
      "CRLF gave %d words, LF gave %d" % (_w_crlf, _w_lf))

# --- Clause lists are not noun triads -----------------------------------------
_h_clause_triad, _, _, _ = run_analyze(
    "clause_list_not_triad",
    "You paste code into a notebook, the kernel dies, and the last save is gone. "
    "Install the extension, restart once, and it starts snapshotting for you.")
check("clause_list_not_flagged_as_triad",
      "rule_of_three" not in cats(_h_clause_triad),
      "a list of clauses was flagged as a noun triad")
_h_real_triad, _, _, _ = run_analyze(
    "real_noun_triad",
    "We ship encryption at rest, row-level access control, and audit logging. "
    "The platform offers automated backups, point-in-time recovery, and cross-region replication.")
check("real_noun_triad_still_flagged", "rule_of_three" in cats(_h_real_triad),
      "a genuine noun triad stopped firing")


# A recap heading is a tell only when the document is wrapping ITSELF up, so it
# has to be the last heading. "Next steps" in the middle of a plan is a section.
_pad = "Some real prose here that carries the argument along for a while. " * 20
_h_mid, _, _, _ = run_analyze(
    "recap_heading_mid_document",
    "# Plan\n\n" + _pad + "\n\n## Next steps\n\n" + _pad + "\n\n## Risks\n\n" + _pad)
check("recap_heading_mid_document_quiet",
      not [h for h in _h_mid if h.category == "assistant_shape" and "closes with" in h.text],
      "a mid-document 'Next steps' section was read as a sign-off")
_h_end, _, _, _ = run_analyze(
    "recap_heading_at_end",
    "# Plan\n\n" + _pad + "\n\n## Risks\n\n" + _pad + "\n\n## Key takeaways\n\n" + _pad)
check("recap_heading_at_end_fires",
      any(h.category == "assistant_shape" and "closes with" in h.text for h in _h_end))

# A setext heading underline is not a horizontal rule between sections.
_h_setext, _r_setext, _, _ = run_analyze(
    "setext_underline_not_a_rule",
    "Title One\n=========\n\nProse here.\n\nTitle Two\n---------\n\nMore prose.\n\n"
    "Title Three\n-----------\n\nAnd more.\n\nTitle Four\n----------\n\nAnd more still.\n")
check("setext_underline_not_a_rule", (_r_setext.get("section_rules") or 0) == 0,
      "setext underlines were counted as %s horizontal rules"
      % _r_setext.get("section_rules"))
_h_rules, _r_rules, _, _ = run_analyze(
    "real_rules_still_counted",
    "Prose.\n\n---\n\nProse.\n\n---\n\nProse.\n\n---\n\nProse.\n\n---\n\nProse.\n")
check("real_rules_still_counted", (_r_rules.get("section_rules") or 0) >= 4,
      "real horizontal rules stopped being counted: %s" % _r_rules.get("section_rules"))

# Column alignment is not a doubled word.
_h_col, _, _, _ = run_analyze(
    "aligned_columns_not_doubled",
    "match     Match a regular expression at the start of the string.\n"
    "search    Search the string for a match anywhere inside it.\n")
check("aligned_columns_not_doubled", "doubled_word" not in cats(_h_col),
      "an aligned two-column table was read as a doubled word")
_h_dbl, _, _, _ = run_analyze("real_doubled_word", "We shipped the the fix on Tuesday.")
check("real_doubled_word_still_fires", "doubled_word" in cats(_h_dbl))

# An emoticon is not a space before punctuation.
_h_emo, _, _, _ = run_analyze("emoticon_not_mechanics", "It worked, plus one :-) and we shipped.")
check("emoticon_not_flagged_as_mechanics", "mechanics" not in cats(_h_emo),
      "a smiley was read as a space before a colon")
_h_sbp, _, _, _ = run_analyze("real_space_before_punct", "We shipped it , then reverted.")
check("real_space_before_punct_fires", "mechanics" in cats(_h_sbp))

# Repeated n-grams are a rate: the floor scales with document length, so
# terminology consistency in a long reference is not a finding.
# Filler built from distinct all-letter tokens (WORD_RE drops digits, so
# "word1 word2" would tokenize to the same word twice). No bigram in it repeats,
# so the only repeated phrase in the document is the one under test.
def _tok(i):
    return chr(97 + (i // 676) % 26) + chr(97 + (i // 26) % 26) + chr(97 + i % 26)


_filler = " ".join(
    "%s %s %s %s." % (_tok(i * 4), _tok(i * 4 + 1), _tok(i * 4 + 2), _tok(i * 4 + 3))
    for i in range(330))
# Four repeats trip the old fixed floor of 4 and must not trip the scaled one in
# a ~1300-word document; eight must still trip it. Terminology consistency in a
# long reference is what principle 6 asks for, and the fixed floor punished it.
_h_ng_lo, _, _, _ = run_analyze(
    "ngram_floor_scales_low", "The scheduler retries the job. " * 4 + _filler)
check("ngram_floor_scales_with_length", "ngram_repetition" not in cats(_h_ng_lo),
      "four repeats in a long document tripped the scaled n-gram floor")
_h_ng_hi, _, _, _ = run_analyze(
    "ngram_floor_scales_high", "The scheduler retries the job. " * 9 + _filler)
check("ngram_floor_still_fires_when_earned", "ngram_repetition" in cats(_h_ng_hi),
      "nine verbatim repeats should still be a finding")
# The floor is still the configured minimum on a short document.
_h_ng_short, _, _, _ = run_analyze(
    "ngram_floor_short_doc",
    "The scheduler retries the job. " * 5 + "A little other prose here. " * 6)
check("ngram_floor_holds_on_short_docs", "ngram_repetition" in cats(_h_ng_short),
      "five verbatim repeats in a short note should fire")

# "e.g." tokenizes to ("e", "g"); single letters are not content words.
_eg = "Use it, e.g. here. " * 8 + "Some other prose to pad this out a little. " * 8
_h_eg, _, _, _ = run_analyze("eg_not_an_ngram", _eg)
check("single_letters_are_not_content_words",
      not [h for h in _h_eg if h.category == "ngram_repetition" and '"e g"' in h.text],
      "'e.g.' was counted as a repeated content n-gram")

# One dash convention used many times is one finding, not one per occurrence.
_many_ascii = "\n".join("name%d -- description of the thing at index %d." % (i, i)
                        for i in range(30))
_h_ascii, _, _, _ = run_analyze("dash_convention_collapsed", _many_ascii)
_ds = [h for h in _h_ascii if h.category == "dash_style"]
check("dash_convention_reported_once", len(_ds) <= 2,
      "30 occurrences of one dash convention produced %d findings" % len(_ds))
check("dash_convention_reports_the_count",
      any("30 occurrences" in h.text for h in _ds),
      "the collapsed finding should carry the real count: %s" % [h.text for h in _ds])


# ---------------------------------------------------------------------------
# Property tests: invariants that must hold on ANY input, not just the fixtures
# ---------------------------------------------------------------------------

_random.seed(20260822)
_FUZZ_ALPHA = list("abcdefgh IJK.,;:!?\n\t*_`#->|[]()—–\"'\\/{}$%^&~=+0123456789é")

_fuzz_fail = None
for _i in range(200):
    _t = "".join(_random.choice(_FUZZ_ALPHA) for _ in range(_random.randint(0, 600)))
    for _reg in ("technical", "creative", "casual", "marketing"):
        try:
            dap.lint(_t, register=_reg, dialect="american", patterns=PAT)
            dap.autofix(_t, PAT, _reg)
        except Exception as _exc:            # noqa: BLE001 - that is the point
            _fuzz_fail = "%s on %r (register %s)" % (type(_exc).__name__, _t[:120], _reg)
            break
    if _fuzz_fail:
        break
check("fuzz_never_crashes", _fuzz_fail is None,
      "adversarial markdown crashed the linter: %s" % _fuzz_fail)

# Autofix is a text transform on prose. Numbers, code spans, and URLs are
# invariants: rewriting one produces a wrong figure, broken code, or a 404.
_INV_FRAGMENTS = [
    "We should leverage the API — quickly.", "`code — here`",
    "https://x.io/a--b", "```\nfoo — bar\n```", "| a | — | b |",
    "10–20 items", "See [x](http://y/z--w).",
    "The result — surprisingly — held.", "delve into it",
    "a — b — c — d", "MAX_RETRY_COUNT and get_user_by_id",
    "value: 3.14159", "footnote[^1]",
]
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*%?")
_CODE_RE = re.compile(r"`[^`\n]*`|```[\s\S]*?```")
_URL_RE = re.compile(r"https?://\S+?(?=[\s)\]]|$)")
_inv_fail = None
for _i in range(200):
    _t = " ".join(_random.choice(_INV_FRAGMENTS)
                  for _ in range(_random.randint(1, 8)))
    for _reg in ("technical", "creative", "casual"):
        _out = dap.autofix(_t, PAT, _reg)[0]
        for _name, _rx in (("numbers", _NUM_RE), ("code", _CODE_RE), ("urls", _URL_RE)):
            if sorted(_rx.findall(_t)) != sorted(_rx.findall(_out)):
                _inv_fail = "%s changed: %r -> %r" % (_name, _t, _out)
                break
        if _inv_fail:
            break
    if _inv_fail:
        break
check("autofix_preserves_invariants", _inv_fail is None,
      "autofix violated an invariant: %s" % _inv_fail)

# Analysis stays roughly linear. The lexical lists are alternated into a handful
# of combined regexes rather than one scan per phrase; before that, a document
# ten times longer with a thousand-entry pattern file took far more than ten times
# as long. A generous ceiling, because CI machines vary.
_perf_unit = ("The system processes requests and returns responses to the caller. "
              "Some sentences are short. Others run considerably longer than this "
              "one does, carrying several clauses and a good deal of detail. ")
_t0 = time.time()
dap.analyze(_perf_unit * 400, "technical", "american", PAT)
_elapsed = time.time() - _t0
check("analysis_is_not_quadratic", _elapsed < 10.0,
      "analyzing ~13k words took %.1fs; the lexical pass has probably regressed to "
      "one regex per phrase" % _elapsed)


# ---------------------------------------------------------------------------
# v0.7: paste artifacts, heading structure, quote seams, copula avoidance
# ---------------------------------------------------------------------------

# Residue, not style. One instance is a finding: no writer types "oaicite".
_art_text = ("The migration notes are collected below for the on-call rotation. "
             "See the summary oaicite:12 and turn0search3 for the raw traces. "
             "The Gemini export left [cite: 4] in the third paragraph. "
             "Send the draft to [Your Name] before Friday afternoon. "
             "Source: https://example.com/x?utm_source=chatgpt.com " + _PAD)
_h_art, _, _, _ = run_analyze("llm_artifact", _art_text)
_art_hits = [h for h in _h_art if h.category == "llm_artifact"]
check("llm_artifact_fires", len(_art_hits) >= 5,
      "expected every residue string flagged; got %d" % len(_art_hits))

# The skill's own placeholders are the author's to resolve, not residue.
_h_art_ok, _, _, _ = run_analyze(
    "llm_artifact_sanctioned",
    "The throughput figure is [SOURCE NEEDED] and the date is [VERIFY]. " + _PAD)
check("llm_artifact_spares_sanctioned_placeholders",
      "llm_artifact" not in cats(_h_art_ok),
      "the anti-hallucination protocol's own markers must not be flagged")

# A document that DOCUMENTS these strings in backticks is not using them.
_h_art_doc, _, _, _ = run_analyze(
    "llm_artifact_documented",
    "Strip `oaicite` and `turn0search3` from pasted output before you file it. " + _PAD)
check("llm_artifact_skips_inline_code", "llm_artifact" not in cats(_h_art_doc),
      "backticked mentions are documentation, not residue")

# Heading scaffolding: skipped rung, second H1, empty parent, heading into a list.
_head_text = ("# Overview\n\n## Background\n\n#### Deep dive\n\n"
              "The team shipped the change on Tuesday and watched the graphs.\n\n"
              "# Second Top Level\n\n## Details\n\n- first item\n- second item\n\n" + _PAD)
_h_head, _r_head, _, _ = run_analyze("heading_structure", _head_text)
_head_msgs = " ".join(h.text for h in _h_head if h.category == "heading_structure")
check("heading_structure_fires", "heading_structure" in cats(_h_head))
check("heading_structure_catches_level_skip", "jumps 2 -> 4" in _head_msgs,
      "expected the skipped rung; got %r" % _head_msgs)
check("heading_structure_catches_second_h1", "level-1 headings" in _head_msgs,
      "expected the duplicate H1; got %r" % _head_msgs)
check("heading_structure_catches_heading_into_list", "runs straight into a list" in _head_msgs,
      "expected the lead-in-less list; got %r" % _head_msgs)

# A conventionally structured document must stay clean.
_h_head_ok, _, _, _ = run_analyze(
    "heading_structure_clean",
    "# Title\n\nThe team shipped the change on Tuesday and watched the graphs.\n\n"
    "## Detail\n\nNothing moved for an hour. Then the queue drained.\n\n"
    "### Sub\n\nThe queue drained again on Wednesday without any intervention.\n\n" + _PAD)
check("heading_structure_no_false_positive",
      "heading_structure" not in cats(_h_head_ok),
      "a normal heading tree fired: %s" % sorted(cats(_h_head_ok)))

# Quote seams: lopsided mixes only, and only with enough quotes to judge.
_quote_seam = ("The report said “the numbers held” and the follow-up said "
               "“they did not”. She wrote “the boiler needs replacing” "
               "and he answered “we knew that”. The invoice quoted \"four hundred\" "
               "and nobody argued the point. " + _PAD)
_h_q, _, _, _ = run_analyze("quote_seam", _quote_seam)
check("quote_style_fires_on_seam", "quote_style" in cats(_h_q),
      "one straight quote among eight curly ones is a paste seam")
_h_q_ok, _, _, _ = run_analyze(
    "quote_balanced",
    "She said “yes” and the config key is \"retries\" in the file. " + _PAD)
check("quote_style_spares_small_mix", "quote_style" not in cats(_h_q_ok),
      "quoted code beside quoted speech is a genuine mix, not a seam")

# Copula avoidance: stacked substitutes for "is", count- and density-gated.
_avoid_text = ("The library serves as a bridge between the two systems. "
               "It stands as a reference implementation for the protocol. "
               "The runtime boasts a scheduler and a work-stealing queue. "
               "The adapter functions as a thin wrapper over the socket. "
               "The result represents the state of the pipeline at cutover. ")
_h_av, _r_av, _, _ = run_analyze("copula_avoidance", _avoid_text + _PAD)
check("copula_avoidance_fires", "copula_avoidance" in cats(_h_av),
      "five elaborate copula substitutes should fire; got %s" % sorted(cats(_h_av)))
check("copula_avoidance_reported", (_r_av.get("copula_avoidance_count") or 0) >= 5,
      "count was %s" % _r_av.get("copula_avoidance_count"))
_h_av1, _, _, _ = run_analyze(
    "copula_avoidance_single",
    "The adapter serves as a thin wrapper over the socket layer. " + _PAD)
check("copula_avoidance_single_does_not_fire", "copula_avoidance" not in cats(_h_av1),
      "one 'serves as' is ordinary English")

# Contraction rate is measured and never scored. Scoring it would flag the
# ESL/formal human corpus, which is the bias this skill exists to argue against.
_h_c, _r_c, _, _ = run_analyze(
    "contraction_diagnostic",
    "We have completed the migration for fourteen services. It is ahead of "
    "schedule. We will confirm the cutover window on Thursday. " + _PAD,
    register="casual")
check("contraction_rate_reported", "contractions_per_1k" in _r_c,
      "the diagnostic must be in the metrics")
check("contraction_rate_not_scored",
      "contractions" not in dap.KNOWN_CATEGORIES
      and "contraction_absence" not in dap.KNOWN_CATEGORIES,
      "contraction absence must never become a scored category")

# register_thresholds only ever widens a bar, and only for the named register.
check("register_thresholds_present",
      isinstance(dap.DEFAULTS.get("register_thresholds"), dict)
      and "creative" in dap.DEFAULTS["register_thresholds"],
      "register_thresholds missing from DEFAULTS")
check("register_thresholds_are_multipliers",
      all(isinstance(v, (int, float)) and v > 0
          for reg in dap.DEFAULTS["register_thresholds"].values()
          for v in reg.values()),
      "multipliers must be positive numbers")
check("register_thresholds_name_real_knobs",
      all(k in dap.DEFAULTS["thresholds"]
          for reg in dap.DEFAULTS["register_thresholds"].values() for k in reg),
      "a multiplier names a threshold that does not exist")
check("register_thresholds_name_real_registers",
      all(r in dap.REGISTERS for r in dap.DEFAULTS["register_thresholds"]),
      "a multiplier names a register that does not exist")


# ---------------------------------------------------------------------------
# v0.8: the stylometric delta (reported, never scored, read inverted)
# ---------------------------------------------------------------------------

from human_voice_linter import stylometry as _sty  # noqa: E402

_prof = _sty.load_profile()
check("stylometry_profile_loads", isinstance(_prof, dict) and _prof.get("features"),
      "the committed human_reference_profile.json failed to load")
if _prof:
    check("stylometry_profile_wellformed",
          len(_prof["features"]) == len(_prof["mean"]) == len(_prof["stdev"])
          and all(v > 0 for v in _prof["stdev"]),
          "profile vectors are ragged or carry a zero stdev")
    check("stylometry_profile_has_human_range",
          all(isinstance(_prof.get(k), (int, float))
              for k in ("human_delta_min", "human_delta_median", "human_delta_max")),
          "the profile must ship the human range it was built from")

_, _r_sty, _, _ = run_analyze(
    "stylometry_metric",
    "The team shipped the change on Tuesday and watched the graphs closely. "
    "Nothing moved for an hour. Then the queue drained and the alarms cleared. "
    "We rolled the second batch at noon without touching the config. " * 4)
check("stylometry_delta_reported", isinstance(_r_sty.get("stylometric_delta"), float),
      "stylometric_delta missing from the metrics")
check("stylometry_never_scored",
      "stylometry" not in dap.KNOWN_CATEGORIES
      and "stylometric_delta" not in dap.KNOWN_CATEGORIES,
      "the delta must never become a scored category")

# Too short to estimate frequencies: the metric is absent, not zero.
_, _r_short, _, _ = run_analyze("stylometry_short", "It broke. We fixed it.")
check("stylometry_absent_when_too_short",
      _r_short.get("stylometric_delta") is None,
      "a 5-word note cannot carry a function-word profile")

# A missing or malformed profile must degrade to silence, never to an exception.
check("stylometry_missing_profile_is_silent",
      _sty.load_profile("/nonexistent/profile.json") is None
      and _sty.delta("word " * 200, None) is not None,
      "a bad profile path must return None rather than raise")
_bad = {"features": ["the"], "mean": [0.1], "stdev": [0.0]}
check("stylometry_survives_zero_stdev",
      isinstance(_sty.delta("the the the " * 100, _bad), float),
      "a zero stdev in a caller-supplied profile must not divide by zero")


# ---------------------------------------------------------------------------
# 13. Content architecture: restatement, section balance, depth drift
# ---------------------------------------------------------------------------
def _arch(text, register="technical"):
    hits, report, _wc = dap.analyze(text, register, None, PAT)
    return hits, report


def _arch_cats(hits):
    return {h.category for h in hits} & {"restatement", "section_balance", "depth_drift"}


_ARCH_RESTATE = """# Ingestion Service

## Overview

The new ingestion service replaces the nightly batch pipeline with a streaming path that delivers events to consumers within a minute. Product teams can register new event types themselves without waiting on the platform team.

## Architecture

Clients post events to the ingestion API, which writes each payload to a Kafka topic partitioned by tenant. Stateless validators read the topic, check each payload against the registered schema, and forward valid events. Invalid events go to a dead-letter topic with the error attached.

## Delivery

Kafka Connect sinks flush validated events to object storage every thirty seconds and to the warehouse every ten. In the load test the p99 from ingestion to warehouse was forty-one seconds at forty thousand events per second.

## Summary

In summary, the ingestion service replaces the nightly batch pipeline with a streaming path delivering events to consumers within a minute. New event types can be registered by product teams themselves without waiting on the platform team.
"""
_h, _r = _arch(_ARCH_RESTATE)
check("arch_restatement_fires", "restatement" in _arch_cats(_h),
      "summary re-words the overview: %s" % _r.get("restated_pairs"))
_rl = sorted(h.line for h in _h if h.category == "restatement")
check("arch_restatement_points_at_the_repeat", _rl and _rl[0] == 17,
      "the hit belongs on the summary line, got %s" % _rl)

# A "duplicate" that carries one fact the original lacks must say so, and the fix
# it suggests is a merge. Deleting that copy would delete the fact.
_EXTRA = _ARCH_RESTATE.replace(
    "New event types can be registered by product teams themselves without waiting on the platform team.",
    "New event types can be registered by product teams themselves without waiting on the platform team, starting March 3.")
_h, _r = _arch(_EXTRA)
_sug = [h.suggestion for h in _h if h.category == "restatement"]
check("arch_restatement_names_distinct_detail",
      any("merge, don't cut" in x and "March" in x and "3" in x for x in _sug), _sug)
check("arch_restatement_plain_copy_says_so",
      any("stated elsewhere" in x for x in _sug), _sug)

# Delete the summary and the same document is quiet.
_h, _r = _arch(_ARCH_RESTATE.split("## Summary")[0])
check("arch_restatement_quiet_without_recap", "restatement" not in _arch_cats(_h),
      "pairs=%s" % _r.get("restated_pairs"))

# Parallel reference entries under function headings are not restatement.
_API = "# lib\n\n" + "\n\n".join(
    "## `%s(value)`\n\nReturns true if the provided value is a valid %s token under "
    "the current parser configuration, and false otherwise for every other input." % (n, n)
    for n in ("isIdentifier", "isKeyword", "isPunctuator", "isNumeric", "isString")) + "\n"
_h, _r = _arch(_API)
check("arch_restatement_quiet_on_api_reference", "restatement" not in _arch_cats(_h),
      "pairs=%s" % _r.get("restated_pairs"))

# Verbatim copies (a pasted note) are not the agent's re-wording.
_NOTE = "Note that this option is ignored when the cache directory is mounted read-only on the host."
_COPY = "# Tool\n\n" + "\n\n".join(
    "## Option %s\n\nThe %s option controls how entries are written.\n\n%s" % (c, c, _NOTE)
    for c in "ABCDE") + "\n"
_h, _r = _arch(_COPY)
check("arch_restatement_quiet_on_verbatim_copies", "restatement" not in _arch_cats(_h),
      "pairs=%s" % _r.get("restated_pairs"))

_ARCH_STUBS = """# Migration Plan

## Schema Design

The profiles collection holds 18.4M documents averaging 3.1 KB. A 1% sample found 212 distinct top-level key combinations, and 7% of documents store the address as a string instead of an embedded object. The target schema normalizes the stable fields into users and user_addresses tables and keeps the long tail in a jsonb column called extra. The legacy object id is kept in legacy_oid so services can dual-read during cutover. String addresses are parsed with libpostal during the backfill; the 0.4% that fail parsing land in extra under raw_address for support to review. Emails are lowercased and deduplicated before insert, keeping the document with the latest login. The backfill reads from a hidden secondary in 500k-document chunks keyed by id range and writes through COPY into staging tables before an upsert on legacy_oid. A change stream consumer started before the backfill replays writes made during it, so the two converge without a write freeze.

Cutover happens per service. Each reader switches from Mongo to Postgres behind the profile_store_backend flag, starting with the notification worker because it only reads display_name and email. The account API goes last: it writes, so it runs dual-write for 72 hours with a nightly diff job comparing 50,000 random users between the stores, and the flag flips only after three consecutive clean diffs. At 9k documents per second the full backfill takes about 35 minutes, so a failed diff costs one evening rather than one week.

## Testing

We will test the migration thoroughly.

## Rollback

If something goes wrong, we will roll back.

## Risks

There are some risks involved.

## Timeline

The work will be completed next quarter.
"""
_h, _r = _arch(_ARCH_STUBS)
check("arch_stub_sections_fire", any(h.category == "section_balance" and "stub" in h.text for h in _h),
      [h.text for h in _h if h.category == "section_balance"])

# The same thin sections as pointers (a link, a command) are a README, not a quota.
_POINTERS = _ARCH_STUBS.replace("We will test the migration thoroughly.",
                                "See [the test plan](docs/testing.md).") \
    .replace("If something goes wrong, we will roll back.", "Run `make rollback STAGE=prod`.") \
    .replace("There are some risks involved.", "Tracked in [RISKS.md](RISKS.md).") \
    .replace("The work will be completed next quarter.", "See the [milestones](https://example.com/m).")
_h, _r = _arch(_POINTERS)
check("arch_pointer_sections_are_not_stubs",
      not any(h.category == "section_balance" and "stub" in h.text for h in _h),
      [h.text for h in _h if h.category == "section_balance"])

# release_notes: fixed sections are the genre, so section_balance is muted there.
_h, _r = _arch(_ARCH_STUBS, register="release_notes")
check("arch_section_balance_muted_in_release_notes", "section_balance" not in _arch_cats(_h))

_ARCH_FRAMING = """# Choosing a Queue

## Overview

Choosing the right message queue is an important decision that will shape how our services communicate for years to come. This document looks at the options and the considerations involved so that the team can make an informed and confident choice going forward. It is intended to give everyone a shared understanding of the landscape before any commitments are made.

## Background

As the platform has grown, more services need to exchange messages reliably. Different teams have adopted different approaches over time, which has created inconsistency and made it harder to reason about how the system behaves as a whole under load. A consistent approach would help teams collaborate more effectively and reduce the operational burden over time.

## Options

SQS gives us at-least-once delivery with a 256 KB message cap and no ordering outside FIFO queues, which cap at 3,000 messages per second with batching. Kafka keeps ordering per partition and lets consumers replay from an offset, at the cost of running brokers ourselves. Billing events need neither replay nor strict ordering. The largest invoice payload we emit today is 41 KB, well under the SQS cap, and peak volume last quarter was 180 events per second.

## Recommendation

Use SQS for the billing events.

## Summary

In summary, choosing a message queue is an important decision. By weighing the considerations described in this document carefully, the team can select the approach that best fits its needs and sets the platform up for long-term success. A thoughtful decision now will pay dividends as the platform continues to grow and evolve in the years ahead.
"""
_h, _r = _arch(_ARCH_FRAMING)
check("arch_framing_share_fires", any(h.category == "section_balance" and "framing" in h.text for h in _h),
      "framing_share=%s" % _r.get("framing_share"))

_EVEN = "# Report\n\n" + "\n\n".join(
    "## Part %s\n\n%s" % (t, " ".join(("%s%d" % (t.lower(), i)) for i in range(55)) + ".")
    for t in ("Alpha", "Bravo", "Charlie", "Delta", "Echo")) + "\n"
_h, _r = _arch(_EVEN)
check("arch_even_sections_fire", any(h.category == "section_balance" and "within a few words" in h.text for h in _h),
      "section_len_cov=%s" % _r.get("section_len_cov"))

_SYM = "# Options\n\n" + "\n\n".join(
    "## Option %d\n\nThis option is described below in some detail for the reader.\n\n"
    "- first point about option %d\n- second point about option %d\n- third point about option %d"
    % (i, i, i, i) for i in range(1, 5)) + "\n\n## Notes\n\n" + ("More words here. " * 70) + "\n"
_h, _r = _arch(_SYM)
check("arch_list_symmetry_fires", any(h.category == "section_balance" and "exactly 3 items" in h.text for h in _h),
      [h.text for h in _h if h.category == "section_balance"])

_ARCH_HOLLOW = """# Postmortem: Checkout Outage

## Impact

The outage had a meaningful impact on customers and on the business. Many customers who attempted to check out during the incident window were unable to complete their purchases, which led to frustration and a significant loss of trust. Some customers contacted support, increasing the load on the support team during an already busy period. From a business perspective the incident resulted in lost revenue and may have affected retention. The reputational impact is harder to measure but should not be underestimated, since reliability is an essential expectation for any shopping experience. Internal teams were affected as well, since engineers across several groups were pulled away from planned work to help with the investigation and the recovery effort. Overall, the impact highlights the importance of a resilient checkout flow.

## Timeline

- 14:02 UTC: PR 4812 merged, lowering DB_POOL_MAX from 80 to 20.
- 14:13 UTC: checkout_db_pool_wait_seconds p99 rises from 0.02 to 9.8.
- 14:16 UTC: PagerDuty fires CheckoutErrorRateHigh at 31% 5xx.
- 14:24 UTC: on-call finds pool saturation in pg_stat_activity.
- 14:31 UTC: revert merged as PR 4815; 5xx back under 0.2% by 14:38.

## Root Cause

With DB_POOL_MAX=20 and 12 pods the service held at most 240 connections while peak traffic needed about 610. Requests queued on pool.acquire() with a 10-second timeout and the gateway gave up at 8 seconds, so most failures surfaced as 504s. PR 4812 was meant for the staging overlay but edited checkout-api/config/prod.yaml, and the config linter checks types but not ranges.
"""
_h, _r = _arch(_ARCH_HOLLOW)
_dd = [h for h in _h if h.category == "depth_drift"]
check("arch_hollow_section_fires", len(_dd) == 1 and _dd[0].line == 3,
      [(h.line, h.text) for h in _dd])

# A conceptual section that talks about particular things without the abstract
# benefit vocabulary is a person explaining, not a section written from outside.
_CONCEPT = _ARCH_HOLLOW.split("## Impact")[0] + """## How Checkout Differs From Cart

Cart writes are cheap and forgiving. A shopper who loses an item from the cart adds it back and rarely notices, so the cart service retries quietly and drops writes under pressure. Checkout cannot do that. Once the card is charged the order has to exist, which means the payment call and the order insert either both happen or the charge is voided by the reconciler that runs behind them. That asymmetry is why checkout holds database connections longer than any other service and why a pool change that cart would shrug off takes checkout down within minutes of deploying.
""" + "## Timeline" + _ARCH_HOLLOW.split("## Timeline")[1]
_h, _r = _arch(_CONCEPT)
check("arch_conceptual_section_is_not_hollow", "depth_drift" not in _arch_cats(_h),
      [(h.line, h.text) for h in _h if h.category == "depth_drift"])

_ARCH_EXPLAIN = """# fastcache

In-process LRU cache for Python with TTL support and async-safe locking.

## What is a cache?

In simple terms, a cache is a place where you keep answers you already worked out. Think of it as a notebook you check before doing the work again. Simply put, it trades memory for speed. Your browser keeps one, your operating system keeps several, and the processor running this code keeps three of its own.

## Usage

```python
from fastcache import LRUCache
cache = LRUCache(maxsize=10_000, ttl=300)
```

`maxsize` bounds entries; eviction is O(1) via an intrusive list. `ttl` is checked lazily on `get()` and by a sweeper every `sweep_interval` seconds (default 30). `AsyncLRUCache` uses one `asyncio.Lock` per shard (16 by default, set with `shards=`) and holds p99 `get` under 1.1 µs with 32 tasks on an M2 Pro running Python 3.12.

Entries are stored in 16 dicts keyed by `hash(key) & 0xF`, each with its own intrusive list, so eviction touches one shard. The sweeper walks at most `sweep_batch` entries (default 512) per tick to cap pause time at roughly 40 µs. Set `ttl=None` to disable expiry entirely; `on_evict(key, value)` fires synchronously inside the shard lock, so keep it short. Benchmarked against cachetools 5.3 with 1M operations at a 90/10 read/write mix and `maxsize=100_000`, `get` p50 is 88 ns against 240 ns, and resident memory is 61 MB against 74 MB. Keys must be hashable; unhashable keys raise `TypeError` at `set()` rather than at eviction, so a bad key fails where it was written.

## Configuration

| Option | Default |
|---|---|
| `maxsize` | 1024 |
| `ttl` | `None` |
| `shards` | 16 |
"""
_h, _r = _arch(_ARCH_EXPLAIN)
check("arch_explainer_whiplash_fires", any(h.category == "depth_drift" and "beginner" in h.text for h in _h),
      "explainers=%s depth=%s" % (_r.get("explainers"), _r.get("depth_per_100")))
# A tutorial explains basics by design: the expert bar doubles there. Wider, not
# exempt, so a moderately technical page passes as a tutorial and still fires as
# a technical doc, while the dense README above would fire in either.
_TUTORIAL = """# Your first deploy

## Before you start

In simple terms, a container is a packaged copy of your app and everything it needs. Think of it as a lunchbox: the same meal, whichever table you open it on. At its core, deploying means handing that lunchbox to a server and asking it to keep the app running for you while you get on with your day.

## Build the image

Open a terminal in the project folder and run `docker build -t myapp:1.0 .` to build the image. The first build downloads the base layers, so expect it to take a few minutes on a home connection. Later builds reuse those layers and usually finish in under 30 seconds. When it finishes, run `docker images` and check that `myapp` appears with the tag `1.0`.

## Push and run

Log in with `docker login`, push with `docker push myapp:1.0`, and start it on the server with `docker run -p 8080:8080 myapp:1.0`. Open the server address in a browser. If the page does not load, run `docker logs` first; nine times out of ten the app is listening on a different port than the one you exposed. Fix the port in your app settings, rebuild, and push again; the server picks up the new image the next time you start it.
"""
_h, _r = _arch(_TUTORIAL)
check("arch_explainer_fires_on_technical_page", any(h.category == "depth_drift" and "beginner" in h.text for h in _h),
      "depth=%s explainers=%s" % (_r.get("depth_per_100"), _r.get("explainers")))
_h, _r = _arch(_TUTORIAL, register="tutorial")
check("arch_explainer_tolerated_in_tutorial", not any(h.category == "depth_drift" and "beginner" in h.text for h in _h),
      "depth=%s" % _r.get("depth_per_100"))

# Every new metric is reported, and the text report renders a structure line.
_h, _r = _arch(_ARCH_STUBS)
check("arch_metrics_reported",
      all(k in _r for k in ("sections", "section_words", "section_len_cov", "framing_share",
                            "restated_pairs", "depth_per_100", "explainers")),
      sorted(k for k in ("sections", "section_words", "section_len_cov", "framing_share",
                         "restated_pairs", "depth_per_100", "explainers") if k not in _r))
check("arch_structure_line_rendered",
      "structure:" in dap.render_text("x", "technical", None, _h, _r, 300, 1.0))

# A document with no headings reports no sections and never raises.
_h, _r = _arch("Plain prose without any headings at all. " * 60)
check("arch_no_sections_is_quiet", _r.get("sections") == 0 and not _arch_cats(_h))

# Hostile input: thousands of near-identical sentences stay bounded.
_t0 = time.time()
_h, _r = _arch("# T\n\n" + "\n\n".join("## S%d\n\nThe cache service stores user session tokens for fast lookup number %d." % (i, i)
                                         for i in range(1500)))
check("arch_bounded_on_hostile_input",
      time.time() - _t0 < 30 and sum(1 for h in _h if h.category == "restatement") <= 40,
      "took %.1fs" % (time.time() - _t0))


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
