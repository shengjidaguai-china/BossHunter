"""Offline only: temporary SQLite, fake browser, and executable JS DOM fixtures."""
import json
import shutil
import subprocess
from unittest.mock import Mock, patch

import pytest

from bosshunter.db import add_history, get_db, insert_job, update_job_status
from bosshunter.executor import platform_delivery as delivery
from bosshunter.executor import sender

URLS = {
    'zhilian': ('CC120975580J40962349215', 'https://www.zhaopin.com/jobdetail/CC120975580J40962349215.htm'),
    '51job': ('173879961', 'https://jobs.51job.com/ningbo-yzq/173879961.html'),
    'liepin': ('123456', 'https://www.liepin.com/job/123456.shtml'),
}


@pytest.fixture
def setup(tmp_path):
    db = get_db(tmp_path / 'test.db')
    yield db, tmp_path / 'test.db'
    db.close()


def make_job(db, platform='51job'):
    source_id, url = URLS[platform]
    job = {'id': f'{platform}:{source_id}', 'source_platform': platform, 'source_job_id': source_id,
               'url': url, 'title': '工程师', 'company': '示例公司', 'status': 'approved'}
    insert_job(db, job)
    update_job_status(db, job['id'], 'approved')
    add_history(db, job['id'], 'approved')
    return job


def config_for(job):
    return {'_workbench_job_ids': [job['id']], 'throttle': {'send_windows': [], 'day_off_probability': 0}}


def run(db, job, states, config=None, throttle=None):
    iterator = iter(states)
    last = states[-1]
    def evaluate(*args):
        nonlocal last
        last = next(iterator, last)
        if isinstance(last, Exception):
            raise last
        return {'state': last} if last is not None else None
    with patch.object(delivery, 'activate_tab', return_value=True), patch.object(delivery, 'new_tab', return_value='review-tab'), \
            patch.object(delivery, 'close_tab'), patch.object(delivery.time, 'sleep'), \
            patch.object(delivery, 'evaluate', side_effect=evaluate) as browser:
        result = delivery.send_platform_delivery(job, config or config_for(job), db, throttle or {})
    return result, browser


@pytest.mark.parametrize('platform', URLS)
def test_ui_success_requires_new_receipt_and_committed_intent(setup, platform):
    db, _ = setup
    job = make_job(db, platform)
    states = iter(['ready', 'ready', 'clicked', 'success_receipt'])
    def evaluate(_, script):
        if '"click": true' in script:
            assert db.execute("SELECT count(*) FROM history WHERE action='delivery_attempt'").fetchone()[0] == 1
            assert not db.in_transaction
        return {'state': next(states)}
    with patch.object(delivery, 'new_tab', return_value='tab'), patch.object(delivery, 'close_tab'), \
            patch.object(delivery.time, 'sleep'), patch.object(delivery, 'evaluate', side_effect=evaluate):
        result, tab = delivery.send_platform_delivery(job, config_for(job), db, {})
    assert result['success'] and result['verified'] and tab is None
    assert db.execute('SELECT platform FROM platform_access_events').fetchone()[0] == platform
    assert delivery.delivery_count(db, platform) == 1
    add_history(db, job['id'], 'sent')
    assert delivery.delivery_count(db) == 1


@pytest.mark.parametrize('state', ['captcha', 'rate_limit', 'blocked', 'login_required',
    'resume_selection_required', 'questionnaire_required', 'paid_recommendation',
    'dialog_requires_review', 'already_applied', 'apply_button_ambiguous', 'job_identity_mismatch'])
def test_preflight_blocks_without_click(setup, state):
    db, _ = setup
    job = make_job(db)
    (result, tab), browser = run(db, job, [state])
    assert not result['success'] and result['error'] == state and tab == 'review-tab'
    assert not any('"click": true' in call.args[1] for call in browser.call_args_list)
    assert not delivery._previous_attempt(db, job['id'])


@pytest.mark.parametrize('state', ['ready', None, RuntimeError('timeout'),
                                  'captcha', 'resume_selection_required', 'dialog_requires_review'])
def test_uncertain_click_is_permanently_fenced_even_after_reset_and_next_day(setup, state):
    db, _ = setup
    job = make_job(db)
    (result, _), browser = run(db, job, ['ready', 'ready', 'clicked', state])
    assert not result['success'] and result['manual_required'] and result['attempted']
    assert sum('"click": true' in c.args[1] for c in browser.call_args_list) == 1
    db.execute("UPDATE history SET created_at='2000-01-01' WHERE action='delivery_attempt'")
    db.commit()
    (again, _), browser = run(db, job, ['ready'])
    assert again['error'] == 'delivery_attempt_requires_review'
    browser.assert_not_called()


