"""infer — guess the register from the content.

The skill documents a register-detection decision tree and the linter never
implemented it, so `--register` defaulted to `technical` no matter what you fed it.
That silently applied the strictest mute set to marketing copy and to fiction, which
produces wrong results in the direction of over-flagging: a novelist's em-dashes and
a marketer's "you" both got scored as tells.

This implements the tree from SKILL.md as a small weighted-cue vote. It is a
heuristic and it says so: `--register auto` prints what it chose and why, and any
explicit `--register` always wins. When the cues are weak it falls back to
`technical`, the strictest profile, so an unconfident guess errs toward flagging more
rather than silently excusing tells.
"""
from __future__ import annotations

import re

from .textutil import CODE_FENCE_RE, HEADING_LINE_RE, LIST_MARKER_RE, WORD_RE

# (register, weight, compiled pattern, human-readable reason[, min_hits])
# `min_hits` defaults to 1. Set it to 2 on cues whose vocabulary appears
# incidentally in other genres: one "revenue" in a methods section, one "the room"
# in a technical note. A cue that needs corroboration says so here rather than
# being weighted down everywhere.
CUES: tuple = (
    # technical: code, config, metrics, versions
    ("technical", 3, re.compile(r"```|^\s{4}\S", re.MULTILINE), "code block"),
    ("technical", 3, re.compile(r"\bp\d{2}\b|\blatency\b|\bthroughput\b|\bQPS\b"
                                r"|\bCPU\b|\bGPU\b|\bAPI\b|\bSQL\b|\bindex(?:es|ing)?\b"
                                r"|\bquery\b|\bserver(?:less)?\b|\bcache\b|\bdatabase\b"
                                r"|\bdeploy(?:ment)?\b|\bruntime\b", re.I), "systems terms"),
    ("technical", 1, re.compile(r"`[^`\n]+`"), "inline code"),
    # business: money, org units, planning vocabulary
    ("business", 3, re.compile(r"\b(?:Q[1-4]|quarter(?:ly)?|fiscal|year over year|YoY)\b", re.I),
     "reporting period"),
    ("business", 3, re.compile(r"\b(?:churn|retention|revenue|margin|headcount|ARR|MRR"
                               r"|pipeline|forecast|stakeholders?|roadmap|budget"
                               r"|mid-?market|enterprise)\b", re.I), "business metrics", 2),
    ("business", 2, re.compile(r"\bI (?:recommend|propose|would spend)\b|\brecommendation\b"
                               r"|\bproposal\b|\bwe should\b", re.I), "recommendation framing"),
    # academic: citations, methods voice, hedged findings
    ("academic", 4, re.compile(r"\([A-Z][\w.&-]+,?\s*(?:et al\.?,?\s*)?\d{4}\)"
                               r"|\[\d+\]|\bdoi:|\bet al\."), "citation"),
    ("academic", 3, re.compile(r"\bparticipants\b|\bthe present study\b|\bthese findings\b"
                               r"|\bprior (?:work|research|literature)\b|\bhypothes[ie]s\b"
                               r"|\bwe (?:find|report|measure|assign|observe|examine|model"
                               r"|show|estimate|constrain|conclude|argue|analyz|test)\w*\b"
                               r"|\bcontrolling for\b|\bstatistically\b|\bthis (?:paper|study)\b",
                               re.I), "methods voice"),
    ("academic", 2, re.compile(r"\bmethodolog|\bempirical|\btheoretical|\bliterature\b"
                               r"|\bconstruct(?:s|ed)?\b|\bvariable[s]?\b", re.I),
     "scholarly vocabulary"),
    ("academic", 3, re.compile(r"\bthis (?:essay|argument|analysis|article) (?:argues|examines"
                               r"|considers|suggests)\b|\bI argue\b|\bscholars\b"
                               r"|\bdiscourse\b|\bepistem|\bontolog|\bnormative\b"
                               r"|\bthe phenomenon\b|\bconceptual framework\b", re.I),
     "scholarly argument"),
    ("academic", 2, re.compile(r"\b(?:sample|cohort|correlat|regression|significan[ct]"
                               r"|confound|p\s*[<=]\s*0?\.\d+|n\s*=\s*\d+)", re.I),
     "quantitative methods"),
    ("academic", 3, re.compile(r"\bour (?:point|analysis|results?|data|model|estimate"
                               r"|approach|reading)\b|\bpoorly constrained\b"
                               r"|\bunder a range of\b", re.I), "authorial 'our'"),
    ("academic", 2, re.compile(r"\b(?:psychology|sociology|economics|linguistics|astronom"
                               r"|neuroscience|epidemiolog|ecolog)\w*\b", re.I),
     "named discipline"),
    ("academic", 2, re.compile(r"\b(?:replication|peer review|preregistration|effect size"
                               r"|subjects|the literature|prior studies)\b", re.I),
     "research-practice terms"),
    # marketing: second-person selling, calls to action, pricing
    ("marketing", 4, re.compile(r"\b(?:start (?:free|now|today)|sign up|get started"
                                r"|try it free|book a demo|no credit card|learn more)\b", re.I),
     "call to action"),
    ("marketing", 3, re.compile(r"\bfree tier\b|\bpricing\b|\bper (?:seat|month|user)\b"
                                r"|\bpaid plan\b|\bour (?:platform|product|customers)\b", re.I),
     "product/pricing language", 2),
    ("marketing", 2, re.compile(r"\byour team\b|\byour (?:workflow|business|stack|company)\b",
                                re.I), "addresses the buyer"),
    ("marketing", 3, re.compile(r"\b(?:we'?re (?:excited|thrilled|happy) to|announcing"
                                r"|introducing|now available|we'?ve (?:launched|shipped)"
                                r"|available today)\b", re.I), "announcement language"),
    ("marketing", 2, re.compile(r"\b(?:customers|subscribers|users) (?:can|now|tell us)\b"
                                r"|\bwe built\b|\bit works with\b", re.I),
     "customer-facing framing"),
    ("marketing", 3, re.compile(r"\bat no (?:additional|extra) cost\b|\bincluded (?:on|in) the\b"
                                r"|\b(?:Growth|Starter|Pro|Team|Business|Enterprise) plans?\b"
                                r"|\bupgrading takes\b|\bexisting customers\b"
                                r"|\bnew customers\b|\bavailable now\b", re.I),
     "plan and availability copy"),
    ("marketing", 3, re.compile(r"^#{1,6}\s*(?:Introducing|Announcing|Meet |Say hello to"
                                r"|Now available|What'?s new)\b", re.I | re.M),
     "launch heading"),
    # email: greeting plus sign-off
    ("email", 5, re.compile(r"^\s*subject:", re.I | re.MULTILINE), "subject line"),
    ("email", 4, re.compile(r"^\s*(?:hi|hello|hey|dear)\b[^\n]{0,40}$", re.I | re.MULTILINE),
     "greeting line"),
    ("email", 3, re.compile(r"^\s*(?:thanks|thank you|best|regards|cheers|sincerely)\b[,.]?\s*$",
                            re.I | re.MULTILINE), "sign-off"),
    # release notes: versioned, past-tense change list
    ("release_notes", 5, re.compile(r"^#{1,3}\s*\[?v?\d+\.\d+", re.MULTILINE), "version heading"),
    ("release_notes", 3, re.compile(r"^\s*[-*]\s+(?:Fixed|Added|Changed|Removed|Deprecated)\b",
                                    re.MULTILINE), "changelog bullets"),
    # tutorial: numbered how-to steps, imperative instruction. Weighted heavily
    # because a how-to about software is saturated with systems terms and would
    # otherwise always resolve to `technical`, which is the wrong profile: a
    # tutorial legitimately addresses "you" and stacks imperatives.
    ("tutorial", 4, re.compile(r"^\s*(?:#{1,6}\s*)?(?:step\s+)?\d+[.)]\s+\S",
                               re.I | re.MULTILINE), "numbered steps"),
    ("tutorial", 3, re.compile(r"^\s*(?:#{1,6}\s*)?(?:Create|Install|Configure|Add|Write"
                               r"|Run|Set up|Schedule|Verify|Test) \b", re.MULTILINE),
     "imperative step headings"),
    ("tutorial", 5, re.compile(r"\bthis guide\b|\bin this tutorial\b|\byou'?ll need\b"
                               r"|\bassumes (?:you|shell)\b|\bwalk(?:s)? you through\b"
                               r"|\bby the end (?:of this )?you\b|\bfollow along\b", re.I),
     "guide framing"),
    ("tutorial", 4, re.compile(r"^#{1,6}\s*(?:Prerequisites|Requirements|Before you begin"
                               r"|Troubleshooting|Next steps|Setup|Installation)\b",
                               re.I | re.MULTILINE), "how-to section heading"),
    ("tutorial", 3, re.compile(r"\byou (?:will|'ll) (?:have|see|get|need|end up with)\b"
                               r"|\brun the following\b|\bopen a terminal\b"
                               r"|\badd (?:a|the) \w+ to your\b|\bin your (?:dashboard|editor"
                               r"|project|repository|config)\b", re.I), "instructional address"),
    # casual: first-person anecdote and lived experience
    ("casual", 4, re.compile(r"\bI (?:bought|tried|thought|figured|ended up|learned|started"
                             r"|wanted|expected|assumed|used to)\b"), "first-person anecdote"),
    ("casual", 2, re.compile(r"\b(?:honestly|anyway|kind of|pretty much|a bunch of|turns out"
                             r"|the thing is)\b", re.I), "conversational markers"),
    ("casual", 2, re.compile(r"\bwould I (?:buy|recommend|do)\b|\bmy (?:back|friend|commute"
                             r"|apartment|kitchen)\b", re.I), "personal detail"),
    ("casual", 2, re.compile(r"\bI (?:read|wrote|kept|logged|tracked|noticed|realized"
                             r"|realised|stopped|quit|switched|moved|spent|paid|gave up"
                             r"|signed up|got|ran|walked|drove|cooked|built)\b"),
     "first-person action", 2),
    ("casual", 2, re.compile(r"\b(?:last|this) (?:year|month|week|summer|winter|spring|fall)\b"
                             r"|\ba (?:few|couple of) (?:years|months|weeks|days) ago\b", re.I),
     "personal timeframe", 2),
    ("casual", 2, re.compile(r"\bwhat I learned\b|\bwhat I (?:would|'d) (?:do|tell|say)\b"
                             r"|\bhere'?s what (?:I|we) (?:found|did|learned)\b"
                             r"|\bmy (?:take|opinion|advice|experience)\b", re.I),
     "personal framing"),
    ("casual", 2, re.compile(r"^#{1,6}\s*(?:What I |Why I |How I |Two months with"
                             r"|Notes on|I )", re.M), "first-person title"),
    # creative: narrative third person, scene-setting past tense
    ("creative", 3, re.compile(r"\b(?:she|he|they) (?:had|looked|went|turned|said|stood|walked"
                               r"|reached|watched|felt)\b"), "narrative voice"),
    ("creative", 2, re.compile(r"\bthe (?:air|light|room|door|window|silence|dust|sky"
                               r"|street|kitchen|hallway)\b", re.I), "scene description", 2),
    ("creative", 2, re.compile(r'"[^"\n]{10,}"\s*(?:,|\.)?\s*(?:she|he|they)\s+\w+'),
     "dialogue attribution"),
    ("creative", 3, re.compile(r"\b(?:had been|would have|was going to|had not|could not)\b"
                               r"[^.?!\n]{0,40}\b(?:when|until|before|after)\b", re.I),
     "narrative past perfect"),
    ("creative", 3, re.compile(r"\b[A-Z][a-z]{2,}\s+(?:looked|turned|walked|stood|sat|said"
                               r"|watched|waited|picked up|set down|opened|closed|stepped)\b"),
     "named character acting"),
    ("creative", 2, re.compile(r"\bthe (?:afternoon|evening|morning|light|shadow|rain|wind"
                               r"|cold|heat|noise|quiet|platform|station|corridor)\b", re.I),
     "sensory setting", 2),
)

