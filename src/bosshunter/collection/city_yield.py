"""City-local activity clock and fixed, committed-insert yield windows."""

from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Callable


DEFAULT_POLICY = {"enabled": True, "warmup_minutes": 10, "window_minutes": 5, "min_new_jobs": 5}
TERMINAL_CITIES = {"completed_scope", "low_yield", "yielded_no_ids"}


def normalize_city_policy(value: Any = None, *, default_enabled: bool = True) -> dict:
    if value is None:
        return {**DEFAULT_POLICY, "enabled": default_enabled}
    if not isinstance(value, dict) or set(value) - set(DEFAULT_POLICY):
        raise ValueError("城市产出策略包含无效字段")
    result = {**DEFAULT_POLICY, **value}
    if type(result["enabled"]) is not bool:
        raise ValueError("城市产出开关必须是布尔值")
    for name, maximum in (("warmup_minutes", 60), ("window_minutes", 30), ("min_new_jobs", 1000)):
        if type(result[name]) is not int or not 1 <= result[name] <= maximum:
            raise ValueError(f"{name} 必须是 1-{maximum} 的整数")
    if result["window_minutes"] > result["warmup_minutes"]:
        raise ValueError("检查窗口不能大于首次检查时间")
    return result


class CityYieldTracker:
    def __init__(self, policy: dict, restored: dict | None = None, *, clock: Callable = time.monotonic):
        self.policy = normalize_city_policy(policy)
        self.clock = clock
        self.started = clock()
        self.state = deepcopy(restored or {})
        if self.state.get("reason_code") == "timing_gap":
            self.state.update(active_elapsed_ms=0, window_events=[], next_check_ms=policy["warmup_minutes"] * 60000)
        self.offset = int(self.state.get("active_elapsed_ms", 0))
        self.state.setdefault("next_check_ms", policy["warmup_minutes"] * 60000)
        self.state.setdefault("new_total", 0)
        self.state.setdefault("window_events", [])
        self.state.update(status="running", reason_code="")

    def elapsed_ms(self) -> int:
        return self.offset + max(0, int((self.clock() - self.started) * 1000))

    def snapshot(self) -> dict:
        return {**deepcopy(self.state), "active_elapsed_ms": self.elapsed_ms()}

    def with_insert(self, job_id: str, elapsed_ms: int) -> dict:
        state = self.snapshot()
        state["new_total"] += 1
        state["window_events"].append({"job_id": job_id, "active_elapsed_ms": elapsed_ms})
        return state

    def record_inserted(self, job_id: str, elapsed_ms: int) -> None:
        self.state = self.with_insert(job_id, elapsed_ms)

    def evaluate_due(self) -> str:
        if not self.policy["enabled"]:
            return "continue"
        now = self.elapsed_ms()
        deadline = self.state["next_check_ms"]
        window = self.policy["window_minutes"] * 60000
        if now < deadline:
            return "continue"
        if now >= deadline + window:
            self.state["reason_code"] = "timing_gap"
            return "timing_gap"
        count = sum(deadline - window < e["active_elapsed_ms"] <= deadline for e in self.state["window_events"])
        self.state.update(last_window_start_ms=deadline - window, last_window_end_ms=deadline, last_window_new=count)
        if count < self.policy["min_new_jobs"]:
            self.state.update(status="low_yield", reason_code="low_yield")
            return "low_yield"
        self.state["next_check_ms"] += window
        self.state["window_events"] = [e for e in self.state["window_events"] if e["active_elapsed_ms"] > deadline]
        return "continue"
