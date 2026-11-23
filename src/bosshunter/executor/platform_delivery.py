"""Confirmed online resume delivery through a configured Ego task space."""

import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

from bosshunter.browser.ego import EgoTaskSpace, EgoTaskSpaceError
from bosshunter.collection.capabilities import platform_supports, delivery_action
from bosshunter.outsourcing import company_name_key
from bosshunter.job_filters import matching_blocked_company
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop

DETAIL_HOSTS = {
    "liepin": {"www.liepin.com", "wow.liepin.com"},
    "zhilian": {"www.zhaopin.com", "jobs.zhaopin.com"},
    "51job": {"jobs.51job.com"},
}


def platform_of(job):
    return job.get("source_platform") or "boss"


def daily_quota(config, platform):
    if platform == "boss":
        return int(config.get("throttle", {}).get("daily_limit", 30))
    value = config["delivery"]["platforms"][platform].get("daily_limit", 10)
    return max(value, 0) if type(value) is int else 0


def sent_today(db, platform):
    row = db.execute("""
        SELECT COUNT(*) FROM history h LEFT JOIN jobs j ON j.id = h.job_id
        WHERE h.action IN ('sent', 'delivery_reserved') AND date(h.created_at) = date('now')
        AND COALESCE(j.source_platform, 'boss') = ?
    """, (platform,)).fetchone()
    return row[0]


def _feedback_company_key(company):
    return "".join(unicodedata.normalize("NFKC", company or "").casefold().split())


def first_application_pending(db):
    return not db.execute("""
        SELECT 1 FROM history h JOIN jobs j ON j.id = h.job_id
        WHERE h.action = 'sent' AND j.source_platform IN ('liepin', 'zhilian', '51job') LIMIT 1
    """).fetchone()


def approval_error(db, job, config):
    current = db.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone()
    if not current or current["deleted_at"] is not None or current["status"] not in {"ready", "approved"}:
        return "job_unavailable"
    platform = platform_of(job)
    if (current["source_platform"] or "boss") != platform:
        return "confirmed_platform_changed"
    if not platform_supports(platform, "deliver", config):
        return "platform_disabled"
    if matching_blocked_company(current["company"], config.get("profile", {}).get("blocked_companies", [])):
        return "blocked_company"
    if any(current[field] != job.get(field) for field in ("company", "title", "url")):
        return "job_identity_changed"
    if job.get("status") and current["status"] != job["status"]:
        return "job_unavailable"
    if "greeting_selection" in job and current["greeting_selection"] != job["greeting_selection"]:
        return "approval_changed"
    if delivery_action(config, platform) == "greeting" and (current["greeting_selection"] == "pending" or current["greeting"] != job.get("greeting")):
        return "approval_changed"
    return None


def reserve_delivery(db, job, config):
    """Serialize quota, same-job protection and optional cross-platform company dedup."""
    platform = platform_of(job)
    key = company_name_key(job.get("company") or "")
    cross_platform_dedup = config.get("delivery", {}).get("cross_platform_dedup", False) is True
    with db:
        db.execute("BEGIN IMMEDIATE")
        if reason := approval_error(db, job, config):
            return reason
        if platform != "boss" and first_application_pending(db):
            selected = config.get("_workbench_job_ids", [])
            expected_platforms = config.get("_workbench_expected_platforms")
            expected_actions = config.get("_workbench_expected_actions")
            if (list(selected) != [job["id"]] or expected_platforms != {job["id"]: platform} or
                expected_actions != {job["id"]: delivery_action(config, platform)}):
                return "single_confirmed_pilot_required"
            pending = db.execute("""
                SELECT 1 FROM history h JOIN jobs j ON j.id = h.job_id
                WHERE h.action = 'delivery_reserved' AND j.source_platform != 'boss' LIMIT 1
            """).fetchone()
            if pending:
                return "pilot_pending"
        if sent_today(db, platform) >= daily_quota(config, platform):
            return "daily_limit"
        prior = db.execute("""
            SELECT j.id, j.company, COALESCE(j.source_platform, 'boss') AS platform
            FROM jobs j
            WHERE j.status IN ('sent','replied','needs_resume','resume_sent','follow_up_sent')
               OR EXISTS (SELECT 1 FROM history h WHERE h.job_id=j.id
                          AND h.action IN ('sent','manual_sent','delivery_reserved','prior_application'))
        """)
        for row in prior:
            if row["id"] == job["id"] or (
                cross_platform_dedup and key and row["platform"] != platform
                and company_name_key(row["company"] or "") == key
            ):
                return "duplicate_company"
        if not key and platform != "boss":
            return "unknown_company"
        db.execute("INSERT INTO history(job_id, action) VALUES (?, 'delivery_reserved')", (job["id"],))
    return None


