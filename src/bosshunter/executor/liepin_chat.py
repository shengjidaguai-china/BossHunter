"""Explicitly confirmed Liepin chat, with independently verified résumé delivery."""
import json
import re
import time
from pathlib import Path

from bosshunter.browser.ego import EgoTaskSpace, EgoTaskSpaceError
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop
from bosshunter.throttle import SendWindowChecker


def submit_chat(db, job, config):
    from .platform_delivery import approval_error, _failed, note_risk
    if config.get('_workbench_expected_actions', {}).get(str(job['id'])) != 'greeting':
        return _failed('confirmed_action_changed')
    greeting = str(job.get('greeting') or '').strip()
    if not greeting or job.get('greeting_selection') == 'pending':
        return _failed('approval_changed')
    browser = EgoTaskSpace.from_config(config, section='delivery')
    guard = PlatformAccessGuard(db, config, 'send', 'liepin')
    stop = config.get('_workbench_stop_event')
    target = None
    dispatched = False
    greeted = False

    def check():
        if stop and stop.is_set():
            raise PlatformSafetyStop('stopped')
        guard.ensure_unlocked()
        if not SendWindowChecker(config.get('throttle', {}).get('send_windows', ['09:00-16:00'])).is_active():
            raise PlatformSafetyStop('outside_window')
        if reason := approval_error(db, job, config):
            raise PlatformSafetyStop(reason)
        risk = browser.evaluate(target, """(() => {
          const text=document.body?.innerText || '';
          return /安全验证|验证码|拖动滑块|请完成验证|扫码登录/.test(text) ? 'captcha' :
            /操作过于频繁|访问过于频繁/.test(text) ? 'rate_limit' :
            /账号异常|访问受限|操作异常/.test(text) ? 'blocked' : null;
        })()""")
        if risk in {'captcha', 'rate_limit', 'blocked'}:
            guard.lock(risk)
            note_risk('liepin', risk, browser.space_id)
            raise PlatformSafetyStop(risk)

    def poll(expression):
        deadline = time.monotonic() + 8
        while True:
            check()
            result = browser.evaluate(target, expression)
            if result or time.monotonic() >= deadline:
                return result
            if stop:
                stop.wait(.25)
            else:
                time.sleep(.25)

    def pending():
        return {'success': True, 'needs_resume': True,
                'history_detail': '聊一聊招呼语已核实；待手动发附件简历'}

    try:
        if stop and stop.is_set():
            return _failed('stopped')
        guard.reserve('job_page')
        target = browser.new_tab(job['url'])
        if not target or not browser.wait_for_load(target):
            return _failed('page_unavailable')
        check()
        expected = {'title': job['title'], 'company': job['company'], 'url': job['url']}
        probe = browser.evaluate(target, _CHAT_PROBE.replace('EXPECTED_JOB', json.dumps(expected)))
        if not isinstance(probe, dict) or not probe.get('selector'):
            return _failed((probe or {}).get('error', 'chat_control_unverified'))
        # Two observed buttons point to the same recruiter. Click only the top one.
        check()
        browser.click_action(target, probe['selector'])
        identity = json.dumps({'title': job['title'], 'name': probe['name']})
        ready_script = """(() => { const e=EXPECTED; const c=document.querySelector('.im-ui-chat-container');
            return !!c && c.innerText.includes(e.title) && c.innerText.includes(e.name) &&
                !!c.querySelector('textarea.im-ui-textarea'); })()""".replace('EXPECTED', identity)
        if not poll(ready_script):
            return _failed('chat_identity_unverified')
        receipt = """(() => { const message=MESSAGE; const c=document.querySelector('.im-ui-chat-container');
          return !!c && [...c.querySelectorAll('.im-ui-message-item-send')].some(e =>
            e.innerText.includes(message) && !e.querySelector('.im-ui-message-item-failed-icon') &&
            ![...e.querySelectorAll('.im-ui-message-item-loadingicon')].some(icon=>!icon.classList.contains('hide'))); })()""".replace('MESSAGE', json.dumps(greeting))
        if browser.evaluate(target, receipt):
            return _failed('existing_chat_message_requires_reconciliation', uncertain=True)
        check()
        browser.click_action(target, 'textarea.im-ui-textarea')
        browser.type_text_action(target, greeting)
        if browser.evaluate(target, "document.querySelector('textarea.im-ui-textarea')?.value") != greeting:
            return _failed('chat_input_unverified')
        check()
        dispatched = True
        browser.press_key_action(target, 'Enter')
        if not poll(receipt):
            return _failed('unconfirmed_chat_message', uncertain=True)
        greeted = True
        # This control first opens the attachment chooser when attachments exist.
        check()
        if browser.evaluate(target, "document.querySelectorAll('.im-ui-chat-input .action-resume').length") != 1:
            return pending()
        browser.click_action(target, '.im-ui-chat-input .action-resume')
        if not poll("[...document.querySelectorAll('[role=dialog]')].some(e=>e.innerText.includes('选择附件简历'))"):
            return pending()
        name = config['delivery']['platforms']['liepin'].get('resume_name', '')
        chosen = browser.evaluate(target, _SELECT_ATTACHMENT.replace('RESUME_NAME', json.dumps(name)))
        if not isinstance(chosen, dict) or not chosen.get('selected'):
            return pending()
        check()
        browser.click_action(target, '.ant-im-modal:has(input[type=radio]:checked) button.ant-im-btn-primary')
        if not poll("document.body.innerText.includes('发送成功')"):
            return pending()
        return {'success': True, 'history_detail': '聊一聊招呼语与附件简历已发送'}
    except (EgoTaskSpaceError, PlatformSafetyStop) as exc:
        if greeted:
            return pending()
        return _failed(getattr(exc, 'reason', 'ego_unavailable'), uncertain=dispatched)
    finally:
        if target:
            if greeted:
                try:
                    directory = Path('data/delivery-receipts').resolve()
                    directory.mkdir(parents=True, exist_ok=True)
                    filename = re.sub(r'[^a-zA-Z0-9_-]', '_', str(job['id'])) + '.png'
                    browser.screenshot(target, directory / filename)
                except (EgoTaskSpaceError, OSError):
                    pass
            browser.close_tab(target)


