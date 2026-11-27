import json
import tempfile
import unittest
from pathlib import Path

from bosshunter.agent_api import AgentRequestError, agent_preferences, apply_preferences
from bosshunter.config import load_config
from bosshunter.db import get_db, insert_job
from bosshunter.job_export import export_jobs
from bosshunter.web import server


def _job(job_id: str, hr_active: str = "") -> dict:
    return {
        "id": job_id,
        "title": "全栈工程师",
        "company": "示例科技",
        "salary": "15-25K",
        "city": "深圳",
        "experience": "1-3年",
        "jd": "负责前后端开发",
        "hr_name": "张经理",
        "hr_title": "HR",
        "hr_active": hr_active,
        "company_size": "100-499人",
        "company_industry": "互联网",
        "url": f"https://www.zhipin.com/job_detail/{job_id}.html",
    }


class HrActiveSearchAndConfigTests(unittest.TestCase):
    def setUp(self):
        self.original_base_dir = server.BASE_DIR

    def tearDown(self):
        server.set_base_dir(self.original_base_dir)

    def _request(self, path: str, method: str = "GET", json_body: dict | None = None):
        from io import BytesIO, StringIO

        body_bytes = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        query_string = ""
        path_info = path
        if "?" in path:
            path_info, query_string = path.split("?", 1)
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path_info,
            "QUERY_STRING": query_string,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body_bytes)),
            "wsgi.input": BytesIO(body_bytes),
            "wsgi.errors": StringIO(),
            "wsgi.url_scheme": "http",
            "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "8686",
        }
        captured = {}

        def start_response(status, headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = headers

        chunks = b"".join(server.app(environ, start_response))
        return captured["status"], captured["headers"], chunks.decode("utf-8")

    def test_search_and_export_filter_and_sort_by_hr_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            db = get_db(base_dir / "data" / "bosshunter.db")
            try:
                for job_id, label in (
                    ("j-online", "在线"),
                    ("j-week", "3日内活跃"),
                    ("j-month", "2周内活跃"),
                    ("j-old", "半年前活跃"),
                    ("j-unknown", ""),
                ):
                    insert_job(db, _job(job_id, hr_active=label))
                exported_csv, _, _ = export_jobs(
                    db,
                    format="csv",
                    scope="filtered",
                    filters={"hr_active": ["online", "week"]},
                )
            finally:
                db.close()

            self.assertIn("j-online", exported_csv.decode("utf-8-sig"))
            self.assertIn("j-week", exported_csv.decode("utf-8-sig"))
            self.assertNotIn("j-month", exported_csv.decode("utf-8-sig"))
            self.assertNotIn("j-old", exported_csv.decode("utf-8-sig"))

            server.set_base_dir(base_dir)
            status, _, body = self._request("/api/jobs/search?hr_active=online&hr_active=unknown")
            self.assertTrue(status.startswith("200"), body)
            ids = [item["id"] for item in json.loads(body)["items"]]
            self.assertEqual(set(ids), {"j-online", "j-unknown"})

            status, _, body = self._request("/api/jobs/search?sort_by=hr_active&sort_order=desc")
            self.assertTrue(status.startswith("200"), body)
            sorted_ids = [item["id"] for item in json.loads(body)["items"]]
            self.assertEqual(sorted_ids, ["j-online", "j-week", "j-month", "j-old", "j-unknown"])

            status, _, body = self._request("/api/jobs/search?hr_active=invalid_tier")
            self.assertTrue(status.startswith("400"), body)

            status, _, body = self._request("/api/jobs/search?hr_active=online&hr_active=week&ids_only=1")
            self.assertTrue(status.startswith("200"), body)
            payload = json.loads(body)
            self.assertEqual(payload["total"], 2)
            self.assertEqual(set(payload["ids"]), {"j-online", "j-week"})

    def test_config_and_agent_api_validate_min_hr_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            server.set_base_dir(Path(tmp))
            status, _, body = self._request("/api/config", "POST", {"profile": {"min_hr_active": "week"}})
            self.assertTrue(status.startswith("200"), body)
            status, _, body = self._request("/api/config")
            self.assertEqual(json.loads(body)["profile"]["min_hr_active"], "week")

            status, _, body = self._request("/api/config", "POST", {"profile": {"min_hr_active": "bad"}})
            self.assertTrue(status.startswith("400"), body)

        cfg = load_config()
        updated, _ = apply_preferences(cfg, {"min_hr_active": "today"})
        self.assertEqual(agent_preferences(updated)["min_hr_active"], "today")
        with self.assertRaises(AgentRequestError):
            apply_preferences(cfg, {"min_hr_active": "invalid"})


if __name__ == "__main__":
    unittest.main()
