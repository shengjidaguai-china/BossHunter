"""Explicit, reviewed outreach to previously contacted jobs without HR replies."""

from __future__ import annotations

import json
import re
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bosshunter.cancellation import get_stop_event
from bosshunter.db import MAX_JOB_IDS, add_history, get_db
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop
from bosshunter.throttle import RequestThrottle, SendWindowChecker, should_take_day_off


REPLY_ACTIONS = (
    "hr_reply_detected", "reply_pending", "reply_dismissed", "replied", "auto_replied",
    "needs_resume", "resume_sent", "resume_failed", "rejected", "recontact_uncertain",
)


def recontact_hours(value: Any = 48) -> int:
    try:
        hours = int(value)
        if isinstance(value, bool) or float(value) != hours or not 1 <= hours <= 720:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise ValueError("再次投递间隔必须是 1 至 720 的整数小时") from None
    return hours


def recontact_job_ids(value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("岗位 ID 必须是字符串数组")
    ids = list(dict.fromkeys(item.strip() for item in value if item.strip()))
    if not ids or len(ids) > MAX_JOB_IDS:
        raise ValueError(f"请选择 1 至 {MAX_JOB_IDS} 个岗位")
    return ids


def get_recontact_candidates(conn, min_hours: Any = 48, job_ids: list[str] | None = None) -> list[dict]:
    """Use immutable contact history, never job.updated_at, as the cooldown clock."""
    return _get_recontact_jobs(conn, min_hours, job_ids, sent_today=False)


def get_recontact_sent_today(conn) -> list[dict]:
    """Read-only daily bucket; a successful first contact or follow-up consumes the day."""
    return _get_recontact_jobs(conn, 48, None, sent_today=True)


def _business_date() -> str:
    return datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def _get_recontact_jobs(conn, min_hours: Any, job_ids: list[str] | None, *, sent_today: bool) -> list[dict]:
    hours = recontact_hours(min_hours)
    params: list[Any] = [_business_date(), *REPLY_ACTIONS]
    if sent_today:
        timing = "AND c.sent_today_at IS NOT NULL"
    else:
        timing = "AND c.sent_today_at IS NULL AND c.last_contact_at <= datetime('now', ?)"
        params.append(f"-{hours} hours")
    selection = ""
    if job_ids is not None:
        ids = recontact_job_ids(job_ids)
        selection = f"AND j.id IN ({','.join('?' for _ in ids)})"
        params.extend(ids)
    rows = conn.execute(
        f"""
        WITH contact AS (
            SELECT job_id, MIN(CASE WHEN action='sent' THEN datetime(created_at) END) AS first_sent_at,
                   MAX(datetime(created_at)) AS last_contact_at,
                   SUM(CASE WHEN action='follow_up_sent' THEN 1 ELSE 0 END) AS recontact_count,
                   MAX(CASE WHEN date(created_at, '+8 hours')=? THEN datetime(created_at) END) AS sent_today_at
            FROM history WHERE action IN ('sent', 'follow_up_sent') GROUP BY job_id
        )
        SELECT j.*, c.first_sent_at, c.last_contact_at, c.recontact_count, c.sent_today_at,
               (SELECT detail FROM history original WHERE original.job_id=j.id
                AND original.action='sent' ORDER BY original.id LIMIT 1) AS first_greeting_preview
        FROM jobs j JOIN contact c ON c.job_id=j.id
        WHERE j.deleted_at IS NULL AND j.status IN ('sent', 'follow_up_sent')
          AND COALESCE(j.source_platform, 'boss')='boss'
          AND TRIM(COALESCE(j.greeting, ''))!=''
          AND COALESCE(j.greeting_selection, '')!='pending'
          AND c.first_sent_at IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM history h WHERE h.job_id=j.id
                AND h.action IN ({','.join('?' for _ in REPLY_ACTIONS)})
          )
          {timing}
          {selection}
        ORDER BY c.last_contact_at, j.score DESC, j.id
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def _outgoing_text(value: Any) -> str:
    """Ignore BOSS delivery labels included before the actual outgoing bubble."""
    return re.sub(r"^(?:已读|送达|未读)\s+", "", str(value or "").strip(), count=1)


def _message_state(messages: Any, job: dict) -> str:
    from bosshunter.executor.monitor import _reconcile_conversation_messages

    if not isinstance(messages, list) or not messages or any(not isinstance(msg, dict) for msg in messages):
        return "unreadable"
    messages = _reconcile_conversation_messages(messages, job)
    if any(msg.get("sender") == "hr" for msg in messages):
        return "hr_replied"
    if any(msg.get("sender") not in {"me", "system"} for msg in messages):
        return "unreadable"
    # Seeing the initial greeting establishes that the visible chat includes its beginning.
    preview = "".join(str(job.get("first_greeting_preview") or job.get("greeting") or "").split())[:40]
    if not preview or not any(
        msg.get("sender") == "me" and "".join(_outgoing_text(msg.get("text")).split()).startswith(preview)
        for msg in messages
    ):
        return "unreadable"
    return "unreplied"


def _read_messages(target_id: str) -> Any:
    from bosshunter.executor import monitor

    raw = monitor.evaluate(target_id, monitor.JS_EXTRACT_CONVERSATION)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return None


def _submit_checked_message(target_id: str, message: str) -> str:
    """Read current HR bubbles and submit in one browser turn, closing the check/send race."""
    from bosshunter.executor import monitor

    extractor = monitor.JS_EXTRACT_CONVERSATION.strip().rstrip(";")
    script = f"""(() => {{
        const messages = JSON.parse({extractor});
        if (!Array.isArray(messages) || !messages.length) return JSON.stringify({{state:'unreadable'}});
        if (messages.some(msg => msg.sender === 'hr')) return JSON.stringify({{state:'hr_replied'}});
        if (messages.some(msg => !['me','system'].includes(msg.sender))) return JSON.stringify({{state:'unreadable'}});
        const input = document.querySelector('#chat-input');
        if (!input || !messages.some(msg => msg.sender === 'me')) return JSON.stringify({{state:'unreadable'}});
        let vue = null;
        for (let el = input, i = 0; el && i < 15; el = el.parentElement, i++) {{
            if (el.__vue__) {{ vue = el.__vue__; break; }}
        }}
        if (!vue || !vue._data || typeof vue.handleSubmit !== 'function') return JSON.stringify({{state:'unreadable'}});
        input.innerText = {json.dumps(message)};
        vue._data.enableSubmit = true;
        vue.handleSubmit();
        return JSON.stringify({{state:'submitted'}});
    }})()"""
    raw = monitor.evaluate(target_id, script)
    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
        return str(result.get("state") or "uncertain") if isinstance(result, dict) else "uncertain"
    except (ValueError, TypeError):
        return "uncertain"


def _record_hr_reply(conn, job: dict) -> None:
    with conn:
        conn.execute(
            "UPDATE jobs SET status='replied', updated_at=CURRENT_TIMESTAMP WHERE id=? AND deleted_at IS NULL AND status IN ('sent','follow_up_sent')",
            (job["id"],),
        )
        conn.execute(
            "INSERT INTO history(job_id,action,detail) VALUES (?, 'hr_reply_detected', ?)",
            (job["id"], "再次投递前发现 HR 已回复，已跳过发送，请在监测执行页查看。"),
        )


def _record_job_closed(conn, job: dict) -> None:
    """Remove a confirmed closed job from future recontact candidates."""
    with conn:
        conn.execute(
            """
            UPDATE jobs
            SET status='skipped', last_error='岗位已关闭或下架',
                last_error_code='job_closed', updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND deleted_at IS NULL AND status IN ('sent','follow_up_sent')
            """,
            (job["id"],),
        )
        conn.execute(
            "INSERT INTO history(job_id,action,detail) VALUES (?, 'job_closed', ?)",
            (job["id"], "再次投递前重新核验：岗位已关闭或下架，已跳过发送。"),
        )


def resolve_recontact_greeting(config: dict, override: Any = "") -> str:
    """Pin a reviewed override or the configured greeting, never a historic job greeting."""
    if not isinstance(override, str):
        raise ValueError("招呼语必须是文本")
    text = override.strip() or str(config.get("profile", {}).get("fixed_greeting") or "").strip()
    if not text:
        raise ValueError("请先在配置中填写打招呼语，或修改本次招呼语后再发送")
    if len(text) > 300:
        raise ValueError("招呼语不能超过300字，请修改后再发送")
    return text


def send_recontacts(config: dict, *, db_path: Path | None = None) -> dict:
    """Recheck and send selected unreplied jobs through the normal sender path."""
    from bosshunter.executor import monitor, sender

    ids = recontact_job_ids(config.get("_recontact_job_ids"))
    hours = recontact_hours(config.get("_recontact_min_hours", 48))
    uniform = resolve_recontact_greeting(config, config.get("_recontact_greeting", ""))
    report = {"requested": len(ids), "sent": 0, "skipped_hr": 0, "skipped_changed": 0,
              "skipped_closed": 0, "unverified": 0, "failed": 0, "deferred": 0, "stop_reason": ""}
    stop_event = get_stop_event(config)
    log = config.get("_workbench_log")

    def emit(text: str) -> None:
        if callable(log):
            log(text)

    conn = get_db(db_path)
    throttle_cfg = config.get("throttle", {})
    window = SendWindowChecker(throttle_cfg.get("send_windows", []))
    send_throttle = RequestThrottle(throttle_cfg.get("interval_min", 60), throttle_cfg.get("interval_max", 180))
    access = PlatformAccessGuard(conn, config, "recontact")
    sender_config = dict(throttle_cfg)
    sender_config.update({
        "_workbench_stop_event": stop_event,
        "_workbench_log": log,
        "_platform_access_guard": access,
        "_send_window_checker": window,
        "_recontact_existing_only": True,
        "_recontact_chat_button_attempts": 8,
    })
    activity = config.get("_workbench_greeting_activity")
    try:
        if should_take_day_off(throttle_cfg.get("day_off_probability", 0.05)):
            report["stop_reason"] = "day_off"
            return report
        for index, job_id in enumerate(ids):
            if stop_event and stop_event.is_set():
                report["stop_reason"] = "stopped"
                break
            if not window.is_active():
                report["stop_reason"] = "outside_window"
                break
            access.ensure_unlocked()
            daily_count = conn.execute(
                "SELECT COUNT(*) FROM history WHERE action IN ('sent','follow_up_sent') AND date(created_at)=date('now')"
            ).fetchone()[0]
            if daily_count >= int(throttle_cfg.get("daily_limit", 30)):
                report["stop_reason"] = "daily_limit"
                break
            if send_throttle.has_marked_request and send_throttle.wait(stop_event):
                report["stop_reason"] = "stopped"
                break
            if not window.is_active():
                report["stop_reason"] = "outside_window"
                break
            target_id = None
            with activity(job_id, "sending") if callable(activity) else nullcontext(True) as acquired:
                if not acquired:
                    report["skipped_changed"] += 1
                    continue
                current = get_recontact_candidates(conn, hours, [job_id])
                if not current:
                    report["skipped_changed"] += 1
                    continue
                job = current[0]
                text = uniform
                if not text or len(text) > 300:
                    report["failed"] += 1
                    continue
                emit(f"再次投递进度 {index + 1}/{len(ids)}：重新采集并核对 {job['company']}｜{job['title']}")
                failed_target_id = None
                sender_config["_recontact_before_send"] = lambda job_id=job_id: bool(
                    get_recontact_candidates(conn, hours, [job_id])
                )
                try:
                    result, failed_target_id = sender._send_greeting_once(job, text, sender_config)
                    error = str(result.get("error") or "")
                    if result.get("success"):
                        with conn:
                            conn.execute(
                                "UPDATE jobs SET status='follow_up_sent', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                (job_id,),
                            )
                            conn.execute(
                                "INSERT INTO history(job_id,action,detail) VALUES (?, 'follow_up_sent', ?)",
                                (job_id, json.dumps({"schema": "follow_up.manual.v1", "manual_reply": text}, ensure_ascii=False)),
                            )
                        send_throttle.mark()
                        report["sent"] += 1
                        emit(f"再次投递成功：{job['company']}｜{job['title']}")
                        continue
                    if error == "hr_replied":
                        _record_hr_reply(conn, job)
                        report["skipped_hr"] += 1
                        emit("HR 已回复，已跳过再次投递")
                        continue
                    if error == "job_page_unavailable":
                        _record_job_closed(conn, job)
                        report["skipped_closed"] += 1
                        emit("岗位已关闭或下架，已从再次投递队列移除")
                        continue
                    if error == "stopped":
                        report["stop_reason"] = "stopped"
                        break
                    if error == "candidate_changed":
                        report["skipped_changed"] += 1
                        emit("岗位状态或 HR 回复记录已变化，已跳过发送")
                        continue
                    if error in {"send_not_confirmed", "send_not_stable", "send_rejected_after_click"}:
                        add_history(conn, job_id, "recontact_uncertain", "再次联系的发送结果未确认，请手动检查对话；已暂停自动重试。")
                        report["failed"] += 1
                        report["stop_reason"] = "send_unconfirmed"
                        break
                    if error in {"daily_platform_page_limit", "persistent_risk_lock", "captcha", "rate_limit", "blocked"}:
                        report["stop_reason"] = error
                        break
                    if error in {"conversation_unverified", "existing_chat_popup", "no_chat_button", "no_chat_input",
                                 "chat_navigation_timeout", "open_page_failed"}:
                        report["unverified"] += 1
                        emit(f"未能确认 {job['company']}｜{job['title']} 的已有会话，已跳过；尚未发送")
                        continue
                    report["unverified"] += 1
                    emit(f"再次投递未完成（{error or 'unknown'}），已跳过；尚未确认发送")
                finally:
                    if failed_target_id:
                        sender.close_tab(failed_target_id)
        return report
    except (PlatformSafetyStop, monitor.MonitorRiskDetected) as exc:
        report["stop_reason"] = getattr(exc, "reason", getattr(exc, "kind", "platform_locked"))
        if isinstance(exc, monitor.MonitorRiskDetected):
            access.lock(report["stop_reason"])
        return report
    finally:
        report["deferred"] = max(0, len(ids) - sum(report[key] for key in ("sent", "skipped_hr", "skipped_changed", "skipped_closed", "unverified", "failed")))
        conn.close()
