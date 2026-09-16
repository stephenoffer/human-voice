"""Tests for the model-agnostic layer: providers, prompt, invariants, loop, MCP, installer.

Standard library only (unittest), so it runs on the bare CI matrix as
`python3 tests/test_llm.py` as well as under pytest.
No test touches the network: every provider call goes through an injected opener.
"""
import datetime
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "human-voice")
SCRIPTS = os.path.join(SKILL, "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, ROOT)

from human_voice_llm import invariants, mcp_server, prompt, providers  # noqa: E402
from human_voice_llm.loop import humanize  # noqa: E402

import install  # noqa: E402

EXAMPLES = os.path.join(SKILL, "examples")
KEYS = {"OPENAI_API_KEY": "sk-openai-secret-123", "ANTHROPIC_API_KEY": "sk-ant-secret-456",
        "GEMINI_API_KEY": "gem-secret-789", "MISTRAL_API_KEY": "m", "XAI_API_KEY": "x",
        "AWS_ACCESS_KEY_ID": "AKID", "AWS_SECRET_ACCESS_KEY": "SECRET", "AWS_REGION": "us-east-1",
        "GOOGLE_CLOUD_PROJECT": "proj", "VERTEX_ACCESS_TOKEN": "ya29.token",
        "AZURE_OPENAI_API_KEY": "az", "AZURE_OPENAI_ENDPOINT": "https://res.openai.azure.com/"}


def _read(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return fh.read()


def reply_for(text):
    return "<rewrite>\n%s\n</rewrite>\n<audit>\n## Humanization Audit: t\n</audit>" % text


class Recorder:
    """An opener that records requests and answers in the right wire format."""

    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = []

    def __call__(self, url, data, headers, timeout):
        body = json.loads(data)
        self.calls.append({"url": url, "body": body, "headers": headers})
        text = self.texts.pop(0) if len(self.texts) > 1 else self.texts[0]
        if url.endswith("/messages") or url.endswith(":rawPredict"):
            return {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}
        if ":generateContent" in url:
            return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}
        if url.endswith("/converse"):
            return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": "end_turn"}
        return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}


class ResolveTest(unittest.TestCase):
    def test_explicit_provider(self):
        self.assertEqual(providers.resolve("openai/gpt-5.6", {}), ("openai", "gpt-5.6"))
        self.assertEqual(providers.resolve("OpenRouter/meta-llama/llama-4", {}),
                         ("openrouter", "meta-llama/llama-4"))

    def test_bare_model_prefixes(self):
        for model, want in [("claude-sonnet-5", "anthropic"), ("gpt-6-astra", "openai"),
                            ("o4-mini", "openai"), ("gemini-3.8-flash", "gemini"),
                            ("grok-4.6", "xai"), ("mistral-large-latest", "mistral"),
                            ("deepseek-v4-pro", "deepseek"), ("command-a-plus-05-2026", "cohere")]:
            self.assertEqual(providers.resolve(model, {})[0], want, model)

    def test_ambiguous_bare_model_is_an_error(self):
        with self.assertRaises(providers.ProviderError):
            providers.resolve("llama-3.3-70b", {})

    def test_provider_only_uses_default(self):
        self.assertEqual(providers.resolve("anthropic", {})[1], "claude-sonnet-5")
        self.assertEqual(providers.resolve("anthropic/", {})[1], "claude-sonnet-5")
        with self.assertRaises(providers.ProviderError):
            providers.resolve("ollama", {})
        self.assertEqual(providers.resolve("ollama", {"OLLAMA_MODEL": "qwen3"}), ("ollama", "qwen3"))

    def test_env_and_auto_order(self):
        self.assertEqual(providers.resolve(None, {"HUMAN_VOICE_MODEL": "xai/grok-4.6"}),
                         ("xai", "grok-4.6"))
        self.assertEqual(providers.resolve(None, {"GEMINI_API_KEY": "g", "MISTRAL_API_KEY": "m"})[0],
                         "gemini")
        self.assertEqual(providers.resolve(None, {"OPENAI_API_KEY": "o", "ANTHROPIC_API_KEY": "a"})[0],
                         "anthropic")
        # Azure has no default model until a deployment is named.
        self.assertEqual(providers.resolve(None, {"AZURE_OPENAI_API_KEY": "z", "GROQ_API_KEY": "g"})[0],
                         "groq")
        with self.assertRaises(providers.ProviderError):
            providers.resolve(None, {})

    def test_every_provider_is_described(self):
        rows = providers.describe_providers({})
        self.assertEqual({r["provider"] for r in rows}, set(providers.PROVIDERS))


