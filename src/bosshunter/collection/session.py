"""Opt-in, bounded BOSS collection sessions using the original guarded collector."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from uuid import uuid4

from bosshunter.browser.ownership import browser_execution
from bosshunter.collection_session_store import create_session, get_session, save_session, claim_session
from bosshunter.collection_run_store import can_resume_boss_run, get_collection_run
from bosshunter.db import get_db, count_platform_access_today, get_active_platform_safety_lock


SESSION_DEFAULTS = {
    "enabled": False, "max_duration_hours": 8, "round_rest_minutes": 15,
    "zero_yield_rest_minutes": 30, "zero_yield_rest_max_minutes": 120,
    "retry_rest_minutes": 5, "max_technical_retries": 2, "max_rate_limit_retries": 1,
    "quota_resume_buffer_minutes": 5,
}
QUOTA_REASONS = {"daily_search_page_limit", "daily_detail_page_limit", "daily_platform_page_limit"}
ROUND_REASONS = {"search_exhausted", "no_new_jobs", "search_page_not_advanced", "repeated_search_page", "low_yield", "no_jobs_for_search"}


def normalize_session_options(value) -> dict:
    if not isinstance(value, dict) or set(value) - (set(SESSION_DEFAULTS) | {"end_at"}):
        raise ValueError("持续采集参数无效")
    result = {**SESSION_DEFAULTS, **value}
    if type(result["enabled"]) is not bool:
        raise ValueError("持续采集开关必须是布尔值")
    limits = {"max_duration_hours": (1, 24), "round_rest_minutes": (5, 120),
              "zero_yield_rest_minutes": (15, 120), "zero_yield_rest_max_minutes": (15, 240),
              "retry_rest_minutes": (5, 120), "max_technical_retries": (0, 2),
              "max_rate_limit_retries": (0, 1), "quota_resume_buffer_minutes": (1, 30)}
    for key, (minimum, maximum) in limits.items():
        if type(result[key]) is not int or not minimum <= result[key] <= maximum:
            raise ValueError(f"{key} 必须是 {minimum}-{maximum} 的整数")
    if result["zero_yield_rest_max_minutes"] < result["zero_yield_rest_minutes"]:
        raise ValueError("最大零新增休息不能小于起始休息")
    if "end_at" in value:
        if "max_duration_hours" in value:
            raise ValueError("结束时刻和最长时长只能设置一个")
        try:
            end = datetime.fromisoformat(value["end_at"])
            if end.tzinfo is None:
                raise ValueError("结束时刻必须包含时区")
        except (TypeError, ValueError) as exc:
            raise ValueError("结束时刻无效") from exc
        result.pop("max_duration_hours")
    return result


class SessionSignal:
    def __init__(self, session):
        self.session = session

    def is_set(self):
        return self.session.stopped()

    @property
    def reason(self):
        return "user_stopped" if self.session.state.get("stop_requested") else "session_deadline"

    def wait(self, seconds):
        end = self.session.clock() + seconds
        while self.session.clock() < end:
            if self.is_set():
                return True
            self.session.sleep(min(1.0, end - self.session.clock()))
        return self.is_set()


class CollectionSession:
    def __init__(self, config: dict, *, db_path: Path, task_id: str = "", session_id: str | None = None,
                 clock=time.monotonic, now=None, sleep=time.sleep, runner_factory=None):
        self.config, self.db_path, self.task_id = config, db_path, task_id
        self.id = session_id or str(uuid4())
        self.resuming = session_id is not None
        self.clock, self.now, self.sleep = clock, now or (lambda: datetime.now(timezone.utc)), sleep
        self.runner_factory = runner_factory
        self.user_stop = config.get("_workbench_stop_event")
        self.owner = str(uuid4())
        self.last_poll = float("-inf")
        self.state = {}

    def stopped(self):
        if self.user_stop is not None and self.user_stop.is_set():
            self.state["stop_requested"] = True
        if self.clock() - self.last_poll >= 0.5:
            saved = get_session(self.db_path, self.id)
            if not saved:
                raise RuntimeError("持续采集会话记录已丢失，停止访问")
            if saved["state"].get("owner") != self.owner:
                raise RuntimeError("持续采集执行所有权已变化")
            self.state["stop_requested"] = self.state.get("stop_requested", False) or saved["state"].get("stop_requested", False)
            self.state["continue_version"] = saved["state"].get("continue_version", 0)
            self.last_poll = self.clock()
        return bool(self.state.get("stop_requested") or self.now() >= self.deadline or self.clock() >= self.monotonic_deadline)

    def persist(self):
        save_session(self.db_path, self.id, self.state, owner=self.owner)

    def phase(self, name: str, reason: str = "", *, wake: datetime | None = None):
        now = self.now()
        previous = self.state.get("phase", "collecting")
        if name == "waiting_user":
            self.state["manual_pending_reason"] = reason
        seconds = max(0, self.clock() - self.phase_clock)
        durations = self.state.setdefault("phase_seconds", {})
        durations[previous] = durations.get(previous, 0) + seconds
        self.phase_clock = self.clock()
        self.state.update(phase=name, reason_code=reason, next_wake_at=wake.isoformat() if wake else None,
                          last_seen_at=now.isoformat())
        self.state.setdefault("history", []).append({"at": now.isoformat(), "phase": name, "reason_code": reason})
        self.state["history"] = self.state["history"][-200:]
        self.persist()
        self.emit()

    def emit(self, child: dict | None = None):
        saved = get_session(self.db_path, self.id)
        if not saved:
            return
        callback = self.config.get("_workbench_collect_progress")
        if callable(callback):
            callback({**saved["counts"], "new": len(saved["collected_job_ids"]), "progress": {
                **((child or {}).get("progress", {})), "session_id": self.id,
                "session": {**self.state, "id": self.id, "new": len(saved["collected_job_ids"]), "city_totals": saved["city_totals"]},
                "outcome": self.state["phase"],
            }})

    def quota_available(self):
        conn = get_db(self.db_path)
        try:
            limits = self.config.get("collection", {})
            safety = self.config.get("safety", {})
            return (count_platform_access_today(conn, platform="boss") < int(safety.get("daily_platform_page_limit", 1100))
                    and count_platform_access_today(conn, platform="boss", stage="collection", action="search_page") < int(limits.get("daily_search_page_limit", 60))
                    and count_platform_access_today(conn, platform="boss", stage="collection", action="detail_page") < int(limits.get("daily_detail_page_limit", 900)))
        finally:
            conn.close()

    def risk_lock(self):
        conn = get_db(self.db_path)
        try:
            return get_active_platform_safety_lock(conn)
        finally:
            conn.close()

    def quota_wake(self):
        local = self.now().astimezone()
        midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return (midnight + timedelta(minutes=self.settings["quota_resume_buffer_minutes"])).astimezone(timezone.utc)

    def wait(self):
        wake_text = self.state.get("next_wake_at")
        wake = datetime.fromisoformat(wake_text) if wake_text else self.deadline
        minimum = self.clock() + max(0, (wake - self.now()).total_seconds())
        continuation = self.state.get("continue_version", 0)
        last_emit = self.clock()
        while not self.stopped():
            if self.state["phase"] == "waiting_user":
                if self.state.get("continue_version", 0) > continuation:
                    self.state["retry_kind"] = ""
                    self.state.pop("manual_pending_reason", None)
                    return
            elif self.now() >= wake and self.clock() >= minimum:
                if self.state["phase"] == "waiting_quota" and not self.quota_available():
                    wake = self.quota_wake()
                    self.phase("waiting_quota", self.state["reason_code"], wake=wake)
                else:
                    lock = self.risk_lock()
                    if not lock:
                        return
                    if self.state.get("risk_reason") != "rate_limit" or lock["reason"] != "rate_limit":
                        self.phase("waiting_user", "persistent_risk_lock")
                        wake = self.deadline
                    else:
                        wake = max(datetime.fromisoformat(lock["locked_until"]), self.now() + timedelta(seconds=1))
                        self.phase("waiting_risk", "rate_limit", wake=wake)
                minimum = self.clock() + max(0, (wake - self.now()).total_seconds())
                continuation = self.state.get("continue_version", 0)
            if self.clock() - last_emit >= 15:
                self.emit()
                last_emit = self.clock()
            self.sleep(1.0)

    def run(self, raw_options: dict | None = None):
        from bosshunter.collection.orchestrator import CollectionOrchestrator, normalize_collection_options
        with browser_execution():
            if self.resuming:
                saved = get_session(self.db_path, self.id)
                if not saved or saved["status"] != "running":
                    raise ValueError("持续采集会话已结束或不存在")
                options = saved["options"]
                self.state = claim_session(self.db_path, self.id, self.owner)
            else:
                options = normalize_collection_options(self.config, raw_options)
                settings = options.get("continuous_collection", {})
                if not settings.get("enabled") or options["platform_order"] != ["boss"]:
                    raise ValueError("请明确开启 BOSS 持续采集")
                deadline = datetime.fromisoformat(settings["end_at"]) if settings.get("end_at") else self.now() + timedelta(hours=settings["max_duration_hours"])
                if not self.now() < deadline <= self.now() + timedelta(hours=24):
                    raise ValueError("持续采集结束时间必须在未来 24 小时内")
                self.state = {"owner": self.owner, "status": "running", "phase": "collecting", "deadline_at": deadline.isoformat(),
                              "started_at": self.now().isoformat(), "round": 0, "zero_rounds": 0, "technical_retries": 0,
                              "rate_limit_retries": 0, "keyword_start": {}, "continue_version": 0}
                create_session(self.db_path, self.id, options, self.state)
            self.settings = options["continuous_collection"]
            self.deadline = datetime.fromisoformat(self.state["deadline_at"])
            self.monotonic_deadline = self.clock() + max(0, (self.deadline - self.now()).total_seconds())
            self.phase_clock = self.clock()
            if self.resuming and self.state.get("last_seen_at") and self.now() < datetime.fromisoformat(self.state["last_seen_at"]) - timedelta(seconds=5):
                self.phase("waiting_user", "clock_unreliable")
            if self.resuming and not self.stopped() and self.state["phase"] != "waiting_user":
                if self.state["technical_retries"] >= self.settings["max_technical_retries"]:
                    self.phase("waiting_user", "restart_retry_exhausted")
                else:
                    self.state["retry_kind"] = "technical"
                    old_wake = datetime.fromisoformat(self.state["next_wake_at"]) if self.state.get("next_wake_at") else self.now()
                    self.phase("waiting_retry", "service_restarted", wake=max(old_wake, self.now() + timedelta(minutes=self.settings["retry_rest_minutes"])))
            try:
                while not self.stopped():
                    if self.state["phase"] != "collecting":
                        self.wait()
                        if self.stopped():
                            break
                    kind = self.state.pop("retry_kind", "")
                    if kind:
                        key = f"{kind}_retries"
                        if self.state[key] >= self.settings[f"max_{key}"]:
                            self.phase("waiting_user", "retry_exhausted")
                            continue
                        self.state[key] += 1
                    self.phase("collecting")
                    run_id = self.state.get("run_id")
                    previous = get_collection_run(self.db_path, run_id) if run_id else None
                    if not run_id:
                        self.state["round"] += 1
                        run_id = self.state["run_id"] = str(uuid4())
                        self.persist()
                    child_options = deepcopy(options)
                    child_options.pop("continuous_collection", None)
                    child_options["auto_score"] = False
                    child_options["platforms"]["boss"]["keyword_start"] = deepcopy(self.state["keyword_start"])
                    resumable = bool(previous and can_resume_boss_run({**previous, "session_id": None}))
                    if previous and previous["status"] in {"completed", "completed_with_shortage", "completed_with_errors"} and not resumable:
                        result = {"platforms": previous["platform_states"], "collected_job_ids": previous["collected_job_ids"]}
                    else:
                        if previous:
                            child_options = {"resume_run_id": run_id}
                        child_config = {**self.config, "_workbench_stop_event": SessionSignal(self),
                                        "_workbench_collect_progress": self.emit, "_collection_session_id": self.id,
                                        "_collection_session_round": self.state["round"]}
                        factory = self.runner_factory or CollectionOrchestrator
                        result = factory(child_config, db_path=self.db_path, task_id=self.task_id, run_id=run_id).run(child_options)
                    boss = result.get("platforms", {}).get("boss", {})
                    reason = boss.get("reason_code", "collection_error")
                    if self.stopped():
                        break
                    if reason in ROUND_REASONS and boss.get("status") in {"completed", "completed_with_shortage"}:
                        for city, state in boss.get("city_results", {}).items():
                            if "next_keyword_index" in state:
                                self.state["keyword_start"][city] = state["next_keyword_index"]
                        self.state["run_id"] = None
                        self.state["zero_rounds"] = 0 if result.get("collected_job_ids") else self.state["zero_rounds"] + 1
                        zero = self.state["zero_rounds"]
                        minutes = min(self.settings["zero_yield_rest_minutes"] * 2 ** min(zero - 1, 10), self.settings["zero_yield_rest_max_minutes"]) if zero else self.settings["round_rest_minutes"]
                        self.phase("waiting_round", reason, wake=self.now() + timedelta(minutes=minutes))
                    elif reason in QUOTA_REASONS:
                        self.phase("waiting_quota", reason, wake=self.quota_wake())
                    elif reason == "rate_limit" and self.state["rate_limit_retries"] < self.settings["max_rate_limit_retries"]:
                        self.state.update(risk_reason="rate_limit", retry_kind="rate_limit")
                        lock = self.risk_lock()
                        wake = self.now() + timedelta(minutes=self.settings["retry_rest_minutes"])
                        if lock:
                            wake = max(wake, datetime.fromisoformat(lock["locked_until"]))
                        self.phase("waiting_risk", reason, wake=wake)
                    elif reason == "consecutive_page_failures" and self.state["technical_retries"] < self.settings["max_technical_retries"]:
                        self.state["retry_kind"] = "technical"
                        self.phase("waiting_retry", reason, wake=self.now() + timedelta(minutes=self.settings["retry_rest_minutes"]))
                    elif reason == "no_valid_city":
                        self.state["status"] = "failed"
                        self.phase("finished", reason)
                        break
                    else:
                        self.phase("waiting_user", reason)
                if self.state["status"] == "running":
                    self.state["status"] = "stopped" if self.state.get("stop_requested") else "completed"
                    self.phase("finished", "user_stopped" if self.state.get("stop_requested") else "session_deadline")
            except Exception:
                self.state["status"] = "failed"
                try:
                    self.phase("finished", "session_error")
                except Exception:
                    pass
                raise
            saved = get_session(self.db_path, self.id)
            if options.get("auto_score") and saved["collected_job_ids"] and self.state["reason_code"] == "session_deadline" and not self.state.get("risk_reason") and not self.state.get("manual_pending_reason") and not (self.user_stop and self.user_stop.is_set()):
                from bosshunter.ai.scorer import score_jobs
                score_jobs(self.config, scope="selected", job_ids=saved["collected_job_ids"], limit=None, force_rescore=False)
            return saved
