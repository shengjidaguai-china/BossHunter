"""Collection-only adapter for the existing persistent platform guard.

Search API calls (including probes) consume search_page, not a second quota.
Limits live under platforms.<platform>.safety; invalid values use conservative
20/50/80 defaults. No connection means no platform access, never an untracked run.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import replace
from functools import wraps

from bosshunter.collection.base import CollectionBlockedError
from bosshunter.collection.models import PlatformCollectionResult
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop

PAGE_RISK_SCRIPT = """
(() => {
  const text = (document.body?.innerText || '') + ' ' + document.title;
  const captcha = /验证码|滑块|滑动验证|安全验证|请完成验证|captcha/i.test(text);
  const limited = /访问频繁|频率限制|限流|拒绝访问|账号异常|too many requests|access denied/i.test(text);
  return JSON.stringify({collection_risk: captcha ? 'captcha' : limited ? 'rate_limit' : ''});
})()
"""

RISK_REASONS = {"blocked", "captcha", "rate_limit", "access_denied", "account_abnormal", "consecutive_page_failures"}


def _limit(value, default):
    try:
        if isinstance(value, bool) or int(value) <= 0:
            return default
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


class CollectionSafety:
    def __init__(self, config, conn, platform):
        platforms = config.get("platforms") or {}
        platform_config = platforms.get(platform, {}) if isinstance(platforms, dict) else {}
        safety = platform_config.get("safety") if isinstance(platform_config, dict) else {}
        safety = safety if isinstance(safety, dict) else {}
        self.limits = {
            action: _limit(safety.get(f"daily_{action}_limit"), default)
            for action, default in (("search_page", 20), ("detail_page", 50), ("platform_page", 80))
        }
        shared = config.get("safety")
        shared = shared if isinstance(shared, dict) else {}
        guard_config = {"safety": {**shared, "daily_platform_page_limit": self.limits["platform_page"]}}
        self.guard = PlatformAccessGuard(conn, guard_config, "collection", platform) if conn is not None else None
        collection = config.get("collection")
        collection = collection if isinstance(collection, dict) else {}
        self.max_failures = _limit(collection.get("max_consecutive_page_failures"), 3)
        self.failures = 0
        self.stop_event = None

    def check(self):
        if self.stop_event is not None and self.stop_event.is_set():
            raise PlatformSafetyStop("user_stopped")
        if self.guard is None:
            raise PlatformSafetyStop("safety_db_unavailable")
        try:
            self.guard.ensure_unlocked()
        except sqlite3.Error as exc:
            raise PlatformSafetyStop("safety_db_unavailable") from exc

    def reserve(self, action):
        self.check()
        try:
            self.guard.reserve(action, daily_limit=self.limits[action])
        except sqlite3.Error as exc:
            raise PlatformSafetyStop("safety_db_unavailable") from exc

    def success(self):
        self.check()
        self.failures = 0

    def failure(self):
        self.check()
        self.failures += 1
        if self.failures >= self.max_failures:
            self.lock("consecutive_page_failures")
            raise PlatformSafetyStop("consecutive_page_failures")

    def api_result(self, analysis):
        if analysis.get("ok"):
            self.success()
        else:
            self.failure()
        return analysis

    def inspect_page(self, evaluate, target):
        self.check()
        raw = evaluate(target, PAGE_RISK_SCRIPT)
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            payload = None
        if not isinstance(payload, dict) or "collection_risk" not in payload:
            raise CollectionBlockedError("browser_disconnected", "无法检查页面安全状态，停止采集")
        reason = payload.get("collection_risk")
        if reason in RISK_REASONS:
            raise CollectionBlockedError(reason, "页面出现验证或限流，停止采集")
        self.check()

    def check_api_response(self, wrapper):
        """A CAPTCHA/403/429 must never turn into a DOM fallback or host retry."""
        status = str(wrapper.get("http_status") or "")
        if status in {"403", "429"}:
            raise CollectionBlockedError("rate_limit", f"API HTTP {status}，停止采集")
        if status == "401":
            raise CollectionBlockedError("login_required", "API 要求重新登录，停止采集")
        body = str(wrapper.get("body") or "")
        try:
            data = json.loads(body)
        except (TypeError, ValueError):
            data = None
        # Successful job descriptions can mention verification; only inspect
        # error metadata or non-JSON challenge pages, never the jobs themselves.
        text = body if data is None else str(data.get("message") or data.get("msg") or "") if isinstance(data, dict) else ""
        if re.search(r"captcha|verify|验证码|滑块|滑动验证|安全验证|请完成验证", text, re.IGNORECASE):
            raise CollectionBlockedError("captcha", "API 出现验证信号，停止采集")
        if re.search(r"访问频繁|频率限制|限流|拒绝访问|账号异常|风控|too many requests|access denied", text, re.IGNORECASE):
            raise CollectionBlockedError("rate_limit", "API 出现限流信号，停止采集")
        if data is None and re.search(r"login|请登录|请先登录|扫码登录", text, re.IGNORECASE):
            raise CollectionBlockedError("login_required", "API 返回登录页，停止采集")

    def lock(self, reason):
        if reason in RISK_REASONS and self.guard is not None:
            try:
                self.guard.lock(reason)
            except sqlite3.Error as exc:
                raise PlatformSafetyStop("safety_db_unavailable") from exc

    def wait(self, seconds, sleep):
        self.check()
        if self.stop_event is not None:
            if self.stop_event.wait(max(0.0, seconds)):
                raise PlatformSafetyStop("user_stopped")
        else:
            sleep(max(0.0, seconds))
        self.check()


def protected_collection(collect):
    """One exit boundary for quota, cancellation and persistent risk signals."""
    @wraps(collect)
    def run(self, request, hooks):
        safety = self._safety
        safety.stop_event = hooks.stop_event
        safety.failures = 0

        def candidate(value):
            safety.check()
            keep_going = hooks.on_candidate(value)
            safety.check()
            if not keep_going:
                raise PlatformSafetyStop("callback_stopped")
            return True

        def parse_failed(message):
            hooks.on_parse_failed(message)
            safety.failure()

        def list_candidate(value):
            safety.check()
            accepted = hooks.on_list_candidate(value)
            safety.check()
            return accepted

        try:
            try:
                safety.check()
                result = collect(self, request, replace(hooks, on_candidate=candidate, on_list_candidate=list_candidate, on_parse_failed=parse_failed))
                if result.reason_code in RISK_REASONS:
                    safety.lock(result.reason_code)
                    return result
                safety.check()
                return result
            except CollectionBlockedError as exc:
                safety.lock(exc.code)
                return PlatformCollectionResult(self.platform, "blocked", exc.code, exc.message)
        except PlatformSafetyStop as exc:
            reason = exc.reason
            status = "stopped" if reason == "user_stopped" else "completed" if reason == "callback_stopped" else "blocked"
            return PlatformCollectionResult(self.platform, status, reason, f"采集安全停止：{reason}")
        finally:
            safety.stop_event = None
    return run
