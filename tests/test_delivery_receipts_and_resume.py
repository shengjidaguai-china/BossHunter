"""Regression boundaries: successful submission, attachment choice and partial chat."""
import json
import shutil
import subprocess
from unittest.mock import Mock, patch

import pytest

from bosshunter.config import DEFAULTS
from bosshunter.executor import platform_delivery as delivery
from bosshunter.collection.capabilities import delivery_capabilities


def run_js(script, fixture):
    node = shutil.which('node')
    assert node, 'Node is required for offline DOM regression tests'
    result = subprocess.run([node, '-'], input=fixture.replace('SCRIPT', json.dumps(script)),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_all_external_platforms_default_to_attachment():
    for platform in ('zhilian', '51job', 'liepin'):
        assert DEFAULTS['delivery']['platforms'][platform]['resume_choice'] == 'attachment'


def test_success_toast_survives_disappearing_apply_button():
    expected = dict(origin='https://jobs.zhaopin.com', path='/123.htm', title='Engineer', company='Acme', platform='zhilian', phase='receipt')
    run_js(delivery._APPLY_SCRIPT.replace('EXPECTED_JOB', json.dumps(expected)), r'''
const assert=require('node:assert/strict');global.location={origin:'https://jobs.zhaopin.com',pathname:'/123.htm'};
global.document={body:{innerText:'Engineer Acme 投递成功'},querySelectorAll:s=>s.includes('[role=alert]')&&document.body.innerText.includes('投递成功')?[{innerText:'投递成功',getClientRects:()=>[{}]}]:[]};
assert.deepEqual(eval(SCRIPT),{receipt:true});
document.body.innerText='Engineer Acme';assert.deepEqual(eval(SCRIPT),{receipt:false});
location.pathname='/other';assert.equal(eval(SCRIPT).error,'job_identity_mismatch');
''')


def test_attachment_not_selected_blocks_the_initial_application_click():
    expected = dict(origin='https://jobs.51job.com', path='/shanghai/123.html', title='Engineer', company='Acme', platform='51job', phase='submit',resume_choice='attachment', resume_name='approved.pdf')
    run_js(delivery._APPLY_SCRIPT.replace('EXPECTED_JOB', json.dumps(expected)), r'''
const assert=require('node:assert/strict');global.location={origin:'https://jobs.51job.com',pathname:'/shanghai/123.html'};
global.getComputedStyle=()=>({visibility:'visible'});let clicks=0;
const button={innerText:'立即投递',id:'123',getClientRects:()=>[{}],getAttribute:()=>null,click:()=>clicks++};
global.document={body:{innerText:'Engineer Acme'},querySelectorAll:s=>s==='div.apply-btn-new.big'?[button]:[]};
assert.equal(eval(SCRIPT).error,'attachment_selection_unverified');assert.equal(clicks,0);
''')


def test_official_record_matches_exact_job_and_success_in_same_row():
    run_js(delivery._ZHILIAN_APPLICATION_RECORD.replace('EXPECTED_RECORD', json.dumps(dict(id='123',title='Engineer',company='Acme'))), r'''
const assert=require('node:assert/strict');global.location={origin:'https://i.zhaopin.com',pathname:'/schedule'};
let row={innerText:'Engineer Acme 成功投递 2026-11-23 16:20:41'};
const a={href:'http://jobs.zhaopin.com/123.htm?refcode=1',closest:()=>row};
global.document={querySelectorAll:()=>[a]};assert.equal(eval(SCRIPT).receipt,true);
a.href='http://jobs.zhaopin.com/1234.htm';assert.equal(eval(SCRIPT).receipt,false);
a.href='http://jobs.zhaopin.com/123.htm';row.innerText='Engineer Acme 已查看';assert.equal(eval(SCRIPT).receipt,false);
''')


def test_record_bridge_error_closes_only_its_owned_tab():
    browser = Mock()
    browser.new_tab.return_value='records'
    browser.evaluate.side_effect=delivery.EgoTaskSpaceError('lost response')
    assert not delivery.verify_zhilian_application(browser,dict(id='zhilian:123',title='Engineer',company='Acme'))
    browser.close_tab.assert_called_once_with('records')


def test_chat_action_is_explicit_opt_in_for_preview():
    config={'delivery':{'ego_task_space_id':14,'platforms':{'liepin':{'enabled':True,'action':'chat'}}}}
    caps=delivery_capabilities(config)['liepin']
    assert caps['action_id']=='greeting'
    assert '聊一聊' in caps['action_label']
    config['delivery']['platforms']['liepin'].pop('action')
    assert delivery_capabilities(config)['liepin']['action_id']=='apply_resume'


def test_chat_cannot_execute_with_an_application_confirmation():
    from bosshunter.executor.liepin_chat import submit_chat
    with patch('bosshunter.executor.liepin_chat.EgoTaskSpace.from_config') as factory:
        assert submit_chat(None, {'id':'liepin:123'}, {'_workbench_expected_actions':{'liepin:123':'apply_resume'}})['error']=='confirmed_action_changed'
        factory.assert_not_called()


def test_verified_greeting_without_attachment_control_remains_pending_resume(tmp_path, monkeypatch):
    from bosshunter.executor import liepin_chat
    monkeypatch.chdir(tmp_path)
    job={'id':'liepin:123','url':'https://www.liepin.com/job/123.shtml', 'company':'Acme','title':'Engineer',
         'greeting':'Reviewed greeting','greeting_selection':'custom'}
    config={'delivery':{'ego_task_space_id':14,'platforms':{'liepin':{'action':'chat','resume_name':'approved.pdf'}}},
            '_workbench_expected_actions':{'liepin:123':'greeting'},'throttle':{'send_windows':['00:00-23:59']}}
    with patch.object(liepin_chat.EgoTaskSpace,'from_config') as factory, patch.object(liepin_chat,'PlatformAccessGuard'), patch.object(delivery,'approval_error',return_value=None):
        browser=factory.return_value
        browser.new_tab.return_value='chat'
        sent=[]
        browser.press_key_action.side_effect=lambda *args: sent.append(args)
        def evaluate(target, script):
            if 'EXPECTED_JOB' in script: raise AssertionError('unexpanded script')
            if "chat-chat" in script:return {'selector':'a[data-selector="chat-chat"] >> nth=0','name':'Recruiter'}
            if "document.querySelector('textarea.im-ui-textarea')?.value" in script:return job['greeting']
            if '.im-ui-message-item-send' in script:return bool(sent)
            if '.action-resume' in script:return 0
            if 'const e=' in script:return True
            return None
        browser.evaluate.side_effect=evaluate
        result=liepin_chat.submit_chat(None,job,config)
        assert result['success'] and result['needs_resume']
        assert len(sent)==1
        browser.close_tab.assert_called_once_with('chat')
        browser.screenshot.assert_called_once()


def test_sender_records_partial_chat_and_blocks_duplicate(tmp_path):
    from bosshunter.db import get_db
    from bosshunter.executor.sender import send_greetings
    db=get_db(tmp_path/'test.db')
    db.execute("INSERT INTO jobs(id,source_platform,company,title,url,status,greeting,greeting_selection) VALUES ('chat','liepin','Acme','Engineer','https://www.liepin.com/job/123.shtml','approved','Hello','custom')")
    db.commit()
    config={'delivery':{'ego_task_space_id':14,'platforms':{'liepin':{'enabled':True,'action':'chat'}}},
            '_workbench_job_ids':['chat'],'_workbench_expected_platforms':{'chat':'liepin'},'_workbench_expected_actions':{'chat':'greeting'}}
    with patch('bosshunter.browser.ego.EgoTaskSpace.check'),patch.object(delivery,'submit_resume',return_value={'success':True,'needs_resume':True}):
        assert send_greetings(config,force=True,db_path=tmp_path/'test.db')==1
    assert db.execute("SELECT status FROM jobs WHERE id='chat'").fetchone()[0]=='needs_resume'
    assert [r[0] for r in db.execute("SELECT action FROM history")] == ['sent','needs_resume']
    db.close()
