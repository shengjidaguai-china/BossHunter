"""Local AI response cache and prompt-cache statistics.

Two independent savings live here:

1. **本地响应缓存**：同样的模型 + 同样的提示词（评分/招呼语/定制简历）只真正请求一次。
   重复评分（force_rescore）、重跑同一批岗位、同一岗位重复生成招呼语都会直接命中，
   不再计费。
2. **缓存命中统计**：把服务商返回的 ``prompt_tokens`` / ``cached_tokens`` 汇总起来，
   每批任务结束时打印命中率，方便判断提示词前缀是否稳定。

提示词前缀是否能被服务商缓存取决于调用方：静态规则放最前、简历其次、JD 最后，
这样同一批任务里除 JD 之外的部分都能命中。
"""

from __future__ import annotations

import hashlib
import threading
import time

_TABLE = "ai_response_cache"
_lock = threading.Lock()
_stats: dict[str, int] = {
    "hits": 0,
    "misses": 0,
    "stored": 0,
    "calls": 0,
    "prompt_tokens": 0,
    "cached_tokens": 0,
}


def cache_settings(config: dict | None) -> tuple[bool, float]:
    """Return ``(enabled, ttl_seconds)`` from ``ai.prompt_cache*``.

    默认关闭：只有显式配置 ``ai.prompt_cache: true`` 才启用，避免离线测试或
    换模型调试时读到上一次的响应。
    """
    ai_cfg = config.get("ai") if isinstance(config, dict) else None
    ai_cfg = ai_cfg if isinstance(ai_cfg, dict) else {}
    enabled = ai_cfg.get("prompt_cache", False) is True
    try:
        ttl_hours = float(ai_cfg.get("prompt_cache_ttl_hours", 168))
    except (TypeError, ValueError):
        ttl_hours = 168.0
    return enabled, max(ttl_hours, 0.0) * 3600


def make_cache_key(*, base_url: str, model: str, purpose: str | None, prompt: str, max_tokens: int) -> str:
    """Stable key: same provider/model/purpose/prompt/limit → same answer."""
    digest = hashlib.sha256()
    for part in (base_url or "", model or "", purpose or "", str(int(max_tokens or 0)), prompt or ""):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def _bump(field: str, amount: int = 1) -> None:
    with _lock:
        _stats[field] = _stats.get(field, 0) + amount


def _connect():
    from bosshunter.db import get_db

    return get_db()


def _ensure_table(conn) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "cache_key TEXT PRIMARY KEY, purpose TEXT, model TEXT, "
        "response TEXT NOT NULL, created_at REAL NOT NULL)"
    )
    conn.commit()


def lookup(key: str, config: dict | None) -> str | None:
    """Return a cached response, or None when disabled/missing/expired."""
    enabled, ttl = cache_settings(config)
    if not enabled or not key:
        return None
    if isinstance(config, dict) and (config.get("_skip_prompt_cache") or config.get("_workbench_regenerate")):
        return None
    try:
        conn = _connect()
    except Exception:
        return None
    try:
        _ensure_table(conn)
        row = conn.execute(
            f"SELECT response, created_at FROM {_TABLE} WHERE cache_key = ?", (key,)
        ).fetchone()
    except Exception:
        return None
    finally:
        conn.close()
    if not row:
        _bump("misses")
        return None
    response, created_at = str(row[0] or ""), float(row[1] or 0)
    if not response or (ttl and time.time() - created_at > ttl):
        _bump("misses")
        return None
    _bump("hits")
    return response


def store(key: str, *, response: str, purpose: str | None, model: str, config: dict | None) -> None:
    enabled, _ttl = cache_settings(config)
    if not enabled or not key or not response:
        return
    try:
        conn = _connect()
    except Exception:
        return
    try:
        _ensure_table(conn)
        conn.execute(
            f"INSERT OR REPLACE INTO {_TABLE} (cache_key, purpose, model, response, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, purpose or "", model or "", response, time.time()),
        )
        conn.commit()
        _bump("stored")
        # 顺手清理过期条目，避免缓存库无限增长。
        conn.execute(f"DELETE FROM {_TABLE} WHERE created_at < ?", (time.time() - 30 * 24 * 3600,))
        conn.commit()
    except Exception:
        return
    finally:
        conn.close()


def record_usage(usage: dict | None) -> None:
    """Accumulate provider-reported prompt/cache token counts."""
    if not isinstance(usage, dict):
        return
    prompt_tokens = usage.get("prompt_tokens")
    details = usage.get("prompt_tokens_details")
    cached = None
    if isinstance(details, dict):
        cached = details.get("cached_tokens")
    if cached is None:
        cached = usage.get("prompt_cache_hit_tokens")
    try:
        prompt_value = int(prompt_tokens or 0)
    except (TypeError, ValueError):
        prompt_value = 0
    try:
        cached_value = int(cached or 0)
    except (TypeError, ValueError):
        cached_value = 0
    with _lock:
        _stats["calls"] += 1
        _stats["prompt_tokens"] += max(prompt_value, 0)
        _stats["cached_tokens"] += max(min(cached_value, prompt_value or cached_value), 0)


def drain_stats() -> dict[str, int]:
    """Return the accumulated counters and reset them."""
    with _lock:
        snapshot = dict(_stats)
        for key in _stats:
            _stats[key] = 0
    return snapshot


def summary_line(stats: dict[str, int]) -> str:
    """Human-readable one-line summary for task logs."""
    calls = int(stats.get("calls") or 0)
    hits = int(stats.get("hits") or 0)
    prompt_tokens = int(stats.get("prompt_tokens") or 0)
    cached_tokens = int(stats.get("cached_tokens") or 0)
    local_total = calls + hits
    local_rate = (hits / local_total * 100) if local_total else 0.0
    provider_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens else 0.0
    return (
        f"AI 缓存：本地复用 {hits}/{local_total}（{local_rate:.0f}%），"
        f"服务商前缀缓存 {cached_tokens}/{prompt_tokens} tokens（{provider_rate:.0f}%），"
        f"实际请求 {calls} 次"
    )
