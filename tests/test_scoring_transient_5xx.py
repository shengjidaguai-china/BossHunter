"""A single flaky upstream hop must not abort a whole scoring batch.

Gateways answer with statuses that never reach the dedicated classifiers in
``credentials.py`` (Cloudflare's 520/524, a proxy's 502/503). Those arrive as the
generic ``request_failed`` kind, which used to return a ``pause_reason`` and stop
the entire run after one bad request.
"""

import json
from unittest.mock import patch

import pytest

from bosshunter.ai import scorer
from bosshunter.ai.credentials import AIRequestError


JOB = {
    "id": "transient-job",
    "title": "C++开发工程师",
    "company": "示例科技",
    "salary": "15-25K",
    "city": "深圳",
    "experience": "1-3年",
    "jd": "负责 C++/Linux 后台服务开发与性能优化。",
}

RESUME = "成都理工大学软件工程，C++/Linux 后台与并发通信经验。"


def _valid_response(score=82):
    return json.dumps({
        **{key: {"score": value, "evidence": "有相关实践"} for key, value in zip(
            scorer.COMPONENT_LIMITS, (30, 19, 10, 7, 8)
        )},
        "reason": "职责匹配",
        "caps": [],
        "hard_gaps": [],
    }, ensure_ascii=False)


CONFIG = {"profile": {"target_cities": ["深圳"], "salary_min": 12, "salary_max": 25}, "ai": {}}


def test_transient_server_error_detection():
    for status in (500, 502, 503, 520, 524):
        exc = AIRequestError("request_failed", "AI 服务请求失败", status)
        assert scorer._is_transient_server_error(exc) is True, f"HTTP {status} 应判为瞬时错误"
        assert scorer._is_transient_error(exc) is True

    # 其它 kind 的 5xx（如限流）保持原有语义，不被误判为可重试的瞬时故障
    assert scorer._is_transient_server_error(AIRequestError("rate_limit", "限流", 529)) is False
    assert scorer._is_transient_server_error(AIRequestError("auth", "鉴权失败", 500)) is False
    # request_failed 的 4xx 是真实请求错误，不应重试
    assert scorer._is_transient_server_error(AIRequestError("request_failed", "失败", 400)) is False
    assert scorer._is_transient_server_error(AIRequestError("request_failed", "失败", None)) is False


def test_network_failures_count_as_transient_but_others_do_not():
    """连接级失败可重试；鉴权/额度/限流保持"服务级故障"语义。"""
    assert scorer._is_transient_error(AIRequestError("network", "连接失败或超时", None)) is True
    for kind in ("auth", "token_quota", "rate_limit", "context_limit", "output_limit", "empty_response"):
        assert scorer._is_transient_error(AIRequestError(kind, "错误", None)) is False, kind


