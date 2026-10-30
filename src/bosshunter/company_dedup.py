"""Treat name variants of one employer as the same company (华为 / 华为技术有限公司 / 上海华为…).

Used by collection to skip a company that was already applied to (on any platform) within the cooldown window
or that already has a job waiting in the pool.
"""

import re
import sqlite3
from datetime import datetime, timedelta, timezone

_REGIONS = (
    "上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "天津", "重庆", "西安", "长沙",
    "厦门", "合肥", "郑州", "青岛", "大连", "东莞", "佛山",
)
_LEGAL_SUFFIX = re.compile(r"(股份有限公司|有限责任公司|有限公司|股份公司|集团|控股)+$")
_NOISE = re.compile(r"[\s()（）·\-_/,，.。]")


def company_key(name: object) -> str:
    """Normalised core of a company name; '' when nothing usable is left."""
    key = _NOISE.sub("", str(name or "")).lower()
    key = _LEGAL_SUFFIX.sub("", key)
    for region in _REGIONS:
        if key.startswith(region) and len(key) >= len(region) + 2:
            key = key[len(region):]
            break
    return key


def same_company(a: object, b: object) -> bool:
    """True when the normalised names are equal or one starts with the other (at least 2 characters).

    Prefix matching groups 华为 / 华为技术 / 华为云计算 but keeps 招商银行 and 中国银行 apart.
    """
    key_a, key_b = company_key(a), company_key(b)
    if not key_a or not key_b:
        return False
    if key_a == key_b:
        return True
    short, long = sorted((key_a, key_b), key=len)
    return len(short) >= 2 and long.startswith(short)


def _local_date(timestamp: str):
    try:
        return datetime.fromisoformat(str(timestamp)).replace(tzinfo=timezone.utc).astimezone().date()
    except ValueError:
        return None


def cooldown_days(config: dict | None) -> int:
    """How many days (including today) a company stays blocked after one of its jobs was approved."""
    raw = ((config or {}).get("automation") or {}).get("company_cooldown_days", 1)
    try:
        return min(max(int(raw), 1), 60)
    except (TypeError, ValueError):
        return 1


def approved_within(conn: sqlite3.Connection, days: int = 1) -> list[dict]:
    """Jobs approved or sent within the last ``days`` local days (1 = today only)."""
    days = max(int(days), 1)
    first_day = datetime.now().date() - timedelta(days=days - 1)
    rows = conn.execute(
        """
        SELECT h.job_id AS id, j.company AS company, h.created_at AS created_at
        FROM history h JOIN jobs j ON j.id = h.job_id
        WHERE h.action IN ('approved', 'sent', 'manual_sent') AND j.deleted_at IS NULL
          AND h.created_at >= datetime('now', ?)
        """,
        (f"-{days + 1} day",),
    ).fetchall()
    seen: set[str] = set()
    result = []
    for row in rows:
        day = _local_date(row["created_at"])
        if day is not None and day >= first_day and row["id"] not in seen:
            seen.add(row["id"])
            result.append({"id": row["id"], "company": row["company"]})
    return result


_LIVE_POOL_STATUSES = ("pending", "scored", "ready", "approved")


def pool_companies(conn: sqlite3.Connection) -> list[str]:
    """Companies that already have a job waiting in the pool (collected, scored or approved, not yet sent)."""
    placeholders = ",".join("?" for _ in _LIVE_POOL_STATUSES)
    rows = conn.execute(
        f"SELECT DISTINCT company FROM jobs WHERE deleted_at IS NULL AND status IN ({placeholders})",
        _LIVE_POOL_STATUSES,
    ).fetchall()
    return [row["company"] for row in rows if row["company"]]


def matching_company(company: object, known: list[str]) -> str | None:
    """First entry of ``known`` that is the same employer as ``company``."""
    for name in known:
        if same_company(company, name):
            return name
    return None
