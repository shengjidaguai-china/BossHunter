"""Conservative UI-only delivery candidates; selectors still require live validation.

Only the identified Zhilian resume chooser is handled automatically.
No generic popup confirmation, private API, or uncertain-result retry is allowed here.
A committed delivery_attempt is a permanent automatic-retry fence, including
when the browser call times out or the process exits before recording a result.
"""
from __future__ import annotations

import json
import re
import time
from urllib.parse import urlsplit

from bosshunter.browser import activate_tab, close_tab, evaluate, get_page_targets, new_tab
from bosshunter.db import count_platform_access_today
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop

PLATFORMS = {
    "zhilian": {
        "hosts": ["www.zhaopin.com", "jobs.zhaopin.com"],
        "path": r"^/jobdetail/([A-Za-z0-9_-]+)\.htm[l]?$",
        "root": ".job-detail-summary, .summary-planes__content, .jobinfo",
        "title": ".job-detail-summary__title-text, .summary-planes__title, .jobinfo__name",
        "company": ".job-detail-summary__company-name, .companyinfo__name, .company-info__name",
        "apply": ["立即申请", "申请职位", "投递简历", "立即投递"],
    },
    "51job": {
        "hosts": ["jobs.51job.com"],
        "path": r"^/[^/]+/([0-9]+)\.html$",
        "root": ".tHeader .in, .job-header",
        "title": "h1, .job-title",
        "company": ".cname a, .company-name, .com_msg > a.com_name",
        "apply": ["申请职位", "立即申请", "立即投递"],
        "extraButton": "div.jobapply-wrapper.apply-btn-wrapper.but_sq",
    },
    "liepin": {
        "hosts": ["www.liepin.com"],
        "path": r"^/job/([0-9]+)\.shtml$",
        "root": ".job-detail-box, .job-detail-container",
        "title": ".job-title-box .ellipsis-1, h1",
        "company": ".company-info-container .ellipsis-1, [data-nick='job-detail-company-info'] .ellipsis-1",
        "apply": ["投简历", "投递简历", "立即应聘", "申请职位"],
    },
}
ATTEMPT = "delivery_attempt"


def paused(code: str, *, attempted: bool = False) -> dict:
    labels = {
        "resume_selection_required": "平台要求选择或完善投递简历，请在原平台页面处理",
        "dialog_requires_review": "平台弹窗需要人工处理",
        "apply_button_obscured": "投递按钮被弹窗遮挡或不在可点击区域，请先处理原平台页面",
        "delivery_result_unknown": "未取得明确成功回执，请先核对原平台投递记录",
        "delivery_attempt_requires_review": "此前已尝试申请，请先核对原平台投递记录",
    }
    message = labels.get(code, code)
    return {"success": False, "error": code, "manual_required": True,
            "attempted": attempted, "retryable": False, "skip_backoff": True,
            "history_detail": f"平台投递已暂停：{message}；不自动重试"}


