import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from bosshunter.db import get_db, insert_job, update_job_status
from bosshunter.executor import monitor


class ResumeNoticeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        tmp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.path = Path(tmp) / "test.db"
        self.job = {"id": "notice", "company": "Example", "title": "Engineer", "hr_name": "HR"}
        db = get_db(self.path)
        insert_job(db, self.job)
        update_job_status(db, "notice", "sent")
        db.close()
        self.stack.enter_context(patch.object(monitor, "get_db", side_effect=lambda: get_db(self.path)))
        for name, value in [("_open_conversation", "tab"), ("_open_scanned_conversation", None),
                            ("_wait_or_stop", False), ("close_tab", True)]:
            self.stack.enter_context(patch.object(monitor, name, return_value=value))
        self.send = self.stack.enter_context(patch.object(monitor, "_send_message_in_chat"))
        self.generate = self.stack.enter_context(patch("bosshunter.ai.resume.generate_tailored_resume", return_value="test.pdf"))

    def state(self):
        db = get_db(self.path)
        status = db.execute("SELECT status FROM jobs WHERE id = 'notice'").fetchone()[0]
        actions = [r[0] for r in db.execute("SELECT action FROM history WHERE job_id = 'notice'")]
        db.close()
        return status, actions

    def handle(self, messages, preview="附件简历请求已发送"):
        with patch.object(monitor, "evaluate", return_value=json.dumps(messages)):
            return monitor._handle_conversation(self.job, {"monitor": {"auto_reply_hr_questions": True}},
                                                {"last_message": preview, "last_direction": "me"})

    def test_notices_are_not_hr_cards_even_with_old_extractor_kind(self):
        for text in ["附件简历请求已发送", "您的附件简历 test.pdf 已发送给 Boss", "附件简历已发送给对方"]:
            with self.subTest(text=text):
                result = monitor._reconcile_conversation_messages(
                    [{"sender": "system", "kind": "resume_request_card", "text": text}], self.job)
                self.assertEqual(result[0]["sender"], "system")
                self.assertFalse(monitor._looks_like_resume_request_card(text))

    def test_scan_schedules_notice_without_changing_status(self):
        for text in ["附件简历请求已发送", "您的附件简历 test.pdf 已发送给 Boss"]:
            conv = {"hr_name": "HR", "company": "Example", "last_message": text,
                    "has_reply": False, "last_direction": "me"}
            with patch.object(monitor, "_get_monitor_chat_target", return_value=("tab", True)), \
                 patch.object(monitor, "_wait_for_page_or_stop", return_value=True), \
                 patch.object(monitor, "_inspect_monitor_page"), \
                 patch.object(monitor, "evaluate", return_value=json.dumps([conv, conv])):
                result = monitor._check_boss_replies({"monitor": {"max_conversations_per_cycle": 1}})
            self.assertEqual(len(result), 1)
            self.assertEqual(self.state(), ("sent", []))

    def test_request_notice_alone_is_not_proof_or_a_request(self):
        action = self.handle([{"sender": "system", "text": "附件简历请求已发送"}])
        self.assertEqual(action, "skipped_unverified_resume_notice")
        self.assertEqual(self.state(), ("sent", []))
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_full_receipt_is_recorded_once_without_sending(self):
        receipt = "您的附件简历 test.pdf 已发送给 Boss"
        messages = [{"sender": "hr", "text": "请发一份简历"}, {"sender": "system", "text": receipt}]
        self.assertEqual(self.handle(messages, receipt), "recorded_resume_sent")
        self.assertEqual(self.handle(messages, receipt), "skipped_existing_resume")
        self.assertEqual(self.state(), ("resume_sent", ["resume_sent"]))
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_request_card_still_needs_manual_sending(self):
        action = self.handle([{"sender": "hr", "text": "想要一份您的附件简历，是否同意", "kind": "resume_request_card"},
                              {"sender": "system", "text": "附件简历请求已发送"}])
        self.assertEqual(action, "needs_resume")
        self.send.assert_not_called()
        self.generate.assert_called_once()

    def test_old_receipt_does_not_hide_new_request(self):
        action = self.handle([{"sender": "system", "text": "附件简历已发送给对方"},
                              {"sender": "hr", "text": "想要一份您的附件简历，是否同意", "kind": "resume_request_card"}])
        self.assertEqual(action, "needs_resume")
        self.send.assert_not_called()

    def test_receipt_does_not_overwrite_rejected_job(self):
        db = get_db(self.path)
        update_job_status(db, "notice", "rejected")
        db.close()
        self.handle([{"sender": "system", "text": "附件简历已发送给对方"}])
        self.assertEqual(self.state(), ("rejected", []))

    def test_receipt_does_not_overwrite_deleted_job(self):
        db = get_db(self.path)
        db.execute("UPDATE jobs SET deleted_at = CURRENT_TIMESTAMP WHERE id = 'notice'")
        db.commit()
        db.close()
        self.handle([{"sender": "system", "text": "附件简历已发送给对方"}])
        self.assertEqual(self.state(), ("sent", []))

    def test_rejection_is_not_overridden_by_receipt(self):
        action = self.handle([{"sender": "hr", "text": "很遗憾，不合适"},
                              {"sender": "system", "text": "附件简历已发送给对方"}])
        self.assertEqual(action, "rejected")
        self.assertEqual(self.state(), ("rejected", ["rejected"]))

    def test_question_after_receipt_is_still_processed(self):
        with patch.object(monitor, "_generate_auto_reply", return_value="周一") as reply:
            action = self.handle([{"sender": "system", "text": "附件简历已发送给对方"},
                                  {"sender": "hr", "text": "什么时候能面试？"}])
        self.assertEqual(action, "auto_replied")
        reply.assert_called_once()
        self.generate.assert_not_called()

    def test_recorded_receipt_does_not_consume_scan_limit(self):
        db = get_db(self.path)
        update_job_status(db, "notice", "resume_sent")
        db.close()
        conv = {"hr_name": "HR", "company": "Example", "last_message": "附件简历已发送给对方", "has_reply": False}
        with patch.object(monitor, "_get_monitor_chat_target", return_value=("tab", True)), \
             patch.object(monitor, "_wait_for_page_or_stop", return_value=True), \
             patch.object(monitor, "_inspect_monitor_page"), \
             patch.object(monitor, "evaluate", return_value=json.dumps([conv])):
            self.assertEqual(monitor._check_boss_replies({}), [])

    def test_no_fuzzy_receipt_matches(self):
        for text in ["附件简历发送失败", "如果附件简历已发送给对方，请等待", "附件简历请求已发送", "附件简历请求已发送给Boss", "简历已发送"]:
            self.assertNotEqual(monitor._attachment_resume_notice(text), "sent")