def test_blank_page_waits_for_two_identity_verified_snapshots(setup):
    db, _ = setup
    job = make_job(db)
    (result, _), browser = run(db, job, [None, 'job_identity_mismatch', 'ready', 'ready', 'clicked', 'success_receipt'])
    assert result['success']
    assert '"click": true' in browser.call_args_list[4].args[1]


@pytest.mark.parametrize('url', ['https://jobs.51job.com.evil.test/x/173879961.html',
    'https://evil.test/jobs.51job.com/x/173879961.html', 'http://jobs.51job.com/x/173879961.html',
    'https://name@jobs.51job.com/x/173879961.html', 'https://jobs.51job.com/x/173879962.html',
    'https://jobs.51job.com:444/x/173879961.html'])
def test_url_identity_is_exact(url):
    assert not delivery.valid_job_url('51job', url, '173879961')


@pytest.mark.parametrize('field,code', [('daily_delivery_limit', 'daily_delivery_limit'),
                                      ('daily_platform_page_limit', 'daily_platform_page_limit')])
def test_zero_platform_budget_prevents_navigation(setup, field, code):
    db, _ = setup
    job = make_job(db)
    config = config_for(job)
    config['platforms'] = {'51job': {'safety': {field: 0}}}
    with patch.object(delivery, 'new_tab') as tab:
        result, _ = delivery.send_platform_delivery(job, config, db, {})
    assert result['error'] == code
    tab.assert_not_called()


def test_approval_and_reevaluation_are_enforced(setup):
    db, _ = setup
    job = make_job(db)
    assert not delivery._approved(db, job, [])
    add_history(db, job['id'], 'agent_evaluated')
    assert not delivery._approved(db, job, [job['id']])
    add_history(db, job['id'], 'approved')
    assert delivery._approved(db, job, [job['id']])


def test_window_boundary_after_reservation_blocks_click(setup):
    db, _ = setup
    job = make_job(db)
    checker = Mock()
    checker.is_active.side_effect = [True, True, True, True, False]
    (result, _), browser = run(db, job, ['ready', 'ready'], throttle={'_send_window_checker': checker})
    assert result['error'] == 'outside_window' and result['attempted']
    assert not any('"click": true' in c.args[1] for c in browser.call_args_list)


def test_sender_native_without_greeting_and_boss_never_used(setup):
    db, path = setup
    job = make_job(db)
    config = config_for(job)
    with patch.object(sender, 'platform_supports', return_value=True), \
            patch.object(sender, 'send_platform_delivery', return_value=({'success': True, 'verified': True}, None)) as native, \
            patch.object(sender, '_send_greeting_once') as boss:
        assert sender.send_greetings(config, db_path=path) == 1
    assert native.call_count == 1
    boss.assert_not_called()
    assert db.execute('SELECT status FROM jobs').fetchone()[0] == 'sent'


def test_sender_manual_pause_retains_tab_and_stops_batch(setup):
    db, path = setup
    job = make_job(db)
    config = config_for(job)
    with patch.object(sender, 'platform_supports', return_value=True), \
            patch.object(sender, 'send_platform_delivery', return_value=(delivery.paused('delivery_result_unknown', attempted=True), 'tab')) as native, \
            patch.object(sender, 'close_tab') as close:
        assert sender.send_greetings(config, db_path=path) == 0
    assert native.call_count == 1
    close.assert_not_called()
    assert config['_workbench_send_report']['manual_review_tabs'] == {job['id']: 'tab'}


def test_boss_function_rejects_external_platform_before_browser():
    with patch.object(sender, 'new_tab') as tab:
        result, _ = sender._send_greeting_once({'source_platform': '51job'}, '', {})
    assert result['error'] == 'unsupported_delivery_platform'
    tab.assert_not_called()


@pytest.mark.parametrize('platform', URLS)
@pytest.mark.parametrize('scenario,expected', [('ready', 'clicked'), ('duplicate', 'apply_button_ambiguous'),
    ('wrong_title', 'job_identity_mismatch'), ('hidden', 'apply_button_ambiguous'),
    ('dialog', 'dialog_requires_review'), ('receipt', 'success_receipt'), ('captcha', 'captcha'),
    ('resume_modal', 'resume_selection_required'), ('continue_chat', 'already_applied')])
