import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from bosshunter.db import get_db, insert_job
from bosshunter.executor import monitor, recontact


class RecontactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "jobs.db"

    def tearDown(self):
        self.temp.cleanup()

    def seed(self, job_id, *, status="sent", age=72, reply=None, source="boss", deleted=False):
        db = get_db(self.path)
        insert_job(db, {
            "id": job_id, "company": f"公司{job_id}", "title": "AI实习", "jd": "开发",
            "hr_name": "招聘者", "url": "https://example.com/job", "source_platform": source,
        })
        greeting = f"原始招呼语-{job_id}"
        db.execute("UPDATE jobs SET status=?, greeting=?, greeting_selection='edited', deleted_at=? WHERE id=?",
                   (status, greeting, "2026-01-01" if deleted else None, job_id))
        db.execute("INSERT INTO history(job_id,action,detail,created_at) VALUES (?,'sent',?,datetime('now',?))",
                   (job_id, greeting, f"-{age} hours"))
        if reply:
            db.execute("INSERT INTO history(job_id,action,detail) VALUES (?,?,?)", (job_id, reply, "HR消息"))
        db.commit()
        db.close()
        return greeting

    def config(self, ids, **extra):
        return {"_recontact_job_ids": ids, "_recontact_min_hours": 48,
                "profile": {"fixed_greeting": f"原始招呼语-{ids[0]}"},
                "throttle": {"daily_limit": 30, "interval_min": 0, "interval_max": 0, "send_windows": []}, **extra}

    def run_worker(self, ids, messages, *, result="submitted", config=None, on_inspect=None, delivery_marker=""):
        sent = []

        def send_once(job, text, _sender_config):
            target = job["id"]
            if on_inspect:
                if isinstance(on_inspect, BaseException):
                    raise on_inspect
                on_inspect(job)
            if any(message.get("sender") == "hr" for message in messages.get(target, [])):
                return {"success": False, "error": "hr_replied"}, target
            if result == "hr_replied":
                return {"success": False, "error": "hr_replied"}, target
            if result == "job_page_unavailable":
                return {
                    "success": False,
                    "error": "job_page_unavailable",
                    "history_detail": "岗位已关闭或下架",
                }, None
            if not on_inspect and recontact._message_state(messages.get(target), job) != "unreplied":
                return {"success": False, "error": "conversation_unverified"}, target
            before_send = _sender_config.get("_recontact_before_send")
            if callable(before_send) and not before_send():
                return {"success": False, "error": "candidate_changed"}, target
            if result == "uncertain":
                sent.append((target, text))
                return {"success": False, "error": "send_not_confirmed"}, target
            sent.append((target, text))
            messages.setdefault(target, [])
            messages[target].append({"sender": "me", "text": delivery_marker + text})
            return {"success": True}, None

        with (
            patch.object(recontact, "should_take_day_off", return_value=False),
            patch("bosshunter.executor.sender._send_greeting_once", side_effect=send_once) as send_greeting,
            patch("bosshunter.executor.sender.close_tab"),
        ):
            report = recontact.send_recontacts(config or self.config(ids), db_path=self.path)
        return report, sent, send_greeting

    def test_candidates_exclude_every_recorded_reply_deleted_external_and_recent_contact(self):
        self.seed("eligible")
        self.seed("recent", age=2)
        self.seed("deleted", deleted=True)
        self.seed("external", source="zhilian")
        self.seed("already-replied", status="replied")
        for action in recontact.REPLY_ACTIONS:
            self.seed(f"history-{action}", reply=action)
        self.seed("recent-followup", status="follow_up_sent")
        db = get_db(self.path)
        db.execute("INSERT INTO history(job_id,action,detail) VALUES ('recent-followup','follow_up_sent','再次联系')")
        db.commit()
        self.assertEqual([job["id"] for job in recontact.get_recontact_candidates(db)], ["eligible"])
        db.close()

    def test_cooldown_uses_last_actual_contact_not_recent_metadata_edits(self):
        self.seed("eligible")
        db = get_db(self.path)
        db.execute("UPDATE jobs SET updated_at=CURRENT_TIMESTAMP WHERE id='eligible'")
        db.commit()
        self.assertEqual(len(recontact.get_recontact_candidates(db, 48)), 1)
        db.close()

    def test_configured_greeting_is_used_instead_of_the_old_job_greeting(self):
        old = self.seed("configured")
        config = self.config(["configured"], profile={"fixed_greeting": "配置中更新的打招呼语"})
        report, sent, _ = self.run_worker(["configured"], {"configured": [{"sender": "me", "text": old}]}, config=config)
        self.assertEqual(report["sent"], 1)
        self.assertEqual(sent, [("configured", "配置中更新的打招呼语")])
        db = get_db(self.path)
        self.assertEqual(json.loads(db.execute("SELECT detail FROM history WHERE action='follow_up_sent'").fetchone()[0])["manual_reply"], "配置中更新的打招呼语")
        self.assertEqual(db.execute("SELECT greeting FROM jobs WHERE id='configured'").fetchone()[0], old)
        db.close()

    def test_custom_greeting_overrides_config_without_modifying_it(self):
        old = self.seed("custom-config")
        config = self.config(["custom-config"], profile={"fixed_greeting": "配置原文"}, _recontact_greeting=" 本次修改文案 ")
        report, sent, _ = self.run_worker(["custom-config"], {"custom-config": [{"sender": "me", "text": old}]}, config=config)
        self.assertEqual((report["sent"], sent), (1, [("custom-config", "本次修改文案")]))
        self.assertEqual(config["profile"]["fixed_greeting"], "配置原文")

    def test_missing_or_oversized_config_never_falls_back_to_history_or_opens_a_browser(self):
        self.seed("missing-config")
        for configured in ("", "字" * 301):
            with self.subTest(configured_length=len(configured)), patch.object(monitor, "_open_conversation") as opened:
                with self.assertRaises(ValueError):
                    recontact.send_recontacts(self.config(["missing-config"], profile={"fixed_greeting": configured}), db_path=self.path)
                opened.assert_not_called()
        self.assertEqual(recontact.resolve_recontact_greeting({}, "显式文案"), "显式文案")

    def test_same_business_day_is_blocked_even_after_hour_cooldown_and_in_a_new_worker(self):
        greeting = self.seed("same-day", age=3)
        db = get_db(self.path)
        day = db.execute("SELECT date(created_at, '+8 hours') FROM history WHERE action='sent'").fetchone()[0]
        with patch.object(recontact, "_business_date", return_value=day):
            self.assertEqual(recontact.get_recontact_candidates(db, 1), [])
            today = recontact.get_recontact_sent_today(db)
            self.assertEqual([job["id"] for job in today], ["same-day"])
            self.assertIsNotNone(today[0]["sent_today_at"])
            report, sent, opened = self.run_worker(["same-day"], {
                "same-day": [{"sender": "me", "text": greeting}],
            }, config=self.config(["same-day"], _recontact_min_hours=1))
            self.assertEqual((report["sent"], report["skipped_changed"]), (0, 1))
            self.assertEqual(sent, [])
            opened.assert_not_called()
        db.close()

    def test_success_moves_to_daily_bucket_and_cannot_be_repeated_after_database_reopen(self):
        greeting = self.seed("daily-success")
        report, sent, _ = self.run_worker(["daily-success"], {
            "daily-success": [{"sender": "me", "text": greeting}],
        })
        self.assertEqual((report["sent"], len(sent)), (1, 1))
        db = get_db(self.path)
        self.assertEqual(recontact.get_recontact_candidates(db, 1), [])
        self.assertEqual([job["id"] for job in recontact.get_recontact_sent_today(db)], ["daily-success"])
        db.close()
        report, sent, opened = self.run_worker(["daily-success"], {}, config=self.config(["daily-success"], _recontact_min_hours=1))
        self.assertEqual((report["sent"], sent), (0, []))
        opened.assert_not_called()

    def test_business_day_uses_beijing_midnight_not_utc_midnight(self):
        self.seed("before-midnight")
        self.seed("at-midnight")
        db = get_db(self.path)
        day = db.execute("SELECT date('now', '+8 hours')").fetchone()[0]
        next_day = db.execute("SELECT date('now', '+8 hours', '+1 day')").fetchone()[0]
        for job_id, offset in (("before-midnight", "-1 second"), ("at-midnight", "+0 seconds")):
            db.execute("INSERT INTO history(job_id,action,detail,created_at) VALUES (?,'follow_up_sent','联系',datetime(?, '-8 hours', ?))", (job_id, day, offset))
        db.commit()
        with patch.object(recontact, "_business_date", return_value=day):
            self.assertEqual([job["id"] for job in recontact.get_recontact_sent_today(db)], ["at-midnight"])
        with patch.object(recontact, "_business_date", return_value=next_day):
            self.assertEqual(recontact.get_recontact_sent_today(db), [])
        db.close()

    def test_only_unreplied_conversation_is_sent_and_new_reply_is_recorded(self):
        greeting = self.seed("eligible")
        live_greeting = self.seed("live-reply")
        self.seed("history-reply", reply="hr_reply_detected")
        report, sent, _ = self.run_worker(
            ["eligible", "live-reply", "history-reply"],
            {"eligible": [{"sender": "me", "text": greeting}],
             "live-reply": [{"sender": "me", "text": live_greeting}, {"sender": "hr", "text": "你好"}]},
        )
        self.assertEqual(sent, [("eligible", greeting)])
        self.assertEqual((report["sent"], report["skipped_hr"], report["skipped_changed"]), (1, 1, 1))
        db = get_db(self.path)
        self.assertEqual(db.execute("SELECT status FROM jobs WHERE id='live-reply'").fetchone()[0], "replied")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM history WHERE action='follow_up_sent'").fetchone()[0], 1)
        self.assertEqual(recontact.get_recontact_candidates(db), [])
        db.close()

    def test_confirmed_closed_job_is_removed_from_recontact_candidates(self):
        greeting = self.seed("closed")
        report, sent, _ = self.run_worker(
            ["closed"],
            {"closed": [{"sender": "me", "text": greeting}]},
            result="job_page_unavailable",
        )
        self.assertEqual((report["sent"], report["skipped_closed"], sent), (0, 1, []))
        db = get_db(self.path)
        try:
            row = db.execute("SELECT status, last_error_code FROM jobs WHERE id='closed'").fetchone()
            self.assertEqual((row["status"], row["last_error_code"]), ("skipped", "job_closed"))
            self.assertEqual(recontact.get_recontact_candidates(db), [])
            self.assertEqual(
                db.execute("SELECT action FROM history WHERE job_id='closed' ORDER BY id DESC LIMIT 1").fetchone()[0],
                "job_closed",
            )
        finally:
            db.close()

    def test_reply_arriving_in_final_browser_check_is_never_sent(self):
        greeting = self.seed("late-reply")
        report, _, _ = self.run_worker(["late-reply"], {"late-reply": [{"sender": "me", "text": greeting}]}, result="hr_replied")
        self.assertEqual((report["sent"], report["skipped_hr"]), (0, 1))
        db = get_db(self.path)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM history WHERE action='follow_up_sent'").fetchone()[0], 0)
        db.close()

    def test_delivery_labels_do_not_break_initial_history_or_custom_message_verification(self):
        greeting = self.seed("delivery-label")
        custom = "您好，希望进一步沟通 AI 应用开发实习岗位，谢谢！"
        for marker in ("已读 ", "送达 ", "未读 "):
            with self.subTest(marker=marker):
                self.assertEqual(recontact._message_state(
                    [{"sender": "me", "text": marker + greeting}],
                    {"greeting": greeting, "first_greeting_preview": greeting},
                ), "unreplied")
        report, sent, _ = self.run_worker(
            ["delivery-label"],
            {"delivery-label": [{"sender": "me", "text": "已读 " + greeting}]},
            config=self.config(["delivery-label"], _recontact_greeting=custom),
            delivery_marker="送达 ",
        )
        self.assertEqual(sent, [("delivery-label", custom)])
        self.assertEqual((report["sent"], report["failed"], report["unverified"]), (1, 0, 0))
        db = get_db(self.path)
        detail = db.execute("SELECT detail FROM history WHERE action='follow_up_sent'").fetchone()[0]
        self.assertEqual(json.loads(detail)["manual_reply"], custom)
        db.close()

    def test_unknown_direction_or_missing_initial_history_is_not_treated_as_no_reply(self):
        self.seed("unknown")
        self.seed("incomplete")
        report, sent, _ = self.run_worker(["unknown", "incomplete"], {
            "unknown": [{"sender": "unknown", "text": "无法辨别来源"}],
            "incomplete": [{"sender": "me", "text": "最近一条，但早期记录没有加载"}],
        })
        self.assertEqual(report["unverified"], 2)
        self.assertEqual(sent, [])
        db = get_db(self.path)
        self.assertEqual(recontact.get_recontact_sent_today(db), [])
        db.close()

    def test_reply_added_to_database_before_send_rejects_stale_candidate(self):
        greeting = self.seed("changed")

        def on_inspect(*_):
            db = get_db(self.path)
            db.execute("INSERT INTO history(job_id,action,detail) VALUES ('changed','reply_pending','新回复')")
            db.commit()
            db.close()

        report, sent, _ = self.run_worker(["changed"], {"changed": [{"sender": "me", "text": greeting}]}, on_inspect=on_inspect)
        self.assertEqual((report["sent"], report["skipped_changed"]), (0, 1))
        self.assertEqual(sent, [])

    def test_recontact_rechecks_window_after_throttle_wait_and_passes_checker_to_sender(self):
        self.seed("window-first")
        self.seed("window-second")
        config = self.config(
            ["window-first", "window-second"],
            throttle={
                "daily_limit": 30,
                "interval_min": 0,
                "interval_max": 0,
                "send_windows": ["09:00-13:00"],
            },
        )
        current_minute = [779]
        calls = []

        def send_once(job, _text, sender_config):
            calls.append((job["id"], sender_config.get("_send_window_checker")))
            return {"success": True}, None

        def wait(_stop_event):
            current_minute[0] = 780
            return False

        with (
            patch.object(recontact, "should_take_day_off", return_value=False),
            patch.object(recontact.SendWindowChecker, "_current_minutes", side_effect=lambda: current_minute[0]),
            patch.object(recontact.RequestThrottle, "wait", side_effect=wait),
            patch("bosshunter.executor.sender._send_greeting_once", side_effect=send_once),
            patch("bosshunter.executor.sender.close_tab"),
        ):
            report = recontact.send_recontacts(config, db_path=self.path)

        self.assertEqual(report["sent"], 1)
        self.assertEqual(report["stop_reason"], "outside_window")
        self.assertEqual([job_id for job_id, _ in calls], ["window-first"])
        self.assertIsInstance(calls[0][1], recontact.SendWindowChecker)

    def test_recontact_counts_toward_shared_daily_quota(self):
        greeting = self.seed("quota")
        db = get_db(self.path)
        db.execute("INSERT INTO history(job_id,action,detail) VALUES ('other','follow_up_sent','今日已联系')")
        db.commit()
        db.close()
        config = self.config(["quota"])
        config["throttle"]["daily_limit"] = 1
        report, sent, opened = self.run_worker(["quota"], {"quota": [{"sender": "me", "text": greeting}]}, config=config)
        self.assertEqual(report["stop_reason"], "daily_limit")
        self.assertEqual(report["deferred"], 1)
        self.assertEqual(sent, [])
        opened.assert_not_called()

    def test_normal_delivery_also_counts_recontact_against_its_quota(self):
        self.seed("ready", status="approved")
        db = get_db(self.path)
        db.execute("INSERT INTO history(job_id,action,detail) VALUES ('other','follow_up_sent','今日已联系')")
        db.commit()
        db.close()
        from bosshunter.executor import sender
        with patch.object(sender, "_send_greeting_once") as send:
            self.assertEqual(sender.send_greetings({"throttle": {"daily_limit": 1}}, force=True, db_path=self.path), 0)
            send.assert_not_called()

    def test_stop_before_start_opens_no_chat(self):
        greeting = self.seed("stopped")
        event = Event()
        event.set()
        report, sent, opened = self.run_worker(["stopped"], {"stopped": [{"sender": "me", "text": greeting}]}, config=self.config(["stopped"], _workbench_stop_event=event))
        self.assertEqual(report["stop_reason"], "stopped")
        opened.assert_not_called()
        self.assertEqual(sent, [])

    def test_outside_window_never_opens_a_chat(self):
        greeting = self.seed("window")
        with patch.object(recontact.SendWindowChecker, "is_active", return_value=False):
            report, sent, opened = self.run_worker(["window"], {"window": [{"sender": "me", "text": greeting}]})
        self.assertEqual(report["stop_reason"], "outside_window")
        opened.assert_not_called()

    def test_platform_risk_stops_without_sending_and_locks_the_runtime_database(self):
        greeting = self.seed("risk")
        with patch.object(monitor, "_record_monitor_risk"):
            report, sent, _ = self.run_worker(["risk"], {"risk": [{"sender": "me", "text": greeting}]},
                                             on_inspect=monitor.MonitorRiskDetected("captcha"))
        self.assertEqual(report["stop_reason"], "captcha")
        self.assertEqual(sent, [])
        from bosshunter.db import get_active_platform_safety_lock
        db = get_db(self.path)
        self.assertIsNotNone(get_active_platform_safety_lock(db))
        db.close()

    def test_invalid_selection_and_interval_are_rejected(self):
        for value in ([], None, "all", [1], ["x"] * 1 + [str(i) for i in range(1001)]):
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                recontact.recontact_job_ids(value)
        for value in (0, -1, 1.5, True, "nan", 721):
            with self.subTest(hours=value), self.assertRaises(ValueError):
                recontact.recontact_hours(value)

    def test_uncertain_submission_is_not_automatically_retried_or_reported_as_sent(self):
        greeting = self.seed("uncertain")
        report, sent, _ = self.run_worker(["uncertain"], {"uncertain": [{"sender": "me", "text": greeting}]}, result="uncertain")
        self.assertEqual((report["sent"], report["failed"], report["stop_reason"]), (0, 1, "send_unconfirmed"))
        self.assertEqual(len(sent), 1)
        db = get_db(self.path)
        self.assertEqual(recontact.get_recontact_candidates(db), [])
        db.close()

    def test_browser_send_guard_verifies_hr_before_submitting_in_the_same_js_turn(self):
        jsdom_path = Path(__file__).resolve().parents[1] / "src/bosshunter/web/frontend/node_modules/jsdom"
        if not shutil.which("node") or not jsdom_path.exists():
            self.skipTest("Node.js and frontend jsdom are needed for browser guard verification")
        with patch.object(monitor, "evaluate", return_value='{"state":"submitted"}') as evaluate:
            recontact._submit_checked_message("test-only", "新的招呼语")
            script = evaluate.call_args.args[1]
        harness = r"""
            const fs = require('node:fs');
            const input = JSON.parse(fs.readFileSync(0, 'utf8'));
            const {JSDOM} = require(input.jsdom);
            const results = [];
            for (const type of ['unreplied', 'hr_replied', 'unknown']) {
                const extra = type === 'hr_replied' ? '<div class="chat-message item-friend"><span class="msg-text">HR has replied</span></div>'
                    : type === 'unknown' ? '<div class="chat-message"><span class="msg-text">Uncertain message</span></div>' : '';
                const dom = new JSDOM('<div class="chat-message item-myself"><span class="msg-text">Old greeting</span></div>' + extra + '<div id="chat-input"></div>', {runScripts:'outside-only'});
                dom.window.Element.prototype.getClientRects = () => [{width:1,height:1}];
                let submissions = 0;
                dom.window.document.querySelector('#chat-input').__vue__ = {_data:{},handleSubmit(){submissions++;}};
                const outcome = JSON.parse(dom.window.eval(input.script));
                results.push({type,state:outcome.state,submissions});
                dom.window.close();
            }
            process.stdout.write(JSON.stringify(results));
        """
        result = subprocess.run([shutil.which("node"), "-e", harness], input=json.dumps({"jsdom": str(jsdom_path), "script": script}),
                                capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertEqual(json.loads(result.stdout), [
            {"type": "unreplied", "state": "submitted", "submissions": 1},
            {"type": "hr_replied", "state": "hr_replied", "submissions": 0},
            {"type": "unknown", "state": "unreadable", "submissions": 0},
        ])

    def test_recontact_never_clicks_a_new_conversation_button(self):
        with (
            patch.object(monitor, "_open_monitor_tab", return_value="job-page"),
            patch.object(monitor, "_wait_or_stop", return_value=False),
            patch.object(monitor, "_wait_for_page_or_stop", return_value=True),
            patch.object(monitor, "_inspect_monitor_page"),
            patch.object(monitor, "_record_page_failure_unless_stopped"),
            patch.object(monitor, "evaluate", return_value='{"opened":false}'),
            patch.object(monitor, "click") as click,
            patch.object(monitor, "close_tab"),
            patch.object(monitor, "_open_conversation_from_chat_list", return_value=None),
        ):
            result = monitor._open_conversation({"url": "https://example.com/job"}, {"_monitor_existing_conversation_only": True})
            self.assertIsNone(result)
            click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
