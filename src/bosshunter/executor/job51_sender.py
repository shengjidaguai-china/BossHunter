"""Guarded 51job resume apply.

51job delivery uses the already-prepared online resume on a logged-in account.
It never uploads attachments, never fills unknown forms, and only records a
job as sent when the page explicitly shows success or an already-applied state.
WAF/slider pages wait for the user to finish verification in the retained tab.
"""

from __future__ import annotations

import json
import random
import time
from threading import Event
from typing import Any
from urllib.parse import urlparse

from rich.console import Console

from bosshunter.browser import close_tab, evaluate, new_tab, wait_for_load
from bosshunter.db import add_history, add_risk_event, get_db, set_platform_safety_lock, update_job_status
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop
from bosshunter.throttle import SendWindowChecker, should_take_day_off

console = Console()

PLATFORM = "51job"
ALLOWED_DOMAIN = "51job.com"
RENDER_POLL_ATTEMPTS = 10
RENDER_POLL_INTERVAL_SECONDS = 0.75
POST_ACTION_WAIT_SECONDS = 1.2
MAX_APPLY_STEPS = 6


def _open_db(config: dict):
    from pathlib import Path

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


def _duration_seconds(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, 0.0)


def _lock_minutes(config: dict) -> int:
    try:
        return max(int(config.get("safety", {}).get("risk_lock_minutes", 10) or 10), 1)
    except (TypeError, ValueError):
        return 10


def _job_label(job: dict) -> str:
    return f"{job.get('company') or '未知公司'}｜{job.get('title') or '未知岗位'}"


def _collection_cfg(config: dict) -> dict[str, Any]:
    collection = config.get("collection") if isinstance(config, dict) else None
    return collection if isinstance(collection, dict) else {}


def _verification_timeout(config: dict) -> float:
    return _duration_seconds(
        _collection_cfg(config).get("job51_manual_verification_timeout_seconds"),
        300.0,
    )


def _verification_poll_interval(config: dict) -> float:
    return max(
        _duration_seconds(
            _collection_cfg(config).get("job51_manual_verification_poll_interval_seconds"),
            2.0,
        ),
        0.5,
    )


def _apply_delay_range(config: dict) -> tuple[float, float]:
    collection = _collection_cfg(config)
    minimum = _duration_seconds(collection.get("job51_detail_delay_min_seconds"), 12.0)
    maximum = _duration_seconds(collection.get("job51_detail_delay_max_seconds"), 20.0)
    minimum = max(minimum, 1.0)
    maximum = max(maximum, minimum)
    return minimum, maximum


JS_SCAN = r"""
(() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    };
    const compact = String((document.body && document.body.innerText) || '').replace(/\s+/g, '');
    const pageText = compact + ' ' + String(document.title || '');
    const wafChallenge = Boolean(document.querySelector('textarea#renderData, meta[name*="aliyun_waf"], script[name*="aliyunwaf"]'));
    if (wafChallenge || /滑动验证页面|请按住滑块|访问验证|访问频繁|人机验证|安全验证|请完成验证/.test(pageText)) {
        return JSON.stringify({kind: 'waf'});
    }
    if (/当前职位审核中或已下线|职位已下线|岗位已下线|职位已关闭|岗位已关闭|已停止招聘|招聘已结束/.test(compact)) {
        return JSON.stringify({kind: 'job_closed'});
    }
    if (/登录后投递|登录后申请|扫码登录|账号登录|请先登录|登录前程无忧|登录已过期|登录失效/.test(compact)
        && !/立即申请|申请职位|投递简历/.test(compact)) {
        return JSON.stringify({kind: 'login_required'});
    }
    const success = /申请成功|投递成功|职位申请成功|您已成功申请|已成功投递|投递完成/.test(compact);
    const already = /您已经申请过|请勿重复申请|已申请该职位|已投递该职位|今日已投递/.test(compact);
    const applyButtons = Array.from(document.querySelectorAll('button, a, [role="button"], input[type=button], input[type=submit], [class*="apply"], [class*="jobapply"], [class*="deliver"], [class*="but_sq"]'))
        .map((el) => {
            const text = String((el.innerText || el.value || el.textContent || '')).replace(/\s+/g, ' ').trim();
            return {el, text, visible: visible(el)};
        })
        .filter((item) => item.visible);
    const appliedButton = applyButtons.find((item) => /^(已申请|已投递|已申请该职位|已投递该职位)$/.test(item.text));
    if (success || already || appliedButton) {
        return JSON.stringify({kind: success ? 'success' : 'already_applied', text: appliedButton ? appliedButton.text : ''});
    }
    const resumeMissing = /请完善简历|简历不完整|缺少简历|请先创建简历|在线简历不完整|请先填写简历/.test(compact);
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"], .el-dialog, .el-overlay, .modal, .dialog, [class*="apply"], [class*="resume"]'))
        .filter((el) => visible(el) && String(el.innerText || '').length < 1800);
    const resumeDialog = dialogs.find((el) => {
        const text = String(el.innerText || '').replace(/\s+/g, '');
        return /选择简历|投递简历|申请职位|确认申请|立即申请/.test(text) && /简历/.test(text);
    }) || dialogs.find((el) => /简历/.test(String(el.innerText || '')) && /申请|投递|确认|确定/.test(String(el.innerText || '')));
    const resumeItems = resumeDialog
        ? Array.from(resumeDialog.querySelectorAll('label, li, [class*="resume"], [role="radio"], .el-radio'))
            .filter((el) => visible(el) && /简历/.test(String(el.innerText || '')) && !/上传|附件|新建|完善/.test(String(el.innerText || '')))
        : [];
    if (resumeDialog && resumeItems.length) {
        return JSON.stringify({kind: 'resume_ready', resumeCount: resumeItems.length});
    }
    if (resumeMissing && !resumeItems.length) {
        return JSON.stringify({kind: 'resume_missing'});
    }
    const exactApply = applyButtons.find((item) => /^(立即申请|申请职位|立即申请职位|投递简历|投递该职位|投递职位|立即投递|申请该职位|申请)$/.test(item.text));
    if (exactApply) {
        return JSON.stringify({kind: 'action_ready', text: exactApply.text});
    }
    return JSON.stringify({kind: 'no_action'});
})()
"""


