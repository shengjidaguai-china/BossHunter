import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bosshunter.db import get_db, insert_job, update_job_greeting, update_job_status
from bosshunter.executor import pilot_sender
from bosshunter.web import server


def _job(job_id: str, platform: str, *, greeting: str = "") -> dict:
    return {
        "id": job_id,
        "title": "AI 产品经理",
        "company": f"公司-{platform}",
        "salary": "20-30K",
        "city": "北京",
        "jd": "负责 AI 产品",
        "url": {
            "boss": "https://www.zhipin.com/job_detail/test.html",
            "zhilian": "https://www.zhaopin.com/jobdetail/zl-test.htm",
            "51job": "https://jobs.51job.com/all/test.html",
        }[platform],
        "status": "ready",
        "source_platform": platform,
        "source_job_id": job_id.split(":", 1)[-1],
        "greeting": greeting if platform == "boss" else "",
    }


def _pilot_config(db_path: Path, job_ids: list[str]) -> dict:
    return {
        "_workbench_db_path": str(db_path),
        "_workbench_job_ids": job_ids,
        "throttle": {
            "daily_limit": 10,
            "send_windows": ["00:00-23:59"],
            "day_off_probability": 0,
        },
        "safety": {"risk_lock_minutes": 1},
    }


class DeliveryPilotAllowedTests(unittest.TestCase):
    def test_pilot_requires_both_delivery_flags(self):
        self.assertFalse(pilot_sender.delivery_pilot_allowed({}))
        self.assertFalse(pilot_sender.delivery_pilot_allowed({
            "delivery": {"auto_apply_pilot_enabled": True},
        }))
        self.assertTrue(pilot_sender.delivery_pilot_allowed({
            "delivery": {
                "auto_apply_pilot_enabled": True,
                "parallel_platforms_enabled": True,
            },
        }))


class ExternalApplyTests(unittest.TestCase):
    def test_external_apply_clicks_confident_button_and_records_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bosshunter.db"
            db = get_db(db_path)
            try:
                job = _job("zhilian:zl-test", "zhilian")
                insert_job(db, job)
            finally:
                db.close()
            scan = json.dumps({"kind": "action_ready"})
            click = json.dumps({"clicked": True})
            confirm = json.dumps({"confirmed": False})
            final = json.dumps({"kind": "success"})
            with (
                mock.patch.object(pilot_sender, "new_tab", return_value="target-1"),
                mock.patch.object(pilot_sender, "wait_for_load", return_value=True),
                mock.patch.object(pilot_sender, "evaluate", side_effect=[scan, click, confirm, final]) as mocked_evaluate,
                mock.patch.object(pilot_sender, "close_tab", return_value=True),
            ):
                db = get_db(db_path)
                try:
                    outcome = pilot_sender._external_apply_once(job, {"safety": {}}, None, db)
                finally:
                    db.close()
            self.assertTrue(outcome["success"])
            self.assertEqual(mocked_evaluate.call_count, 4)

    def test_external_apply_fails_closed_when_no_apply_button(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bosshunter.db"
            db = get_db(db_path)
            try:
                job = _job("51job:job-test", "51job")
                insert_job(db, job)
            finally:
                db.close()
            with mock.patch(
                "bosshunter.executor.job51_sender.apply_job51_once",
                return_value={"success": False, "error": "no_apply_button", "history_detail": "页面未找到可识别的申请按钮"},
            ) as apply_once:
                db = get_db(db_path)
                try:
                    outcome = pilot_sender._external_apply_once(job, {"safety": {}}, None, db)
                finally:
                    db.close()
            self.assertFalse(outcome["success"])
            self.assertEqual(outcome["error"], "no_apply_button")
            apply_once.assert_called_once()


class PilotDeliveryParallelTests(unittest.TestCase):
    def test_three_platform_jobs_are_delivered_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bosshunter.db"
            db = get_db(db_path)
            job_ids = []
            try:
                for platform, greeting in (("boss", "您好，我是候选人。"), ("zhilian", ""), ("51job", "")):
                    job = _job(f"{platform}:{platform}-job", platform, greeting=greeting)
                    job_ids.append(job["id"])
                    insert_job(db, job)
                    update_job_status(db, job["id"], "ready")
                    update_job_greeting(db, job["id"], greeting)
            finally:
                db.close()
            with (
                mock.patch.object(pilot_sender, "_boss_deliver_once", return_value={"success": True, "history_detail": "BOSS ok"}),
                mock.patch.object(pilot_sender, "_external_apply_once", return_value={"success": True, "history_detail": "外部 ok"}),
            ):
                report = pilot_sender.deliver_pilot(_pilot_config(db_path, job_ids))
            db = get_db(db_path)
            try:
                statuses = {
                    str(row["id"]): str(row["status"])
                    for row in db.execute("SELECT id, status FROM jobs WHERE deleted_at IS NULL").fetchall()
                }
                sent_count = int(db.execute(
                    "SELECT COUNT(*) AS cnt FROM history WHERE action='sent'"
                ).fetchone()["cnt"])
            finally:
                db.close()
            self.assertEqual(report["sent_count"], 3)
            self.assertEqual(set(statuses.values()), {"sent"})
            self.assertEqual(sent_count, 3)

    def test_disabled_pilot_route_rejects_without_starting_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            db_path = base_dir / "data" / "bosshunter.db"
            db = get_db(db_path)
            try:
                job = _job("zhilian:disabled", "zhilian")
                insert_job(db, job)
            finally:
                db.close()
            server.set_base_dir(base_dir)
            raw = json.dumps({"job_ids": ["zhilian:disabled"], "confirmed": True}).encode("utf-8")
            result: dict[str, str] = {}

            def start_response(status, headers, exc_info=None):
                result["status"] = status
                result["headers"] = dict(headers)

            environ = {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/api/jobs/auto-deliver-pilot",
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
            with mock.patch.object(server.task_runner, "start") as start:
                body = b"".join(
                    chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
                    for chunk in server.app(environ, start_response)
                ).decode("utf-8")
            self.assertTrue(result["status"].startswith("403"), body)
            start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