def _limit(value, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def valid_job_url(platform: str, url: str, source_id: str) -> bool:
    spec = PLATFORMS.get(platform)
    if not spec or not source_id:
        return False
    try:
        parsed = urlsplit(url)
        match = re.fullmatch(spec["path"], parsed.path)
        return bool(parsed.scheme == "https" and parsed.hostname in spec["hosts"]
                    and not parsed.username and not parsed.password and parsed.port in (None, 443)
                    and not parsed.fragment and match and match.group(1) == source_id)
    except (TypeError, ValueError):
        return False


def delivery_count(db, platform: str | None = None) -> int:
    """Count sent rows plus uncertain attempts, never count one attempt twice."""
    return db.execute("""
        SELECT count(*) FROM history h JOIN jobs j ON j.id=h.job_id
        WHERE date(h.created_at)=date('now')
          AND (? IS NULL OR j.source_platform=?)
          AND (h.action='sent' OR (h.action='delivery_attempt' AND NOT EXISTS (
            SELECT 1 FROM history s WHERE s.job_id=h.job_id AND s.action='sent'
              AND date(s.created_at)=date('now')
          )) OR (h.action='delivery_submit_attempt' AND NOT EXISTS (
            SELECT 1 FROM history prior WHERE prior.job_id=h.job_id
              AND prior.action IN ('delivery_attempt', 'sent')
              AND date(prior.created_at)=date('now')
          )))
    """, (platform, platform)).fetchone()[0]


def _previous_attempt(db, job_id: str) -> bool:
    # Also fence another local row representing the exact same platform job.
    return bool(db.execute("""
        SELECT 1 FROM history h JOIN jobs old ON old.id=h.job_id
        JOIN jobs current ON current.id=?
        WHERE h.action IN ('delivery_attempt', 'sent') AND (
          old.id=current.id OR (old.source_platform=current.source_platform
          AND old.source_job_id=current.source_job_id AND current.source_job_id IS NOT NULL
          AND current.source_job_id<>'')) LIMIT 1
    """, (job_id,)).fetchone())


def _approved(db, job: dict, selected) -> bool:
    if str(job["id"]) not in selected or job.get("status") not in {"ready", "approved"}:
        return False
    approval = db.execute("SELECT max(id) FROM history WHERE job_id=? AND action='approved'",
                          (job["id"],)).fetchone()[0]
    evaluation = db.execute("SELECT max(id) FROM history WHERE job_id=? AND action='agent_evaluated'",
                            (job["id"],)).fetchone()[0]
    return bool((job.get("status") == "approved" or approval is not None)
                and (evaluation is None or (approval is not None and approval > evaluation)))


def _reserve_attempt(db, job, config, daily_limit):
    """Atomic quota + approval + duplicate check; commit BEFORE browser mutation."""
    db.execute("BEGIN IMMEDIATE")
    try:
        current = db.execute("SELECT * FROM jobs WHERE id=? AND deleted_at IS NULL", (job["id"],)).fetchone()
        if current is None or not _approved(db, dict(current), {str(x) for x in config.get("_workbench_job_ids", [])}):
            raise PlatformSafetyStop("delivery_confirmation_required")
        if any(current[key] != job.get(key) for key in ("source_platform", "source_job_id", "url", "title", "company")):
            raise PlatformSafetyStop("job_identity_changed")
        if _previous_attempt(db, job["id"]):
            raise PlatformSafetyStop("delivery_attempt_requires_review")
        if delivery_count(db) >= _limit(config.get("throttle", {}).get("daily_limit", 30), 30):
            raise PlatformSafetyStop("daily_limit")
        if delivery_count(db, job["source_platform"]) >= daily_limit:
            raise PlatformSafetyStop("daily_delivery_limit")
        db.execute("INSERT INTO history(job_id, action, detail) VALUES (?, ?, ?)",
                   (job["id"], ATTEMPT, json.dumps({"platform": job["source_platform"],
                    "source_job_id": job["source_job_id"], "state": "reserved_before_click"})))
        db.commit()
    except BaseException:
        db.rollback()
        raise


def _script(job: dict, click: bool = False, *, resume_name: str = "", resume_action: str = "") -> str:
    """All identity/visibility/blocker checks repeat inside the single click script."""
    spec = PLATFORMS[job["source_platform"]]
    payload = {**spec, "sourceId": str(job["source_job_id"]), "expectedTitle": job["title"],
               "expectedCompany": job["company"], "click": click,
               "resumeName": resume_name, "resumeAction": resume_action, "platform": job["source_platform"]}
    return "(() => { const spec = " + json.dumps(payload, ensure_ascii=False) + r""";
      const result = (state) => JSON.stringify({state});
      const norm = x => String(x || '').replace(/\s+/g, ' ').trim();
      const visible = el => {
        const r=el.getBoundingClientRect(), s=getComputedStyle(el);
        return !!(r.width && r.height && s.display!=='none' && s.visibility==='visible'
          && Number(s.opacity)!==0 && !el.closest('[hidden], [aria-hidden="true"]'));
      };
      const text = document.body ? document.body.innerText : '';
      if (/验证码|滑块|安全验证|人机验证|captcha/i.test(text)) return result('captcha');
      if (/访问频繁|操作频繁|频率限制|稍后再试/.test(text)) return result('rate_limit');
      if (/账号异常|账号受限|拒绝访问|访问受限/.test(text)) return result('blocked');
      if (/请先登录|请登录|扫码登录|登录后|登录失效/.test(text)
          || /login|passport/i.test(location.pathname)) return result('login_required');
      const resumePrompt = /选择.{0,12}简历|完善简历|上传简历/.test(text);
      if (/填写问卷|申请问卷|回答以下|补充申请信息/.test(text)) return result('questionnaire_required');
      if (/付费|购买服务|支付|开通会员|置顶简历|优先推荐/.test(text)) return result('paid_recommendation');
      const u=new URL(location.href), m=u.pathname.match(new RegExp(spec.path));
      if (u.protocol!=='https:' || !spec.hosts.includes(u.hostname) || u.username || u.password
          || (u.port && u.port!=='443') || u.hash || !m || m[1]!==spec.sourceId)
        return result('job_identity_mismatch');
      const roots=Array.from(document.querySelectorAll(spec.root)).filter(visible);
      if (roots.length!==1) return result('detail_root_ambiguous');
      const root=roots[0];
      const exact=(scope, selector, expected) => {
        const names=new Set(Array.from(scope.querySelectorAll(selector)).filter(visible)
          .map(el => norm(el.innerText)).filter(Boolean));
        return names.size===1 && names.has(norm(expected));
      };
      // Detail-company regions can be siblings of the action header. Do not
      // search page text or recommendations for the expected company name.
      if (!spec.expectedTitle || !spec.expectedCompany || !exact(root, spec.title, spec.expectedTitle)
          || !exact(document, spec.company, spec.expectedCompany)) return result('job_identity_mismatch');
      const resumeDialogs=Array.from(document.querySelectorAll('.a-job-apply-workflow--attachment-select')).filter(visible);
      if (resumePrompt || resumeDialogs.length) {
        if (spec.platform!=='zhilian' || !spec.resumeName || !spec.resumeAction)
          return result('resume_selection_required');
        if (resumeDialogs.length!==1) return result('resume_selection_required');
        const dialog=resumeDialogs[0];
        const otherDialogs=Array.from(document.querySelectorAll('[role="dialog"], dialog[open], [aria-modal="true"], .a-modal, .ant-modal'))
          .filter(visible).filter(el=>el!==dialog && !el.contains(dialog) && !dialog.contains(el));
        if (otherDialogs.length) return result('dialog_requires_review');
        const items=Array.from(dialog.querySelectorAll('.a-attachment-select__item--attachment')).filter(visible)
          .filter(el=>norm(el.querySelector('.attachment-name')?.innerText)===spec.resumeName);
        if (items.length!==1) return result('resume_selection_required');
        const item=items[0], preference=dialog.querySelector('.a-attachment-select__action-btn__default');
        const selected=()=>item.classList.contains('is-active');
        const remembered=()=>{
          const icon=preference?.querySelector('.radio-icon');
          return !!icon && icon.classList.contains('radio') && !icon.classList.contains('radio-unchecked');
        };
        if (!preference || !visible(preference) || norm(preference.innerText)!=='每次投递默认发送该简历')
          return result('resume_selection_required');
        if (spec.resumeAction==='prepare') {
          if (!selected()) item.click();
          if (!remembered()) preference.click();
          return result('resume_preparing');
        }
        if (!selected() || !remembered()) return result('resume_preparing');
        const submit=Array.from(dialog.querySelectorAll('.a-attachment-select__action-btn__delivery')).filter(visible)
          .filter(el=>norm(el.innerText)==='投递简历');
        if (submit.length!==1) return result('resume_selection_required');
        if (spec.resumeAction!=='submit') return result('resume_ready');
        const button=submit[0];
        if (button.disabled || button.getAttribute('aria-disabled')==='true' || button.classList.contains('disabled'))
          return result('apply_button_disabled');
        button.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
        const r=button.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height/2;
        const top=document.elementFromPoint(x,y);
        if (!top || !(top===button || button.contains(top))) return result('apply_button_obscured');
        button.click();
        return result('resume_submitted');
      }
      // A new explicit status toast may sit outside the detail action header.
      const successTexts=new Set(Array.from(document.querySelectorAll(
        '[role="status"], [role="alert"], .apply-success, .delivery-success, .ant-message-success, .el-message--success'
      )).filter(visible).map(el => norm(el.innerText)).filter(t =>
        ['申请成功', '投递成功', '简历投递成功'].includes(t)));
      if (successTexts.size===1) return result('success_receipt');
      // Any modal requires human inspection. Never select generic confirm buttons.
      if (Array.from(document.querySelectorAll('[role="dialog"], dialog[open], [aria-modal="true"], .a-modal, .ant-modal, .modal, .dialog, .popup'))
          .some(visible)) return result('dialog_requires_review');
      const labels=Array.from(root.querySelectorAll('button, a, [role="button"], input[type="button"], input[type="submit"]' + (spec.extraButton ? ", " + spec.extraButton : "")))
        .filter(visible);
      const label=el => norm(el.innerText || el.value);
      const receipts=Array.from(root.querySelectorAll('[role="status"], .apply-success, .delivery-success'))
        .filter(visible).filter(el => ['申请成功', '投递成功', '简历投递成功'].includes(norm(el.innerText)));
      if (receipts.length===1) return result('success_receipt');
      if (labels.some(el => ['已申请', '已投递', '已投递简历'].includes(label(el))
          || (spec.platform==='zhilian' && label(el)==='继续沟通'))) return result('already_applied');
      const buttons=labels.filter(el => spec.apply.includes(label(el)));
      if (buttons.length!==1) return result('apply_button_ambiguous');
      const button=buttons[0];
      if (button.disabled || button.getAttribute('aria-disabled')==='true' || button.classList.contains('disabled'))
        return result('apply_button_disabled');
      if (button.tagName==='A' && button.getAttribute('href') && button.getAttribute('href')!=='#')
        return result('apply_link_requires_review');
      if (button.getAttribute('target')==='_blank') return result('apply_link_requires_review');
      const r=button.getBoundingClientRect(), x=r.left+r.width/2, y=r.top+r.height/2;
      const top=document.elementFromPoint(x,y);
      if (x<0 || y<0 || x>=innerWidth || y>=innerHeight || !top || !(top===button || button.contains(top)))
        return result('apply_button_obscured');
      if (!spec.click) return result('ready');
      button.click();
      return result('clicked');
    })()"""


def _state(target, job, *, click=False, resume_name="", resume_action=""):
    value = evaluate(target, _script(job, click, resume_name=resume_name, resume_action=resume_action))
    try:
        value = json.loads(value) if isinstance(value, str) else value
        return value.get("state", "page_unreadable") if isinstance(value, dict) else "page_unreadable"
    except (ValueError, TypeError):
        return "page_unreadable"


def _has_submit_attempt(db, job: dict) -> bool:
    return bool(db.execute("""
        SELECT 1 FROM history h JOIN jobs j ON j.id=h.job_id
        WHERE h.action IN ('delivery_submit_attempt', 'sent') AND
          (j.id=? OR (j.source_platform=? AND j.source_job_id=?)) LIMIT 1
    """, (job["id"], job["source_platform"], job["source_job_id"])).fetchone())


def _claim_resume_submit(db, job, config):
    """Fence the final form submission separately from opening its chooser."""
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT * FROM jobs WHERE id=? AND deleted_at IS NULL", (job["id"],)).fetchone()
        if row is None or not _approved(db, dict(row), set(config.get("_workbench_job_ids", []))):
            raise PlatformSafetyStop("delivery_confirmation_required")
        if any(row[key] != job.get(key) for key in ("source_platform", "source_job_id", "url", "title", "company")):
            raise PlatformSafetyStop("job_identity_changed")
        if _has_submit_attempt(db, job):
            raise PlatformSafetyStop("delivery_attempt_requires_review")
        reserved_today = db.execute("SELECT 1 FROM history WHERE job_id=? AND action='delivery_attempt' AND date(created_at)=date('now')", (job["id"],)).fetchone()
        if not reserved_today:
            if delivery_count(db) >= _limit(config.get("throttle", {}).get("daily_limit", 30), 30):
                raise PlatformSafetyStop("daily_limit")
            limit = _limit(config.get("platforms", {}).get(job["source_platform"], {}).get("safety", {}).get("daily_delivery_limit", 10), 10)
            if delivery_count(db, job["source_platform"]) >= limit:
                raise PlatformSafetyStop("daily_delivery_limit")
        if not db.execute("SELECT 1 FROM history WHERE job_id=? AND action='delivery_attempt'", (job["id"],)).fetchone():
            raise PlatformSafetyStop("delivery_confirmation_required")
        db.execute("INSERT INTO history(job_id,action,detail) VALUES (?, 'delivery_submit_attempt', ?)",
                   (job["id"], "confirmed_resume_before_submit"))
        db.commit()
    except BaseException:
        db.rollback()
        raise


def _chooser_reopen_authorized(db, job, resume_name):
    """A known chooser stop can be retried only after a new human confirmation."""
    if not resume_name or job["source_platform"] != "zhilian" or _has_submit_attempt(db, job):
        return False
    attempt = db.execute("SELECT max(id) FROM history WHERE job_id=? AND action='delivery_attempt'", (job["id"],)).fetchone()[0]
    approval = db.execute("SELECT max(id) FROM history WHERE job_id=? AND action='approved'", (job["id"],)).fetchone()[0]
    pause = db.execute("SELECT id,detail FROM history WHERE job_id=? AND action='delivery_paused' ORDER BY id DESC LIMIT 1", (job["id"],)).fetchone()
    return bool(attempt is not None and approval is not None and approval > attempt and pause is not None
                and pause["id"] > attempt and pause["detail"] == "resume_selection_required")


def _resume_recovery_target(db, job, resume_name):
    """Only a fresh confirmation may finish an existing, unsubmitted chooser."""
    if not resume_name or job["source_platform"] != "zhilian" or _has_submit_attempt(db, job):
        return None
    attempt = db.execute("SELECT max(id) FROM history WHERE job_id=? AND action='delivery_attempt'", (job["id"],)).fetchone()[0]
    approval = db.execute("SELECT max(id) FROM history WHERE job_id=? AND action='approved'", (job["id"],)).fetchone()[0]
    if attempt is None or approval is None or approval <= attempt:
        return None
    tabs = [t for t in get_page_targets() if valid_job_url(job["source_platform"], str(t.get("url") or ""), str(job["source_job_id"]))]
    if len(tabs) != 1:
        return None
    target = tabs[0].get("targetId")
    return target if target and _state(target, job) == "resume_selection_required" else None


def _submit_selected_resume(target, job, config, db, boundary):
    name = str(config.get("platforms", {}).get(job["source_platform"], {}).get("delivery", {}).get("resume_name") or "").strip()
    if job["source_platform"] != "zhilian" or not name:
        return "resume_selection_required"
    boundary()
    if not activate_tab(target):
        return "page_unreadable"
    # Vue enter animations can remain opacity=0 in background tabs. Wait for
    # the real visible chooser; do not change styles or click hidden elements.
    for _ in range(20):
        boundary()
        state = _state(target, job, resume_name=name, resume_action="prepare")
        if state == "resume_preparing":
            break
        if state != "resume_selection_required":
            return state
        time.sleep(0.2)
    else:
        return "resume_selection_required"
    for _ in range(10):
        boundary()
        state = _state(target, job, resume_name=name, resume_action="inspect")
        if state == "resume_ready":
            break
        if state != "resume_preparing":
            return state
        time.sleep(0.2)
    else:
        return "resume_selection_required"
    boundary()
    _claim_resume_submit(db, job, config)
    boundary()
    return _state(target, job, resume_name=name, resume_action="submit")


def send_platform_delivery(job: dict, config: dict, db, throttle_config: dict) -> tuple[dict, str | None]:
    """Return (result, tab for human review); never retry uncertain submissions."""
    platform = str(job.get("source_platform") or "")
    if platform not in PLATFORMS:
        return paused("unsupported_delivery_platform"), None
    if not _approved(db, job, {str(x) for x in config.get("_workbench_job_ids", [])}):
        return paused("delivery_confirmation_required"), None
    if not valid_job_url(platform, str(job.get("url") or ""), str(job.get("source_job_id") or "")):
        return paused("job_identity_mismatch"), None
    previous_attempt = _previous_attempt(db, job["id"])
    resume_name = str(config.get("platforms", {}).get(platform, {}).get("delivery", {}).get("resume_name") or "").strip()
    if previous_attempt and (platform != "zhilian" or not resume_name or _has_submit_attempt(db, job)):
        return paused("delivery_attempt_requires_review"), None
    safety = config.get("platforms", {}).get(platform, {}).get("safety", {})
    page_limit = _limit(safety.get("daily_platform_page_limit", 80), 80)
    daily_limit = _limit(safety.get("daily_delivery_limit", 10), 10)
    # Explicit platform is essential: never debit BOSS's page budget for other sites.
    guard_config = {**config, "safety": {**config.get("safety", {}), "daily_platform_page_limit": page_limit}}
    guard = PlatformAccessGuard(db, guard_config, "send", platform=platform)
    target = None
    attempted = False
    stop = throttle_config.get("_workbench_stop_event")
    window = throttle_config.get("_send_window_checker")

    def boundary():
        guard.ensure_unlocked()
        if stop and stop.is_set():
            raise PlatformSafetyStop("stopped")
        if window and not window.is_active():
            raise PlatformSafetyStop("outside_window")

    try:
        boundary()
        recovery = _resume_recovery_target(db, job, resume_name) if previous_attempt else None
        reopen_chooser = previous_attempt and _chooser_reopen_authorized(db, job, resume_name)
        if previous_attempt and not recovery and not reopen_chooser:
            return paused("delivery_attempt_requires_review"), None
        if not recovery and delivery_count(db, platform) >= daily_limit:
            raise PlatformSafetyStop("daily_delivery_limit")
        if not recovery and count_platform_access_today(db, platform=platform) >= page_limit:
            raise PlatformSafetyStop("daily_platform_page_limit")
        if not recovery:
            guard.reserve("job_page")
        target = recovery or new_tab(job["url"], background=True)
        if not target:
            return paused("open_page_failed"), None
        # new_tab may initially expose about:blank/null. Read-only polling waits
        # for two stable, identity-verified DOM snapshots; never click on a timer.
        before = "page_unreadable"
        previous = None
        for _ in range(20):
            boundary()
            before = _state(target, job)
            if before in {"captcha", "rate_limit", "blocked", "login_required",
                          "resume_selection_required", "questionnaire_required", "paid_recommendation",
                          "dialog_requires_review", "already_applied", "success_receipt"}:
                break
            if before == "ready" and previous == "ready":
                break
            previous = before
            time.sleep(0.5)
        else:
            return paused("page_not_stable" if before == "ready" else before), target
        if before in {"captcha", "rate_limit", "blocked"}:
            guard.lock(before)
        if before != "ready" and not (recovery and before == "resume_selection_required"):
            # Existing application is evidence, but not a new send by this run.
            return paused("already_applied" if before in {"already_applied", "success_receipt"} else before), target
        boundary()
        if not recovery and not reopen_chooser:
            _reserve_attempt(db, job, config, daily_limit)
        elif reopen_chooser and not recovery:
            # Reuse the already-budgeted application intent; count the new page
            # access above, and retain history instead of clearing a retry fence.
            db.execute("INSERT INTO history(job_id,action,detail) VALUES (?, 'delivery_chooser_reopened', ?)",
                       (job["id"], "fresh_confirmation_after_known_chooser_stop"))
            db.commit()
        attempted = True
        boundary()
        clicked = "clicked" if recovery else _state(target, job, click=True)
        if clicked in {"captcha", "rate_limit", "blocked"}:
            guard.lock(clicked)
        if clicked != "clicked":
            return paused(clicked, attempted=True), target
        # After the single submit, allow slow platform requests to settle.
        # Polling is read-only; an absent receipt never authorizes another click.
        boundary()
        after = "page_unreadable"
        handled_resume = False
        prior_after = None
        for _ in range(40):
            boundary()
            after = _state(target, job)
            if after == "resume_selection_required" and not handled_resume:
                handled_resume = True
                after = _submit_selected_resume(target, job, config, db, boundary)
                if after != "resume_submitted":
                    # A reactive chooser can disappear between inspect and submit,
                    # or remain visible while its request completes. Once the
                    # durable final fence exists, only poll; never click again.
                    if not (_has_submit_attempt(db, job) and after in {"resume_selection_required", "page_unreadable", "ready", "already_applied", "success_receipt"}):
                        break
                    if after == "success_receipt":
                        break
                time.sleep(0.5)
                continue
            if after == "already_applied" and prior_after == "already_applied":
                after = "success_receipt"
                break
            if after == "resume_selection_required" and handled_resume and _has_submit_attempt(db, job):
                time.sleep(0.5)
                continue
            if after not in {"ready", "page_unreadable", "already_applied"}:
                break
            prior_after = after
            time.sleep(0.5)
        if after in {"captcha", "rate_limit", "blocked"}:
            guard.lock(after)
            return paused(after, attempted=True), target
        boundary()
        if after == "success_receipt":
            close_tab(target)
            return {"success": True, "verified": True, "attempted": True,
                    "platform": platform, "receipt": "success_receipt", "retryable": False}, None
        if after in {"ready", "already_applied"} or (after == "resume_selection_required" and _has_submit_attempt(db, job)):
            after = "delivery_result_unknown"
        return paused(after, attempted=True), target
    except PlatformSafetyStop as exc:
        return paused(exc.reason, attempted=attempted), target
    except Exception:  # noqa: BLE001 - a browser failure after click must keep the retry fence
        # Browser exceptions may happen after a click reached the page. Never retry.
        return paused("delivery_result_unknown" if attempted else "page_unreadable", attempted=attempted), target
