"""Exercise generic provider routing, authentication and the settings contract."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from bosshunter.ai import credentials, scorer
from bosshunter.config import AI_SERVICE_PRESETS, load_config, save_config
from bosshunter.web import server
from bosshunter.web.preflight import check_ai_connection


def model_response():
    return httpx.Response(200, json={"data": [{"id": "Vendor/CaseSensitive-Model"}]},
                          request=httpx.Request("GET", "https://example.invalid/models"))


def text_response():
    return httpx.Response(200, json={"choices": [{"message": {"content": "模型回复"}, "finish_reason": "stop"}]},
                          request=httpx.Request("POST", "https://example.invalid/chat/completions"))


class ProviderRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        old_base = server.BASE_DIR
        server.set_base_dir(self.root)
        self.addCleanup(server.set_base_dir, old_base)

    def request(self, path, body=None):
        encoded = json.dumps(body).encode() if body is not None else b""
        environ = {
            "REMOTE_ADDR": "127.0.0.1", "HTTP_HOST": "127.0.0.1:8686",
            "REQUEST_METHOD": "POST" if body is not None else "GET", "PATH_INFO": path,
            "QUERY_STRING": "", "SERVER_NAME": "127.0.0.1", "SERVER_PORT": "8686",
            "wsgi.version": (1, 0), "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(encoded),
            "wsgi.errors": io.StringIO(), "wsgi.multithread": False, "wsgi.multiprocess": False,
            "wsgi.run_once": False, "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(encoded)),
        }
        status = []
        def start_response(value, headers, exc_info=None):
            status.append(int(value.split()[0]))
        response = server.app(environ, start_response)
        try:
            result = json.loads(b"".join(response))
        finally:
            if hasattr(response, "close"):
                response.close()
        return status[0], result

    def test_cloud_presets_load_discover_and_generate_with_their_own_credentials(self):
        for service in ("openai", "gemini", "qwen", "moonshot", "zhipu", "minimax", "siliconflow", "openrouter"):
            with self.subTest(service=service):
                save_config({"ai": {"service": service, "model": "Vendor/CaseSensitive-Model", "thinking": "off"}}, server.CONFIG_PATH)
                config = load_config(server.CONFIG_PATH)
                self.assertEqual(config["ai"]["provider"], "openai_compatible")
                key_env = AI_SERVICE_PRESETS[service]["key_env"]
                with (
                    patch.dict("os.environ", {key_env: "provider-test-key", "ANTHROPIC_API_KEY": "unrelated-key"}, clear=True),
                    patch.object(credentials.httpx, "get", return_value=model_response()) as get,
                    patch.object(credentials.httpx, "post", return_value=text_response()) as post,
                ):
                    self.assertEqual(credentials.list_ai_models(config), ["Vendor/CaseSensitive-Model"])
                    self.assertEqual(scorer._call_claude("岗位与简历", config, 256), "模型回复")
                    self.assertEqual(credentials.get_ai_key_source(config), key_env)
                self.assertTrue(get.call_args.args[0].endswith("/models"))
                self.assertTrue(post.call_args.args[0].endswith("/chat/completions"))
                for call in (get.call_args, post.call_args):
                    self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer provider-test-key")
                    self.assertFalse(call.kwargs["trust_env"])
                payload = post.call_args.kwargs["json"]
                self.assertEqual(payload["model"], "Vendor/CaseSensitive-Model")
                self.assertEqual(payload["messages"], [{"role": "user", "content": "岗位与简历"}])
                if service == "openai":
                    self.assertEqual(payload["max_completion_tokens"], 256)
                    self.assertNotIn("max_tokens", payload)
                    self.assertNotIn("temperature", payload)

    def test_new_cloud_service_never_inherits_another_providers_environment_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "unrelated", "ANTHROPIC_API_KEY": "also-unrelated"}, clear=True):
            config = {"ai": {"service": "gemini"}}
            self.assertIsNone(credentials.get_ai_api_key(config))
            self.assertIsNone(credentials.get_ai_key_source(config))

    def test_keyless_remote_service_can_discover_diagnose_and_score_without_ambient_keys(self):
        resume = self.root / "resume.md"
        resume.write_text("产品经历", encoding="utf-8")
        config = {"ai": {"service": "custom", "provider": "openai_compatible", "auth_mode": "none",
                         "api_key": "must-not-send", "auth_token": "must-not-send-token",
                         "base_url": "http://192.0.2.22:11434/v1", "model": "team/私有模型", "thinking": "off"},
                  "profile": {"resume_path": str(resume)}}
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "must-not-inherit", "ANTHROPIC_API_KEY": "must-not-inherit"}, clear=True),
            patch.object(credentials.httpx, "get", return_value=model_response()) as get,
            patch.object(credentials.httpx, "post", return_value=text_response()) as post,
        ):
            self.assertIsNone(credentials.get_ai_api_key(config))
            credentials.list_ai_models(config)
            self.assertEqual(check_ai_connection(config)[0]["status"], "pass")
            self.assertEqual(server._preflight_messages("rescore", config), [])
            self.assertEqual(scorer._call_claude("岗位与简历", config), "模型回复")
        for call in get.call_args_list + post.call_args_list:
            self.assertTrue(call.args[0].startswith("http://192.0.2.22:11434/v1/"))
            self.assertNotIn("Authorization", call.kwargs["headers"])
        self.assertEqual(post.call_args.kwargs["json"]["model"], "team/私有模型")

    def test_deployment_presets_can_enable_auth_and_override_the_host(self):
        for service in ("ollama", "lmstudio"):
            config = {"ai": {"service": service, "model": "private-model", "auth_mode": "api_key",
                             "base_url": "https://inference.example/v1", "api_key": "private-host-key"}}
            with patch.object(credentials.httpx, "post", return_value=text_response()) as post:
                self.assertEqual(credentials.call_anthropic_text("prompt", config, 256), "模型回复")
            self.assertEqual(post.call_args.args[0], "https://inference.example/v1/chat/completions")
            self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer private-host-key")

    def test_custom_anthropic_protocol_survives_save_and_uses_messages_and_models(self):
        config = {"ai": {"service": "custom", "provider": "anthropic", "api_key": "gateway-key",
                         "base_url": "https://gateway.example/v1", "model": "vendor-specific-model"}}
        self.assertEqual(self.request("/api/config", config)[0], 200)
        loaded = load_config(server.CONFIG_PATH)
        self.assertEqual(loaded["ai"]["provider"], "anthropic")
        with patch.object(credentials.httpx, "get", return_value=model_response()) as get:
            credentials.list_ai_models(loaded)
        self.assertEqual(get.call_args.args[0], "https://gateway.example/v1/models")
        self.assertEqual(get.call_args.kwargs["headers"]["x-api-key"], "gateway-key")
        class Client:
            def __init__(self, **kwargs):
                self.messages = self
                self.kwargs = kwargs
            def create(self, **kwargs):
                return SimpleNamespace(content=[SimpleNamespace(type="text", text="gateway reply")])
        with (
            patch.object(credentials, "resolve_anthropic_model", side_effect=lambda model, config: model),
            patch.dict("sys.modules", {"anthropic": SimpleNamespace(Anthropic=Client)}),
        ):
            self.assertEqual(credentials.call_anthropic_text("prompt", loaded, 256), "gateway reply")

    def test_changing_provider_clears_old_secret_even_without_frontend_clear_flag(self):
        save_config({"ai": {"service": "anthropic", "api_key": "old-provider-secret"}}, server.CONFIG_PATH)
        old_mask = server._mask_api_key("old-provider-secret")
        for posted in ({}, {"api_key": old_mask}):
            cleaned = server._sanitize_config_for_write({"ai": {"service": "gemini", "model": "new-model", **posted}})
            self.assertNotIn("api_key", cleaned["ai"])
        cleaned = server._sanitize_config_for_write({"ai": {"service": "gemini", "api_key": "new-secret"}})
        self.assertEqual(cleaned["ai"]["api_key"], "new-secret")

    def test_schema_exposes_registry_and_rejects_invalid_auth_before_persisting(self):
        status, schema = self.request("/api/config/schema")
        self.assertEqual(status, 200)
        self.assertEqual(set(schema["ai_services"]), set(AI_SERVICE_PRESETS))
        choices = next(field["options"] for section in schema["sections"] if section["key"] == "ai"
                       for field in section["fields"] if field["key"] == "service")
        self.assertIn("gemini", choices)
        self.assertIn("openrouter", choices)
        for ai in ({"service": "custom", "provider": "anthropic", "auth_mode": "none"},
                   {"service": "gemini", "auth_mode": "typo"},
                   {"service": "gemini", "token_limit_field": "unknown"}):
            self.assertEqual(self.request("/api/config", {"ai": ai})[0], 400)
        self.assertFalse(server.CONFIG_PATH.exists())

    def test_inline_provider_reasoning_is_not_returned_as_the_greeting_or_score(self):
        config = {"ai": {"service": "minimax", "model": "vendor-model", "api_key": "test-key", "thinking": "off"}}
        response = httpx.Response(200, json={"choices": [{"message": {
            "content": '<think>private reasoning with {"score": 0}</think>{"score": 88}',
        }}]}, request=httpx.Request("POST", "https://example.invalid/chat/completions"))
        with patch.object(credentials.httpx, "post", return_value=response):
            self.assertEqual(credentials.call_anthropic_text("prompt", config, 1024), '{"score": 88}')
        response = httpx.Response(200, json={"choices": [{"message": {"content": "<think>unfinished reasoning"}}]},
                                  request=httpx.Request("POST", "https://example.invalid/chat/completions"))
        with (
            patch.object(credentials.httpx, "post", return_value=response),
            self.assertRaises(credentials.AIRequestError),
        ):
            credentials.call_anthropic_text("prompt", config, 1024)


if __name__ == "__main__":
    unittest.main()