def release_delivery(db, job_id):
    with db:
        db.execute("DELETE FROM history WHERE job_id = ? AND action = 'delivery_reserved'", (job_id,))


def note_risk(platform, reason, space_id):
    with Path("需要扫码.txt").open("a", encoding="utf-8") as file:
        file.write(f"{platform} 检测到 {reason}，请在现有 Ego Lite 任务空间 {space_id} 手动处理。\n")


def _failed(reason, *, uncertain=False):
    result = {"success": False, "error": reason, "uncertain": uncertain}
    if uncertain:
        result["history_detail"] = "投递结果待核实，已保留名额并阻止重复投递。请在原站检查后手动标记。"
    return result


def submit_resume(db, job, config):
    platform = platform_of(job)
    if not platform_supports(platform, "deliver", config) or platform not in DETAIL_HOSTS:
        return _failed("platform_disabled")
    url = str(job.get("url") or "")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in DETAIL_HOSTS[platform] or parsed.path in ("", "/"):
        return _failed("unverified_job_url")
    options = config.get("delivery", {}).get("platforms", {}).get(platform, {})
    choice = options.get("resume_choice", "attachment")
    if choice not in {"attachment", "online"}:
        return _failed("invalid_resume_choice")
    if delivery_action(config, platform) == "greeting":
        from bosshunter.executor.liepin_chat import submit_chat
        return submit_chat(db, job, config)
    browser = EgoTaskSpace.from_config(config, section="delivery")
    stop = config.get("_workbench_stop_event")
    if stop and stop.is_set():
        return _failed("stopped")
    guard = PlatformAccessGuard(db, config, "send", platform)
    try:
        guard.reserve("job_page")
    except PlatformSafetyStop as exc:
        return _failed(exc.reason)
    if stop and stop.is_set():
        return _failed("stopped")
    try:
        resume_verified = False
        if platform == "zhilian":
            guard.reserve("resume_page")
            resume_verified = prepare_zhilian_resume(browser, choice, options.get("resume_name", ""), stop, guard)
            if not resume_verified:
                return _failed("resume_selection_unverified")
        target = browser.new_tab(url)
    except PlatformSafetyStop as exc:
        if exc.reason in {"captcha", "blocked", "rate_limit"}:
            guard.lock(exc.reason)
            note_risk(platform, exc.reason, browser.space_id)
        return _failed(exc.reason)
    except EgoTaskSpaceError:
        return _failed("ego_unavailable")
    if not target:
        return _failed("page_unavailable")
    clicked = False
    try:
        if not browser.wait_for_load(target):
            return _failed("page_unavailable")
        for phase in ("probe", "submit", "receipt"):
            if stop and stop.is_set():
                return _failed("stopped", uncertain=clicked)
            guard.ensure_unlocked()
            expected = {
                "origin": f"https://{parsed.netloc}", "path": parsed.path, "platform": platform,
                "company": job.get("company"), "title": job.get("title"), "phase": phase,
                "resume_choice": choice, "resume_name": options.get("resume_name", ""),
                "resume_verified": resume_verified,
            }
            if phase == "submit":
                if reason := approval_error(db, job, config):
                    return _failed(reason)
                clicked = True  # Lost bridge response may follow a successful click.
            script = _APPLY_SCRIPT.replace("EXPECTED_JOB", json.dumps(expected))
            result = browser.evaluate(target, script)
            if phase == "receipt":
                deadline = time.monotonic() + 4
                while result == {"receipt": False} and time.monotonic() < deadline:
                    if stop and stop.wait(0.25):
                        return _failed("stopped", uncertain=True)
                    if not stop:
                        time.sleep(0.25)
                    result = browser.evaluate(target, script)
            if not isinstance(result, dict):
                return _failed("unconfirmed_application", uncertain=clicked)
            if reason := result.get("error"):
                if reason in {"captcha", "blocked", "rate_limit"}:
                    guard.lock(reason)
                    note_risk(platform, reason, config["delivery"]["ego_task_space_id"])
                if clicked and phase == "receipt" and platform == "zhilian" and reason not in {"captcha", "blocked", "rate_limit"}:
                    if verify_zhilian_application(browser, job, stop, guard):
                        return {"success": True, "history_detail": "原站投递记录已核实"}
                return _failed(reason, uncertain=clicked and (phase == "receipt"))
        if result.get("receipt") is True:
            return {"success": True}
        if platform == "zhilian" and verify_zhilian_application(browser, job, stop, guard):
            return {"success": True, "history_detail": "原站投递记录已核实"}
        return _failed("unconfirmed_application", uncertain=True)
    except PlatformSafetyStop as exc:
        return _failed(exc.reason, uncertain=clicked)
    except EgoTaskSpaceError:
        if clicked and platform == "zhilian" and verify_zhilian_application(browser, job, stop, guard):
            return {"success": True, "history_detail": "原站投递记录已核实"}
        return _failed("ego_unavailable", uncertain=clicked)
    finally:
        browser.close_tab(target)