_CHAT_PROBE = r"""
(() => {
 const e=EXPECTED_JOB, u=new URL(e.url);
 if(location.origin!==u.origin || location.pathname!==u.pathname ||
    !document.body.innerText.includes(e.title) || !document.body.innerText.includes(e.company))
   return {error:'job_identity_mismatch'};
 if([...document.querySelectorAll('a[data-selector="apply-job"]')].some(e=>e.getClientRects().length))
   return {error:'confirmed_action_changed'};
 const buttons=[...document.querySelectorAll('a[data-selector="chat-chat"]')].filter(e=>e.getClientRects().length);
 const first=buttons[0]; if(!first) return {error:'chat_control_unverified'};
 let params;try {params=buttons.map(e=>JSON.parse(e.getAttribute('data-params') || '{}'));}
 catch {return {error:'chat_identity_unverified'};}
 if(params.some(p=>!p.imId || p.imId!==params[0].imId || !p.jobId || p.jobId!==params[0].jobId))
   return {error:'chat_identity_unverified'};
 if(!u.pathname.includes(params[0].jobId)) return {error:'chat_identity_unverified'};
 return {selector:'a[data-selector="chat-chat"] >> nth=0',name:params[0].recruiterName};
})()
"""

_SELECT_ATTACHMENT = r"""
(() => {
 const name=RESUME_NAME;
 const dialogs=[...document.querySelectorAll('[role=dialog]')].filter(e=>e.getClientRects().length && e.innerText.includes('选择附件简历'));
 if(dialogs.length!==1)return {selected:false};
 const radios=[...dialogs[0].querySelectorAll('label')].filter(e=>e.querySelector('input[type=radio]'));
 const filename=e=>(e.querySelector('p')?.innerText || '').trim();
 const matches=name?radios.filter(e=>filename(e)===name || filename(e)===name+'.pdf'):radios;
 // The observed chooser is newest-first. Multiple unknown versions require an explicit name.
 if(matches.length!==1)return {selected:false};
 matches[0].click(); return {selected:!!matches[0].querySelector('input:checked')};
})()
"""