def test_actual_browser_script_on_dom_fixture(platform, scenario, expected):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for offline DOM fixture execution')
    source_id, url = URLS[platform]
    job = {'source_platform': platform, 'source_job_id': source_id, 'url': url, 'title': '工程师', 'company': '示例公司'}
    spec = delivery.PLATFORMS[platform]
    payload = json.dumps({'spec': spec, 'url': url, 'scenario': scenario, 'platform': platform}, ensure_ascii=False)
    harness = r'''
const fixture = FIXTURE;
let clicks=0;
const element = (text) => ({innerText:text, tagName:'BUTTON', disabled:false,
 getBoundingClientRect:()=>({width:100,height:30,left:10,top:10}),
 closest:()=>null, getAttribute:()=>null, classList:{contains:()=>false},
 contains:el=>false, click:()=>{clicks++}});
const apply=element(fixture.platform==='liepin'?'投递简历':'立即投递');
if (fixture.platform==='51job') apply.tagName='DIV';
if(fixture.scenario==='continue_chat') apply.innerText='继续沟通';
const root=element('');
root.querySelectorAll=selector=>{
 if(selector===fixture.spec.title) return [element(fixture.scenario==='wrong_title'?'其他岗位':'工程师')];
 if(selector===fixture.spec.company) return [element('示例公司')];
 if(selector.includes('[role="status"]')) return fixture.scenario==='receipt'?[element('投递成功')]:[];
 if(fixture.platform==='51job' && !selector.includes(fixture.spec.extraButton)) return [];
 return fixture.scenario==='duplicate'?[apply,element(apply.innerText)]:[apply];
};
global.location=new URL(fixture.url);
global.innerWidth=1000; global.innerHeight=800;
global.getComputedStyle=el=>({display:fixture.scenario==='hidden'&&el===apply?'none':'block',visibility:'visible',opacity:'1'});
global.document={body:{innerText:fixture.scenario==='captcha'?'请完成验证码':fixture.scenario==='resume_modal'?'请选择要投递的简历':''},
 querySelectorAll:selector=>selector===fixture.spec.company?[element('示例公司')]:selector===fixture.spec.root?[root]:(fixture.scenario==='dialog'&&selector.includes('[role="dialog"]')?[element('确认')] : []),
 elementFromPoint:()=>apply};
const result=SCRIPT;
console.log(JSON.stringify({result:JSON.parse(result),clicks}));
'''.replace('FIXTURE', payload).replace('SCRIPT', delivery._script(job, click=True))
    output = subprocess.run([node, '-e', harness], capture_output=True, text=True, check=True)
    data = json.loads(output.stdout)
    if scenario == 'continue_chat' and platform != 'zhilian':
        expected = 'apply_button_ambiguous'
    assert data['result']['state'] == expected
    assert data['clicks'] == int(expected == 'clicked')


@pytest.mark.parametrize('platform', URLS)
def test_default_daily_delivery_limit_counts_uncertain_attempts(setup, platform):
    db, _ = setup
    job = make_job(db, platform)
    for i in range(10):
        other = {**job, 'id': f'{platform}:other{i}', 'source_job_id': f'other{i}'}
        insert_job(db, other)
        add_history(db, other['id'], 'delivery_attempt')
    with patch.object(delivery, 'new_tab') as tab:
        result, _ = delivery.send_platform_delivery(job, config_for(job), db, {})
    assert result['error'] == 'daily_delivery_limit'
    tab.assert_not_called()


def test_default_page_limit_includes_collection_pages(setup):
    from bosshunter.db import add_platform_access
    db, _ = setup
    job = make_job(db)
    for _ in range(80):
        add_platform_access(db, 'collect', 'detail_page', platform='51job')
    with patch.object(delivery, 'new_tab') as tab:
        result, _ = delivery.send_platform_delivery(job, config_for(job), db, {})
    assert result['error'] == 'daily_platform_page_limit'
    tab.assert_not_called()


def test_reservation_survives_new_connection_and_quota_race(setup):
    db, path = setup
    job = make_job(db)
    config = config_for(job)
    delivery._reserve_attempt(db, job, config, 10)
    db2 = get_db(path)
    try:
        with pytest.raises(delivery.PlatformSafetyStop, match='delivery_attempt_requires_review'):
            delivery._reserve_attempt(db2, job, config, 10)
        assert delivery.delivery_count(db2) == 1
    finally:
        db2.close()