JS_CLICK_APPLY = r"""
(() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    };
    const matches = Array.from(document.querySelectorAll('button, a, [role="button"], input[type=button], input[type=submit], [class*="apply"], [class*="jobapply"], [class*="deliver"], [class*="but_sq"]'))
        .map((el) => {
            const text = String((el.innerText || el.value || el.textContent || '')).replace(/\s+/g, ' ').trim();
            return {el, text, visible: visible(el)};
        })
        .filter((item) => item.visible && /^(立即申请|申请职位|立即申请职位|投递简历|投递该职位|投递职位|立即投递|申请该职位|申请)$/.test(item.text));
    if (!matches.length) return JSON.stringify({clicked: false, reason: 'no_action_button'});
    const preferred = matches.find((item) => /apply-btn/.test(String(item.el.className || '')))
        || matches.find((item) => item.text !== '申请')
        || matches[0];
    try {
        preferred.el.scrollIntoView({block: 'center'});
        preferred.el.click();
        return JSON.stringify({clicked: true, text: preferred.text});
    } catch (error) {
        return JSON.stringify({clicked: false, reason: String(error && error.message || error)});
    }
})()
"""


JS_HANDLE_RESUME = r"""
(() => {
    const visible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return !!(rect.width && rect.height && style.display !== 'none'
            && style.visibility !== 'hidden' && style.pointerEvents !== 'none');
    };
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"], .el-dialog, .el-overlay, .modal, .dialog, [class*="apply"], [class*="resume"], body > div'))
        .filter((el) => visible(el));
    const dialog = [...dialogs].reverse().find((el) => {
        const text = String(el.innerText || '').replace(/\s+/g, '');
        return text.length < 1800 && /简历/.test(text) && /申请|投递|确认|确定/.test(text);
    });
    if (!dialog) return JSON.stringify({handled: false, reason: 'no_dialog'});
    const resumeItems = Array.from(dialog.querySelectorAll('label, li, [class*="resume"], [role="radio"], .el-radio, input[type=radio]'))
        .filter((el) => visible(el) && /简历/.test(String(el.innerText || el.value || '')) && !/上传|附件|新建|完善/.test(String(el.innerText || el.value || '')));
    if (!resumeItems.length) {
        const compact = String(dialog.innerText || '').replace(/\s+/g, '');
        if (/请完善简历|请先创建简历|缺少简历|请上传简历/.test(compact)) {
            return JSON.stringify({handled: false, reason: 'resume_missing'});
        }
    } else {
        const selected = resumeItems.find((el) => /checked|is-checked|selected|active/.test(String(el.className || ''))) || resumeItems[0];
        try { selected.click(); } catch (_) {}
    }
    const buttons = Array.from(dialog.querySelectorAll('button, a, [role="button"], input[type=button], input[type=submit], [class*="apply"], [class*="jobapply"], [class*="deliver"], [class*="but_sq"]')).filter(visible);
    const confirm = buttons.find((el) => /^(立即申请|立即申请职位|确认申请|确认投递|立即投递|继续申请|确定|确认)$/.test(
        String((el.innerText || el.value || '')).replace(/\s+/g, ' ').trim()
    ));
    if (!confirm) return JSON.stringify({handled: false, reason: 'no_confirm'});
    try {
        confirm.click();
        return JSON.stringify({handled: true, selected: resumeItems.length > 0});
    } catch (error) {
        return JSON.stringify({handled: false, reason: String(error && error.message || error)});
    }
})()
"""


