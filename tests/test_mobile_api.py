"""API tests for mobile endpoints."""

import io
import json
import unittest
from bosshunter.web.server import app


class MobileApiTests(unittest.TestCase):
    def setUp(self):
        self.app = app

    def _make_env(self, path: str):
        return {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "HTTP_HOST": "127.0.0.1:8686",
            "wsgi.errors": io.StringIO(),
            "wsgi.input": io.BytesIO(),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
        }

    def test_mobile_info_api_returns_lan_and_url(self):
        env = self._make_env("/api/mobile/info")
        res_status = []
        def start_response(status, headers, exc_info=None):
            res_status.append(status)
            return lambda _: None

        body = self.app(env, start_response)
        self.assertTrue(res_status[0].startswith("200"))
        data = json.loads(b"".join(body).decode("utf-8"))
        self.assertIn("primary_ip", data)
        self.assertIn("mobile_url", data)
        self.assertTrue(data["mobile_url"].startswith("http://"))
        self.assertIn(":8686", data["mobile_url"])

    def test_mobile_qrcode_api_returns_png_image(self):
        env = self._make_env("/api/mobile/qrcode")
        res_status = []
        content_type = []
        def start_response(status, headers, exc_info=None):
            res_status.append(status)
            for k, v in headers:
                if k.lower() == "content-type":
                    content_type.append(v)
            return lambda _: None

        body = self.app(env, start_response)
        self.assertTrue(res_status[0].startswith("200"))
        raw_bytes = b"".join(body)
        self.assertTrue(len(raw_bytes) > 100)
        self.assertEqual(content_type, ["image/png"])
        # PNG 文件头标识: 89 50 4E 47 0D 0A 1A 0A
        self.assertEqual(raw_bytes[:8], b"\x89PNG\r\n\x1a\n")
