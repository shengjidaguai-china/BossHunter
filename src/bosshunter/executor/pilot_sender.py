"""Guarded auto-apply pilot for BOSS, Zhilian and 51job delivery.

This module intentionally stays behind explicit opt-in configuration and a
visible Web confirmation. Each selected platform runs at most one browser
worker/tab at a time; a risk or login signal from any platform stops the whole
round. Zhilian/51job apply actions are attempted only when the page exposes an
unambiguous, visible action; when a manual resume upload or unknown dialog is
required the job is recorded as failed instead of being guessed as sent.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock
from typing import Any
from urllib.parse import urlparse

from rich.console import Console

from bosshunter.browser import close_tab, evaluate, new_tab, wait_for_load
from bosshunter.db import (
    add_history,
    add_risk_event,
    get_db,
    set_platform_safety_lock,
    update_job_status,
)
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop
from bosshunter.throttle import SendWindowChecker, should_take_day_off

console = Console()

EXTERNAL_PLATFORMS = {"zhilian", "51job"}
SUPPORTED_PLATFORMS = {"boss", "zhilian", "51job"}


def _open_db(config: dict):
    db_path = config.get("_workbench_db_path") if isinstance(config, dict) else None
    return get_db(Path(str(db_path))) if db_path else get_db()


def _parse_result(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {"kind": "unexpected", "detail": str(value)[:200]}
    return value if isinstance(value, dict) else {}


def _notify(config: dict, message: str, *, error: bool = False) -> None:
    console.print(f"[{'red' if error else 'yellow'}]{message}[/{'red' if error else 'yellow'}]")
    callback = config.get("_workbench_log")
    if callable(callback):
        callback(message)


def _progress(config: dict, state: dict[str, Any]) -> None:
    callback = config.get("_workbench_send_progress")
    if callable(callback):
        callback(state)


def _stop_requested(stop_event: Event | None) -> bool:
    return bool(stop_event is not None and stop_event.is_set())


def _sleep_or_stop(seconds: float, stop_event: Event | None) -> bool:
    if stop_event is not None:
        return bool(stop_event.wait(max(float(seconds), 0)))
    time.sleep(max(float(seconds), 0))
    return False


def _platform_label(platform: str) -> str:
    return {
        "boss": "BOSS 直聘",
        "zhilian": "智联招聘",
        "51job": "前程无忧",
    }.get(str(platform), str(platform))


def _job_label(job: dict) -> str:
    return f"{job.get('company') or '未知公司'}｜{job.get('title') or '未知岗位'}"


def _lock_minutes(config: dict) -> int:
    try:
        return max(int(config.get("safety", {}).get("risk_lock_minutes", 10) or 10), 1)
    except (TypeError, ValueError):
        return 10


# The action scanner intentionally looks for exact visible action labels rather
# than trusting a single brittle CSS class.  Navigation labels such as “我的投递”
# or “投递记录” are excluded.
JS_APPLY_SCAN = r"""
(() => {
    const compact = String((document.body && document.body.innerText) || '').replace(/\s+/g, '');
    const fullText = String((document.body && document.body.innerText) || '');
    const risk = /验证码|滑动验证|访问验证|访问频繁|人机验证|安全验证|请完成验证/.test(compact);
    const login = /登录后投递|扫码登录|账号登录|请先登录|登录智联|登录前程无忧/.test(compact);
    const offline = /职位已下线|岗位已下线|职位已关闭|岗位已关闭|已停止招聘|招聘已结束/.test(compact);
    const resumeMissing = /请完善简历|简历不完整|缺少简历|请先创建简历|在线简历不完整|请上传简历|添加简历/.test(compact);
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    };
    const fileInputs = Array.from(document.querySelectorAll('input[type=file]')).filter(visible);
    if (risk) return JSON.stringify({kind: 'risk', reason: 'captcha_or_verification'});
    if (offline) return JSON.stringify({kind: 'job_closed'});
    if (resumeMissing || fileInputs.length) return JSON.stringify({kind: 'manual_resume_required'});
    if (login && !document.querySelector('button, a, [role="button"]')) {
        return JSON.stringify({kind: 'login_required'});
    }
    if (/今日已投递|已投递|投递成功|申请成功|投递完成/.test(compact)) {
        return JSON.stringify({kind: 'already_applied'});
    }
    const candidates = Array.from(document.querySelectorAll('button, a, [role="button"], input[type=button], input[type=submit]'))
        .map((el, index) => {
            const text = String((el.innerText || el.value || el.textContent || '')).replace(/\s+/g, ' ').trim();
            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            const isVisible = !!(rect.width && rect.height && style.display !== 'none'
                && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
            const inViewport = isVisible && rect.bottom > 0 && rect.right > 0
                && rect.top < innerHeight && rect.left < innerWidth;
            const className = String(el.className || '');
            let score = 0;
            if (isVisible) score += 1000;
            if (inViewport) score += 500;
            if (/btn|apply|deliver|send|primary|submit/i.test(className)) score += 200;
            const exact = /^(立即投递|投递简历|投递该职位|投递职位|立即申请|申请职位|申请该职位)$/.test(text);
            if (exact) score += 700;
            if (!exact && /投递|申请/.test(text)) score -= 800;
            if (/记录|管理|收藏|结果|我的/.test(text)) score -= 1000;
            return {index, text, isVisible, inViewport, score, className};
        })
        .filter((item) => item.isVisible && item.score > 200);
    if (!candidates.length) {
        return JSON.stringify({kind: 'no_action_button'});
    }
    candidates.sort((a, b) => b.score - a.score || a.index - b.index);
    const best = candidates[0];
    const confident = best && best.score >= 1150;
    return JSON.stringify({kind: confident ? 'action_ready' : 'ambiguous_action', best, candidates: candidates.length});
})()
"""


JS_APPLY_CLICK = r"""
(() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    };
    const elements = Array.from(document.querySelectorAll('button, a, [role="button"], input[type=button], input[type=submit]'));
    const matches = elements.map((el, index) => {
        const text = String((el.innerText || el.value || el.textContent || '')).replace(/\s+/g, ' ').trim();
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        const isVisible = !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
        const inViewport = isVisible && rect.bottom > 0 && rect.right > 0
            && rect.top < innerHeight && rect.left < innerWidth;
        const className = String(el.className || '');
        let score = 0;
        if (isVisible) score += 1000;
        if (inViewport) score += 500;
        if (/btn|apply|deliver|send|primary|submit/i.test(className)) score += 200;
        const exact = /^(立即投递|投递简历|投递该职位|投递职位|立即申请|申请职位|申请该职位)$/.test(text);
        if (exact) score += 700;
        if (!exact && /投递|申请/.test(text)) score -= 800;
        if (/记录|管理|收藏|结果|我的/.test(text)) score -= 1000;
        return {index, el, text, isVisible, inViewport, score};
    }).filter((item) => item.isVisible && item.score > 200);
    if (!matches.length) return JSON.stringify({clicked: false, reason: 'no_action_button'});
    matches.sort((a, b) => b.score - a.score || a.index - b.index);
    const best = matches[0];
    if (best.score < 1150) return JSON.stringify({clicked: false, reason: 'ambiguous_action'});
    try {
        best.el.scrollIntoView({block: 'center'});
        best.el.click();
        return JSON.stringify({clicked: true, text: best.text});
    } catch (error) {
        return JSON.stringify({clicked: false, reason: String(error && error.message || error)});
    }
})()
"""


JS_CONFIRM_APPLY = r"""
(() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    };
    const dialogs = Array.from(document.querySelectorAll('div, section, [role="dialog"], .modal, .dialog')).filter((el) => {
        if (!visible(el)) return false;
        const text = String(el.innerText || '');
        return /投递|申请/.test(text.replace(/\s+/g, '')) && text.length < 600;
    });
    const dialog = dialogs[dialogs.length - 1];
    if (!dialog) return JSON.stringify({confirmed: false});
    const buttons = Array.from(dialog.querySelectorAll('button, a, [role="button"]')).filter(visible);
    const confirm = buttons.find((el) => /^(确认|确定|继续投递|确认投递|继续申请|确认申请|立即投递)$/.test(
        String((el.innerText || el.value || '')).replace(/\s+/g, ' ').trim()
    ));
    if (!confirm) return JSON.stringify({confirmed: false});
    try {
        confirm.click();
        return JSON.stringify({confirmed: true});
    } catch (error) {
        return JSON.stringify({confirmed: false});
    }
})()
"""


JS_APPLY_FINAL = r"""
(() => {
    const compact = String((document.body && document.body.innerText) || '').replace(/\s+/g, '');
    const risk = /验证码|滑动验证|访问验证|访问频繁|人机验证|安全验证|请完成验证/.test(compact);
    const login = /登录后投递|扫码登录|账号登录|请先登录|登录已过期|登录失效/.test(compact);
    const resumeMissing = /请完善简历|简历不完整|缺少简历|请先创建简历|在线简历不完整|请上传简历|添加简历/.test(compact);
    const fileInputs = Array.from(document.querySelectorAll('input[type=file]')).filter((el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    });
    if (risk) return JSON.stringify({kind: 'risk', reason: 'captcha_or_verification'});
    if (login) return JSON.stringify({kind: 'login_required'});
    if (resumeMissing || fileInputs.length) return JSON.stringify({kind: 'manual_resume_required'});
    if (/今日已投递|已投递|投递成功|申请成功|投递完成/.test(compact)) return JSON.stringify({kind: 'success'});
    return JSON.stringify({kind: 'unverified'});
})()
"""


def _external_apply_once(job: dict, config: dict, stop_event: Event | None, db) -> dict[str, Any]:
    """Open one external job and click the unambiguous apply action."""
    platform = str(job.get("source_platform") or "zhilian")
    if platform == "51job":
        from bosshunter.executor.job51_sender import apply_job51_once
        return apply_job51_once(job, config, stop_event, db)
    url = str(job.get("url") or "").strip()
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except ValueError:
        hostname = ""
    allowed_domain = ("zhaopin.com" if platform == "zhilian" else "51job.com")
    if not url or not hostname or allowed_domain not in hostname:
        return {"success": False, "error": "unsafe_job_url", "history_detail": "岗位链接域名与平台不符，未自动投递", "skip_backoff": True}
    guard = PlatformAccessGuard(db, config, "deliver", platform)
    try:
        guard.ensure_unlocked()
        guard.reserve("job_page")
    except PlatformSafetyStop as exc:
        return {"success": False, "error": exc.reason, "history_detail": "平台访问受限或风险锁未结束", "risk": exc.reason}
    target_id = new_tab(url, background=True)
    if not target_id:
        return {"success": False, "error": "open_page_failed", "history_detail": "无法打开岗位页面", "skip_backoff": True}
    try:
        wait_for_load(target_id, timeout=12)
        if _stop_requested(stop_event):
            return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
        scan = _parse_result(evaluate(target_id, JS_APPLY_SCAN))
        kind = scan.get("kind")
        if kind == "risk":
            return {"success": False, "error": "captcha", "history_detail": "检测到验证码或访问验证", "risk": "captcha"}
        if kind == "login_required":
            return {"success": False, "error": "login_required", "history_detail": "平台登录状态失效或要求登录", "skip_backoff": True}
        if kind == "job_closed":
            return {"success": False, "error": "job_closed", "history_detail": "岗位已关闭或下架", "skip_backoff": True}
        if kind == "manual_resume_required":
            return {"success": False, "error": "manual_resume_required", "history_detail": "平台要求上传或完善简历附件，未代替操作", "skip_backoff": True}
        if kind == "already_applied":
            return {"success": True, "already_sent": True, "history_detail": "平台显示该岗位已经投递"}
        if kind not in {"action_ready", "ambiguous_action"}:
            return {"success": False, "error": "no_apply_button", "history_detail": "页面未找到可识别的投递按钮", "skip_backoff": True}
        if kind == "ambiguous_action":
            return {"success": False, "error": "ambiguous_action", "history_detail": "页面投递动作不唯一，未自动点击", "skip_backoff": True}

        click_state = _parse_result(evaluate(target_id, JS_APPLY_CLICK))
        if not click_state.get("clicked"):
            return {"success": False, "error": "apply_click_failed", "history_detail": "未点击到唯一投递按钮", "skip_backoff": True}
        if _sleep_or_stop(1.2, stop_event):
            return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
        confirm_state = _parse_result(evaluate(target_id, JS_CONFIRM_APPLY))
        if confirm_state.get("confirmed") and _sleep_or_stop(1.0, stop_event):
            return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
        if _sleep_or_stop(1.0, stop_event):
            return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
        final = _parse_result(evaluate(target_id, JS_APPLY_FINAL))
        final_kind = final.get("kind")
        if final_kind == "risk":
            return {"success": False, "error": "captcha", "history_detail": "点击后出现验证码或访问验证", "risk": "captcha"}
        if final_kind == "login_required":
            return {"success": False, "error": "login_required", "history_detail": "点击后要求登录", "skip_backoff": True}
        if final_kind == "manual_resume_required":
            return {"success": False, "error": "manual_resume_required", "history_detail": "点击后平台要求完善或上传简历，未代替操作", "skip_backoff": True}
        if final_kind == "success":
            return {"success": True, "history_detail": "页面显示投递成功"}
        return {"success": False, "error": "unverified", "history_detail": "已点击投递但页面未能确认成功，未记录为已投递", "skip_backoff": True}
    finally:
        close_tab(target_id)


def _boss_deliver_once(job: dict, config: dict, stop_event: Event | None, db) -> dict[str, Any]:
    """Use the existing BOSS first-contact sender inside the pilot worker."""
    from bosshunter.executor.sender import _send_greeting_once

    throttle = dict(config.get("throttle", {}) or {})
    throttle["_workbench_stop_event"] = stop_event
    throttle["_platform_access_guard"] = PlatformAccessGuard(db, config, "send", "boss")
    result_data, failed_target_id = _send_greeting_once(job, str(job.get("greeting") or ""), throttle)
    if failed_target_id:
        close_tab(failed_target_id)
    if result_data.get("success"):
        return {"success": True, "already_sent": bool(result_data.get("already_present")), "history_detail": "BOSS 招呼语发送成功"}
    error = str(result_data.get("error") or "boss_send_failed")
    risk = error if error in {"captcha", "rate_limit", "blocked"} else ""
    return {
        "success": False,
        "error": error,
        "history_detail": str(result_data.get("history_detail") or f"BOSS 发送失败：{error}"),
        "risk": risk,
    }


@dataclass
class _Budget:
    remaining: int
    total: int
    lock: Lock = Lock()

    def reserve(self) -> bool:
        with self.lock:
            if self.remaining <= 0:
                return False
            self.remaining -= 1
            return True


def _run_platform_worker(
    platform: str,
    jobs: list[dict],
    config: dict,
    stop_event: Event | None,
    budget: _Budget,
) -> dict[str, int]:
    db = _open_db(config)
    result = {"attempted": 0, "sent": 0, "failed": 0, "deferred": 0, "already": 0}
    try:
        for job in jobs:
            if _stop_requested(stop_event):
                result["deferred"] += 1
                continue
            if not budget.reserve():
                result["deferred"] += 1
                continue
            job_id = str(job.get("id") or "")
            current = {
                "id": job_id,
                "company": str(job.get("company") or "未知公司"),
                "title": str(job.get("title") or "未知岗位"),
            }
            processed_before = result["sent"] + result["failed"] + result["deferred"]
            _progress(config, {
                "status": "running",
                "total": budget.total,
                "attempted": processed_before,
                "sent": result["sent"],
                "failed": result["failed"],
                "deferred": result["deferred"],
                "current_job": current,
                "platform": platform,
            })
            try:
                if platform == "boss":
                    outcome = _boss_deliver_once(job, config, stop_event, db)
                else:
                    outcome = _external_apply_once(job, config, stop_event, db)
            except Exception as exc:  # pragma: no cover - defensive boundary
                outcome = {
                    "success": False,
                    "error": "pilot_exception",
                    "history_detail": f"投递执行异常：{type(exc).__name__}",
                }
            result["attempted"] += 1
            risk = str(outcome.get("risk") or "")
            if outcome.get("success"):
                update_job_status(db, job_id, "sent")
                add_history(db, job_id, "sent", str(outcome.get("history_detail") or "试点自动投递成功"))
                result["sent"] += 1
                if outcome.get("already_sent"):
                    result["already"] += 1
            else:
                error = str(outcome.get("error") or "unknown")
                update_job_status(db, job_id, "error")
                add_history(db, job_id, "error", str(outcome.get("history_detail") or f"投递失败：{error}"))
                result["failed"] += 1
                if error in {"captcha", "rate_limit", "blocked", "persistent_risk_lock", "daily_platform_page_limit"} or risk:
                    add_risk_event(db, error or risk, f"{platform} 投递触发风控")
                    set_platform_safety_lock(db, error or risk, minutes=_lock_minutes(config))
                    if stop_event is not None:
                        stop_event.set()
                    break
            _progress(config, {
                "status": "running",
                "total": budget.total,
                "attempted": result["sent"] + result["failed"] + result["deferred"],
                "sent": result["sent"],
                "failed": result["failed"],
                "deferred": result["deferred"],
                "current_job": None,
                "platform": platform,
            })
        return result
    finally:
        db.close()


def delivery_pilot_allowed(config: dict) -> bool:
    delivery = config.get("delivery", {}) if isinstance(config.get("delivery"), dict) else {}
    return bool(
        delivery.get("auto_apply_pilot_enabled") is True
        and delivery.get("parallel_platforms_enabled") is True
    )


def deliver_pilot(config: dict) -> dict[str, Any]:
    """Deliver selected jobs across platforms with one worker per platform."""
    db = _open_db(config)
    try:
        return _deliver_pilot_impl(config, db)
    finally:
        db.close()


def _deliver_pilot_impl(config: dict, db) -> dict[str, Any]:
    selected = {str(job_id) for job_id in config.get("_workbench_job_ids", []) if str(job_id)}
    if not selected:
        return {"stop_reason": "no_jobs", "requested_count": 0, "sent_count": 0, "failed_count": 0, "deferred_count": 0}
    placeholders = ",".join("?" for _ in selected)
    rows = db.execute(
        f"""SELECT * FROM jobs
            WHERE deleted_at IS NULL AND id IN ({placeholders})
              AND status IN ('ready', 'approved')""",
        list(selected),
    ).fetchall()
    jobs = [dict(row) for row in rows]

    stop_event = config.get("_workbench_stop_event")
    platform_map: dict[str, list[dict]] = {platform: [] for platform in SUPPORTED_PLATFORMS}
    unsupported: list[dict] = []
    for job in jobs:
        platform = str(job.get("source_platform") or "boss")
        if platform not in SUPPORTED_PLATFORMS:
            unsupported.append(job)
            continue
        if platform == "boss" and not str(job.get("greeting") or "").strip():
            unsupported.append(job)
            continue
        platform_map[platform].append(job)

    report: dict[str, Any] = {
        "requested_count": len(selected),
        "eligible_count": len(jobs),
        "attempted_count": 0,
        "sent_count": 0,
        "failed_count": 0,
        "deferred_count": len(selected),
        "quota_deferred_count": 0,
        "already_sent": 0,
        "daily_limit": 0,
        "remaining_quota": 0,
        "stop_reason": None,
    }
    config["_workbench_send_report"] = report
    if unsupported:
        report["failed_count"] = len(unsupported)
        for job in unsupported:
            _notify(config, f"跳过 {_job_label(job)}：BOSS 需要招呼语，智联/51job 需要受支持岗位链接", error=True)

    # Same send-window and random-day-off guards as the normal BOSS sender.
    try:
        window_checker = SendWindowChecker(config.get("throttle", {}).get("send_windows", []))
        if not window_checker.is_active():
            report["stop_reason"] = "outside_window"
            report["deferred_count"] = len(jobs)
            return report
        if should_take_day_off(config.get("throttle", {}).get("day_off_probability", 0.05)):
            add_risk_event(db, "day_off", "随机休息日")
            report["stop_reason"] = "day_off"
            report["deferred_count"] = len(jobs)
            return report
    except Exception:  # defensive: never let time guards block pilot permanently
        pass

    today = db.execute(
        "SELECT COUNT(*) AS cnt FROM history WHERE action='sent' AND date(created_at)=date('now')"
    ).fetchone() if db else None
    already = int(today["cnt"] if today else 0)
    daily_limit = int(config.get("throttle", {}).get("daily_limit", 30) or 30)
    remaining_quota = max(daily_limit - already, 0)
    report["already_sent"] = already
    report["daily_limit"] = daily_limit
    report["remaining_quota"] = remaining_quota
    report["deferred_count"] = len(selected)
    if remaining_quota <= 0:
        report["quota_deferred_count"] = len(selected)
        report["stop_reason"] = "daily_limit"
        return report

    active_platforms = [platform for platform, items in platform_map.items() if items]
    if not active_platforms:
        report["stop_reason"] = "no_eligible_jobs"
        return report
    report["remaining_quota"] = remaining_quota
    budget = _Budget(remaining=min(remaining_quota, len(jobs)), total=len(jobs))
    # The pilot is deliberately limited to one worker per platform so the
    # configured daily quota is never exceeded by multiple platform workers.
    worker_count = min(len(active_platforms), 3)
    summary: dict[str, int] = {"attempted": 0, "sent": 0, "failed": 0, "deferred": 0, "already": 0}
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="bosshunter-pilot") as executor:
        futures: dict[Future[dict[str, int]], str] = {
            executor.submit(
                _run_platform_worker,
                platform,
                platform_map[platform],
                config,
                stop_event,
                budget,
            ): platform
            for platform in active_platforms
        }
        while futures:
            done, _ = wait(futures, timeout=0.2, return_when=FIRST_COMPLETED)
            if _stop_requested(stop_event) and not done:
                # Workers already check the event between jobs. Keep waiting for
                # the short browser op that is in flight rather than abandoning
                # a worker that may be mid-click.
                continue
            if not done:
                continue
            for future in done:
                platform = futures.pop(future)
                try:
                    part = future.result()
                except Exception as exc:  # pragma: no cover - defensive
                    part = {"attempted": 0, "sent": 0, "failed": 0, "deferred": len(platform_map[platform]), "already": 0}
                    _notify(config, f"{_platform_label(platform)} 投递试点异常：{type(exc).__name__}", error=True)
                for key in ("attempted", "sent", "failed", "deferred", "already"):
                    summary[key] += int(part.get(key) or 0)

    report.update({
        "attempted_count": summary["attempted"],
        "sent_count": summary["sent"],
        "failed_count": summary["failed"],
        "deferred_count": max(len(selected) - summary["sent"] - summary["failed"], 0),
        "quota_deferred_count": max(summary["deferred"], 0),
        "already_sent": summary["already"],
    })
    if _stop_requested(stop_event):
        report["stop_reason"] = report.get("stop_reason") or "stopped"
    elif summary["failed"] and not summary["sent"]:
        report["stop_reason"] = "failed"
    console.print(f"\n[green]✓ 试点自动投递：成功 {summary['sent']}，失败 {summary['failed']}，待处理 {report['deferred_count']}[/green]")
    return report
