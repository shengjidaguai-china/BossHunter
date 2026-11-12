from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from threading import Thread
from unittest import TestCase
from unittest.mock import patch

from bosshunter.browser.ownership import BrowserBusyError, browser_execution
from bosshunter.collection.orchestrator import normalize_collection_options
from bosshunter.collection.session import CollectionSession, normalize_session_options
from bosshunter.collection_run_store import create_collection_run, get_collection_run, save_city_state, update_collection_run
from bosshunter.collection_session_store import create_session, get_session, request_session_action, save_session
from bosshunter.db import get_db, insert_job_if_new, get_active_platform_safety_lock, set_platform_safety_lock


class VirtualTime:
    def __init__(self, start=None):
        self.start = start or datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.elapsed = 0.0

    def clock(self):
        return self.elapsed

    def now(self):
        return self.start + timedelta(seconds=self.elapsed)

    def sleep(self, seconds):
        self.elapsed += seconds * 60


class SessionTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "jobs.db"
        self.time = VirtualTime()
        self.calls = []
        self.sequence = []
        self.progress = []
        self.config = {"_workbench_collect_progress": self.progress.append}

    def options(self, minutes=20, **settings):
        return {"platform_order": ["boss"], "auto_score": False, "platforms": {"boss": {
            "keywords": ["A", "B", "C"], "cities": ["北京", "上海"], "max_pages": 2}},
            "continuous_collection": {"enabled": True, "end_at": (self.time.now() + timedelta(minutes=minutes)).isoformat(), **settings}}

    def runner(self, config, *, db_path, task_id, run_id):
        fixture = self
        class Runner:
            def run(self, options):
                prior = get_collection_run(db_path, run_id)
                actual_options = prior["options"] if prior else options
                fixture.calls.append({"at": fixture.time.now(), "run_id": run_id, "options": actual_options})
                reason, new_ids = fixture.sequence.pop(0) if fixture.sequence else ("search_page_not_advanced", [])
                status = "blocked" if reason in {"captcha", "login_required", "blocked", "rate_limit", "persistent_risk_lock"} else "completed_with_shortage"
                if prior is None:
                    create_collection_run(db_path, run_id=run_id, options=actual_options, platform_states={}, enable_boss_resume=True,
                                          session_id=config["_collection_session_id"], session_round=config["_collection_session_round"])
                inserted = []
                city_results = {}
                with closing(get_db(db_path)) as conn:
                    for job_id in new_ids:
                        if insert_job_if_new(conn, {"id": job_id, "title": "Test", "company": "Test"}):
                            inserted.append(job_id)
                    if reason in {"search_page_not_advanced", "search_exhausted", "low_yield"}:
                        for city in ("北京", "上海"):
                            state = {"status": "yielded_no_ids", "new_total": len(inserted) if city == "北京" else 0,
                                     "next_keyword_index": (actual_options["platforms"]["boss"].get("keyword_start", {}).get(city, 0) + 1) % 3}
                            city_results[city] = state
                            save_city_state(conn, run_id, city, state)
                    if reason == "captcha":
                        set_platform_safety_lock(conn, "captcha", minutes=10)
                boss = {"status": status, "reason_code": reason, "new": len(inserted), "city_results": city_results}
                update_collection_run(db_path, run_id, status=status, platform_states={"boss": boss}, collected_job_ids=inserted)
                return {"platforms": {"boss": boss}, "collected_job_ids": inserted}
        return Runner()

    def session(self, session_id=None):
        return CollectionSession(self.config, db_path=self.path, session_id=session_id, clock=self.time.clock,
                                 now=self.time.now, sleep=self.time.sleep, runner_factory=self.runner)

    def test_productive_round_rests_then_rotates_keywords(self):
        self.sequence = [("search_page_not_advanced", ["one"]), ("search_page_not_advanced", ["one", "two"])]
        result = self.session().run(self.options())
        self.assertEqual(len(self.calls), 2)
        self.assertGreaterEqual((self.calls[1]["at"] - self.calls[0]["at"]).total_seconds(), 900)
        self.assertEqual(self.calls[1]["options"]["platforms"]["boss"]["keyword_start"], {"北京": 1, "上海": 1})
        self.assertEqual(result["collected_job_ids"], ["one", "two"])
        self.assertEqual(result["city_totals"]["北京"], 2)
        self.assertEqual(result["state"]["reason_code"], "session_deadline")

    def test_zero_yield_backoff_is_thirty_sixty_one_twenty(self):
        result = self.session().run(self.options(minutes=240))
        gaps = [(self.calls[i + 1]["at"] - self.calls[i]["at"]).total_seconds() / 60 for i in range(3)]
        self.assertEqual(gaps, [30, 60, 120])
        self.assertEqual(result["state"]["zero_rounds"], 4)

    def test_virtual_overnight_spans_rounds_quota_rate_limit_and_manual_risk(self):
        self.time = VirtualTime(datetime(2026, 10, 26, 23, 30).astimezone().astimezone(timezone.utc))
        self.sequence = [("search_page_not_advanced", ["before-midnight"]), ("daily_search_page_limit", []),
                         ("rate_limit", []), ("search_exhausted", ["after-midnight"]), ("captcha", [])]
        result = self.session().run(self.options(minutes=480))
        self.assertEqual(len(self.calls), 5)
        self.assertEqual(result["collected_job_ids"], ["before-midnight", "after-midnight"])
        self.assertEqual(result["state"]["rate_limit_retries"], 1)
        self.assertEqual(result["state"]["manual_pending_reason"], "captcha")
        phases = {item["phase"] for item in result["state"]["history"]}
        self.assertTrue({"waiting_round", "waiting_quota", "waiting_risk", "waiting_user"} <= phases)
        self.assertGreaterEqual((self.calls[2]["at"].astimezone() - self.time.start.astimezone()).total_seconds(), 35 * 60)

    def test_captcha_keeps_lock_and_waits_without_more_attempts(self):
        self.sequence = [("captcha", [])]
        result = self.session().run(self.options())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result["state"]["manual_pending_reason"], "captcha")
        with closing(get_db(self.path)) as conn:
            self.assertEqual(get_active_platform_safety_lock(conn)["reason"], "captcha")

    def test_known_rate_limit_recovers_once_and_budget_persists(self):
        self.sequence = [("rate_limit", []), ("rate_limit", [])]
        session = self.session()
        session.risk_lock = lambda: None
        result = session.run(self.options())
        self.assertEqual(len(self.calls), 2)
        self.assertGreaterEqual((self.calls[1]["at"] - self.calls[0]["at"]).total_seconds(), 300)
        self.assertEqual(result["state"]["rate_limit_retries"], 1)
        self.assertEqual(result["state"]["manual_pending_reason"], "rate_limit")

    def test_technical_failure_has_two_recoveries_only(self):
        self.sequence = [("consecutive_page_failures", [])] * 3
        result = self.session().run(self.options())
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(result["state"]["technical_retries"], 2)
        self.assertEqual(len({call["run_id"] for call in self.calls}), 1)
        self.assertEqual(result["state"]["manual_pending_reason"], "consecutive_page_failures")

    def test_unknown_risk_and_technical_errors_are_not_automatic_retries(self):
        for reason in ("blocked", "login_required", "persistent_risk_lock", "salary_decode_failed", "timing_gap", "persistence_error", "collection_error"):
            with self.subTest(reason=reason):
                self.calls = []
                self.sequence = [(reason, [])]
                result = self.session().run(self.options(minutes=2))
                self.assertEqual(len(self.calls), 1)
                self.assertEqual(result["state"]["manual_pending_reason"], reason)

    def test_waiting_quota_never_probes_before_local_midnight(self):
        self.time = VirtualTime(datetime(2026, 10, 26, 23, 58).astimezone().astimezone(timezone.utc))
        self.sequence = [("daily_search_page_limit", []), ("search_page_not_advanced", ["new-day"])]
        session = self.session()
        earliest = session.now().astimezone().replace(hour=0, minute=5, second=0) + timedelta(days=1)
        session.quota_available = lambda: session.now() >= earliest
        result = session.run(self.options(minutes=20))
        self.assertEqual(len(self.calls), 2)
        self.assertGreaterEqual(self.calls[1]["at"], earliest)
        self.assertEqual(self.calls[0]["run_id"], self.calls[1]["run_id"])
        self.assertEqual(result["collected_job_ids"], ["new-day"])

    def test_deadline_prevents_quota_probe(self):
        self.sequence = [("daily_platform_page_limit", [])]
        result = self.session().run(self.options(minutes=2))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result["state"]["reason_code"], "session_deadline")

    def test_user_stop_during_wait_is_persistent(self):
        def progress(state):
            session = state["progress"].get("session", {})
            if session.get("phase") == "waiting_round":
                request_session_action(self.path, session["id"], "stop")
        self.config["_workbench_collect_progress"] = progress
        result = self.session().run(self.options())
        self.assertEqual(result["state"]["reason_code"], "user_stopped")
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(ValueError):
            self.session(result["id"]).run()

    def test_old_owner_cannot_overwrite_new_owner_or_stop(self):
        state = {"owner": "new", "phase": "waiting_user", "status": "running"}
        create_session(self.path, "test", {}, state)
        request_session_action(self.path, "test", "stop")
        with self.assertRaises(RuntimeError):
            save_session(self.path, "test", {**state, "owner": "old"}, owner="old")
        save_session(self.path, "test", state, owner="new")
        self.assertTrue(get_session(self.path, "test")["state"]["stop_requested"])

    def test_stop_wins_race_with_deadline_completion(self):
        state = {"owner": "worker", "status": "running", "phase": "collecting"}
        create_session(self.path, "race", {}, state)
        request_session_action(self.path, "race", "stop")
        state.update(status="completed", phase="finished", reason_code="session_deadline")
        save_session(self.path, "race", state, owner="worker")
        saved = get_session(self.path, "race")
        self.assertEqual(saved["status"], "stopped")
        self.assertEqual(saved["state"]["reason_code"], "user_stopped")

    def test_missing_session_stops_before_another_round(self):
        def progress(state):
            session = state["progress"].get("session", {})
            if session.get("phase") == "waiting_round":
                with closing(get_db(self.path)) as conn:
                    conn.execute("DELETE FROM collection_sessions WHERE id = ?", (session["id"],))
                    conn.commit()
        self.config["_workbench_collect_progress"] = progress
        with self.assertRaisesRegex(RuntimeError, "会话记录已丢失"):
            self.session().run(self.options())
        self.assertEqual(len(self.calls), 1)

    def test_manual_continue_returns_through_original_risk_guard(self):
        continued = []
        def progress(state):
            session = state["progress"].get("session", {})
            if session.get("phase") == "waiting_user" and not continued:
                continued.append(True)
                request_session_action(self.path, session["id"], "continue")
        self.config["_workbench_collect_progress"] = progress
        self.sequence = [("captcha", []), ("persistent_risk_lock", [])]
        result = self.session().run(self.options(minutes=2))
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0]["run_id"], self.calls[1]["run_id"])
        self.assertEqual(result["state"]["manual_pending_reason"], "persistent_risk_lock")
        with closing(get_db(self.path)) as conn:
            self.assertEqual(get_active_platform_safety_lock(conn)["reason"], "captcha")

    def test_restart_waits_and_consumes_recovery_budget(self):
        options = normalize_collection_options({}, self.options(minutes=10))
        state = {"owner": "dead", "status": "running", "phase": "collecting", "deadline_at": options["continuous_collection"]["end_at"],
                 "round": 0, "zero_rounds": 0, "technical_retries": 0, "rate_limit_retries": 0, "keyword_start": {}}
        create_session(self.path, "restart", options, state)
        result = self.session("restart").run()
        self.assertGreaterEqual((self.calls[0]["at"] - self.time.start).total_seconds(), 300)
        self.assertEqual(result["state"]["technical_retries"], 1)

    def test_strict_config_and_supported_mode(self):
        for invalid in ({"max_technical_retries": 3}, {"max_rate_limit_retries": 2}, {"retry_rest_minutes": 1},
                        {"enabled": 1}, {"max_duration_hours": True}, {"unknown": 1}, {"zero_yield_rest_max_minutes": 15}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                normalize_session_options(invalid)
        options = self.options()
        options["platform_order"] = ["boss", "zhilian"]
        options["platforms"]["zhilian"] = {"cities": ["北京"], "keywords": ["A"]}
        with self.assertRaises(ValueError):
            normalize_collection_options({}, options)

    def test_both_deadline_and_duration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_session_options({"enabled": True, "end_at": self.time.now().isoformat(), "max_duration_hours": 8})


class BrowserOwnershipTests(TestCase):
    def test_other_process_denied_and_lock_released(self):
        script = """
import sys
from unittest.mock import patch
from bosshunter.browser.ownership import BrowserBusyError, browser_execution
with patch('bosshunter.browser.ownership.get_runtime_url', return_value=sys.argv[1]):
    try:
        with browser_execution():
            pass
    except BrowserBusyError:
        sys.exit(23)
"""
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
            command = [sys.executable, "-X", "utf8", "-B", "-c", script, tmp]
            with patch("bosshunter.browser.ownership.get_runtime_url", return_value=tmp):
                with browser_execution():
                    denied = subprocess.run(command, env=env, capture_output=True, timeout=20)
                released = subprocess.run(command, env=env, capture_output=True, timeout=20)
        self.assertEqual(denied.returncode, 23, denied.stderr.decode())
        self.assertEqual(released.returncode, 0, released.stderr.decode())

    def test_nested_owner_allowed_other_thread_denied_then_released(self):
        errors = []
        def contender():
            try:
                with browser_execution():
                    errors.append("unexpected access")
            except BrowserBusyError:
                errors.append("busy")
        with browser_execution(), browser_execution():
            thread = Thread(target=contender)
            thread.start()
            thread.join(timeout=5)
        self.assertEqual(errors, ["busy"])
        with browser_execution():
            pass
