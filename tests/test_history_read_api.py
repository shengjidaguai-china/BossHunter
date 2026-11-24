import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bosshunter.db import add_history, get_db, insert_job
from bosshunter.web import server


def _job(job_id: str) -> dict:
    return {
        "id": job_id,
        "title": f"Role {job_id}",
        "company": f"Corp {job_id}",
        "salary": "150-200元/天",
        "city": "广州",
        "experience": "在校/应届",
        "jd": "AI Agent internship",
        "hr_name": "HR",
        "hr_title": "Recruiter",
        "hr_active": "",
        "company_size": "",
        "company_industry": "",
        "url": f"https://example.com/job/{job_id}",
    }


class HistoryReadApiTests(unittest.TestCase):
    def setUp(self):
        self.original_base_dir = server.BASE_DIR

    def tearDown(self):
        server.set_base_dir(self.original_base_dir)

    def _request(self, path: str, method: str = "GET", json_body: dict | None = None):
        if "?" in path:
            path_info, query_string = path.split("?", 1)
        else:
            path_info, query_string = path, ""

        status_headers = {}

        def start_response(status, headers, exc_info=None):
            status_headers["status"] = status
            status_headers["headers"] = dict(headers)

        request_body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "REQUEST_METHOD": method,
            "PATH_INFO": path_info,
            "QUERY_STRING": query_string,
            "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "8686",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(request_body),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }
        if json_body is not None:
            environ["CONTENT_LENGTH"] = str(len(request_body))
            environ["CONTENT_TYPE"] = "application/json"

        response_iter = server.app(environ, start_response)
        try:
            body = b"".join(
                chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
                for chunk in response_iter
            ).decode("utf-8")
        finally:
            close = getattr(response_iter, "close", None)
            if close:
                close()
        return status_headers["status"], status_headers["headers"], body

    def test_unread_history_and_mark_all_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            db = get_db(base_dir / "data" / "bosshunter.db")
            try:
                insert_job(db, _job("h1"))
                insert_job(db, _job("h2"))
                insert_job(db, _job("h3"))
                add_history(db, "h1", "sent", "first")
                add_history(db, "h2", "replied", "second")
                ids = [
                    r["id"]
                    for r in db.execute("SELECT id FROM history ORDER BY id ASC").fetchall()
                ]
                self.assertEqual(len(ids), 2)
                id2 = ids[1]
            finally:
                db.close()

            server.set_base_dir(base_dir)

            status, _, body = self._request("/api/history?limit=10&unread_only=1")
            self.assertTrue(status.startswith("200"), body)
            unread_before = json.loads(body)
            self.assertEqual(len(unread_before), 2)

            status, _, body = self._request("/api/history/read-all", "POST", {"max_id": id2})
            self.assertTrue(status.startswith("200"), body)
            self.assertEqual(json.loads(body), {"success": True, "marked_count": 2})

            status, _, body = self._request("/api/history?limit=10&unread_only=1")
            self.assertTrue(status.startswith("200"), body)
            self.assertEqual(json.loads(body), [])

            # Monitor endpoint (without unread_only) still returns full history.
            status, _, body = self._request("/api/history?limit=10")
            self.assertTrue(status.startswith("200"), body)
            self.assertEqual(len(json.loads(body)), 2)

            # A newly created activity after max_id still appears as unread.
            db = get_db(base_dir / "data" / "bosshunter.db")
            try:
                add_history(db, "h3", "scored", "third")
            finally:
                db.close()

            status, _, body = self._request("/api/history?limit=10&unread_only=1")
            self.assertTrue(status.startswith("200"), body)
            unread_after = json.loads(body)
            self.assertEqual([item["job_id"] for item in unread_after], ["h3"])

            # Empty body marks all remaining unread rows as read.
            status, _, body = self._request("/api/history/read-all", "POST", {})
            self.assertTrue(status.startswith("200"), body)
            self.assertEqual(json.loads(body), {"success": True, "marked_count": 1})

            status, _, body = self._request("/api/history?limit=10&unread_only=1")
            self.assertTrue(status.startswith("200"), body)
            self.assertEqual(json.loads(body), [])

    def test_mark_read_rejects_invalid_max_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            db = get_db(base_dir / "data" / "bosshunter.db")
            db.close()
            server.set_base_dir(base_dir)
            for bad in ("abc", 0, -5, True):
                with self.subTest(bad=bad):
                    status, _, body = self._request("/api/history/read-all", "POST", {"max_id": bad})
                    self.assertTrue(status.startswith("400"), body)
                    self.assertIn("error", json.loads(body))

    def test_existing_history_table_without_read_at_migrates_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "legacy.db"
            raw = sqlite3.connect(db_path)
            raw.executescript(
                """
                CREATE TABLE jobs (id TEXT PRIMARY KEY, title TEXT, company TEXT, salary TEXT, city TEXT, experience TEXT, jd TEXT, hr_name TEXT, hr_title TEXT, hr_active TEXT, company_size TEXT, company_industry TEXT, url TEXT, score INTEGER DEFAULT 0, score_reason TEXT, greeting TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, action TEXT NOT NULL, detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE risk_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE platform_access_events (id INTEGER PRIMARY KEY AUTOINCREMENT, stage TEXT NOT NULL, action TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE platform_safety_state (id INTEGER PRIMARY KEY CHECK (id = 1), reason TEXT NOT NULL, locked_until TEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                """
            )
            raw.execute("INSERT INTO jobs (id, title, company) VALUES ('legacy-1', 'AI', 'Co')")
            raw.execute("INSERT INTO history (job_id, action, detail) VALUES ('legacy-1', 'sent', 'ok')")
            raw.commit()
            raw.close()

            migrated = get_db(db_path)
            try:
                cols = {row[1] for row in migrated.execute("PRAGMA table_info(history)").fetchall()}
                self.assertIn("read_at", cols)
                row = migrated.execute("SELECT read_at FROM history WHERE job_id = 'legacy-1'").fetchone()
                self.assertIsNone(row["read_at"])
            finally:
                migrated.close()
