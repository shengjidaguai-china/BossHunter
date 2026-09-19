from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from bosshunter.ai import greeter
from bosshunter.ai.greeter import _generate_greeting_once


def test_greeting_preference_is_bounded_and_cannot_replace_fixed_rules():
    captured = {}

    def fake_call(prompt, config, max_tokens=None, **kwargs):
        captured["prompt"] = prompt
        return "自然简短的招呼语"

    with patch("bosshunter.ai.greeter._call_claude", side_effect=fake_call):
        result = _generate_greeting_once(
            {
                "title": "产品经理",
                "company": "示例公司",
                "salary": "20-30K",
                "education": "本科",
                "recruitment_type": "experienced",
                "jd": "负责产品规划。",
                "score_reason": "经验匹配",
                "source_platform": "boss",
            },
            "真实简历摘要",
            {"profile": {"greeting_preference": "语气简洁，不主动询问薪资"}},
        )

    assert result == "自然简短的招呼语"
    assert "语气简洁，不主动询问薪资" in captured["prompt"]
    assert "不得捏造我没有的经历" in captured["prompt"]
    assert "不得覆盖下方事实与安全要求" in captured["prompt"]


def test_positive_match_reason_removes_missing_suffix():
    reason = "后端技能扎实，项目经验匹配。 | 缺失: 缺乏大型分布式系统架构经验"

    cleaned = greeter._positive_match_reason(reason)

    assert cleaned == "后端技能扎实，项目经验匹配。"


def test_greeting_prompt_uses_positive_match_reason_only():
    captured = {}

    def fake_call(prompt, config, max_tokens=None, **kwargs):
        captured["prompt"] = prompt
        return "我有后端项目经验，和岗位方向比较匹配，可以进一步沟通。"

    with patch("bosshunter.ai.greeter._call_claude", side_effect=fake_call):
        result = _generate_greeting_once(
            {
                "title": "后端开发",
                "company": "示例公司",
                "salary": "10-15K",
                "education": "本科",
                "recruitment_type": "experienced",
                "jd": "负责后端服务开发。",
                "score_reason": "后端技能扎实，项目经验匹配。 | 缺失: 缺乏大型分布式系统架构经验",
                "source_platform": "boss",
            },
            "真实简历摘要",
            {"profile": {}},
        )

    assert result
    match_line = next(line for line in captured["prompt"].splitlines() if line.startswith("- 匹配分析："))
    assert "后端技能扎实" in match_line
    assert "缺失" not in match_line
    assert "不得提及我的缺点" in captured["prompt"]


def test_greeting_style_guard_flags_self_weakness():
    issues = greeter._greeting_style_issues("我有后端项目经验，但还在学习分布式架构，可以先从基础工作做起。")

    assert any("不要暴露缺点" in issue for issue in issues)


def test_graduation_context_uses_education_end_year_as_class_year():
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 3)

    resume = "教育经历\n某大学 软件工程 本科 2022.09-2026.06\n项目经历\n后台系统"

    with patch("bosshunter.ai.greeter.date", FixedDate):
        context = greeter._parse_graduation_context(resume)

    assert "2026 届" in context
    assert "已毕业" in context
    assert "不得改写为其他届别" in context


def test_review_receives_user_preferences():
    with patch.object(greeter, '_call_claude', return_value='{"avg": 9, "critique": ""}') as call:
        greeter._review_greeting('您好，我做过内容运营。', {'title': '运营', 'company': '示例'}, {'profile': {'greeting_preference': '简洁，不要问问题'}})
    assert '简洁，不要问问题' in call.call_args.args[0]
    assert '不得建议补问句' in call.call_args.args[0]


@pytest.mark.parametrize('greeting', [
    '你们的内容获客可以先围绕一个细分场景试选题。我做过公众号和社群运营，想聊聊这个岗位。',
    '您好，我做过公众号和社群运营，想应聘这个岗位。',
])
def test_business_suggestion_is_optional_and_does_not_trigger_regeneration(greeting):
    config = {'profile': {'greeting_preference': '自然简短，有依据时带业务建议'}}
    with (
        patch.object(greeter, 'get_db', return_value=MagicMock()),
        patch.object(greeter, 'get_jobs_by_status', return_value=[{
            'id': 'one', 'title': '运营', 'company': '示例', 'salary': '',
            'jd': '负责内容获客', 'status': 'approved',
        }]),
        patch.object(greeter, '_get_resume_summary', return_value='做过公众号和社群运营'),
        patch.object(greeter, '_call_claude', return_value=greeting) as call,
        patch.object(greeter, 'save_generated_greeting_preview', return_value=True) as save,
    ):
        assert greeter.generate_greetings(config) == 1
    call.assert_called_once()
    assert '不硬编建议' in call.call_args.args[0]
    assert save.call_args.kwargs['selected_greeting'] == greeting
    assert config['_workbench_greeting_report']['failed_count'] == 0