_APPLY_SCRIPT = r"""
(() => {
    const expected = EXPECTED_JOB;
    const text = document.body?.innerText || '';
    if (/安全验证|验证码|拖动滑块|请完成验证/.test(text) || /captcha|verify/i.test(location.pathname))
        return {error:'captcha'};
    if (/访问过于频繁|操作过于频繁/.test(text)) return {error:'rate_limit'};
    if (/访问受限|账号异常|操作异常|扫码登录/.test(text)) return {error:'blocked'};
    const signInPrompt = [...document.querySelectorAll('header *,nav *,li,button,a')].some(el => {
        const rect = el.getBoundingClientRect();
        return rect.height > 0 && rect.width > 0 && rect.top >= 0 && rect.top < 140 &&
            /^(登录\s*[\/|]\s*注册|登录后投递)$/.test((el.innerText || '').trim());
    });
    if (signInPrompt) return {error:'blocked'};
    if (location.origin !== expected.origin || location.pathname !== expected.path ||
        !expected.title || !expected.company || !text.includes(expected.title) || !text.includes(expected.company))
        return {error:'job_identity_mismatch'};
    if (expected.phase === 'receipt' && [...document.querySelectorAll('[role=alert],[role=status],.a-message,.ivu-message,.success-popup-2')]
        .some(el => el.getClientRects().length && /投递成功|申请成功|简历已投递/.test(el.innerText || ''))) return {receipt:true};
    const rules = {
        zhilian: ['button.a-button', '立即投递'],
        '51job': ['div.apply-btn-new.big', '立即投递'],
        liepin: ['a[data-selector="apply-job"]', '投简历'],
    };
    const [selector, expectedLabel] = rules[expected.platform];
    const label = el => (el.innerText || '').trim();
    const controls = [...document.querySelectorAll(selector)].filter(el =>
        el.getClientRects().length && getComputedStyle(el).visibility === 'visible' &&
        (expected.platform !== '51job' || expected.path.endsWith('/' + el.id + '.html')) &&
        (label(el) === expectedLabel || /^(已申请|已投递)$/.test(label(el))));
    if (controls.length !== 1) return expected.phase === 'receipt' ? {receipt:false} : {error:'application_control_unverified'};
    const receipt = /^(已申请|已投递)$/.test(label(controls[0]));
    if (expected.phase === 'receipt') return {receipt};
    if (receipt) return {error:'already_applied'};
    const matches = controls.filter(el => label(el) === expectedLabel &&
        !el.disabled && el.getAttribute('aria-disabled') !== 'true');
    if (matches.length !== 1) return {error:'application_control_unverified'};
    // The initial click can submit immediately. Require a verified selected résumé BEFORE it.
    // Never infer selection from an attachment merely existing in the résumé centre.
    if (expected.phase === 'submit' && expected.resume_choice === 'attachment' && !expected.resume_verified) {
        const candidates = [...document.querySelectorAll('.attachment_item')].filter(el =>
            el.getClientRects().length && el.querySelector('input[type=radio],.radio'));
        const matches = expected.resume_name ? candidates.filter(el => (el.innerText || '').includes(expected.resume_name)) : candidates;
        if (matches.length === 1) matches[0].click();
        const selected = [...document.querySelectorAll('.attachment_item:has(.radio.selected),.attachment_item:has(input:checked)')]
            .filter(el => el.getClientRects().length);
        const names = selected.map(el => (el.closest('.attachment_item') || el).innerText || '');
        if (!names.length || (expected.resume_name && !names.some(name => name.includes(expected.resume_name))))
            return {error:'attachment_selection_unverified'};
    }
    if (expected.phase === 'submit') matches[0].click();
    return {found:true};
})()
"""