def _scan(target_id: str) -> dict[str, Any]:
    return _parse_result(evaluate(target_id, JS_SCAN))


def _wait_for_page(target_id: str, config: dict, stop_event: Event | None) -> dict[str, Any]:
    """Wait for the SPA/WAF shell to become an actionable job page."""
    render_deadline = time.monotonic() + (RENDER_POLL_ATTEMPTS * RENDER_POLL_INTERVAL_SECONDS)
    waf_deadline = time.monotonic() + _verification_timeout(config)
    notified_waf = False
    last = {"kind": "no_action"}
    while True:
        if _stop_requested(stop_event):
            return {"kind": "stopped"}
        last = _scan(target_id)
        kind = str(last.get("kind") or "no_action")
        if kind == "waf":
            if not notified_waf:
                _notify(config, "51job 详情页需要人工验证，请在保留的浏览器标签页完成验证，完成后将自动继续投递")
                notified_waf = True
            if time.monotonic() >= waf_deadline:
                last["keep_tab"] = True
                last["kind"] = "waf_timeout"
                return last
            if _sleep_or_stop(_verification_poll_interval(config), stop_event):
                return {"kind": "stopped"}
            continue
        if kind != "no_action":
            if notified_waf:
                _notify(config, "51job 人工验证已完成，继续投递当前岗位")
            return last
        if notified_waf:
            # After a WAF challenge the SPA still needs a short render window.
            render_deadline = time.monotonic() + (RENDER_POLL_ATTEMPTS * RENDER_POLL_INTERVAL_SECONDS)
            notified_waf = False
        if time.monotonic() >= render_deadline:
            return last
        if _sleep_or_stop(RENDER_POLL_INTERVAL_SECONDS, stop_event):
            return {"kind": "stopped"}


