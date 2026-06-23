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
# 4b. False-positive regressions + new tells (HV-015/016/017/018, HV-065/066)
# Each known false-positive class has a negative case (must stay quiet) paired
# with a positive case (the real tell must still fire).
# ---------------------------------------------------------------------------
# proper-noun triad must NOT fire rule_of_three; adjective triad must
h_pn, _, _, _ = run_analyze("fp_proper_noun_triad", "We shipped with Python, Django, and Flask in production this year here.")
check("fp_proper_noun_no_rule3", "rule_of_three" not in cats(h_pn))
h_adj, _, _, _ = run_analyze("tp_adjective_triad", "The system is fast, reliable, and scalable across every workload here.")
check("tp_adjective_rule3", "rule_of_three" in cats(h_adj))

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
          "past the five-sentence minimum the burstiness check needs to run here.")
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
    "The platform is fast, reliable and scalable across all of the workloads here today.")
check("tp_oxfordless_triad_fires", "rule_of_three" in cats(h_ox))

# wordiness padding flags as redundancy (HV-025)
h_word, _, _, _ = run_analyze("tp_wordiness",
    "In order to win, due to the fact that the majority of users wait, we act now.")
check("tp_wordiness_fires", "redundancy" in cats(h_word))

# spaced double-hyphen counts toward em-dash (HV-028)
h_sdh, _, _, _ = run_analyze("tp_spaced_double_hyphen",
    "We shipped it -- finally -- after review and it held -- surprisingly -- up well here.")
check("tp_spaced_double_hyphen", "em_dash" in cats(h_sdh))

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

# narrator-from-a-distance: lecturer voice fires (casual); muted academic
h_nd, _, _, _ = run_analyze("tp_narrator_distance",
    "Nobody designed this. People tend to follow the path of least resistance, and humans are wired to coast.",
    register="casual")
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

# strict JSON schema: exact key set + value types (HV-130)
expected_keys = {"schema_version", "input", "register", "dialect", "words",
                 "score", "verdict", "metrics", "hits"}
check("json_strict_keys", set(jb) == expected_keys, "got %s" % sorted(set(jb)))
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
check("cli_fix_strips_dash_emoji", "—" not in _pf and "✨" not in _pf and "won, again, here" in _pf)
os.remove(_dfile)

# lowered em-dash threshold: just two em-dashes in technical prose now flags em_dash
h_lowdash, _, _, _ = run_analyze("tp_two_em_dashes",
    "The result surprised us — it held — and we shipped it the next morning here.")
check("low_threshold_flags_two_em_dashes", "em_dash" in cats(h_lowdash))

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
for _sect in ("thresholds", "category_weights", "score_bands"):
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
                      "academic": "academic", "email": "email"}
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
