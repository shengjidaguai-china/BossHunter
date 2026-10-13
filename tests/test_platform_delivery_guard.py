import io
import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from bosshunter.db import get_db, insert_job
from bosshunter.web import server


class PlatformDeliveryGuardTests(TestCase):
    def setUp(self):
        self.original_base_dir = server.BASE_DIR

    def tearDown(self):
        server.set_base_dir(self.original_base_dir)

    @staticmethod
    def _request(path: str, body: dict | None = None):
        raw = json.dumps(body or {}).encode("utf-8")
        result = {}

        def start_response(status, headers, exc_info=None):
            result["status"] = status
            result["headers"] = dict(headers)

        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "8686",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(raw),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }
        payload = b"".join(
            chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
            for chunk in server.app(environ, start_response)
        ).decode("utf-8")
        return result["status"], json.loads(payload)

    def test_native_platforms_reject_unreviewed_jobs_and_chat_resume_routes(self):
        for platform, job_id, url in (
            ("zhilian", "zhilian:zl-1", "https://www.zhaopin.com/jobdetail/zl-1.htm"),
            ("51job", "51job:job-1", "https://jobs.51job.com/shanghai/job-1.html"),
            ("liepin", "liepin:job-1", "https://www.liepin.com/job/1.shtml"),
        ):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                db = get_db(base_dir / "data" / "bosshunter.db")
                try:
                    insert_job(db, {
                        "id": job_id,
                        "title": "采集岗位",
                        "company": "示例公司",
                        "jd": "JD",
                        "url": url,
                        "source_platform": platform,
                        "source_job_id": job_id.split(":", 1)[1],
                    })
                finally:
                    db.close()
                server.set_base_dir(base_dir)

                with mock.patch.object(server.task_runner, "start") as start:
                    deliver_status, deliver_payload = self._request(
                        "/api/workbench/deliver",
                        {"job_ids": [job_id]},
                    )
                resume_status, resume_payload = self._request(f"/api/jobs/{job_id}/mark-resume-sent")

                self.assertTrue(deliver_status.startswith("409"), deliver_payload)
                self.assertTrue(resume_status.startswith("403"), resume_payload)
                start.assert_not_called()

    def test_confirmed_native_delivery_does_not_require_a_greeting_or_ai(self):
        for platform in ("zhilian", "51job", "liepin"):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                base_dir = Path(tmp)
                server.set_base_dir(base_dir)
                db = get_db(base_dir / "data" / "bosshunter.db")
                try:
                    insert_job(db, {"id": platform + ":1", "title": "测试岗位", "company": "测试公司", "source_platform": platform})
                    db.execute("UPDATE jobs SET status='ready', score=90 WHERE id=?", (platform + ":1",))
                    db.commit()
                finally:
                    db.close()
                with mock.patch.object(server.task_runner, "status", return_value={"active": None}), mock.patch.object(
                    server.task_runner, "start", return_value={"id": "mock-native-delivery"}
                ) as start, mock.patch("bosshunter.ai.greeter.greeting_config_error", side_effect=AssertionError("native application must not require AI")):
                    status, payload = self._request("/api/workbench/deliver", {"job_ids": [platform + ":1"]})
                self.assertTrue(status.startswith("200"), payload)
                self.assertEqual(start.call_args.args[1]["_workbench_job_ids"], [platform + ":1"])
                db = get_db(base_dir / "data" / "bosshunter.db")
                try:
                    self.assertEqual(db.execute("SELECT status FROM jobs").fetchone()["status"], "approved")
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM history WHERE action='sent'").fetchone()[0], 0)
                finally:
                    db.close()

    def test_native_batch_skips_greeting_generation(self):
        from bosshunter.web.tasks import WorkbenchTask
        with tempfile.TemporaryDirectory() as tmp:
            server.set_base_dir(Path(tmp))
            db = get_db(Path(tmp) / "data" / "bosshunter.db")
            insert_job(db, {"id": "51job:1", "source_platform": "51job", "title": "测试", "company": "测试"})
            db.close()
            task = WorkbenchTask(id="test", mode="deliver", label="测试")
            with mock.patch("bosshunter.ai.greeter.generate_greetings") as greet, mock.patch("bosshunter.executor.sender.send_greetings", return_value=0) as send:
                server._execute_deliver_batch(task, {"_workbench_job_ids": ["51job:1"]})
            greet.assert_not_called()
            send.assert_called_once()