def test_transient_520_is_retried_and_eventually_scores():
    calls = {"n": 0}

    def flaky(prompt, config, max_tokens=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise AIRequestError("request_failed", "AI 服务请求失败", 520)
        return _valid_response()

    with patch.object(scorer, "_call_claude", side_effect=flaky), patch.object(
        scorer.time, "sleep"
    ) as sleep_mock:
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

    assert outcome.pause_reason == "", "瞬时 5xx 不应中断整批评分"
    assert outcome.failure_detail == ""
    assert outcome.result is not None
    assert outcome.result.score == 74  # 30+19+10+7+8
    assert calls["n"] == 2
    # 退避必须真实发生，否则等于对故障服务猛打
    assert sleep_mock.call_count >= 1, "瞬时错误重试前应退避等待"


def test_persistent_520_falls_back_to_a_single_job_failure():
    def always_520(prompt, config, max_tokens=None, **kwargs):
        raise AIRequestError("request_failed", "AI 服务请求失败", 520)

    with patch.object(scorer, "_call_claude", side_effect=always_520), patch.object(scorer.time, "sleep"):
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

    assert outcome.pause_reason == "", "持续瞬时错误也只应记岗位级失败，不暂停整批"
    assert outcome.result is None
    assert "520" in outcome.failure_detail
    assert f"已重试 {scorer._TRANSIENT_RETRIES} 次" in outcome.failure_detail


def test_transient_network_failure_is_retried_and_batch_survives():
    """实测模式：约 5 秒快速失败的连接错误，重试后成功，整批不停。"""
    calls = {"n": 0}

    def flaky(prompt, config, max_tokens=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise AIRequestError("network", "AI 服务连接失败或超时", None)
        return _valid_response()

    with patch.object(scorer, "_call_claude", side_effect=flaky), patch.object(scorer.time, "sleep") as slp:
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

    assert outcome.pause_reason == "", "单次连接故障不应中断整批评分"
    assert outcome.failure_detail == ""
    assert outcome.result is not None and outcome.result.score == 74
    assert calls["n"] == 2
    assert slp.call_count >= 1, "重试前必须退避"


def test_persistent_network_failure_still_pauses_the_batch():
    """持续连接失败 = 服务可能下线，中断整批（不无限猛打）。"""
    with patch.object(
        scorer, "_call_claude", side_effect=AIRequestError("network", "连接失败", None)
    ), patch.object(scorer.time, "sleep"):
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

    assert outcome.pause_reason != ""
    assert f"重试 {scorer._TRANSIENT_RETRIES} 次后仍失败" in outcome.pause_reason
    assert outcome.result is None


def test_non_transient_error_during_retry_still_pauses():
    """重试中途冒出鉴权失败：立即中断整批，带着原始错误。"""
    calls = {"n": 0}

    def flaky(prompt, config, max_tokens=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise AIRequestError("network", "连接失败", None)
        raise AIRequestError("auth", "AI API Key 无效", 401)

    with patch.object(scorer, "_call_claude", side_effect=flaky), patch.object(scorer.time, "sleep"):
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

    assert "auth" in outcome.pause_reason


def test_transient_then_real_service_error_still_pauses():
    """第一次 520、第二次鉴权失败：应以服务级故障中断整批。"""
    calls = {"n": 0}

    def flaky(prompt, config, max_tokens=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise AIRequestError("request_failed", "AI 服务请求失败", 520)
        raise AIRequestError("auth", "AI API Key 无效或当前模型没有访问权限", 401)

    with patch.object(scorer, "_call_claude", side_effect=flaky), patch.object(scorer.time, "sleep"):
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

    assert outcome.pause_reason != ""
    assert "auth" in outcome.pause_reason


def test_auth_and_rate_limit_still_pause_the_batch():
    """非瞬时故障必须立即中断整批（防重复消耗与风控），不做任何重试。"""
    for kind, status in (("auth", 401), ("token_quota", 402), ("rate_limit", 429), ("request_failed", 404)):
        with patch.object(
            scorer, "_call_claude",
            side_effect=AIRequestError(kind, "服务级故障", status),
        ) as call_ai:
            outcome = scorer._request_score(JOB, RESUME, CONFIG, 2)

        assert outcome.pause_reason != "", f"{kind} 必须继续中断整批（防重复消耗与风控）"
        assert call_ai.call_count == 1, f"{kind} 不应触发重试"


def test_validation_retry_does_not_pause_on_transient_5xx():
    """重试循环里遇到瞬时 5xx：退回空结果，最终只记岗位级失败。"""
    calls = {"n": 0}

    def flaky(prompt, config, max_tokens=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _valid_response()
        raise AIRequestError("request_failed", "AI 服务请求失败", 502)

    with patch.object(scorer, "_call_claude", side_effect=flaky), patch.object(scorer.time, "sleep"):
        outcome = scorer._request_score(JOB, RESUME, CONFIG, 3)

    # 首次已拿到有效评分，后续抖动被容纳，结果保留
    assert outcome.pause_reason == ""
    assert outcome.result is not None


def test_one_flaky_job_does_not_stop_the_rest_of_the_batch(tmp_path):
    """端到端：持续 520 时整轮继续跑完，且失败岗位保持待处理状态。"""
    from bosshunter.db import get_db, insert_job

    db_path = tmp_path / "jobs.db"
    db = get_db(db_path)
    ids = ["transient-job"] + [f"transient-job-{index}" for index in range(2, 6)]
    for position, job_id in enumerate(ids):
        insert_job(db, {**JOB, "id": job_id, "title": f"岗位{position + 1}", "status": "pending"})
    db.close()

    def flaky(prompt, config, max_tokens=None, **kwargs):
        # 第一个岗位永远 520（重试也失败），其余岗位正常返回
        if "岗位1" in prompt and "示例科技" in prompt:
            raise AIRequestError("request_failed", "AI 服务请求失败", 520)
        return _valid_response(80)

    with patch.object(scorer, "_call_claude", side_effect=flaky), patch.object(
        scorer.time, "sleep"
    ), patch.object(scorer, "_load_resume", return_value=RESUME), patch.object(
        scorer, "get_db", side_effect=lambda: get_db(db_path)
    ):
        scored, filtered = scorer.score_jobs(CONFIG)

    # 4 个健康岗位照常完成，未被第一个故障岗位拖停
    assert scored >= 4, f"其余岗位应继续完成评分，实际 scored={scored} filtered={filtered}"

    db = get_db(db_path)
    remaining = db.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'").fetchone()[0]
    db.close()
    assert remaining == 1, "持续失败的那个岗位应保持待处理，等待下次重跑"

