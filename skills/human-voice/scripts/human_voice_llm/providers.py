"""providers — one chat call, any major LLM provider, standard library only.

The skill itself is plain Markdown and runs in any agent that can read a file. This
module is for the other case: no agent at all, just an API key and a draft. It
turns a model string into one HTTP request and returns the text.

    anthropic/claude-sonnet-5        openai/gpt-5.6         gemini/gemini-3.8-flash
    bedrock/<model-id>               vertex/gemini-3.8-flash  azure/<deployment>
    mistral/mistral-large-latest     groq/<model>           deepseek/deepseek-v4-pro
    xai/grok-4.6                     openrouter/<vendor>/<model>
    together/<model>                 fireworks/<model>      cohere/command-a-plus-05-2026
    ollama/<model>                   lmstudio/<model>       compat/<model> (+ base URL)

A bare model name works when its prefix is unambiguous (`claude-*`, `gpt-*`,
`gemini-*`, `grok-*`, ...). With no model at all, the first provider whose API key
is set wins, so `export OPENAI_API_KEY=...` is the whole setup.

Four wire formats cover every provider: OpenAI chat completions (which most
vendors now also speak), Anthropic messages, Gemini generateContent, and Bedrock
Converse. Nothing is sent anywhere until a call is made, there is no telemetry,
and `opener` is injectable so the tests never touch the network.

Default model names age faster than anything else in this repository. Every one
is overridable with the model string or HUMAN_VOICE_MODEL, and a stale default
fails loudly with the provider's own error message rather than silently.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

# kind: which wire format. key_env: env vars checked in order (first set wins).
# base_env: env var that overrides base_url. max_tokens: default output budget;
# reasoning models spend part of it thinking, so they get more.
PROVIDERS: dict = {
    "anthropic": {
        "kind": "anthropic", "label": "Anthropic",
        "base_url": "https://api.anthropic.com/v1", "base_env": "ANTHROPIC_BASE_URL",
        "key_env": ("ANTHROPIC_API_KEY",), "default_model": "claude-sonnet-5",
        "max_tokens": 16000,
    },
    "openai": {
        "kind": "openai", "label": "OpenAI", "native_openai": True,
        "base_url": "https://api.openai.com/v1", "base_env": "OPENAI_BASE_URL",
        "key_env": ("OPENAI_API_KEY",), "default_model": "gpt-5.6",
        "max_tokens": 32000,
    },
    "azure": {
        "kind": "azure", "label": "Azure OpenAI",
        "base_url": None, "base_env": "AZURE_OPENAI_ENDPOINT",
        "key_env": ("AZURE_OPENAI_API_KEY",), "default_model": None,
        "max_tokens": 32000, "model_hint": "the deployment name",
        "model_env": "AZURE_OPENAI_DEPLOYMENT",
    },
    "gemini": {
        "kind": "gemini", "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "base_env": "GEMINI_BASE_URL",
        "key_env": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "default_model": "gemini-3.8-flash",
        "max_tokens": 32000,
    },
    "vertex": {
        "kind": "vertex", "label": "Google Vertex AI (Gemini or Claude)",
        "base_url": None, "base_env": None,
        "key_env": ("VERTEX_ACCESS_TOKEN",), "default_model": "gemini-3.8-flash",
        "max_tokens": 32000, "needs": ("GOOGLE_CLOUD_PROJECT",),
    },
    "bedrock": {
        "kind": "bedrock", "label": "Amazon Bedrock (Converse API, any model)",
        "base_url": None, "base_env": "BEDROCK_ENDPOINT",
        "key_env": ("AWS_ACCESS_KEY_ID",), "default_model": None,
        "max_tokens": 8192, "model_hint": "a Bedrock model or inference-profile id",
        "model_env": "BEDROCK_MODEL_ID",
    },
    "mistral": {
        "kind": "openai", "label": "Mistral",
        "base_url": "https://api.mistral.ai/v1", "base_env": "MISTRAL_BASE_URL",
        "key_env": ("MISTRAL_API_KEY",), "default_model": "mistral-large-latest",
        "max_tokens": 16000,
    },
    "groq": {
        "kind": "openai", "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1", "base_env": "GROQ_BASE_URL",
        "key_env": ("GROQ_API_KEY",), "default_model": "llama-3.3-70b-versatile",
        "max_tokens": 16000,
    },
    "deepseek": {
        "kind": "openai", "label": "DeepSeek",
        "base_url": "https://api.deepseek.com", "base_env": "DEEPSEEK_BASE_URL",
        "key_env": ("DEEPSEEK_API_KEY",), "default_model": "deepseek-v4-pro",
        "max_tokens": 8000,
    },
    "xai": {
        "kind": "openai", "label": "xAI Grok",
        "base_url": "https://api.x.ai/v1", "base_env": "XAI_BASE_URL",
        "key_env": ("XAI_API_KEY",), "default_model": "grok-4.6",
        "max_tokens": 32000,
    },
    "openrouter": {
        "kind": "openai", "label": "OpenRouter (hundreds of models, one key)",
        "base_url": "https://openrouter.ai/api/v1", "base_env": "OPENROUTER_BASE_URL",
        "key_env": ("OPENROUTER_API_KEY",), "default_model": "anthropic/claude-sonnet-5",
        "max_tokens": 16000,
        "extra_headers": {"HTTP-Referer": "https://github.com/stephenoffer/human-voice",
                          "X-Title": "human-voice"},
    },
    "together": {
        "kind": "openai", "label": "Together AI",
        "base_url": "https://api.together.xyz/v1", "base_env": "TOGETHER_BASE_URL",
        "key_env": ("TOGETHER_API_KEY",),
        "default_model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", "max_tokens": 16000,
    },
    "fireworks": {
        "kind": "openai", "label": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference/v1", "base_env": "FIREWORKS_BASE_URL",
        "key_env": ("FIREWORKS_API_KEY",),
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "max_tokens": 16000,
    },
    "cohere": {
        "kind": "openai", "label": "Cohere (OpenAI compatibility API)",
        "base_url": "https://api.cohere.ai/compatibility/v1", "base_env": "COHERE_BASE_URL",
        "key_env": ("COHERE_API_KEY", "CO_API_KEY"), "default_model": "command-a-plus-05-2026",
        "max_tokens": 8000,
    },
    "ollama": {
        "kind": "openai", "label": "Ollama (local)", "local": True,
        "base_url": "http://localhost:11434/v1", "base_env": "OLLAMA_BASE_URL",
        "key_env": (), "default_model": None, "max_tokens": 16000,
        "model_hint": "a pulled model, e.g. ollama/qwen3:32b", "model_env": "OLLAMA_MODEL",
    },
    "lmstudio": {
        "kind": "openai", "label": "LM Studio (local)", "local": True,
        "base_url": "http://localhost:1234/v1", "base_env": "LMSTUDIO_BASE_URL",
        "key_env": (), "default_model": None, "max_tokens": 16000,
        "model_hint": "the loaded model's identifier",
    },
    "compat": {
        "kind": "openai", "label": "Any OpenAI-compatible server (vLLM, LiteLLM, TGI, ...)",
        "local": True,
        "base_url": None, "base_env": "HUMAN_VOICE_BASE_URL",
        "key_env": ("HUMAN_VOICE_API_KEY",), "default_model": None, "max_tokens": 16000,
        "model_hint": "the model name the server expects",
    },
}

# Auto-selection order when no model is given: the first provider with a key set.
AUTO_ORDER = ("anthropic", "openai", "gemini", "openrouter", "azure", "mistral", "xai",
              "deepseek", "groq", "together", "fireworks", "cohere")

# Bare model names whose owner is unambiguous from the prefix.
PREFIXES = (
    ("claude", "anthropic"),
    ("gpt-", "openai"), ("chatgpt", "openai"), ("o1", "openai"), ("o3", "openai"),
    ("o4", "openai"), ("codex", "openai"),
    ("gemini", "gemini"), ("gemma", "gemini"),
    ("grok", "xai"),
    ("mistral", "mistral"), ("magistral", "mistral"), ("codestral", "mistral"),
    ("ministral", "mistral"), ("devstral", "mistral"), ("pixtral", "mistral"),
    ("deepseek", "deepseek"),
    ("command", "cohere"),
)

RETRY_STATUS = (408, 409, 425, 429, 500, 502, 503, 504, 529)


class ProviderError(RuntimeError):
    """A call failed in a way the user can act on. The message says how."""


class Completion:
    """Text plus the bookkeeping a caller needs to trust it."""

    def __init__(self, text, provider, model, truncated=False, usage=None, raw=None):
        self.text = text
        self.provider = provider
        self.model = model
        self.truncated = truncated
        self.usage = usage or {}
        self.raw = raw

    def __repr__(self):
        return "Completion(%s/%s, %d chars%s)" % (
            self.provider, self.model, len(self.text), ", TRUNCATED" if self.truncated else "")


# ---------------------------------------------------------------------------
# Resolution: model string -> (provider, model)
# ---------------------------------------------------------------------------

def _env(env, names):
    for name in names:
        val = env.get(name)
        if val:
            return name, val
    return None, None


def _default_model(provider, env):
    info = PROVIDERS[provider]
    return (env.get(info["model_env"]) if info.get("model_env") else None) or info["default_model"]


def infer_provider(model):
    """Provider name for a bare model id, or None when the prefix is ambiguous."""
    low = model.lower()
    for prefix, provider in PREFIXES:
        if low.startswith(prefix):
            return provider
    return None


def resolve(model_spec=None, env=None):
    """(provider_name, model_id) for a model string, an env default, or a set key.

    Order: explicit spec, then HUMAN_VOICE_MODEL, then the first provider in
    AUTO_ORDER that has an API key configured.
    """
    env = os.environ if env is None else env
    spec = (model_spec or env.get("HUMAN_VOICE_MODEL") or "").strip()
    if spec:
        head, sep, tail = spec.partition("/")
        if head.lower() in PROVIDERS:
            provider, model = head.lower(), tail.strip()
        else:
            provider, model = infer_provider(spec), spec
            if provider is None:
                raise ProviderError(
                    "cannot tell which provider serves %r. Prefix it with one, e.g. "
                    "openrouter/%s or together/%s. Providers: %s"
                    % (spec, spec, spec, ", ".join(PROVIDERS)))
        if not model:
            model = _default_model(provider, env)
        if not model:
            raise ProviderError("%s needs a model: %s/<%s>" % (
                provider, provider, PROVIDERS[provider].get("model_hint", "model")))
        return provider, model

    for provider in AUTO_ORDER:
        info = PROVIDERS[provider]
        model = _default_model(provider, env)
        if _env(env, info["key_env"])[1] and model:
            return provider, model
    raise ProviderError(
        "no model given and no provider key found. Either pass --model "
        "provider/model, set HUMAN_VOICE_MODEL, or export one of: %s. Local models "
        "need no key: --model ollama/<model>."
        % ", ".join(v for p in AUTO_ORDER for v in PROVIDERS[p]["key_env"]))


def describe_providers(env=None):
    """Rows for `humanize.py --list-providers`: what exists and what is configured."""
    env = os.environ if env is None else env
    rows = []
    for name, info in PROVIDERS.items():
        key_var, key = _env(env, info["key_env"])
        if info.get("local"):
            status = "local"
        elif name == "vertex":
            ready = env.get("GOOGLE_CLOUD_PROJECT") and (key or shutil.which("gcloud"))
            status = "ready" if ready else "needs GOOGLE_CLOUD_PROJECT + gcloud"
        elif name == "bedrock":
            status = "ready" if key and _region(env) else "needs AWS credentials + AWS_REGION"
        elif name == "azure":
            status = "ready" if key and env.get("AZURE_OPENAI_ENDPOINT") else \
                "needs AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT"
        else:
            status = ("ready (%s)" % key_var) if key else "set " + " or ".join(info["key_env"])
        rows.append({"provider": name, "label": info["label"],
                     "default_model": _default_model(name, env) or "<%s>" % info.get("model_hint", "model"),
                     "status": status})
    return rows


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

def _urlopen(url, data, headers, timeout):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _redact(text, secrets):
    for s in secrets:
        if s and len(s) > 6:
            text = text.replace(s, s[:3] + "…")
    return text


def post_json(url, body, headers, timeout=300, opener=None, retries=3, secrets=(),
              sleep=time.sleep):
    """POST JSON with retry on rate limits and transient 5xx. Returns parsed JSON.

    `opener(url, data, headers, timeout)` replaces the network for tests. It may
    raise urllib.error.HTTPError to exercise the retry path.
    """
    data = json.dumps(body).encode("utf-8")
    headers = dict({"Content-Type": "application/json",
                    "User-Agent": "human-voice (+https://github.com/stephenoffer/human-voice)"},
                   **headers)
    call = opener or _urlopen
    attempt = 0
    while True:
        attempt += 1
        try:
            return call(url, data, headers, timeout)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:800]
            except Exception:
                pass
            if exc.code in RETRY_STATUS and attempt <= retries:
                wait = 2 ** attempt
                try:
                    wait = max(wait, float(exc.headers.get("retry-after") or 0))
                except (TypeError, ValueError, AttributeError):
                    pass
                sleep(min(wait, 60))
                continue
            hint = {401: " (check the API key)", 403: " (key lacks access to this model?)",
                    404: " (unknown model or endpoint; is the model id current?)"}.get(exc.code, "")
            raise ProviderError(_redact("HTTP %d from %s%s: %s" % (
                exc.code, url.split("?")[0], hint, detail.strip()), secrets)) from None
        except urllib.error.URLError as exc:
            if attempt <= retries:
                sleep(2 ** attempt)
                continue
            raise ProviderError(_redact("cannot reach %s: %s" % (url.split("?")[0], exc.reason),
                                        secrets)) from None


# ---------------------------------------------------------------------------
# Wire formats
# ---------------------------------------------------------------------------

def _openai_body(model, system, messages, max_tokens, temperature, native):
    body = {"model": model,
            "messages": [{"role": "system", "content": system}] + list(messages)}
    # OpenAI's reasoning models reject max_tokens and any non-default temperature.
    # Everyone else speaking the format still expects max_tokens.
    body["max_completion_tokens" if native else "max_tokens"] = max_tokens
    if temperature is not None:
        body["temperature"] = temperature
    return body


def _openai_parse(payload):
    try:
        choice = payload["choices"][0]
    except (KeyError, IndexError, TypeError):
        raise ProviderError("response has no choices: %s" % str(payload)[:400]) from None
    content = (choice.get("message") or {}).get("content")
    if isinstance(content, list):  # content-part arrays (some compat servers)
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or "", choice.get("finish_reason") == "length", payload.get("usage") or {}


def _anthropic_body(model, system, messages, max_tokens, temperature):
    # The system prompt is the same on every pass of the loop, so cache it.
    body = {"model": model, "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": list(messages)}
    if temperature is not None:
        body["temperature"] = temperature
    return body


def _anthropic_parse(payload):
    blocks = payload.get("content")
    if not isinstance(blocks, list):
        raise ProviderError("response has no content: %s" % str(payload)[:400])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    return text, payload.get("stop_reason") == "max_tokens", payload.get("usage") or {}


def _gemini_body(system, messages, max_tokens, temperature):
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]} for m in messages]
    config: dict = {"maxOutputTokens": max_tokens}
    if temperature is not None:
        config["temperature"] = temperature
    return {"systemInstruction": {"parts": [{"text": system}]},
            "contents": contents, "generationConfig": config}


def _gemini_parse(payload):
    cands = payload.get("candidates") or []
    if not cands:
        block = (payload.get("promptFeedback") or {}).get("blockReason")
        raise ProviderError("Gemini returned no candidates%s" % (
            " (blocked: %s)" % block if block else ": %s" % str(payload)[:400]))
    cand = cands[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return text, cand.get("finishReason") == "MAX_TOKENS", payload.get("usageMetadata") or {}


def _bedrock_body(system, messages, max_tokens, temperature):
    config: dict = {"maxTokens": max_tokens}
    if temperature is not None:
        config["temperature"] = temperature
    return {"system": [{"text": system}],
            "messages": [{"role": m["role"], "content": [{"text": m["content"]}]}
                         for m in messages],
            "inferenceConfig": config}


def _bedrock_parse(payload):
    try:
        blocks = payload["output"]["message"]["content"]
    except (KeyError, TypeError):
        raise ProviderError("Bedrock response has no output message: %s"
                            % str(payload)[:400]) from None
    text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
    return text, payload.get("stopReason") == "max_tokens", payload.get("usage") or {}


# ---------------------------------------------------------------------------
# Credentials for the two clouds that do not take a plain API key
# ---------------------------------------------------------------------------

def _region(env):
    return env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION")


def sigv4_headers(method, url, body_bytes, access_key, secret_key, region, service,
                  session_token=None, now=None):
    """AWS Signature Version 4 headers, standard library only."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    parsed = urllib.parse.urlsplit(url)
    # Non-S3 services sign the path URI-encoded a second time.
    canonical_uri = "/".join(urllib.parse.quote(seg, safe="-_.~")
                             for seg in parsed.path.split("/")) or "/"
    payload_hash = hashlib.sha256(body_bytes).hexdigest()
    headers = {"host": parsed.netloc, "x-amz-date": amz_date,
               "x-amz-content-sha256": payload_hash, "content-type": "application/json"}
    if session_token:
        headers["x-amz-security-token"] = session_token
    signed = ";".join(sorted(headers))
    canonical = "\n".join([method, canonical_uri, parsed.query,
                           "".join("%s:%s\n" % (k, headers[k]) for k in sorted(headers)),
                           signed, payload_hash])
    scope = "%s/%s/%s/aws4_request" % (date, region, service)
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope,
                         hashlib.sha256(canonical.encode()).hexdigest()])

    def _h(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()
    k = _h(_h(_h(_h(("AWS4" + secret_key).encode(), date), region), service), "aws4_request")
    signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    out = {k2: v for k2, v in headers.items() if k2 != "host"}
    out["Authorization"] = ("AWS4-HMAC-SHA256 Credential=%s/%s, SignedHeaders=%s, Signature=%s"
                            % (access_key, scope, signed, signature))
    return out


def _vertex_token(env):
    token = env.get("VERTEX_ACCESS_TOKEN")
    if token:
        return token
    gcloud = shutil.which("gcloud")
    if not gcloud:
        raise ProviderError("vertex needs VERTEX_ACCESS_TOKEN or the gcloud CLI "
                            "(gcloud auth application-default login)")
    try:
        return subprocess.run([gcloud, "auth", "print-access-token"], check=True,
                              capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:
        raise ProviderError("gcloud auth print-access-token failed: %s" % exc) from None


# ---------------------------------------------------------------------------
# The one entry point
# ---------------------------------------------------------------------------

def chat(model_spec, system, messages, max_tokens=None, temperature=None, timeout=300,
         env=None, opener=None, base_url=None, api_key=None, retries=3, sleep=time.sleep):
    """Send one conversation to any provider and return a Completion.

    `messages` is a list of {"role": "user"|"assistant", "content": str}. The
    system prompt is passed separately because three of the four wire formats
    want it outside the message list.
    """
    env = os.environ if env is None else env
    provider, model = resolve(model_spec, env)
    info = PROVIDERS[provider]
    kind = info["kind"]
    max_tokens = int(max_tokens or env.get("HUMAN_VOICE_MAX_TOKENS") or info["max_tokens"])
    key = api_key or _env(env, info["key_env"])[1]
    base = (base_url or (env.get(info["base_env"]) if info.get("base_env") else None)
            or info["base_url"])
    secrets = (key,)
    kw = {"timeout": timeout, "opener": opener, "retries": retries, "sleep": sleep}

    if kind in ("openai", "azure") or provider in ("compat",):
        if kind == "azure":
            if not (key and base):
                raise ProviderError("azure needs AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
            version = env.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
            url = "%s/openai/deployments/%s/chat/completions?api-version=%s" % (
                base.rstrip("/"), urllib.parse.quote(model, safe=""), version)
            headers = {"api-key": key}
            native = True
        else:
            if not base:
                raise ProviderError("%s needs a base URL: --base-url or %s"
                                    % (provider, info["base_env"]))
            if not key and not info.get("local"):
                raise ProviderError("%s needs an API key: export %s"
                                    % (provider, " or ".join(info["key_env"])))
            url = base.rstrip("/") + "/chat/completions"
            headers = {"Authorization": "Bearer " + key} if key else {}
            headers.update(info.get("extra_headers") or {})
            native = bool(info.get("native_openai"))
        body = _openai_body(model, system, messages, max_tokens, temperature, native)
        text, truncated, usage = _openai_parse(post_json(url, body, headers, secrets=secrets, **kw))

    elif kind == "anthropic":
        if not key:
            raise ProviderError("anthropic needs an API key: export ANTHROPIC_API_KEY")
        url = base.rstrip("/") + "/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        body = _anthropic_body(model, system, messages, max_tokens, temperature)
        text, truncated, usage = _anthropic_parse(post_json(url, body, headers, secrets=secrets, **kw))

    elif kind == "gemini":
        if not key:
            raise ProviderError("gemini needs an API key: export GEMINI_API_KEY")
        url = "%s/models/%s:generateContent" % (base.rstrip("/"), urllib.parse.quote(model, safe="-._"))
        body = _gemini_body(system, messages, max_tokens, temperature)
        text, truncated, usage = _gemini_parse(
            post_json(url, body, {"x-goog-api-key": key}, secrets=secrets, **kw))

    elif kind == "vertex":
        project = env.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ProviderError("vertex needs GOOGLE_CLOUD_PROJECT (and GOOGLE_CLOUD_LOCATION)")
        location = env.get("GOOGLE_CLOUD_LOCATION", "global")
        host = "aiplatform.googleapis.com" if location == "global" else \
            "%s-aiplatform.googleapis.com" % location
        token = _vertex_token(env)
        secrets = (token,)
        headers = {"Authorization": "Bearer " + token}
        if model.startswith("claude"):
            url = ("https://%s/v1/projects/%s/locations/%s/publishers/anthropic/models/%s:rawPredict"
                   % (host, project, location, model))
            body = _anthropic_body(model, system, messages, max_tokens, temperature)
            del body["model"]
            body["anthropic_version"] = "vertex-2023-10-16"
            text, truncated, usage = _anthropic_parse(post_json(url, body, headers, secrets=secrets, **kw))
        else:
            url = ("https://%s/v1/projects/%s/locations/%s/publishers/google/models/%s:generateContent"
                   % (host, project, location, model))
            body = _gemini_body(system, messages, max_tokens, temperature)
            text, truncated, usage = _gemini_parse(post_json(url, body, headers, secrets=secrets, **kw))

    elif kind == "bedrock":
        secret = env.get("AWS_SECRET_ACCESS_KEY")
        region = _region(env)
        if not (key and secret and region):
            raise ProviderError("bedrock needs AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and "
                                "AWS_REGION (plus AWS_SESSION_TOKEN for temporary credentials)")
        host = base.rstrip("/") if base else "https://bedrock-runtime.%s.amazonaws.com" % region
        url = "%s/model/%s/converse" % (host, urllib.parse.quote(model, safe=""))
        body = _bedrock_body(system, messages, max_tokens, temperature)
        data = json.dumps(body).encode("utf-8")
        headers = sigv4_headers("POST", url, data, key, secret, region, "bedrock",
                                env.get("AWS_SESSION_TOKEN"))
        secrets = (key, secret)
        text, truncated, usage = _bedrock_parse(post_json(url, body, headers, secrets=secrets, **kw))

    else:  # pragma: no cover - table and dispatcher out of sync
        raise ProviderError("no wire format for provider kind %r" % kind)

    return Completion(text, provider, model, truncated, usage)


__all__ = [
    "PROVIDERS", "AUTO_ORDER", "ProviderError", "Completion",
    "infer_provider", "resolve", "describe_providers", "post_json", "sigv4_headers", "chat",
]
