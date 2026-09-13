import unittest
from unittest.mock import patch

import httpx

from bosshunter.ai.credentials import AIRequestError, list_ai_models


class AIModelListTests(unittest.TestCase):
    def test_model_discovery_paths_auth_and_pagination(self):
        cases = [
            ("custom", "https://gateway.example/v1/", ["https://gateway.example/v1/models"], False),
            ("custom", "https://gateway.example/api/v3", ["https://gateway.example/api/v3/models"], False),
            ("deepseek", "https://gateway.example", ["https://gateway.example/models", "https://gateway.example/v1/models"], False),
            ("anthropic", "https://gateway.example/v1", ["https://gateway.example/v1/models"] * 2, True),
            ("anthropic", "", ["https://api.anthropic.com/v1/models"] * 2, True),
        ]
        for service, base, urls, paginated in cases:
            with self.subTest(service=service, base=base), patch.dict("os.environ", {}, clear=True):
                calls = []

                def get(url, **kwargs):
                    calls.append((url, kwargs))
                    payload = {"data": [{"id": "z-model"}, {"id": "a-model"}, {"id": "a-model"}, None, {"id": 123}]}
                    if paginated:
                        payload.update(has_more=len(calls) == 1, last_id="z-model")
                        if len(calls) == 2:
                            self.assertEqual(kwargs["params"]["after_id"], "z-model")
                    status = 404 if service == "deepseek" and len(calls) == 1 else 200
                    return httpx.Response(status, json=payload, request=httpx.Request("GET", url))

                with patch("bosshunter.ai.credentials.httpx.get", side_effect=get):
                    result = list_ai_models({"ai": {"service": service, "base_url": base, "api_key": "test-secret"}})
                self.assertEqual(result, ["a-model", "z-model"])
                self.assertEqual([call[0] for call in calls], urls)
                for _, kwargs in calls:
                    self.assertFalse(kwargs["follow_redirects"])
                    self.assertFalse(kwargs["trust_env"])
                    self.assertEqual(kwargs["headers"].get("x-api-key" if paginated else "Authorization"), "test-secret" if paginated else "Bearer test-secret")

    def test_failures_are_safe_and_empty_list_is_valid(self):
        config = {"ai": {"service": "custom", "base_url": "https://gateway.example/v1", "api_key": "test-secret"}}
        for status, payload, kind in [
            (401, {"error": "test-secret"}, "auth"),
            (429, {"error": "test-secret"}, "rate_limit"),
            (404, {}, "unsupported"),
            (200, {"data": {}}, "invalid_response"),
            (200, [], "invalid_response"),
            (302, {}, "request_failed"),
        ]:
            with self.subTest(status=status, payload=payload):
                response = httpx.Response(status, json=payload, request=httpx.Request("GET", config["ai"]["base_url"]))
                with patch("bosshunter.ai.credentials.httpx.get", return_value=response), self.assertRaises(AIRequestError) as error:
                    list_ai_models(config)
                self.assertEqual(error.exception.kind, kind)
                self.assertNotIn("test-secret", str(error.exception))
        with patch("bosshunter.ai.credentials.httpx.get", side_effect=httpx.ReadTimeout("test-secret")), self.assertRaises(AIRequestError) as error:
            list_ai_models(config)
        self.assertEqual(error.exception.kind, "network")
        self.assertNotIn("test-secret", str(error.exception))
        response = httpx.Response(200, json={"data": []}, request=httpx.Request("GET", config["ai"]["base_url"]))
        with patch("bosshunter.ai.credentials.httpx.get", return_value=response):
            self.assertEqual(list_ai_models(config), [])
        with patch.dict("os.environ", {}, clear=True), patch("bosshunter.ai.credentials.httpx.get") as get:
            for base in ("", "file:///tmp/models", "https://user:secret@example.com", "https://example.com?key=secret"):
                with self.subTest(base=base), self.assertRaises(AIRequestError):
                    list_ai_models({"ai": {"service": "custom", "base_url": base}})
            with self.assertRaises(AIRequestError):
                list_ai_models({"ai": {"service": "custom", "base_url": "https://example.com"}})
            get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
