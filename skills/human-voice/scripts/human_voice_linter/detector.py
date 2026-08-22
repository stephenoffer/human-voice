"""detector — call an external AI detector, so the rewrite can be *verified*.

The linter is a floor and says so everywhere. It computes no perplexity, runs no
model, and a document can score 0.0 on it and still be flagged by a trained
classifier. That gap is the reason this module exists: the only way to know
whether a rewrite actually clears a detector is to ask that detector.

Nothing here runs unless the user sets an API key. There is no default endpoint,
no telemetry, and no network call on the offline path. The skill's verification
gate (SKILL.md, Workflow step 9) drives this: rewrite, probe, and do not call the
job done while the detector still flags the text.

REQUEST SHAPES ARE UNVERIFIED AGAINST LIVE APIS. They come from each vendor's
published documentation, not from a call made in this repo. A stale shape surfaces
as a clear error naming the field that was missing, and the fix is one entry in
DETECTORS. Treat the first run against a new provider as a smoke test.

Detector verdicts are evidence, not truth, in either direction. Liang et al.
(2023, Patterns) found GPT detectors systematically misclassify non-native-English
writing as machine-generated, so a "human" verdict does not certify authorship and
an "AI" verdict does not refute it. Use the gate to catch a rewrite that did not go
far enough; never use it to tune prose into nonsense that happens to score well
(see references/what-detectors-see.md on why that loses anyway).
"""
from __future__ import annotations

import json as _json
import os

# Each entry: how to build the POST, and where p(AI) lives in the response.
DETECTORS: dict = {
    "GPTZERO_API_KEY": {
        "name": "GPTZero",
        "url": "https://api.gptzero.me/v2/predict/text",
        "headers": lambda key: {"x-api-key": key, "Content-Type": "application/json"},
        "body": lambda text: {"document": text},
        "path": ("documents", 0, "completely_generated_prob"),
    },
    "ORIGINALITY_API_KEY": {
        "name": "Originality.ai",
        "url": "https://api.originality.ai/api/v1/scan/ai",
        "headers": lambda key: {"X-OAI-API-KEY": key, "Content-Type": "application/json"},
        "body": lambda text: {"content": text},
        "path": ("score", "ai"),
    },
    "SAPLING_API_KEY": {
        "name": "Sapling",
        "url": "https://api.sapling.ai/api/v1/aidetect",
        "headers": lambda key: {"Content-Type": "application/json"},
        "body": lambda text: {"text": text},
        "path": ("score",),
        "key_in_body": True,
    },
    "WINSTON_API_KEY": {
        "name": "Winston AI",
        "url": "https://api.gowinston.ai/v2/ai-content-detection",
        "headers": lambda key: {"Authorization": "Bearer " + key,
                                "Content-Type": "application/json"},
        "body": lambda text: {"text": text},
        # Winston reports a 0-100 "human score"; normalized in probe().
        "path": ("score",),
        "human_scale_100": True,
    },
}
# Generic alias so a provider this table does not know can still be pointed at
# GPTZero-compatible request shape.
DETECTORS["AI_DETECTOR_API_KEY"] = DETECTORS["GPTZERO_API_KEY"]

KEY_ENV_VARS = tuple(DETECTORS)

# Default gate: a document is treated as clearing the detector below this p(AI).
# Deliberately strict, because the cost of a false "clear" is the user shipping
# text they believed was verified.
DEFAULT_MAX_P_AI = 0.10


class DetectorUnavailable(RuntimeError):
    """No API key configured, so no detector can be called."""


def find_api_key(env=None):
    """(env_var, key) for the first configured detector, or (None, None)."""
    env = os.environ if env is None else env
    for var in KEY_ENV_VARS:
        val = env.get(var)
        if val:
            return var, val
    return None, None


def dig(payload, path):
    """Walk a mixed dict/list path, raising KeyError naming the failing step."""
    node = payload
    for step in path:
        try:
            node = node[step]
        except (KeyError, IndexError, TypeError):
            raise KeyError("detector response has no %r (found %s); the request "
                           "shape in DETECTORS is probably stale"
                           % (step, type(node).__name__)) from None
    return node


def probe(text, api_key=None, key_var=None, timeout=30, opener=None):
    """Return p(AI) in [0,1] for `text` from the configured external detector.

    `opener` is an injection point for tests: any callable taking (url, data,
    headers, timeout) and returning the decoded JSON. Standard library only on the
    real path, so the zero-dependency promise holds.
    """
    if key_var is None or api_key is None:
        found_var, found_key = find_api_key()
        key_var = key_var or found_var
        api_key = api_key or found_key
    if not api_key:
        raise DetectorUnavailable(
            "no detector API key set. Set one of %s to enable verification."
            % ", ".join(KEY_ENV_VARS))
    spec = DETECTORS.get(key_var)
    if spec is None:
        raise ValueError("no request shape registered for %s" % key_var)

    body = spec["body"](text)
    if spec.get("key_in_body"):
        body = dict(body, key=api_key)
    headers = spec["headers"](api_key)
    data = _json.dumps(body).encode("utf-8")

    if opener is not None:
        payload = opener(spec["url"], data, headers, timeout)
    else:
        import urllib.request
        req = urllib.request.Request(spec["url"], data=data, headers=headers,
                                     method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = _json.load(resp)

    value = float(dig(payload, spec["path"]))
    if spec.get("human_scale_100"):
        # A 0-100 "how human is this" score inverts into p(AI).
        value = 1.0 - (value / 100.0)
    if not 0.0 <= value <= 1.0:
        raise ValueError("detector returned %r, which is not a probability" % value)
    return value


def verdict(p_ai, max_p_ai=DEFAULT_MAX_P_AI):
    """('clear'|'flagged', bool) for a probability against the gate threshold."""
    clear = p_ai < max_p_ai
    return ("clear" if clear else "flagged"), clear


__all__ = [
    "DETECTORS",
    "KEY_ENV_VARS",
    "DEFAULT_MAX_P_AI",
    "DetectorUnavailable",
    "find_api_key",
    "dig",
    "probe",
    "verdict",
]
