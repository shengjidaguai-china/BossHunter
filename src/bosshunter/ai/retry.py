"""Bounded retries for transient AI service failures.

网络抖动和限流这类瞬时故障不应让整批评分或招呼语停下来。这里集中在
``_call_claude`` 之上做指数退避重试：只有瞬时错误（network / rate_limit /
5xx）会重试，鉴权、额度、上下文超限等确定性错误立即抛出，仍由上层决定暂停。
"""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from bosshunter.ai.credentials import AIRequestError

T = TypeVar("T")

# 瞬时错误：同一请求稍后重发有机会成功。
TRANSIENT_KINDS = frozenset({"network", "rate_limit"})
MAX_RETRY_SECONDS = 60.0


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def is_transient(error: AIRequestError) -> bool:
    """True when retrying the same request can plausibly succeed."""
    kind = str(getattr(error, "kind", "") or "")
    if kind in TRANSIENT_KINDS:
        return True
    if kind == "request_failed":
        status = getattr(error, "status_code", None)
        if status is None:
            return True
        try:
            return int(status) >= 500
        except (TypeError, ValueError):
            return True
    return False


def retry_settings(config: dict[str, Any] | None) -> tuple[int, float]:
    """Return ``(attempts, base_delay_seconds)`` from ``ai.retry_*``."""
    ai_cfg = config.get("ai", {}) if isinstance(config, dict) else {}
    ai_cfg = ai_cfg if isinstance(ai_cfg, dict) else {}
    attempts = _bounded_int(ai_cfg.get("retry_attempts", 3), 3, 1, 6)
    base_delay = _bounded_float(ai_cfg.get("retry_backoff_seconds", 5.0), 5.0, 0.0, MAX_RETRY_SECONDS)
    return attempts, base_delay


def _wait(seconds: float, stop_event: Any) -> bool:
    """Sleep in small steps so a stopped task does not wait out the backoff."""
    remaining = seconds
    while remaining > 0:
        if stop_event is not None and stop_event.is_set():
            return True
        step = min(remaining, 0.5)
        time.sleep(step)
        remaining -= step
    return bool(stop_event is not None and stop_event.is_set())


def call_with_retry(
    call: Callable[[], T],
    *,
    config: dict[str, Any] | None,
    purpose: str = "ai",
    on_retry: Callable[[str], None] | None = None,
) -> T:
    """Run ``call`` and retry transient AI failures with exponential backoff."""
    attempts, base_delay = retry_settings(config)
    logger = on_retry
    if logger is None and isinstance(config, dict):
        candidate = config.get("_workbench_log")
        logger = candidate if callable(candidate) else None
    stop_event = config.get("_workbench_stop_event") if isinstance(config, dict) else None

    for attempt in range(1, attempts + 1):
        try:
            return call()
        except AIRequestError as exc:
            if attempt >= attempts or not is_transient(exc):
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), MAX_RETRY_SECONDS)
            if callable(logger):
                logger(f"AI 服务瞬时故障（{exc}），{delay:.0f} 秒后重试 {attempt}/{attempts - 1}（{purpose}）")
            if _wait(delay, stop_event):
                raise
    raise AIRequestError("request_failed", "AI 请求重试未执行")