FEEDBACK_URLS = {
    "zhilian": "https://i.zhaopin.com/schedule?status=unsuitable",
    "51job": "https://i.51job.com/userset/my_apply.php",
}


def observe_replies(db, config, platform, jobs):
    """Open an owned feedback page. Only evidenced feedback layouts can emit events."""
    if not jobs or platform not in FEEDBACK_URLS or not platform_supports(platform, "inspect_feedback", config):
        return 0
    browser = EgoTaskSpace.from_config(config, section="delivery")
    stop = config.get("_workbench_stop_event")
    guard = PlatformAccessGuard(db, config, "monitor", platform)
    if stop and stop.is_set():
        return 0
    guard.reserve("feedback_page")
    target = browser.new_tab(FEEDBACK_URLS[platform])
    if not target:
        return 0
    try:
        if not browser.wait_for_load(target) or (stop and stop.is_set()):
            return 0
        if platform == "zhilian":
            # Switch the view only in our newly opened page.
            selected = browser.evaluate(target, _ZHILIAN_INTEREST_FILTER)
            if selected in ("captcha", "rate_limit", "blocked"):
                guard.lock(selected)
                note_risk(platform, selected, config["delivery"]["ego_task_space_id"])
                raise PlatformSafetyStop(selected)
            if selected != "selected" or (stop and stop.is_set()):
                return 0
        script = _ZHILIAN_FEEDBACK_SCRIPT if platform == "zhilian" else _JOB51_FEEDBACK_SCRIPT
        result = browser.evaluate(target, script)
        if not isinstance(result, dict):
            return 0
        if reason := result.get("risk"):
            guard.lock(reason)
            note_risk(platform, reason, config["delivery"]["ego_task_space_id"])
            raise PlatformSafetyStop(reason)
        if stop and stop.is_set():
            return 0
        if platform == "51job":
            return 0  # Only an empty real-account list has been verified.
        return record_replies(db, platform, jobs, result.get("rows", []))
    finally:
        browser.close_tab(target)


def record_replies(db, platform, jobs, rows):
    """Match an explicit incoming reply to one sent job by its detail URL."""
    count = 0
    for row in rows:
        if row.get("direction") != "incoming" or not row.get("message"):
            continue
        if platform != "zhilian" or row.get("kind") != "platform_feedback":
            continue
        if row["message"] != "企业对你有意" or not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", row.get("time", "")):
            continue
        link = urlsplit(row.get("url") or "")
        source = re.fullmatch(r"/([A-Za-z0-9]+)\.htm", link.path)
        if link.netloc != "jobs.zhaopin.com" or link.scheme not in {"http", "https"} or not source:
            continue
        matches = [
            job for job in jobs if platform_of(job) == platform
            and str(job.get("source_job_id") or "") == source[1]
            and _feedback_company_key(job.get("company")) == _feedback_company_key(row.get("company"))
            and job.get("title") == row.get("title")
        ]
        if len(matches) != 1:
            continue
        job_id = matches[0]["id"]
        detail = f"平台反馈: {row['message']}（{row['time']}）"
        with db:
            db.execute("BEGIN IMMEDIATE")
            already_seen = db.execute("""
                SELECT 1 FROM history WHERE job_id=? AND action='hr_reply_detected' AND detail=?
            """, (job_id, detail)).fetchone()
            if already_seen:
                continue
            changed = db.execute("""
                UPDATE jobs SET status='replied', updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND source_platform=? AND status IN ('sent','replied') AND deleted_at IS NULL
            """, (job_id, platform)).rowcount
            if changed:
                db.execute("INSERT INTO history(job_id,action,detail) VALUES (?,'hr_reply_detected',?)", (job_id, detail))
                count += 1
    return count