def test_global_quota_is_rechecked_atomically_before_click(setup):
    db, _ = setup
    job = make_job(db)
    config = config_for(job)
    config['throttle']['daily_limit'] = 0
    (result, _), browser = run(db, job, ['ready', 'ready'], config=config)
    assert result['error'] == 'daily_limit'
    assert not any('"click": true' in c.args[1] for c in browser.call_args_list)


@pytest.mark.parametrize('selected,approved', [(False, True), (True, False)])
def test_sender_does_not_infer_external_approval(setup, selected, approved):
    db, path = setup
    job = make_job(db)
    config = config_for(job)
    if not selected:
        config['_workbench_job_ids'] = []
    if not approved:
        db.execute("DELETE FROM history WHERE action='approved'")
        update_job_status(db, job['id'], 'ready')
    with patch.object(sender, 'send_platform_delivery') as native:
        assert sender.send_greetings(config, db_path=path) == 0
    native.assert_not_called()


def test_sender_approved_internship_still_excluded(setup):
    db, path = setup
    job = make_job(db)
    db.execute("UPDATE jobs SET title='实习生'")
    db.commit()
    config = config_for(job)
    config['profile'] = {'allow_internship': False}
    with patch.object(sender, 'send_platform_delivery') as native:
        assert sender.send_greetings(config, db_path=path) == 0
    native.assert_not_called()


def resume_config(job):
    config = config_for(job)
    config['platforms'] = {'zhilian': {'delivery': {'resume_name': 'approved-resume.pdf'}}}
    return config


