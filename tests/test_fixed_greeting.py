from unittest.mock import patch

import pytest

from bosshunter.ai import greeter
from bosshunter.db import get_db, insert_job, update_job_status
from bosshunter.web.greeting_activity import GreetingActivityRegistry
from bosshunter.web import server


def make_job(db, job_id, status='approved', greeting=None, reviewed=None):
    insert_job(db, {'id': job_id, 'title': '内容运营', 'company': '示例公司', 'salary': '16-25K', 'jd': '内容运营'})
    update_job_status(db, job_id, status)
    db.execute('UPDATE jobs SET greeting=?, greeting_reviewed_at=? WHERE id=?', (greeting, reviewed, job_id))
    db.commit()


def test_fixed_greeting_is_verbatim_without_ai_or_resume_and_never_sends(tmp_path):
    path = tmp_path / 'jobs.db'
    db = get_db(path)
    make_job(db, 'new')
    make_job(db, 'reviewed', greeting='我已选择的文案', reviewed='2026-09-15')
    make_job(db, 'sent', status='sent', greeting='已发送的文案')
    config = {
        'profile': {'ai_greeting_enabled': False, 'fixed_greeting': '您好，我想了解这个岗位。方便聊聊吗？'},
        'ai': {'greeting_style_suggestions': True, 'greeting_auto_apply_style': True},
        '_workbench_regenerate': True,
        '_workbench_greeting_activity': GreetingActivityRegistry().claim,
    }
    with patch.object(greeter, '_call_claude') as ai, patch.object(greeter, '_get_resume_summary') as resume:
        assert greeter.generate_greetings(config, ['new', 'reviewed', 'sent'], path) == 1
    ai.assert_not_called()
    resume.assert_not_called()
    job = dict(db.execute("SELECT * FROM jobs WHERE id='new'").fetchone())
    assert job['greeting'] == config['profile']['fixed_greeting']
    assert job['greeting_original'] == job['greeting']
    assert not job['greeting_optimized']
    assert job['greeting_selection'] == 'generated'
    assert job['status'] == 'ready'
    assert not job['greeting_reviewed_at']
    assert db.execute("SELECT greeting FROM jobs WHERE id='reviewed'").fetchone()[0] == '我已选择的文案'
    assert db.execute("SELECT greeting FROM jobs WHERE id='sent'").fetchone()[0] == '已发送的文案'
    assert db.execute("SELECT COUNT(*) FROM history WHERE action='sent'").fetchone()[0] == 0
    db.close()


@pytest.mark.parametrize('fixed', ['', '   ', '字' * 301, 123])
def test_invalid_fixed_greeting_stops_without_fallback_to_ai(fixed):
    config = {'profile': {'ai_greeting_enabled': False, 'fixed_greeting': fixed}}
    with patch.object(greeter, '_call_claude') as ai, patch.object(greeter, 'get_db') as db:
        assert greeter.generate_greetings(config) == 0
    ai.assert_not_called()
    db.assert_not_called()
    assert config['_workbench_greeting_report']['pause_reason']


def test_running_task_uses_latest_greeting_preferences_without_changing_other_settings():
    config = {
        '_workbench_live_greeting_settings': True,
        'profile': {'ai_greeting_enabled': True, 'salary_min': 16},
        'ai': {'greeting_style_suggestions': True, 'model': 'original-model'},
        'throttle': {'daily_limit': 30},
    }
    with patch.object(server, 'load_config', return_value={
        'profile': {'ai_greeting_enabled': False, 'fixed_greeting': '新固定文案', 'salary_min': 1},
        'ai': {'greeting_style_suggestions': False, 'model': 'another-model'},
        'throttle': {'daily_limit': 100},
    }):
        result = server._refresh_greeting_settings(config)
    assert result['profile']['fixed_greeting'] == '新固定文案'
    assert result['profile']['ai_greeting_enabled'] is False
    assert result['profile']['salary_min'] == 16
    assert result['ai']['model'] == 'original-model'
    assert result['throttle']['daily_limit'] == 30
    assert config['profile']['ai_greeting_enabled'] is True


@pytest.mark.parametrize('greeting', [
    'AI创作工具真正的门槛不在生成，而在让创作者愿意持续用下去。我有实际体感。',
    '身心灵内容要让人信得过，靠的是真实感和持续陪伴，不是硬推。我能自己扛，可以聊十分钟。',
    '票务转化最后拼的是私域触达和社群黏性，KOL和渠道联动是现成打法。',
])
def test_style_review_catches_observed_ai_slogans(greeting):
    issues = greeter._greeting_style_issues(greeting)
    assert any('说教' in issue for issue in issues)
    assert any('套话' in issue for issue in issues)


def test_normal_greeting_and_simple_closing_do_not_trigger_forced_rewrite():
    greeting = '您好，我做过品牌内容，也独立运营过账号，负责选题和社群互动。方便聊聊吗？'
    assert greeter._greeting_style_issues(greeting, ['您好']) == []