_ZHILIAN_INTEREST_FILTER = r"""
(async () => {
    const text = document.body?.innerText || '';
    if (/拖动滑块|请完成验证|安全验证|扫码登录/.test(text) || /captcha|verify/i.test(location.pathname)) return 'captcha';
    if (/访问过于频繁|操作过于频繁/.test(text)) return 'rate_limit';
    if (/账号异常|访问受限|操作异常/.test(text)) return 'blocked';
    if (location.origin !== 'https://i.zhaopin.com' || location.pathname !== '/schedule') return 'wrong_page';
    const controls = [...document.querySelectorAll('li a')].filter(el =>
        el.getClientRects().length && el.innerText.trim() === '有意向');
    if (controls.length !== 1) return 'missing_filter';
    controls[0].click();
    for (let i = 0; i < 12; i++) {
        if ([...document.querySelectorAll('.ji-item-status p')].some(el => el.innerText.trim() === '企业对你有意')) break;
        await new Promise(resolve => setTimeout(resolve, 200));
    }
    return 'selected';
})()
"""

_ZHILIAN_FEEDBACK_SCRIPT = r"""
(() => {
    const url = location.href, text = document.body?.innerText || '';
    if (/拖动滑块|请完成验证|安全验证|扫码登录/.test(text)) return {risk:'captcha',url};
    if (/访问过于频繁|操作过于频繁/.test(text)) return {risk:'rate_limit',url};
    if (/账号异常|访问受限|操作异常/.test(text)) return {risk:'blocked',url};
    if (location.origin !== 'https://i.zhaopin.com' || location.pathname !== '/schedule') return {url,rows:[]};
    const rows = [];
    for (const item of document.querySelectorAll('.ji-item')) {
        const link = item.querySelector('a.ji-item-info-jobName');
        const company = item.querySelector('.ji-item-info-companyName')?.innerText.trim();
        const status = item.querySelector('.ji-item-status p')?.innerText.trim();
        const stamp = [...item.querySelectorAll('.ji-item-status-timer span')].map(el => el.innerText.trim()).join(' ');
        if (item.getClientRects().length && link && company && status === '企业对你有意' &&
            /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(stamp)) {
            rows.push({kind:'platform_feedback', direction:'incoming', message:status,
                title:link.innerText.trim(), company, url:link.href, time:stamp});
        }
    }
    return {url, rows};
})()
"""


_JOB51_FEEDBACK_SCRIPT = r"""
(() => {
    const text = document.body?.innerText || '';
    if (/拖动滑块|请完成验证|安全验证|扫码登录/.test(text) || /captcha|verify/i.test(location.pathname))
        return {risk:'captcha'};
    if (/账号异常|访问受限|操作异常/.test(text)) return {risk:'blocked'};
    if (/访问过于频繁|操作过于频繁/.test(text)) return {risk:'rate_limit'};
    if (location.origin !== 'https://i.51job.com' || location.pathname !== '/userset/my_apply.php')
        return {state:'unknown_page'};
    return {state:text.includes('暂无社会申请记录') ? 'empty' : 'unverified_rows'};
})()
"""


def verify_zhilian_application(browser, job, stop=None, guard=None):
    """Read official application rows; never submit or repeat an application."""
    if stop and stop.is_set():
        return False
    if guard:
        try:
            guard.reserve("application_record")
        except PlatformSafetyStop:
            return False
    try:
        target = browser.new_tab("https://i.zhaopin.com/schedule")
    except EgoTaskSpaceError:
        return False
    if not target:
        return False
    try:
        if not browser.wait_for_load(target):
            return False
        identity = {"id": str(job.get("source_job_id") or job["id"].removeprefix("zhilian:")),
                    "company": job.get("company"), "title": job.get("title")}
        script = _ZHILIAN_APPLICATION_RECORD.replace("EXPECTED_RECORD", json.dumps(identity))
        deadline = time.monotonic() + 5
        while True:
            if stop and stop.is_set():
                return False
            result = browser.evaluate(target, script)
            if isinstance(result, dict) and result.get("receipt") is True:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(.25)
    except EgoTaskSpaceError:
        return False
    finally:
        browser.close_tab(target)


