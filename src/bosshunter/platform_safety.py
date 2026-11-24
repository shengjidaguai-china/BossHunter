"""Shared page-access budgets and persistent safety locks for platform workflows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable

from bosshunter.db import (
    add_platform_access,
    count_platform_access_today,
    get_active_platform_safety_lock,
    set_platform_safety_lock,
)

class PlatformSafetyStop(RuntimeError):
    """Raised before another platform page is opened when a safety guard stops work."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class PlatformAccessGuard:
    conn: sqlite3.Connection
    config: dict
    stage: str
    platform: str = "boss"

    def ensure_unlocked(self) -> None:
        lock = get_active_platform_safety_lock(self.conn)
        if lock:
            raise PlatformSafetyStop("persistent_risk_lock")

    def check_available(self, action: str, *, daily_limit: int | None = None) -> None:
        """Check original access limits without consuming a page attempt.

        ``0``（或负数）表示该额度不限制：采集/评分想跑多久就跑多久，
        只有投递受发送时间窗约束。
        """
        self.ensure_unlocked()
        safety_cfg = self.config.get("safety", {})
        global_limit = _limit(safety_cfg.get("daily_platform_page_limit", 1100), 1100)
        if global_limit is not None and count_platform_access_today(self.conn, platform=self.platform) >= global_limit:
            raise PlatformSafetyStop("daily_platform_page_limit")
        stage_limit = _limit(daily_limit, None) if daily_limit is not None else None
        if stage_limit is not None:
            stage_count = count_platform_access_today(
                self.conn,
                platform=self.platform,
                stage=self.stage,
                action=action,
            )
            if stage_count >= stage_limit:
                raise PlatformSafetyStop(f"daily_{action}_limit")

    def reserve(self, action: str, *, daily_limit: int | None = None) -> None:
        """Reserve one page-open attempt before navigation."""
        self.check_available(action, daily_limit=daily_limit)
        add_platform_access(self.conn, self.stage, action, platform=self.platform)

    def lock(self, reason: str, *, minutes: int | None = None) -> None:
        safety_cfg = self.config.get("safety", {})
        lock_minutes = (
            _positive_int(minutes, 1)
            if minutes is not None
            else _positive_int(safety_cfg.get("risk_lock_minutes", 10), 10)
        )
        set_platform_safety_lock(self.conn, reason, minutes=lock_minutes)


@dataclass
class TransientPlatformAccessGuard:
    """Open a short-lived DB connection for workflows without a cycle-long connection."""

    config: dict
    stage: str
    db_factory: Callable[[], sqlite3.Connection]
    platform: str = "boss"

    def ensure_unlocked(self) -> None:
        conn = self.db_factory()
        try:
            PlatformAccessGuard(conn, self.config, self.stage, self.platform).ensure_unlocked()
        finally:
            conn.close()

    def reserve(self, action: str, *, daily_limit: int | None = None) -> None:
        conn = self.db_factory()
        try:
            PlatformAccessGuard(conn, self.config, self.stage, self.platform).reserve(
                action,
                daily_limit=daily_limit,
            )
        finally:
            conn.close()


def _positive_int(value: object, default: int) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def _limit(value: object, default: int | None) -> int | None:
    """Return a positive page budget; ``0`` or a negative value means unlimited."""
    try:
        parsed: int | None = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = default
    if parsed is None:
        return None
    return None if parsed <= 0 else parsed
