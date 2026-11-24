"""Transient AI failures are retried; deterministic ones are not."""

import threading

import pytest

from bosshunter.ai.credentials import AIRequestError
from bosshunter.ai.retry import call_with_retry, is_transient, retry_settings


def config(**ai_overrides):
    return {"ai": {"retry_attempts": 3, "retry_backoff_seconds": 0, **ai_overrides}}


def test_transient_network_error_is_retried_then_succeeds():
    calls = []

    def call():
        calls.append(1)
        if len(calls) < 3:
            raise AIRequestError("network", "AI 服务连接失败或超时")
        return "ok"

    assert call_with_retry(call, config=config()) == "ok"
    assert len(calls) == 3


def test_rate_limit_and_server_errors_are_transient():
    assert is_transient(AIRequestError("network", "x"))
    assert is_transient(AIRequestError("rate_limit", "x", 429))
    assert is_transient(AIRequestError("request_failed", "x", 503))
    assert is_transient(AIRequestError("request_failed", "x"))


@pytest.mark.parametrize("error", [
    AIRequestError("auth", "AI API Key 无效或当前模型没有访问权限", 401),
    AIRequestError("token_quota", "AI Token 额度或账户余额不足", 402),
    AIRequestError("context_limit", "请求内容超过当前模型的上下文限制", 400),
    AIRequestError("output_limit", "当前模型不接受设置的输出 Token 上限", 400),
    AIRequestError("request_failed", "AI 服务请求失败", 400),
    AIRequestError("invalid_url", "AI 接口地址无效"),
])
def test_deterministic_errors_are_not_retried(error):
    calls = []

    def call():
        calls.append(1)
        raise error

    with pytest.raises(AIRequestError) as caught:
        call_with_retry(call, config=config())
    assert caught.value.kind == error.kind
    assert len(calls) == 1


def test_retries_stop_at_configured_attempts():
    calls = []

    def call():
        calls.append(1)
        raise AIRequestError("network", "AI 服务连接失败或超时")

    with pytest.raises(AIRequestError):
        call_with_retry(call, config=config(retry_attempts=2))
    assert len(calls) == 2


def test_attempts_of_one_disables_retry():
    calls = []

    def call():
        calls.append(1)
        raise AIRequestError("network", "AI 服务连接失败或超时")

    with pytest.raises(AIRequestError):
        call_with_retry(call, config=config(retry_attempts=1))
    assert len(calls) == 1


def test_stopped_task_does_not_wait_out_the_backoff():
    stop_event = threading.Event()
    stop_event.set()
    calls = []

    def call():
        calls.append(1)
        raise AIRequestError("network", "AI 服务连接失败或超时")

    cfg = config()
    cfg["ai"]["retry_backoff_seconds"] = 30
    cfg["_workbench_stop_event"] = stop_event
    with pytest.raises(AIRequestError):
        call_with_retry(call, config=cfg)
    assert len(calls) == 1


def test_workbench_log_receives_retry_notice():
    messages = []
    calls = []

    def call():
        calls.append(1)
        if len(calls) == 1:
            raise AIRequestError("network", "AI 服务连接失败或超时")
        return "ok"

    assert call_with_retry(call, config={**config(), "_workbench_log": messages.append}) == "ok"
    assert messages and "重试" in messages[0]


def test_bounds_are_clamped():
    assert retry_settings({"ai": {"retry_attempts": 99, "retry_backoff_seconds": 999}}) == (6, 60.0)
    assert retry_settings({"ai": {"retry_attempts": 0, "retry_backoff_seconds": -5}}) == (1, 0.0)
    assert retry_settings(None) == (3, 5.0)
