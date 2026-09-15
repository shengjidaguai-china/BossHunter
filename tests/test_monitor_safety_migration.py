import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from bosshunter.db import add_history, get_db, insert_job, update_job_status


def _job(job_id: str) -> dict:
    return {
        "id": job_id,
        "title": "AI产品经理",
        "company": "Example",
        "salary": "20-30K",
        "city": "杭州",
        "experience": "3-5年",
        "jd": "负责AI产品规划与落地",
        "hr_name": "HR",
        "hr_title": "招聘者",
        "hr_active": "",
        "company_size": "",
        "company_industry": "",
        "url": "https://example.com/job",
    }


class ResumeRequestLifecycleTests(unittest.TestCase):
    def test_explicit_request_is_detected_but_receipt_is_not(self):
        from bosshunter.executor import monitor

        for text in (
            "麻烦提供一份个人简历",
            "简历可以发我一下吗",
            "能不能投送下附件简历？",
            "希望看看你的简历",
        ):
            with self.subTest(text=text):
                self.assertTrue(
                    monitor._detect_resume_request([{"sender": "hr", "text": text}])
                )

        for text in (
            "简历已收到，后续有结果联系你。",
            "谢谢，简历已转给面试官评审。",
            "看过简历了，目前和岗位不太匹配。",
        ):
            with self.subTest(text=text):
                self.assertFalse(
                    monitor._detect_resume_request([{"sender": "hr", "text": text}])
                )

    def test_request_survives_unrelated_reply_until_resolved(self):
        from bosshunter.executor import monitor

        request = {
            "sender": "hr",
            "text": "我想要一份您的附件简历，您是否同意",
            "kind": "resume_request_card",
        }
        pending = [
            request,
            {"sender": "me", "text": "周末也可以调休吗？", "kind": "message"},
            {"sender": "hr", "text": "对啊", "kind": "message"},
        ]

        self.assertTrue(monitor._detect_resume_request(pending))
        detail = json.loads(
            monitor._build_reply_detail(pending, "待手动发送", "needs_resume.v1")
        )
        self.assertIn("附件简历", detail["hr_question"])

        resolved_conversations = (
            [request, {"sender": "me", "text": "附件简历已经发您了。"}],
            [request, {"sender": "hr", "text": "已收到您的简历，我们会尽快查看。"}],
            [request, {"sender": "hr", "text": "暂时不用发简历了。"}],
        )
        for messages in resolved_conversations:
            with self.subTest(messages=messages):
                self.assertFalse(monitor._detect_resume_request(messages))
                self.assertFalse(monitor._has_resume_request_card(messages))

    def test_unknown_request_is_reconciled_without_promoting_receipts(self):
        from bosshunter.executor import monitor

        request = monitor._reconcile_conversation_messages(
            [{"sender": "unknown", "text": "方便把最新简历发我一下吗？"}],
            {"greeting": ""},
        )
        receipt = monitor._reconcile_conversation_messages(
            [{"sender": "unknown", "text": "简历已收到，后续有结果联系你。"}],
            {"greeting": ""},
        )

        self.assertEqual(request[0]["sender"], "hr")
        self.assertTrue(monitor._detect_resume_request(request))
        self.assertEqual(receipt[0]["sender"], "unknown")
        self.assertFalse(monitor._detect_resume_request(receipt))


class FollowUpSafetyTests(unittest.TestCase):
    def test_history_reply_blocks_follow_up_across_monitor_runs(self):
        from bosshunter.executor import monitor

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "data" / "bosshunter.db"
            db = get_db(db_path)
            try:
                insert_job(db, _job("job-history-guard"))
                update_job_status(db, "job-history-guard", "sent")
                db.execute(
                    "UPDATE jobs SET updated_at = datetime('now', '-72 hours') WHERE id = ?",
                    ("job-history-guard",),
                )
                detail = monitor._build_reply_detail(
                    [{"sender": "hr", "text": "方便介绍一下你的项目吗？"}],
                    "",
                    "hr_replied.v1",
                )
                add_history(db, "job-history-guard", "replied", detail)
                db.commit()
            finally:
                db.close()

            def open_db():
                return get_db(db_path)

            with patch.object(monitor, "get_db", side_effect=open_db), \
                 patch.object(monitor, "_open_conversation") as open_conversation, \
                 patch.object(monitor, "_generate_follow_up") as generate_follow_up:
                count = monitor._check_follow_ups(
                    {
                        "follow_up": {
                            "enabled": True,
                            "skip_weekends": False,
                            "interval_hours": 1,
                        }
                    },
                    Mock(),
                )

            verify_db = get_db(db_path)
            try:
                status = verify_db.execute(
                    "SELECT status FROM jobs WHERE id = ?",
                    ("job-history-guard",),
                ).fetchone()["status"]
            finally:
                verify_db.close()

        self.assertEqual(count, 0)
        self.assertEqual(status, "replied")
        open_conversation.assert_not_called()
        generate_follow_up.assert_not_called()

    def test_loaded_conversation_reply_blocks_follow_up_before_generation(self):
        from bosshunter.executor import monitor

        messages = [
            {"sender": "me", "text": "你好，我对岗位感兴趣。"},
            {"sender": "hr", "text": "方便介绍一下你的项目吗？"},
            {"sender": "me", "text": "可以，我整理后发您。"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "data" / "bosshunter.db"
            db = get_db(db_path)
            try:
                insert_job(db, _job("job-live-guard"))
                update_job_status(db, "job-live-guard", "sent")
                db.execute(
                    "UPDATE jobs SET updated_at = datetime('now', '-72 hours') WHERE id = ?",
                    ("job-live-guard",),
                )
                db.commit()
            finally:
                db.close()

            def open_db():
                return get_db(db_path)

            with patch.object(monitor, "get_db", side_effect=open_db), \
                 patch.object(monitor, "_open_conversation", return_value="target-1"), \
                 patch.object(monitor, "evaluate", return_value=json.dumps(messages, ensure_ascii=False)), \
                 patch.object(monitor, "close_tab") as close_tab, \
                 patch.object(monitor, "_generate_follow_up") as generate_follow_up, \
                 patch.object(monitor, "_send_message_in_chat") as send_message, \
                 patch.object(monitor, "_wait_or_stop", return_value=False):
                count = monitor._check_follow_ups(
                    {
                        "follow_up": {
                            "enabled": True,
                            "skip_weekends": False,
                            "interval_hours": 1,
                        }
                    },
                    Mock(),
                )

            verify_db = get_db(db_path)
            try:
                status = verify_db.execute(
                    "SELECT status FROM jobs WHERE id = ?",
                    ("job-live-guard",),
                ).fetchone()["status"]
            finally:
                verify_db.close()

        self.assertEqual(count, 0)
        self.assertEqual(status, "replied")
        generate_follow_up.assert_not_called()
        send_message.assert_not_called()
        close_tab.assert_called_once_with("target-1")


if __name__ == "__main__":
    unittest.main()
