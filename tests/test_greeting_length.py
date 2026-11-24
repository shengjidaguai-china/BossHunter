"""Greeting length rule: 50-90 字, enforced by prompt and optional retry."""

from unittest.mock import patch

from bosshunter.ai import greeter

JOB = {"title": "内容运营实习生", "company": "示例公司", "salary": "150-200元/天"}

GOOD = (
    "您好，我想应聘贵司内容运营实习生。我做过公众号内容运营，负责选题和社群维护，"
    "三个月把账号从0做到1.2万粉丝，也做过数据复盘。"
)
SHORT = "您好，我想应聘这个岗位。"
LONG = "我负责内容和社群运营，做过选题、社群维护和数据复盘。" * 4


def test_size_constants_are_50_to_90():
    assert greeter.GREETING_MIN_CHARS == 50
    assert greeter.GREETING_MAX_CHARS == 90


def test_prompt_states_the_hard_range():
    prompt = greeter.GREETING_PROMPT
    assert "{min_chars}-{max_chars} 字" in prompt
    assert "不得少于 {min_chars} 字" in prompt
    assert "不得超过 {max_chars} 字" in prompt
    assert "必须说清“我做过什么”" in prompt
    assert "必须回应 JD 的硬性要求" in prompt


def test_style_issues_flag_both_bounds():
    assert any("少于50字" in issue for issue in greeter._greeting_style_issues(SHORT))
    assert any("超过90字" in issue for issue in greeter._greeting_style_issues(LONG))
    length_issues = [issue for issue in greeter._greeting_style_issues(GOOD) if "字" in issue]
    assert length_issues == []


def test_short_draft_is_regenerated_when_enforcement_is_on():
    config = {"ai": {"greeting_enforce_length": True, "greeting_max_attempts": 2}}
    with patch.object(greeter, "_call_claude", side_effect=[SHORT, GOOD]) as call:
        result = greeter._generate_with_token_retry(JOB, "真实简历", config)
    assert result == GOOD
    assert call.call_count == 2
    assert "少于 50 字" in call.call_args_list[1].args[0]


def test_long_draft_is_regenerated_when_enforcement_is_on():
    config = {"ai": {"greeting_enforce_length": True, "greeting_max_attempts": 2}}
    with patch.object(greeter, "_call_claude", side_effect=[LONG, GOOD]) as call:
        result = greeter._generate_with_token_retry(JOB, "真实简历", config)
    assert result == GOOD
    assert call.call_count == 2
    assert "超出 90 字上限" in call.call_args_list[1].args[0]


def test_enforcement_off_keeps_the_first_draft():
    with patch.object(greeter, "_call_claude", side_effect=[SHORT]) as call:
        result = greeter._generate_with_token_retry(JOB, "真实简历", {"ai": {}})
    assert result == SHORT
    assert call.call_count == 1


def test_fallback_keeps_last_draft_when_both_attempts_miss():
    config = {"ai": {"greeting_enforce_length": True, "greeting_max_attempts": 2}}
    with patch.object(greeter, "_call_claude", side_effect=[SHORT, SHORT]):
        assert greeter._generate_with_token_retry(JOB, "真实简历", config) == SHORT
