"""招呼语生成并发：并发窗口、结果落库与串行回退。"""

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from bosshunter.ai import greeter
from bosshunter.ai.greeter import MAX_GREETING_CONCURRENCY, get_greeting_concurrency
from bosshunter.db import get_db as open_db
from bosshunter.db import insert_job, update_job_status


def _job(job_id: str) -> dict:
    return {
        "id": job_id,
        "title": f"全栈开发工程师 {job_id}",
        "company": f"公司 {job_id}",
        "salary": "15-25K",
        "experience": "1-3年",
        "jd": "负责前后端开发与 AI 应用落地。" * 80,
        "score_reason": "技能匹配",
    }


class GreetingConcurrencyConfigTests(unittest.TestCase):
    def test_default_is_serial(self):
        self.assertEqual(get_greeting_concurrency({}), 1)
        self.assertEqual(get_greeting_concurrency({"ai": {}}), 1)

    def test_user_value_is_honoured_up_to_the_safety_ceiling(self):
        self.assertEqual(get_greeting_concurrency({"ai": {"greeting_concurrency": 8}}), 8)
        self.assertEqual(
            get_greeting_concurrency({"ai": {"greeting_concurrency": 99}}),
            MAX_GREETING_CONCURRENCY,
        )
        self.assertEqual(get_greeting_concurrency({"ai": {"greeting_concurrency": 0}}), 1)
        self.assertEqual(get_greeting_concurrency({"ai": {"greeting_concurrency": "invalid"}}), 1)


class GreetingConcurrencyRunTests(unittest.TestCase):
    """端到端跑真实 SQLite，只把 AI 调用换成可控的假实现。"""

    def _run_batch(self, db_path, config, job_ids, fake_call):
        with (
            patch("bosshunter.ai.greeter.get_db", side_effect=lambda *a, **k: open_db(db_path)),
            patch(
                "bosshunter.ai.greeter.get_jobs_by_status",
                side_effect=lambda db_, status: [
                    dict(row)
                    for row in db_.execute(
                        "SELECT * FROM jobs WHERE status = ? AND deleted_at IS NULL", (status,)
                    ).fetchall()
                ],
            ),
            patch("bosshunter.ai.greeter._get_resume_summary", return_value="真实简历摘要，不含网址。"),
            patch("bosshunter.ai.greeter._call_claude", side_effect=fake_call),
        ):
            return greeter.generate_greetings(config, job_ids=job_ids, db_path=db_path)

    def _prepare(self, tmp, ids):
        db_path = Path(tmp) / "data" / "bosshunter.db"
        db = open_db(db_path)
        try:
            for job_id in ids:
                insert_job(db, _job(job_id))
                update_job_status(db, job_id, "approved")
        finally:
            db.close()
        return db_path

    def _read_greetings(self, db_path):
        db = open_db(db_path)
        try:
            return {
                row["id"]: row["greeting"]
                for row in db.execute("SELECT id, greeting FROM jobs ORDER BY id").fetchall()
            }
        finally:
            db.close()

    def test_concurrent_batch_saves_every_greeting(self):
        ids = [f"job-{index}" for index in range(6)]
        seen_lock = threading.Lock()
        seen: list[str] = []

        def fake_call(prompt, config, max_tokens=None, purpose=None, **kwargs):
            with seen_lock:
                seen.append(purpose or "greeting")
                index = len(seen)
            time.sleep(0.5)
            return f"你好，我做过第{index}个全栈项目，熟悉 Vue 与 Spring Boot，期待进一步沟通。"

        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._prepare(tmp, ids)
            started = time.time()
            count = self._run_batch(
                db_path,
                {
                    "ai": {"greeting_concurrency": 3, "greeting_max_attempts": 1, "greeting_style_suggestions": False},
                    "profile": {"ai_greeting_enabled": True},
                },
                job_ids=ids,
                fake_call=fake_call,
            )
            elapsed = time.time() - started
            greetings = self._read_greetings(db_path)

        self.assertEqual(count, 6)
        self.assertEqual(len([g for g in greetings.values() if (g or "").strip()]), 6)
        # 六个岗位分两轮跑完；真正并发时总耗时应当明显小于串行的 6×0.5s。
        self.assertLess(elapsed, 2.5)

    def test_serial_fallback_still_works(self):
        ids = [f"serial-{index}" for index in range(3)]

        def fake_call(prompt, config, max_tokens=None, purpose=None, **kwargs):
            return "你好，我做过后端与前端开发，期待进一步沟通。"

        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._prepare(tmp, ids)
            count = self._run_batch(
                db_path,
                {"ai": {"greeting_concurrency": 1, "greeting_max_attempts": 1}, "profile": {"ai_greeting_enabled": True}},
                job_ids=ids,
                fake_call=fake_call,
            )
            greetings = self._read_greetings(db_path)

        self.assertEqual(count, 3)
        self.assertTrue(all((greetings[job_id] or "").strip() for job_id in ids))

    def test_service_failure_pauses_and_keeps_saved_drafts(self):
        from bosshunter.ai.credentials import AIRequestError

        ids = [f"fail-{index}" for index in range(4)]
        calls = {"n": 0}
        lock = threading.Lock()

        def fake_call(prompt, config, max_tokens=None, purpose=None, **kwargs):
            with lock:
                calls["n"] += 1
                first = calls["n"] == 1
            if first:
                return "你好，我做过订单系统与前端开发，期待沟通。"
            raise AIRequestError("rate_limit", "AI 服务触发请求或 Token 频率限制")

        with tempfile.TemporaryDirectory() as tmp:
            db_path = self._prepare(tmp, ids)
            logs: list[str] = []
            count = self._run_batch(
                db_path,
                {
                    "ai": {"greeting_concurrency": 1, "greeting_max_attempts": 1},
                    "profile": {"ai_greeting_enabled": True},
                    "_workbench_log": logs.append,
                },
                job_ids=ids,
                fake_call=fake_call,
            )
            greetings = self._read_greetings(db_path)

        # 服务级故障必须暂停整批并显性上报，已生成的草稿不能丢。
        self.assertEqual(count, 1)
        self.assertEqual(len([g for g in greetings.values() if (g or "").strip()]), 1)
        self.assertTrue(any("频率限制" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