def apply_job51_once(job: dict, config: dict, stop_event: Event | None, db) -> dict[str, Any]:
    """Open one 51job detail page and apply with the existing online resume."""
    url = str(job.get("url") or "").strip()
    try:
        hostname = (urlparse(url).hostname or "").lower()
    except ValueError:
        hostname = ""
    if not url or not hostname or ALLOWED_DOMAIN not in hostname:
        return {
            "success": False,
            "error": "unsafe_job_url",
            "history_detail": "岗位链接域名与 51job 不符，未自动投递",
            "skip_backoff": True,
        }
    guard = PlatformAccessGuard(db, config, "deliver", PLATFORM)
    try:
        guard.ensure_unlocked()
        guard.reserve("job_page")
    except PlatformSafetyStop as exc:
        return {
            "success": False,
            "error": exc.reason,
            "history_detail": "平台访问受限或风险锁未结束",
            "risk": exc.reason,
        }
    target_id = new_tab(url, background=True)
    if not target_id:
        return {"success": False, "error": "open_page_failed", "history_detail": "无法打开 51job 岗位页", "skip_backoff": True}
    keep_tab = False
    try:
        wait_for_load(target_id, timeout=15)
        if _stop_requested(stop_event):
            return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
        state = _wait_for_page(target_id, config, stop_event)
        kind = str(state.get("kind") or "no_action")
        if state.get("keep_tab"):
            keep_tab = True
        if kind == "stopped":
            return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
        if kind == "waf_timeout":
            keep_tab = True
            return {
                "success": False,
                "error": "captcha",
                "history_detail": "51job 人工验证超时，详情页已保留，请完成验证后重试",
                "risk": "captcha",
                "keep_tab": True,
            }
        if kind == "login_required":
            return {"success": False, "error": "login_required", "history_detail": "51job 登录状态失效或要求登录", "skip_backoff": True}
        if kind == "job_closed":
            return {"success": False, "error": "job_closed", "history_detail": "岗位已关闭或下架", "skip_backoff": True}
        if kind in {"success", "already_applied"}:
            return {"success": True, "already_sent": kind == "already_applied", "history_detail": "51job 显示该岗位已经投递或申请成功"}
        if kind == "resume_missing":
            return {"success": False, "error": "manual_resume_required", "history_detail": "51job 要求完善或创建在线简历，未代替操作", "skip_backoff": True}

        for _ in range(MAX_APPLY_STEPS):
            if _stop_requested(stop_event):
                return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
            kind = str(state.get("kind") or "no_action")
            if kind in {"success", "already_applied"}:
                return {"success": True, "already_sent": kind == "already_applied", "history_detail": "页面显示投递成功"}
            if kind == "waf":
                state = _wait_for_page(target_id, config, stop_event)
                if state.get("keep_tab") or str(state.get("kind") or "") == "waf_timeout":
                    keep_tab = True
                    return {
                        "success": False,
                        "error": "captcha",
                        "history_detail": "点击后出现验证码或访问验证，详情页已保留",
                        "risk": "captcha",
                        "keep_tab": True,
                    }
                continue
            if kind == "login_required":
                return {"success": False, "error": "login_required", "history_detail": "点击后要求登录", "skip_backoff": True}
            if kind == "job_closed":
                return {"success": False, "error": "job_closed", "history_detail": "岗位已关闭或下架", "skip_backoff": True}
            if kind == "resume_missing":
                return {"success": False, "error": "manual_resume_required", "history_detail": "51job 要求完善或创建在线简历，未代替操作", "skip_backoff": True}
            if kind == "resume_ready":
                handled = _parse_result(evaluate(target_id, JS_HANDLE_RESUME))
                if not handled.get("handled"):
                    reason = str(handled.get("reason") or "")
                    if reason == "resume_missing":
                        return {"success": False, "error": "manual_resume_required", "history_detail": "未找到可投递的在线简历，未代替上传附件", "skip_backoff": True}
                    return {"success": False, "error": "resume_confirm_failed", "history_detail": "简历选择框无法确认，未记录为已投递", "skip_backoff": True}
            elif kind == "action_ready":
                clicked = _parse_result(evaluate(target_id, JS_CLICK_APPLY))
                if not clicked.get("clicked"):
                    return {"success": False, "error": "apply_click_failed", "history_detail": "未点击到 51job 申请按钮", "skip_backoff": True}
            else:
                return {"success": False, "error": "no_apply_button", "history_detail": "页面未找到可识别的申请按钮", "skip_backoff": True}
            if _sleep_or_stop(POST_ACTION_WAIT_SECONDS, stop_event):
                return {"success": False, "error": "stopped", "history_detail": "用户已请求停止", "skip_backoff": True}
            state = _scan(target_id)

        kind = str(state.get("kind") or "unverified")
        if kind in {"success", "already_applied"}:
            return {"success": True, "already_sent": kind == "already_applied", "history_detail": "页面显示投递成功"}
        if kind == "resume_missing":
            return {"success": False, "error": "manual_resume_required", "history_detail": "点击后平台要求完善或上传简历，未代替操作", "skip_backoff": True}
        return {"success": False, "error": "unverified", "history_detail": "已尝试申请但页面未能确认成功，未记录为已投递", "skip_backoff": True}
    finally:
        if not keep_tab:
            close_tab(target_id)


def deliver_job51(config: dict) -> dict[str, Any]:
    """Sequentially apply to selected 51job jobs with the existing online resume."""
    db = _open_db(config)
    try:
        return _deliver_job51_impl(config, db)
    finally:
        db.close()