_ZHILIAN_APPLICATION_RECORD = r"""
(() => {
 const expected = EXPECTED_RECORD;
 if (location.origin !== 'https://i.zhaopin.com' || location.pathname !== '/schedule') return {receipt:false};
 const links = [...document.querySelectorAll('a[href]')].filter(a => {
   try { const u=new URL(a.href);return ['jobs.zhaopin.com','www.zhaopin.com'].includes(u.hostname) &&
     u.pathname === '/' + expected.id + '.htm'; } catch {return false;}
 });
 const rows=links.map(a=>a.closest('.ji-item') || a.closest('li') || a.closest('tr')).filter(Boolean);
 return {receipt:rows.some(row => {
   const text=row.innerText || '';
   return text.includes(expected.company) && text.includes(expected.title) && /投递成功|成功投递/.test(text);
 })};
})()
"""


def prepare_zhilian_resume(browser, choice, name, stop=None, guard=None):
    """Select and read back the official default before opening a job page."""
    target = browser.new_tab("https://i.zhaopin.com/resume")
    if not target:
        return False
    try:
        if not browser.wait_for_load(target):
            return False
        script = _ZHILIAN_SELECT_RESUME.replace("RESUME_OPTIONS", json.dumps({"choice": choice, "name": name}))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if stop and stop.is_set():
                return False
            if guard:
                guard.ensure_unlocked()
            result = browser.evaluate(target, script)
            if isinstance(result, dict) and result.get("error") in {"captcha", "blocked", "rate_limit"}:
                raise PlatformSafetyStop(result["error"])
            if isinstance(result, dict) and result.get("selected") is True:
                return True
            if isinstance(result, dict) and result.get("error"):
                return False
            time.sleep(.25)
        return False
    finally:
        browser.close_tab(target)


_ZHILIAN_SELECT_RESUME = r"""
(() => {
 const e=RESUME_OPTIONS;
 if(location.origin!=='https://i.zhaopin.com' || location.pathname!=='/resume') return {error:'resume_page_unverified'};
 const text=document.body?.innerText || '';
 if(/安全验证|验证码|拖动滑块|请完成验证|扫码登录/.test(text)) return {error:'captcha'};
 const rows=[...document.querySelectorAll('.parse-item,.online-resume')].filter(e=>e.getClientRects().length);
 if(!rows.length)return {selected:false};
 const candidates=e.choice==='attachment' ? rows.filter(e=>e.querySelector('.parse-item__left-title-text')) :
   rows.filter(e=>e.innerText.includes('我的在线简历'));
 let matches=e.name && e.choice==='attachment'?candidates.filter(row=>row.querySelector('.parse-item__left-title-text')?.innerText.trim()===e.name ||
   row.querySelector('.parse-item__left-title-text')?.innerText.trim()===e.name+'.pdf'):candidates;
 if(!e.name && e.choice==='attachment' && matches.length>1) {
   const stamp=row=>{ const value=row.querySelector('.create-time')?.innerText || '';
     const now=new Date(), day=now.toISOString().slice(0,10);
     const normalized=value.replace('今日',day).replace(' 上传','');
     const parsed=Date.parse(normalized);return Number.isFinite(parsed)?parsed:0; };
   matches.sort((a,b)=>stamp(b)-stamp(a));
   if(stamp(matches[0])>stamp(matches[1]))matches=[matches[0]];
 }
 if(matches.length!==1)return {error:'resume_selection_unverified'};
 const row=matches[0];
 if(row.innerText.includes('默认投递'))return {selected:true};
 const button=row.querySelector('.parse-item__right-text,.online-resume__right-text');
 if(button?.innerText.trim()==='设为默认')button.click();
 return {selected:false};
})()
"""