def test_selected_resume_is_submitted_only_once_after_durable_fence(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    states = ['ready', 'ready', 'clicked', 'resume_selection_required',
              'resume_preparing', 'resume_ready', 'resume_submitted', 'success_receipt']
    iterator = iter(states)
    def browser(_, script):
        if '\"resumeAction\": \"submit\"' in script:
            assert db.execute("SELECT count(*) FROM history WHERE action='delivery_submit_attempt'").fetchone()[0] == 1
            assert not db.in_transaction
        return {'state': next(iterator)}
    with patch.object(delivery, 'activate_tab', return_value=True), patch.object(delivery, 'new_tab', return_value='tab'), patch.object(delivery, 'close_tab'), \
            patch.object(delivery.time, 'sleep'), patch.object(delivery, 'evaluate', side_effect=browser) as evaluate:
        result, _ = delivery.send_platform_delivery(job, config, db, {})
    assert result['success']
    assert sum('"resumeAction": "submit"' in c.args[1] for c in evaluate.call_args_list) == 1
    with patch.object(delivery, 'evaluate') as again:
        result, _ = delivery.send_platform_delivery(job, config, db, {})
    assert result['error'] == 'delivery_attempt_requires_review'
    again.assert_not_called()


@pytest.mark.parametrize('failure', ['resume_selection_required', 'captcha', 'job_identity_mismatch'])
def test_resume_preparation_failure_never_submits(setup, failure):
    db, _ = setup
    job = make_job(db, 'zhilian')
    (result, _), browser = run(db, job, ['ready', 'ready', 'clicked', 'resume_selection_required', failure], config=resume_config(job))
    assert not result['success']
    assert not any('"resumeAction": "submit"' in c.args[1] for c in browser.call_args_list)
    assert db.execute("SELECT COUNT(*) FROM history WHERE action='delivery_submit_attempt'").fetchone()[0] == 0


def test_resume_final_submit_timeout_stays_fenced(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    (result, _), browser = run(db, job, ['ready', 'ready', 'clicked', 'resume_selection_required',
        'resume_preparing', 'resume_ready', RuntimeError('timeout')], config=config)
    assert not result['success'] and result['error'] == 'delivery_result_unknown'
    add_history(db, job['id'], 'approved')
    (result, _), browser = run(db, job, ['ready'], config=config)
    assert result['error'] == 'delivery_attempt_requires_review'
    browser.assert_not_called()


def test_existing_resume_chooser_requires_fresh_confirmation(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    delivery._reserve_attempt(db, job, config, 10)
    with patch.object(delivery, 'get_page_targets') as tabs:
        assert delivery._resume_recovery_target(db, job, 'approved-resume.pdf') is None
    tabs.assert_not_called()
    add_history(db, job['id'], 'approved')
    with patch.object(delivery, 'get_page_targets', return_value=[{'targetId':'original', 'url': job['url']}]), \
            patch.object(delivery, '_state', return_value='resume_selection_required'):
        assert delivery._resume_recovery_target(db, job, 'approved-resume.pdf') == 'original'


def test_stable_already_applied_transition_verifies_receipt(setup):
    db, _ = setup
    job = make_job(db)
    (result, _), _ = run(db, job, ['ready', 'ready', 'clicked', 'already_applied', 'already_applied'])
    assert result['success'] and result['verified']


def test_resume_activation_must_succeed_before_any_selection(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    with patch.object(delivery, 'activate_tab', return_value=False), patch.object(delivery, '_state') as state:
        assert delivery._submit_selected_resume('tab', job, config, db, lambda: None) == 'page_unreadable'
    state.assert_not_called()


def test_background_resume_animation_is_waited_for_after_activation(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    delivery._reserve_attempt(db, job, config, 10)
    with patch.object(delivery, 'activate_tab', return_value=True) as activate, \
            patch.object(delivery, '_state', side_effect=['resume_selection_required', 'resume_preparing', 'resume_ready', 'resume_submitted']), \
            patch.object(delivery.time, 'sleep'):
        assert delivery._submit_selected_resume('tab', job, config, db, lambda: None) == 'resume_submitted'
    activate.assert_called_once_with('tab')


def test_resume_claim_rejects_changed_job_and_duplicate_submission(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    delivery._reserve_attempt(db, job, config, 10)
    delivery._claim_resume_submit(db, job, config)
    with pytest.raises(delivery.PlatformSafetyStop, match='delivery_attempt_requires_review'):
        delivery._claim_resume_submit(db, job, config)


def test_known_chooser_reopen_requires_new_approval_and_no_final_submit(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    delivery._reserve_attempt(db, job, config, 10)
    add_history(db, job['id'], 'delivery_paused', 'resume_selection_required')
    assert not delivery._chooser_reopen_authorized(db, job, 'approved-resume.pdf')
    add_history(db, job['id'], 'approved')
    assert delivery._chooser_reopen_authorized(db, job, 'approved-resume.pdf')
    add_history(db, job['id'], 'delivery_paused', 'delivery_result_unknown')
    assert not delivery._chooser_reopen_authorized(db, job, 'approved-resume.pdf')
    add_history(db, job['id'], 'delivery_paused', 'resume_selection_required')
    delivery._claim_resume_submit(db, job, config)
    assert not delivery._chooser_reopen_authorized(db, job, 'approved-resume.pdf')


def test_native_error_without_greeting_is_visible_for_manual_retry(setup):
    from bosshunter.db import get_jobs_with_send_errors
    db, _ = setup
    job = make_job(db, 'zhilian')
    update_job_status(db, job['id'], 'error')
    assert [row['id'] for row in get_jobs_with_send_errors(db)] == [job['id']]


def test_cross_day_resume_submission_reserves_current_day_quota(setup):
    db, _ = setup
    job = make_job(db, 'zhilian')
    config = resume_config(job)
    delivery._reserve_attempt(db, job, config, 10)
    db.execute("UPDATE history SET created_at='2000-01-01' WHERE action='delivery_attempt'")
    db.commit()
    assert delivery.delivery_count(db) == 0
    delivery._claim_resume_submit(db, job, config)
    assert delivery.delivery_count(db) == 1


@pytest.mark.parametrize("submit_state", ["resume_submitted", "resume_selection_required"])
def test_final_resume_waits_for_lingering_chooser_without_resubmit(setup, submit_state):
    db, _ = setup
    job = make_job(db, "zhilian")
    (result, _), browser = run(db, job, ["ready", "ready", "clicked",
        "resume_selection_required", "resume_preparing", "resume_ready", submit_state,
        "resume_selection_required", "resume_selection_required", "already_applied", "already_applied"],
        config=resume_config(job))
    assert result["success"] and result["verified"]
    assert sum('"resumeAction": "submit"' in c.args[1] for c in browser.call_args_list) == 1


def test_final_resume_persistent_chooser_reports_unknown_and_never_retries(setup):
    db, _ = setup
    job = make_job(db, "zhilian")
    (result, _), browser = run(db, job, ["ready", "ready", "clicked",
        "resume_selection_required", "resume_preparing", "resume_ready", "resume_submitted",
        "resume_selection_required"], config=resume_config(job))
    assert result["error"] == "delivery_result_unknown"
    assert sum('"resumeAction": "submit"' in c.args[1] for c in browser.call_args_list) == 1
    (again, _), browser = run(db, job, ["ready"], config=resume_config(job))
    assert again["error"] == "delivery_attempt_requires_review"
    browser.assert_not_called()
