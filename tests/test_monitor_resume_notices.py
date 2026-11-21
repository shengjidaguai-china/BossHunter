import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from bosshunter.db import add_history, get_db, insert_job, update_job_status
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

    def scan(self, conversations):
        with patch.object(monitor, "_get_monitor_chat_target", return_value=("tab", True)), \
             patch.object(monitor, "_wait_for_page_or_stop", return_value=True), \
             patch.object(monitor, "_inspect_monitor_page"), \
             patch.object(monitor, "evaluate", return_value=json.dumps(conversations)):
            return monitor._check_boss_replies({"monitor": {"max_conversations_per_cycle": 1}})

    def notice_preview(self, **overrides):
        return {"hr_name": "HR", "company": "Example", "last_message": "附件简历请求已发送",
                "has_reply": False, "last_direction": "me", **overrides}

    def other_hr_preview(self):
        db = get_db(self.path)
        try:
            insert_job(db, {"id": "other", "company": "Other", "title": "Engineer", "hr_name": "Other HR"})
            update_job_status(db, "other", "sent")
        finally:
            db.close()
        return {"hr_name": "Other HR", "company": "Other", "last_message": "可以明天面试吗？",
                "has_reply": True, "last_direction": "hr"}

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
        self.assertEqual(self.state(), ("sent", ["resume_notice_checked"]))
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_unchanged_unverified_notice_does_not_starve_other_conversations(self):
        preview = self.notice_preview()
        other = self.other_hr_preview()
        self.assertEqual(self.scan([preview, other])[0]["job"]["id"], "notice")
        self.handle([{"sender": "system", "text": preview["last_message"]}])
        for _ in range(2):
            self.assertEqual([item["job"]["id"] for item in self.scan([preview, other])], ["other"])
        self.assertEqual(self.state(), ("sent", ["resume_notice_checked"]))
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_checked_notice_is_reopened_for_new_receipt_or_unread_message(self):
        self.handle([{"sender": "system", "text": "附件简历请求已发送"}])
        for preview in [self.notice_preview(last_message="附件简历已发送给对方"),
                        self.notice_preview(has_unread=True),
                        self.notice_preview(last_message="可以明天面试吗？", has_reply=True, last_direction="hr")]:
            with self.subTest(preview=preview):
                self.assertEqual([item["job"]["id"] for item in self.scan([preview])], ["notice"])

    def test_failed_extraction_does_not_suppress_next_notice_check(self):
        self.assertEqual(self.handle({"invalid": "conversation"}), "failed")
        self.assertEqual(self.state(), ("sent", []))
        self.assertEqual(len(self.scan([self.notice_preview()])), 1)

    def test_notice_with_only_our_greeting_is_not_reopened_each_cycle(self):
        messages = [{"sender": "me", "text": "您好，我对岗位感兴趣。"},
                    {"sender": "system", "text": "附件简历请求已发送"}]
        self.assertEqual(self.handle(messages), "skipped_user_replied")
        self.assertEqual(self.handle(messages), "skipped_user_replied")
        self.assertEqual(self.state(), ("sent", ["resume_notice_checked"]))
        self.assertEqual(self.scan([self.notice_preview()]), [])
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_unchanged_request_after_resume_generation_does_not_consume_scan_limit(self):
        self.assertEqual(self.handle([
            {"sender": "hr", "text": "想要一份您的附件简历，是否同意", "kind": "resume_request_card"},
            {"sender": "system", "text": "附件简历请求已发送"},
        ]), "needs_resume")
        result = self.scan([self.notice_preview(), self.other_hr_preview()])
        self.assertEqual([item["job"]["id"] for item in result], ["other"])
        self.assertEqual(len(self.scan([self.notice_preview(has_unread=True)])), 1)
        self.send.assert_not_called()
        self.generate.assert_called_once()

    def test_legacy_generated_resume_notice_is_checked_once(self):
        db = get_db(self.path)
        try:
            db.execute("UPDATE jobs SET status = 'needs_resume', resume_path = 'synthetic.pdf' WHERE id = 'notice'")
            db.commit()
        finally:
            db.close()
        messages = [{"sender": "hr", "text": "想要一份您的附件简历，是否同意", "kind": "resume_request_card"},
                    {"sender": "system", "text": "附件简历请求已发送"}]
        self.assertEqual(self.handle(messages), "skipped_existing_resume")
        self.assertEqual(self.scan([self.notice_preview()]), [])
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_request_notice_for_sent_resume_is_checked_once(self):
        db = get_db(self.path)
        try:
            update_job_status(db, "notice", "resume_sent")
        finally:
            db.close()
        self.assertEqual(len(self.scan([self.notice_preview()])), 1)
        self.handle([{"sender": "system", "text": "附件简历请求已发送"}])
        self.assertEqual(self.scan([self.notice_preview()]), [])
        self.assertEqual(self.state()[0], "resume_sent")

    def test_legacy_pending_reply_does_not_hide_a_new_receipt(self):
        db = get_db(self.path)
        try:
            add_history(db, "notice", "reply_pending", "旧格式建议回复")
        finally:
            db.close()
        receipt = "附件简历已发送给对方"
        self.assertEqual(len(self.scan([self.notice_preview(last_message=receipt)])), 1)
        self.assertEqual(self.handle([{"sender": "system", "text": receipt}], receipt), "recorded_resume_sent")
        self.assertEqual(self.state()[0], "resume_sent")

    def test_pending_reply_without_preview_is_checked_once_before_skipping_notice(self):
        messages = [{"sender": "hr", "text": "可以明天面试吗？"}]
        db = get_db(self.path)
        try:
            add_history(db, "notice", "reply_pending", monitor._build_reply_detail(messages, "可以"))
        finally:
            db.close()
        self.assertEqual(len(self.scan([self.notice_preview()])), 1)
        self.assertEqual(self.handle([*messages, {"sender": "system", "text": "附件简历请求已发送"}]),
                         "skipped_existing_pending")
        self.assertEqual(self.scan([self.notice_preview()]), [])
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

    def test_manual_reply_after_receipt_is_recorded_once_and_not_rescanned(self):
        reply = "附件简历已发送，我周一可以参加面试。"
        messages = [{"sender": "hr", "text": "请发一份简历"},
                    {"sender": "system", "text": "附件简历已发送给对方"},
                    {"sender": "unknown", "text": reply}]
        # The scan snapshot can still be 'sent' when the receipt is persisted.
        self.job["status"] = "sent"
        self.assertEqual(self.handle(messages, reply), "recorded_user_reply")
        self.assertEqual(self.handle(messages, reply), "skipped_existing_resume")
        self.assertEqual(self.state(), ("resume_sent", ["resume_sent", "replied"]))
        db = get_db(self.path)
        try:
            payload = json.loads(db.execute(
                "SELECT detail FROM history WHERE job_id = 'notice' AND action = 'replied'"
            ).fetchone()[0])
        finally:
            db.close()
        self.assertEqual(payload["schema"], "replied.external.v1")
        self.assertEqual(payload["manual_reply"], reply)
        self.assertEqual(payload["hr_question"], "请发一份简历")
        self.assertEqual(self.scan([self.notice_preview(last_message=reply)]), [])
        self.send.assert_not_called()
        self.generate.assert_not_called()

    def test_request_preview_does_not_hide_manual_reply_in_full_thread(self):
        messages = [{"sender": "hr", "text": "请发一份简历"},
                    {"sender": "me", "text": "好的，稍后发给您"},
                    {"sender": "system", "text": "附件简历请求已发送"}]
        self.assertEqual(self.handle(messages), "recorded_user_reply")
        self.assertEqual(self.scan([self.notice_preview()]), [])
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
        self.handle([{"sender": "hr", "text": "请发一份简历"},
                     {"sender": "system", "text": "附件简历已发送给对方"},
                     {"sender": "me", "text": "好的，已发送"}], "好的，已发送")
        self.assertEqual(self.state(), ("rejected", []))

    def test_receipt_does_not_overwrite_deleted_job(self):
        db = get_db(self.path)
        db.execute("UPDATE jobs SET deleted_at = CURRENT_TIMESTAMP WHERE id = 'notice'")
        db.commit()
        db.close()
        self.handle([{"sender": "hr", "text": "请发一份简历"},
                     {"sender": "system", "text": "附件简历已发送给对方"},
                     {"sender": "me", "text": "好的，已发送"}], "好的，已发送")
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