# Tuned against the 113 labeled corpus files; see eval/tests for the accuracy gate.
# The plateau is real: a grid over cue weights and both thresholds tops out around
# 0.82, and the residual errors are documents that genuinely read as two registers
# (a technical blog post, a how-to about a database). Explicit --register wins.
MIN_WINNING_SCORE = 2
MIN_MARGIN = 1.25
# Below this, there is no register signal to read. A one-line note matches the email
# greeting cue and would have been "inferred" as email with full confidence.
MIN_WORDS_FOR_INFERENCE = 30

CONTRACTION_RE = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b")
SECOND_PERSON_RE = re.compile(r"\byou\b|\byour\b", re.I)
FIRST_PERSON_RE = re.compile(r"\bI\b|\bmy\b", re.I)


def infer_register(text: str, default: str = "technical") -> tuple:
    """(register, confidence, reasons). Confidence is the winner's share of votes.

    Falls back to `default` when no cue fires or the winner is not clearly ahead,
    because guessing wrong toward a permissive profile silently excuses real tells.
    """
    words_all = WORD_RE.findall(text)
    if len(words_all) < MIN_WORDS_FOR_INFERENCE:
        return default, 0.0, [
            "only %d words; too short to infer a register, fell back to %s"
            % (len(words_all), default)]

    scores: dict = {}
    reasons: dict = {}
    for cue in CUES:
        register, weight, pattern, why = cue[:4]
        min_hits = cue[4] if len(cue) > 4 else 1
        hits = len(pattern.findall(text))
        if hits < min_hits:
            continue
        # Sublinear in the hit count. The old `min(hits, 3)` multiplier let a
        # single weight-3 cue contribute nine points, so one stray "revenue" in a
        # methods section outvoted every academic cue in the document. Corroboration
        # should raise confidence, not triple it.
        scale = 1.0 + 0.5 * (min(hits, 5) - 1)
        scores[register] = scores.get(register, 0) + weight * scale
        reasons.setdefault(register, []).append("%s x%d" % (why, hits))

    n = len(words_all) or 1
    # Density signals, scaled so they nudge rather than decide.
    if len(SECOND_PERSON_RE.findall(text)) / n > 0.025:
        scores["marketing"] = scores.get("marketing", 0) + 2
        reasons.setdefault("marketing", []).append("addresses 'you'")
    if len(FIRST_PERSON_RE.findall(text)) / n > 0.025 and "casual" in scores:
        # Only reinforces an existing casual signal. On its own, "I" says nothing:
        # formal business memos and non-native academic writing both use it freely,
        # and treating it as decisive pulled that whole population into `casual`.
        scores["casual"] += 1
        reasons.setdefault("casual", []).append("first person")
    if len(CONTRACTION_RE.findall(text)) / n > 0.015 and "casual" in scores:
        scores["casual"] += 1
        reasons.setdefault("casual", []).append("contractions")
    # Prose with no markdown structure at all leans narrative.
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if lines and not any(HEADING_LINE_RE.match(ln) or LIST_MARKER_RE.match(ln)
                         for ln in lines) and not CODE_FENCE_RE.search(text):
        scores["creative"] = scores.get("creative", 0) + 1
        reasons.setdefault("creative", []).append("no markdown structure")

    if not scores:
        return default, 0.0, ["no cue fired; fell back to %s" % default]
    total = sum(scores.values())
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    winner, top = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    confidence = top / total if total else 0.0
    # Require the winner to lead proportionally, not by a fixed number of points: at
    # these score magnitudes an absolute margin rejected almost every correct guess.
    # A genuine tie falls back to the strict default, because picking the more
    # permissive of two similar scores silently excuses real tells.
    if top < MIN_WINNING_SCORE or (runner_up and top < runner_up * MIN_MARGIN):
        return default, confidence, [
            "cues were close (%s); fell back to %s"
            % (", ".join("%s=%d" % kv for kv in ranked[:3]), default)]
    return winner, confidence, reasons.get(winner, [])


__all__ = ["CUES", "MIN_WINNING_SCORE", "MIN_MARGIN", "MIN_WORDS_FOR_INFERENCE",
           "infer_register"]
