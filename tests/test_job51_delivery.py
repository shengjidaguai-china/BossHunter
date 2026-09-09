import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bosshunter.db import get_db, insert_job, update_job_score, update_job_status
from bosshunter.executor import job51_sender
from bosshunter.web import server
from bosshunter.web.tasks import WorkbenchTask


def _job51(job_id: str = "51job:173263084") -> dict:
    return {
        "id": job_id,
        "title": "AI 工程师",
        "company": "示例公司",
        "salary": "20-30K",
        "city": "杭州",
        "jd": "负责大模型应用",
        "url": "https://jobs.51job.com/all/173263084.html",
        "status": "ready",
        "source_platform": "51job",
        "source_job_id": job_id.split(":", 1)[-1],
    }


class ApplyJob51OnceTests(unittest.TestCase):
    def test_clicks_apply_and_records_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = get_db(Path(tmp) / "bosshunter.db")
            try:
                job = _job51()
                insert_job(db, job)
                scan = json.dumps({"kind": "action_ready", "text": "立即申请"})
                click = json.dumps({"clicked": True, "text": "立即申请"})
                success = json.dumps({"kind": "success"})
                with (
                    mock.patch.object(job51_sender, "new_tab", return_value="target-51"),
                    mock.patch.object(job51_sender, "wait_for_load", return_value=True),
                    mock.patch.object(job51_sender, "evaluate", side_effect=[scan, click, success]),
                    mock.patch.object(job51_sender, "close_tab", return_value=True) as close_tab,
                    mock.patch.object(job51_sender, "_sleep_or_stop", return_value=False),
                ):
                    outcome = job51_sender.apply_job51_once(job, {"safety": {}}, None, db)
            finally:
                db.close()
        self.assertTrue(outcome["success"])
        close_tab.assert_called_once_with("target-51")

    def test_selects_online_resume_in_dialog(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = get_db(Path(tmp) / "bosshunter.db")
            try:
                job = _job51()
                insert_job(db, job)
                scan = json.dumps({"kind": "resume_ready", "resumeCount": 1})
                handled = json.dumps({"handled": True, "selected": True})
                success = json.dumps({"kind": "already_applied"})
                with (
                    mock.patch.object(job51_sender, "new_tab", return_value="target-51"),
                    mock.patch.object(job51_sender, "wait_for_load", return_value=True),
                    mock.patch.object(job51_sender, "evaluate", side_effect=[scan, handled, success]),
                    mock.patch.object(job51_sender, "close_tab", return_value=True),
                    mock.patch.object(job51_sender, "_sleep_or_stop", return_value=False),
                ):
                    outcome = job51_sender.apply_job51_once(job, {"safety": {}}, None, db)
            finally:
                db.close()
        self.assertTrue(outcome["success"])
        self.assertTrue(outcome["already_sent"])

    def test_waits_for_waf_then_applies(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = get_db(Path(tmp) / "bosshunter.db")
            try:
                job = _job51()
                insert_job(db, job)
                waf = json.dumps({"kind": "waf"})
                ready = json.dumps({"kind": "action_ready", "text": "申请职位"})
                click = json.dumps({"clicked": True, "text": "申请职位"})
                success = json.dumps({"kind": "success"})
                with (
                    mock.patch.object(job51_sender, "new_tab", return_value="target-51"),
                    mock.patch.object(job51_sender, "wait_for_load", return_value=True),
                    mock.patch.object(job51_sender, "evaluate", side_effect=[waf, ready, click, success]),
                    mock.patch.object(job51_sender, "close_tab", return_value=True),
                    mock.patch.object(job51_sender, "_sleep_or_stop", return_value=False),
                    mock.patch.object(job51_sender, "_notify"),
                ):
                    outcome = job51_sender.apply_job51_once(job, {"safety": {}}, None, db)
            finally:
                db.close()
        self.assertTrue(outcome["success"])

    def test_scan_script_recognizes_div_apply_buttons(self):
        for script in (job51_sender.JS_SCAN, job51_sender.JS_CLICK_APPLY, job51_sender.JS_HANDLE_RESUME):
            self.assertIn('[class*="apply"]', script)
            self.assertIn('立即投递', script)
        self.assertIn('apply-btn', job51_sender.JS_CLICK_APPLY)

    def test_rejects_unsafe_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = get_db(Path(tmp) / "bosshunter.db")
            try:
                job = _job51()
                job["url"] = "https://example.com/phishing"
                outcome = job51_sender.apply_job51_once(job, {"safety": {}}, None, db)
            finally:
                db.close()
        self.assertFalse(outcome["success"])
        self.assertEqual(outcome["error"], "unsafe_job_url")


class DeliverJob51Tests(unittest.TestCase):
    def test_marks_selected_jobs_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bosshunter.db"
            db = get_db(db_path)
            try:
                job = _job51()
                insert_job(db, job)
                update_job_status(db, job["id"], "approved")
            finally:
                db.close()
            config = {
                "_workbench_db_path": str(db_path),
                "_workbench_job_ids": [job["id"]],
                "throttle": {"daily_limit": 10, "send_windows": ["00:00-23:59"], "day_off_probability": 0},
            }
            with mock.patch.object(
                job51_sender,
                "apply_job51_once",
                return_value={"success": True, "history_detail": "页面显示投递成功"},
            ):
                report = job51_sender.deliver_job51(config)
            db = get_db(db_path)
            try:
                status = db.execute("SELECT status FROM jobs WHERE id = ?", (job["id"],)).fetchone()["status"]
                sent = db.execute("SELECT COUNT(*) AS cnt FROM history WHERE action='sent'").fetchone()["cnt"]
            finally:
                db.close()
        self.assertEqual(report["sent_count"], 1)
        self.assertEqual(status, "sent")
        self.assertEqual(sent, 1)


class DeliverBatchSplitTests(unittest.TestCase):
    def test_regular_deliver_sends_boss_and_applies_51job(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            db = get_db(base_dir / "data" / "bosshunter.db")
            try:
                insert_job(db, {
                    "id": "boss-1",
                    "title": "产品经理",
                    "company": "BOSS公司",
                    "jd": "JD",
                    "url": "https://www.zhipin.com/job_detail/boss.html",
                })
                update_job_score(db, "boss-1", 88, "匹配")
                update_job_status(db, "boss-1", "approved")
                insert_job(db, _job51("51job:1"))
                update_job_score(db, "51job:1", 90, "匹配")
                update_job_status(db, "51job:1", "approved")
            finally:
                db.close()
            server.set_base_dir(base_dir)
            task = WorkbenchTask(id="deliver-1", mode="deliver", label="投递")
            greet_config = {}
            send_config = {}
            apply_config = {}

            def fake_greet(config):
                greet_config["job_ids"] = list(config.get("_workbench_job_ids", []))
                return len(config.get("_workbench_job_ids", []))

            def fake_send(config, force=False):
                send_config["job_ids"] = list(config.get("_workbench_job_ids", []))
                send_config["force"] = force
                config["_workbench_send_report"] = {"sent_count": 1, "failed_count": 0, "deferred_count": 0}
                return 1

            def fake_apply(config):
                apply_config["job_ids"] = list(config.get("_workbench_job_ids", []))
                config["_workbench_send_report"] = {"sent_count": 1, "failed_count": 0, "deferred_count": 0}
                return config["_workbench_send_report"]

            with (
                mock.patch("bosshunter.ai.greeter.generate_greetings", side_effect=fake_greet),
                mock.patch("bosshunter.executor.sender.send_greetings", side_effect=fake_send),
                mock.patch("bosshunter.executor.job51_sender.deliver_job51", side_effect=fake_apply),
            ):
                server._execute_deliver_batch(task, {"_workbench_job_ids": ["boss-1", "51job:1"]})
        self.assertEqual(greet_config["job_ids"], ["boss-1"])
        self.assertEqual(send_config["job_ids"], ["boss-1"])
        self.assertEqual(apply_config["job_ids"], ["51job:1"])
        self.assertEqual(task.metrics["send_success"], 2)


if __name__ == "__main__":
    unittest.main()