class WireFormatTest(unittest.TestCase):
    def call(self, model, env=None, **kw):
        rec = Recorder(["hello"])
        out = providers.chat(model, "SYS", [{"role": "user", "content": "hi"},
                                            {"role": "assistant", "content": "a"},
                                            {"role": "user", "content": "again"}],
                             env=dict(KEYS, **(env or {})), opener=rec, **kw)
        self.assertEqual(out.text, "hello")
        return rec.calls[0], out

    def test_openai_native_uses_max_completion_tokens_and_no_temperature(self):
        call, out = self.call("openai/gpt-5.6")
        self.assertEqual(call["url"], "https://api.openai.com/v1/chat/completions")
        self.assertIn("max_completion_tokens", call["body"])
        self.assertNotIn("max_tokens", call["body"])
        self.assertNotIn("temperature", call["body"])
        self.assertEqual(call["body"]["messages"][0], {"role": "system", "content": "SYS"})
        self.assertEqual(call["headers"]["Authorization"], "Bearer " + KEYS["OPENAI_API_KEY"])

    def test_openai_compatible_vendors_use_max_tokens(self):
        call, _ = self.call("mistral/mistral-large-latest", temperature=0.7)
        self.assertEqual(call["url"], "https://api.mistral.ai/v1/chat/completions")
        self.assertIn("max_tokens", call["body"])
        self.assertEqual(call["body"]["temperature"], 0.7)

    def test_local_needs_no_key_and_base_url_overrides(self):
        call, _ = self.call("ollama/qwen3:32b", env={"OLLAMA_BASE_URL": "http://gpu:11434/v1"})
        self.assertEqual(call["url"], "http://gpu:11434/v1/chat/completions")
        self.assertNotIn("Authorization", call["headers"])
        call, _ = self.call("compat/my-model", base_url="http://vllm:8000/v1/")
        self.assertEqual(call["url"], "http://vllm:8000/v1/chat/completions")

    def test_missing_key_is_actionable(self):
        with self.assertRaisesRegex(providers.ProviderError, "GROQ_API_KEY"):
            providers.chat("groq/llama-3.3-70b-versatile", "s", [], env={}, opener=Recorder(["x"]))

    def test_anthropic(self):
        call, _ = self.call("claude-sonnet-5")
        self.assertEqual(call["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(call["headers"]["x-api-key"], KEYS["ANTHROPIC_API_KEY"])
        self.assertEqual(call["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(call["body"]["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual([m["role"] for m in call["body"]["messages"]], ["user", "assistant", "user"])

    def test_gemini(self):
        call, _ = self.call("gemini/gemini-3.8-flash")
        self.assertTrue(call["url"].endswith("/v1beta/models/gemini-3.8-flash:generateContent"))
        self.assertEqual(call["headers"]["x-goog-api-key"], KEYS["GEMINI_API_KEY"])
        self.assertEqual([c["role"] for c in call["body"]["contents"]], ["user", "model", "user"])
        self.assertEqual(call["body"]["systemInstruction"]["parts"][0]["text"], "SYS")

    def test_vertex_routes_by_publisher(self):
        call, _ = self.call("vertex/claude-sonnet-5")
        self.assertIn("/publishers/anthropic/models/claude-sonnet-5:rawPredict", call["url"])
        self.assertNotIn("model", call["body"])
        self.assertEqual(call["body"]["anthropic_version"], "vertex-2023-10-16")
        call, _ = self.call("vertex/gemini-3.8-flash", env={"GOOGLE_CLOUD_LOCATION": "europe-west4"})
        self.assertTrue(call["url"].startswith("https://europe-west4-aiplatform.googleapis.com/"))
        self.assertEqual(call["headers"]["Authorization"], "Bearer ya29.token")

    def test_azure(self):
        call, _ = self.call("azure/prod-gpt")
        self.assertEqual(call["url"], "https://res.openai.azure.com/openai/deployments/prod-gpt/"
                                      "chat/completions?api-version=2024-10-21")
        self.assertEqual(call["headers"]["api-key"], "az")

    def test_bedrock(self):
        call, _ = self.call("bedrock/us.anthropic.claude-sonnet-5-v1:0")
        self.assertEqual(call["url"], "https://bedrock-runtime.us-east-1.amazonaws.com/model/"
                                      "us.anthropic.claude-sonnet-5-v1%3A0/converse")
        self.assertTrue(call["headers"]["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKID/"))
        self.assertEqual(call["body"]["messages"][0]["content"], [{"text": "hi"}])

    def test_sigv4_matches_botocore_vector(self):
        # Reference signature computed with botocore.auth.SigV4Auth for this exact request.
        url = ("https://bedrock-runtime.us-east-1.amazonaws.com/model/"
               "us.anthropic.claude-sonnet-5-v1%3A0/converse")
        body = json.dumps({"a": 1}).encode()
        now = datetime.datetime(2026, 9, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
        h = providers.sigv4_headers("POST", url, body, "AKID", "SECRET", "us-east-1", "bedrock",
                                    "TOK", now=now)
        self.assertEqual(h["x-amz-content-sha256"], hashlib.sha256(body).hexdigest())
        self.assertTrue(h["Authorization"].endswith(
            "Signature=20161486b47d1f7a706625899a7f500589162c6fa75cb78044337b531249fc10"))

    def test_truncation_and_thought_parts(self):
        def opener(url, data, headers, timeout):
            return {"candidates": [{"content": {"parts": [{"text": "plan", "thought": True},
                                                          {"text": "answer"}]},
                                    "finishReason": "MAX_TOKENS"}]}
        out = providers.chat("gemini-3.8-flash", "s", [{"role": "user", "content": "x"}],
                             env=KEYS, opener=opener)
        self.assertEqual(out.text, "answer")
        self.assertTrue(out.truncated)

    def test_blocked_gemini_prompt(self):
        with self.assertRaisesRegex(providers.ProviderError, "SAFETY"):
            providers.chat("gemini-3.8-flash", "s", [{"role": "user", "content": "x"}], env=KEYS,
                           opener=lambda *a: {"promptFeedback": {"blockReason": "SAFETY"}})


class TransportTest(unittest.TestCase):
    def test_retries_rate_limit_then_succeeds(self):
        state = {"n": 0}
        slept = []

        def opener(url, data, headers, timeout):
            state["n"] += 1
            if state["n"] < 3:
                raise urllib.error.HTTPError(url, 429, "slow down", {"retry-after": "1"}, io.BytesIO(b"{}"))
            return {"ok": True}
        self.assertEqual(providers.post_json("https://x", {}, {}, opener=opener, sleep=slept.append),
                         {"ok": True})
        self.assertEqual(len(slept), 2)

    def test_auth_error_redacts_key(self):
        secret = "sk-very-secret-key-0001"

        def opener(url, data, headers, timeout):
            raise urllib.error.HTTPError(url, 401, "no", {}, io.BytesIO(
                ("bad key %s" % secret).encode()))
        with self.assertRaises(providers.ProviderError) as ctx:
            providers.post_json("https://x", {}, {}, opener=opener, secrets=(secret,),
                                sleep=lambda s: None)
        self.assertNotIn(secret, str(ctx.exception))
        self.assertIn("check the API key", str(ctx.exception))


class PromptTest(unittest.TestCase):
    def test_system_prompt_is_the_whole_skill(self):
        api = prompt.build_system_prompt("api", "core")
        self.assertNotIn("\nname: human-voice\n", api)  # frontmatter stripped
        self.assertIn("## Invariant guard", api)
        self.assertIn("<rewrite>", api)
        for ref in prompt.CORE_REFERENCES:
            self.assertIn("# Reference: references/%s" % ref, api)
        self.assertNotIn("competitive-landscape.md\n", prompt.build_system_prompt("api", "core")
                         .split("---")[-1][:60])
        chat = prompt.build_system_prompt("chat", "none")
        self.assertIn("no-tool checklist", chat)
        self.assertNotIn("# Reference:", chat)
        self.assertLess(len(chat), len(api))

    def test_parse_response(self):
        self.assertEqual(prompt.parse_response(reply_for("Body."))[:2],
                         ("Body.", "## Humanization Audit: t"))
        self.assertEqual(prompt.parse_response("<rewrite>\nOnly body")[0], "Only body")
        self.assertEqual(prompt.parse_response("<rewrite>\n```markdown\n# T\n\nx\n```\n</rewrite>",
                                               "# T\n\nx")[0], "# T\n\nx")
        self.assertIsNotNone(prompt.parse_response("Sure! Here you go: text")[2])
        self.assertIsNotNone(prompt.parse_response("<rewrite>  </rewrite>")[2])
        # A model that echoes the instructions first: the last section wins.
        self.assertEqual(prompt.parse_response("<rewrite>x</rewrite> ... <rewrite>real</rewrite>")[0],
                         "real")


class InvariantTest(unittest.TestCase):
    SRC = ("p99 dropped from 340 ms to 120 ms after v2.4.1 shipped [3]. See "
           "[the runbook](https://example.com/runbook) and `cache.ttl`.\n\n"
           "```yaml\nttl: 30\n```\n")

    def test_identical_is_ok(self):
        self.assertTrue(invariants.compare(self.SRC, self.SRC)["ok"])

    def test_detects_lost_and_invented(self):
        bad = ("Latency fell sharply, by 64%, after the release. See the runbook "
               "and `cache.ttl`.\n\n```yaml\nttl: 60\n```\n")
        r = invariants.compare(self.SRC, bad)
        self.assertFalse(r["ok"])
        self.assertIn("340", r["missing"]["numbers"])
        self.assertIn("v2.4.1", r["missing"]["numbers"])
        self.assertIn("https://example.com/runbook", r["missing"]["links"])
        self.assertIn("[3]", r["missing"]["citations"])
        self.assertEqual(len(r["missing"]["code_blocks"]), 1)
        self.assertIn("64%", r["added"]["numbers"])
        self.assertTrue(any("MISSING" in line for line in invariants.summarize(r)))

    def test_context_numbers_are_sourced_and_comments_ignored(self):
        src = "<!-- score 3.3 -->\nLatency improved after the change."
        out = "Latency fell from 340 ms to 120 ms after the change."
        self.assertEqual(invariants.compare(src, out)["added"], {"numbers": ["120", "340"]})
        self.assertTrue(invariants.compare(src, out, context="p99: 340 ms before, 120 ms after")["ok"])

    def test_placeholders_reported_and_list_markers_ignored(self):
        r = invariants.compare("1. First step\n2. Second", "1. First step [SOURCE NEEDED]\n2. Second")
        self.assertTrue(r["ok"])
        self.assertEqual(r["placeholders"], ["[SOURCE NEEDED]"])


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.before = _read("modern-ai-before.md")
        self.after = _read("modern-ai-after.md")

    def test_accepts_clean_rewrite_first_pass(self):
        rec = Recorder([reply_for(self.after)])
        r = humanize(self.before, model="openai/gpt-5.6", register="technical", opener=rec, env=KEYS)
        self.assertTrue(r["accepted"])
        self.assertEqual(len(r["passes"]), 1)
        self.assertGreater(r["before"]["score"], r["after"]["score"])
        task = rec.calls[0]["body"]["messages"][1]["content"]
        self.assertIn("Baseline linter report", task)
        self.assertIn("<source>", task)

    def test_lost_number_is_fed_back_and_fixed(self):
        src = self.after + "\n\nThe p99 held at 340 ms.\n"
        lost = self.after + "\n\nThe p99 held steady.\n"
        rec = Recorder([reply_for(lost), reply_for(src)])
        r = humanize(src, model="claude-sonnet-5", register="technical", opener=rec, env=KEYS)
        self.assertTrue(r["accepted"])
        self.assertEqual(r["best_pass"], 2)
        feedback = rec.calls[1]["body"]["messages"][-1]["content"]
        self.assertIn("Invariant check FAILED", feedback)
        self.assertIn("'340'", feedback)

    def test_format_error_recovers(self):
        rec = Recorder(["Sure! Here is the rewrite.", reply_for(self.after)])
        r = humanize(self.before, model="gemini-3.8-flash", register="technical", opener=rec, env=KEYS)
        self.assertTrue(r["accepted"])
        self.assertIn("error", r["passes"][0])

    def test_never_usable_raises(self):
        with self.assertRaises(providers.ProviderError):
            humanize(self.before, model="openai/gpt-5.6", opener=Recorder(["no tags"]), env=KEYS,
                     max_passes=2)

    def test_stalls_stop_early_and_keep_best(self):
        rec = Recorder([reply_for(self.before)])  # the model returns the slop unchanged
        r = humanize(self.before, model="xai/grok-4.6", register="technical", opener=rec,
                     env=KEYS, max_passes=5)
        self.assertFalse(r["accepted"])
        self.assertEqual(len(r["passes"]), 3)  # first + two without improvement
        self.assertEqual(r["best_pass"], 1)

    def test_generate_flags_invented_numbers(self):
        brief = "Write a two-paragraph note announcing that the cache TTL moved to 30 seconds."
        rec = Recorder([reply_for("The cache TTL is now 30 seconds. It cut load by 45%.")])
        r = humanize(brief, model="openai/gpt-5.6", mode="generate", register="technical",
                     opener=rec, env=KEYS, max_passes=1)
        self.assertIsNone(r["before"])
        self.assertEqual(r["invariants"]["added"], {"numbers": ["45%"]})
        self.assertFalse(r["accepted"])


class McpTest(unittest.TestCase):
    def rpc(self, method, params=None, mid=1):
        return mcp_server.handle({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}})

    def test_handshake_and_listing(self):
        init = self.rpc("initialize", {"protocolVersion": "2025-03-26"})["result"]
        self.assertEqual(init["protocolVersion"], "2025-03-26")
        self.assertEqual(self.rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]
                         ["protocolVersion"], mcp_server.PROTOCOL_VERSIONS[0])
        self.assertIsNone(mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        names = {t["name"] for t in self.rpc("tools/list")["result"]["tools"]}
        self.assertEqual(names, {"lint_prose", "check_invariants", "get_skill", "humanize",
                                 "verify_detector"})
        self.assertEqual(self.rpc("nope")["error"]["code"], -32601)

    def test_tools(self):
        out = self.rpc("tools/call", {"name": "lint_prose", "arguments": {
            "text": _read("modern-ai-before.md"), "register": "technical"}})["result"]
        self.assertIn("floor points", out["content"][0]["text"])
        inv = self.rpc("tools/call", {"name": "check_invariants", "arguments": {
            "original": "It took 340 ms.", "rewrite": "It was fast."}})["result"]
        self.assertIn("CHANGED", inv["content"][0]["text"])
        skill = self.rpc("tools/call", {"name": "get_skill", "arguments": {}})["result"]
        self.assertIn("lint_prose", skill["content"][0]["text"])
        ref = self.rpc("tools/call", {"name": "get_skill", "arguments": {"reference": "ai-tells"}})
        self.assertNotIn("isError", ref["result"])
        missing = self.rpc("tools/call", {"name": "get_skill", "arguments": {"reference": "../../x"}})
        self.assertTrue(missing["result"]["isError"])

    def test_resources_and_prompt(self):
        uris = [r["uri"] for r in self.rpc("resources/list")["result"]["resources"]]
        self.assertIn("human-voice://references/ai-tells.md", uris)
        for uri in uris:
            self.assertIn("result", self.rpc("resources/read", {"uri": uri}))
        self.assertIn("error", self.rpc("resources/read", {"uri": "human-voice://../SKILL.md"}))
        msgs = self.rpc("prompts/get", {"name": "human-voice", "arguments": {"text": "draft"}})
        self.assertIn("<source>\ndraft\n</source>", msgs["result"]["messages"][0]["content"]["text"])

    def test_stdio_loop(self):
        lines = "\n".join(json.dumps(m) for m in [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "ping"}]) + "\nnot json\n"
        out = io.StringIO()
        mcp_server.serve(io.StringIO(lines), out)
        replies = [json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual([r.get("id") for r in replies], [1, 2, None])
        self.assertEqual(replies[2]["error"]["code"], -32700)


class InstallerTest(unittest.TestCase):
    def test_plan_dedupes_shared_directories(self):
        self.assertEqual(install.plan(["codex", "cursor", "claude", "windsurf"]),
                         [("agents", ["codex", "cursor"]), ("claude", ["claude"]),
                          ("windsurf", ["windsurf"])])
        self.assertEqual(install.plan(["cursor"], exact=True), [("cursor", ["cursor"])])

    def test_installs_into_project(self):
        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            old, sys.stdout = sys.stdout, buf
            try:
                rc = install.main(["codex", "windsurf", "aider", "--project", d])
                again = install.main(["codex", "--project", d])
            finally:
                sys.stdout = old
            self.assertEqual(rc, 0)
            self.assertEqual(again, 1)  # refuses to overwrite without --force
            self.assertTrue(os.path.isfile(os.path.join(d, ".agents/skills/human-voice/SKILL.md")))
            self.assertTrue(os.path.isfile(os.path.join(
                d, ".windsurf/skills/human-voice/scripts/detect_ai_prose.py")))
            self.assertFalse(os.path.exists(os.path.join(
                d, ".agents/skills/human-voice/scripts/human_voice_llm/__pycache__")))
            with open(os.path.join(d, "CONVENTIONS.human-voice.md"), encoding="utf-8") as fh:
                self.assertIn("Running as a system prompt", fh.read())

    def test_mcp_configs_parse(self):
        for client in install.MCP_CLIENTS:
            text = install.mcp_config(client)
            self.assertIn("mcp_server.py", text)
            if client in ("cursor", "vscode", "windsurf", "cline", "claude-desktop", "opencode", "zed"):
                json.loads(text.split("\n", 1)[1])


class PortabilityTest(unittest.TestCase):
    """The skill folder must load in every agent that implements the open spec."""

    def frontmatter(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(m)
        return m.group(1)

    def test_frontmatter_follows_agent_skills_spec(self):
        allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
        fm = self.frontmatter()
        top = re.findall(r"^([A-Za-z_-]+):", fm, re.M)
        self.assertEqual(set(top) - allowed, set(), "fields outside the Agent Skills spec fail "
                         "`skills-ref validate` and may not load in strict agents")
        name = re.search(r"^name: (.+)$", fm, re.M).group(1).strip()
        self.assertEqual(name, os.path.basename(SKILL))
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        desc = re.search(r"^description: (.+)$", fm, re.M).group(1).strip()
        self.assertLessEqual(len(desc), 1024)
        compat = re.search(r"^compatibility: (.+)$", fm, re.M).group(1).strip()
        self.assertLessEqual(len(compat), 500)

    def test_versions_agree(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            canonical = json.load(fh)["version"]
        with open(os.path.join(ROOT, "gemini-extension.json"), encoding="utf-8") as fh:
            gem = json.load(fh)
        self.assertEqual(gem["version"], canonical)
        self.assertEqual(gem["name"], "human-voice")
        self.assertEqual(mcp_server.SERVER_INFO["version"], canonical)
        self.assertIn('version: "%s"' % canonical, self.frontmatter())


if __name__ == "__main__":
    unittest.main()