def _deliver_job51_impl(config: dict, db) -> dict[str, Any]:
    stop_event = config.get("_workbench_stop_event") if isinstance(config.get("_workbench_stop_event"), Event) else None
    selected_ids = [str(job_id) for job_id in config.get("_workbench_job_ids", []) if str(job_id)]
    report: dict[str, Any] = {
        "requested_count": len(selected_ids),
        "eligible_count": 0,
        "attempted_count": 0,
        "sent_count": 0,
        "failed_count": 0,
        "deferred_count": len(selected_ids),
        "quota_deferred_count": 0,
        "already_sent": 0,
        "daily_limit": 0,
        "remaining_quota": 0,
        "stop_reason": None,
    }
    config["_workbench_send_report"] = report
    if not selected_ids:
        report["stop_reason"] = "no_eligible_jobs"
        return report

    placeholders = ",".join("?" for _ in selected_ids)
    rows = db.execute(
        f"""SELECT * FROM jobs
            WHERE deleted_at IS NULL AND id IN ({placeholders})
            ORDER BY score DESC""",
        selected_ids,
    ).fetchall()
    by_id = {str(row["id"]): dict(row) for row in rows}
    jobs = [by_id[job_id] for job_id in selected_ids if job_id in by_id]
    jobs = [
        job for job in jobs
        if str(job.get("source_platform") or "") == PLATFORM
        and str(job.get("status") or "") in {"ready", "approved", "error"}
    ]
    report["eligible_count"] = len(jobs)
    if not jobs:
        report["stop_reason"] = "no_eligible_jobs"
        return report

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
    except Exception:
        pass

    today = db.execute(
        "SELECT COUNT(*) AS cnt FROM history WHERE action='sent' AND date(created_at)=date('now')"
    ).fetchone()
    already = int(today["cnt"] if today else 0)
    daily_limit = int(config.get("throttle", {}).get("daily_limit", 30) or 30)
    remaining_quota = max(daily_limit - already, 0)
    report["already_sent"] = already
    report["daily_limit"] = daily_limit
    report["remaining_quota"] = remaining_quota
    if remaining_quota <= 0:
        report["quota_deferred_count"] = len(jobs)
        report["stop_reason"] = "daily_limit"
        return report

    delay_min, delay_max = _apply_delay_range(config)
    attempted = 0
    for index, job in enumerate(jobs):
        if _stop_requested(stop_event):
            report["stop_reason"] = report.get("stop_reason") or "stopped"
            break
        if remaining_quota <= 0:
            leftover = len(jobs) - index
            report["quota_deferred_count"] += leftover
            report["stop_reason"] = "daily_limit"
            break
        job_id = str(job.get("id") or "")
        current = {
            "id": job_id,
            "company": str(job.get("company") or "未知公司"),
            "title": str(job.get("title") or "未知岗位"),
        }
        _progress(config, {
            "status": "running",
            "total": len(jobs),
            "attempted": attempted,
            "sent": report["sent_count"],
            "failed": report["failed_count"],
            "deferred": report["quota_deferred_count"],
            "current_job": current,
            "platform": PLATFORM,
        })
        if index > 0:
            delay = delay_min if delay_max <= delay_min else random.uniform(delay_min, delay_max)
            _notify(config, f"51job 投递安全间隔 {delay:.1f} 秒")
            if _sleep_or_stop(delay, stop_event):
                report["stop_reason"] = "stopped"
                break
        outcome = apply_job51_once(job, config, stop_event, db)
        attempted += 1
        report["attempted_count"] = attempted
        if outcome.get("success"):
            update_job_status(db, job_id, "sent")
            add_history(db, job_id, "sent", str(outcome.get("history_detail") or "51job 简历投递成功"))
            report["sent_count"] += 1
            remaining_quota -= 1
            report["remaining_quota"] = remaining_quota
            if outcome.get("already_sent"):
                report["already_sent"] += 1
            _notify(config, f"已投递 {_job_label(job)}")
        else:
            error = str(outcome.get("error") or "unknown")
            update_job_status(db, job_id, "error")
            add_history(db, job_id, "error", str(outcome.get("history_detail") or f"51job 投递失败：{error}"))
            report["failed_count"] += 1
            _notify(config, f"投递失败 {_job_label(job)}：{outcome.get('history_detail') or error}", error=True)
            risk = str(outcome.get("risk") or "")
            if error in {"captcha", "rate_limit", "blocked", "persistent_risk_lock", "daily_platform_page_limit"} or risk:
                add_risk_event(db, error or risk, "51job 投递触发风控")
                set_platform_safety_lock(db, error or risk, minutes=_lock_minutes(config))
                report["stop_reason"] = error or risk
                if stop_event is not None:
                    stop_event.set()
                break
        _progress(config, {
            "status": "running",
            "total": len(jobs),
            "attempted": attempted,
            "sent": report["sent_count"],
            "failed": report["failed_count"],
            "deferred": report["quota_deferred_count"],
            "current_job": None,
            "platform": PLATFORM,
        })

    processed = report["sent_count"] + report["failed_count"]
    report["deferred_count"] = max(len(selected_ids) - processed, 0)
    if _stop_requested(stop_event):
        report["stop_reason"] = report.get("stop_reason") or "stopped"
    console.print(
        f"\n[green]✓ 51job 简历投递：成功 {report['sent_count']}，失败 {report['failed_count']}，待处理 {report['deferred_count']}[/green]"
    )
    return report