def test_no_question_preference_stays_in_prompt_without_rejecting_draft():
    config = {'profile': {'greeting_preference': '简洁，不要问问题'}, 'ai': {'greeting_style_suggestions': False}}
    job = {'title': '运营', 'company': '示例', 'salary': '16-25K'}
    with patch.object(greeter, '_call_claude', return_value='您好，方便聊聊吗？') as call:
        result = greeter._generate_with_token_retry(job, '真实简历', config)
    assert result == '您好，方便聊聊吗？'
    assert call.call_count == 1
    assert '【本次必须不提问】' in call.call_args.args[0]


def test_topic_specific_question_preference_does_not_ban_all_questions_in_prompt():
    config = {'profile': {'greeting_preference': '不主动询问薪资'}}
    with patch.object(greeter, '_call_claude', return_value='您好，方便聊聊吗？') as call:
        result = greeter._generate_greeting_once(
            {'title': '运营', 'company': '示例', 'salary': ''}, '真实简历', config,
        )
    assert result == '您好，方便聊聊吗？'
    assert '【本次必须不提问】' not in call.call_args.args[0]


def test_url_rejection_feedback_does_not_leak_to_next_job():
    config = {'profile': {'greeting_preference': '不提问'}}
    job = {'title': '运营', 'company': '示例', 'salary': ''}
    with patch.object(greeter, '_call_claude', side_effect=[
        '作品：https://invented.example/work', '您好，我做过内容运营。', '您好，我做过内容运营。',
    ]) as call:
        greeter._generate_with_token_retry(job, '真实简历', config, critique='只讲内容运营经历')
        greeter._generate_with_token_retry({**job, 'company': '另一家'}, '真实简历', config)
    retry_prompt = call.call_args_list[1].args[0]
    assert '只讲内容运营经历' in retry_prompt
    assert '上一稿包含来源未提供的网址' in retry_prompt
    assert '上一稿包含' not in call.call_args_list[2].args[0]


def test_no_question_mismatch_is_saved_as_advice_not_failure():
    config = {'profile': {'greeting_preference': '不提问'}}
    greeting = '您好，方便聊聊吗？'
    with (
        patch.object(greeter, 'get_db', return_value=MagicMock()),
        patch.object(greeter, 'get_jobs_by_status', return_value=[{'id': 'one', 'title': '运营', 'company': '示例', 'salary': '', 'status': 'approved'}]),
        patch.object(greeter, '_get_resume_summary', return_value='真实简历'),
        patch.object(greeter, '_call_claude', return_value=greeting) as call,
        patch.object(greeter, 'save_generated_greeting_preview', return_value=True) as save,
    ):
        assert greeter.generate_greetings(config) == 1
    call.assert_called_once()
    assert save.call_args.kwargs['selected_greeting'] == greeting
    assert any('不提问' in issue for issue in save.call_args.kwargs['style_issues'])
    assert config['_workbench_greeting_report']['failed_count'] == 0


@pytest.mark.parametrize('preference', ['', '语气自然', '不主动询问薪资', '结尾问一个与岗位相关的问题'])
def test_general_generation_and_review_do_not_impose_no_question_preference(preference):
    config = {'profile': {'greeting_preference': preference}}
    job = {'title': '运营', 'company': '示例', 'salary': ''}
    greeting = '您好，我做过内容运营，请问岗位主要面向哪些渠道？'
    with patch.object(greeter, '_call_claude', return_value=greeting) as call:
        assert greeter._generate_with_token_retry(job, '真实简历', config) == greeting
    assert call.call_count == 1
    prompt = call.call_args.args[0]
    assert '不强制使用或禁止问句' in prompt
    assert '【本次必须不提问】' not in prompt
    assert '只有用户明确要求提问时' not in prompt
    assert not greeter._greeting_style_issues(greeting)
    with patch.object(greeter, '_call_claude', return_value='{"avg": 9, "critique": ""}') as review_call:
        greeter._review_greeting(greeting, job, config)
    review_prompt = review_call.call_args.args[0]
    assert '不得仅因包含问句或没有问句扣分' in review_prompt
    assert '不得建议补问句' not in review_prompt
