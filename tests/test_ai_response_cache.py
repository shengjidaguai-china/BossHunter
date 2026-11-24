"""Local AI response cache + prompt prefix layout (cache-hit regressions)."""

from pathlib import Path

import pytest

from bosshunter import db as db_module
from bosshunter.ai import greeter, response_cache, resume, scorer


@pytest.fixture
def cache_db(tmp_path: Path, monkeypatch):
    path = tmp_path / "cache.db"
    monkeypatch.setattr(db_module, "DB_PATH", path)
    return path


def config(**ai_overrides):
    return {"ai": {"prompt_cache": True, "prompt_cache_ttl_hours": 24, **ai_overrides}}


def key(prompt="prompt", purpose="scoring", max_tokens=8192):
    return response_cache.make_cache_key(
        base_url="https://api.example.com", model="m1", purpose=purpose,
        prompt=prompt, max_tokens=max_tokens,
    )


def test_cache_key_is_stable_and_sensitive_to_every_part():
    assert key() == key()
    assert key() != key(prompt="prompt-2")
    assert key() != key(purpose="greeting")
    assert key() != key(max_tokens=1024)
    other_model = response_cache.make_cache_key(
        base_url="https://api.example.com", model="m2", purpose="scoring", prompt="prompt", max_tokens=8192,
    )
    assert other_model != key()


def test_store_then_lookup_returns_cached_text(cache_db):
    response_cache.drain_stats()
    response_cache.store(key(), response="result-1", purpose="scoring", model="m1", config=config())
    assert response_cache.lookup(key(), config()) == "result-1"
    stats = response_cache.drain_stats()
    assert stats["stored"] == 1
    assert stats["hits"] == 1


def test_lookup_without_entry_is_a_miss(cache_db):
    assert response_cache.lookup(key("missing"), config()) is None
    assert response_cache.drain_stats()["misses"] == 1


def test_cache_is_off_by_default(cache_db):
    """未显式配置 ai.prompt_cache 时读写都不发生（测试/调试不读旧响应）。"""
    assert response_cache.lookup(key(), {"ai": {}}) is None
    response_cache.store(key(), response="x", purpose="scoring", model="m1", config={"ai": {}})
    assert response_cache.lookup(key(), {"ai": {}}) is None


def test_disabled_cache_neither_stores_nor_reads(cache_db):
    disabled = config(prompt_cache=False)
    response_cache.store(key(), response="x", purpose="scoring", model="m1", config=disabled)
    assert response_cache.lookup(key(), disabled) is None
    assert response_cache.drain_stats()["hits"] == 0


def test_expired_entry_is_a_miss(cache_db, monkeypatch):
    response_cache.store(key(), response="old", purpose="scoring", model="m1", config=config())
    real_time = response_cache.time.time
    monkeypatch.setattr(response_cache.time, "time", lambda: real_time() + 25 * 3600)
    assert response_cache.lookup(key(), config(prompt_cache_ttl_hours=1)) is None


def test_regenerate_and_skip_flags_bypass_the_cache(cache_db):
    response_cache.store(key(), response="fresh", purpose="greeting", model="m1", config=config())
    regenerate = {**config(), "_workbench_regenerate": True}
    skip = {**config(), "_skip_prompt_cache": True}
    assert response_cache.lookup(key(purpose="greeting"), regenerate) is None
    assert response_cache.lookup(key(purpose="greeting"), skip) is None


def test_record_usage_reads_provider_cache_fields():
    response_cache.drain_stats()
    response_cache.record_usage({
        "prompt_tokens": 1000,
        "completion_tokens": 20,
        "prompt_tokens_details": {"cached_tokens": 640},
        "prompt_cache_hit_tokens": 640,
    })
    stats = response_cache.drain_stats()
    assert stats["calls"] == 1
    assert stats["prompt_tokens"] == 1000
    assert stats["cached_tokens"] == 640


def test_record_usage_accepts_deepseek_style_only():
    response_cache.drain_stats()
    response_cache.record_usage({"prompt_tokens": 500, "prompt_cache_hit_tokens": 384})
    stats = response_cache.drain_stats()
    assert stats["cached_tokens"] == 384


def test_summary_line_reports_both_rates():
    line = response_cache.summary_line({
        "hits": 3, "misses": 1, "stored": 1, "calls": 4, "prompt_tokens": 1000, "cached_tokens": 900,
    })
    assert "本地复用 3/7（43%）" in line
    assert "900/1000 tokens（90%）" in line


# ─── Prompt layout: static prefix first, volatile job last ───

def _job():
    return {
        "id": "job-1", "title": "AI Agent 开发实习生", "company": "测试公司",
        "salary": "200-300元/天", "city": "广州", "experience": "3天/周",
        "education": "本科", "recruitment_type": "campus", "jd": "负责 Agent 工作流开发。",
    }


def test_scoring_prompt_keeps_the_static_prefix_first():
    library = [{"id": "primary", "label": "AI", "focus": "", "text": "简历正文", "primary": "1"}]
    prompt = scorer._build_scoring_prompt(_job(), library, {"profile": {"salary_min": 0, "salary_max": 0}})
    assert prompt.index("## 证据核对规则") < prompt.index("## 输出格式")
    assert prompt.index("## 输出格式") < prompt.index("## 候选人简历")
    assert prompt.index("## 候选人简历") < prompt.index("## 岗位信息")
    # 岗位相关的内容只能出现在尾部，否则每个岗位都会让整段前缀失效。
    assert prompt.index("## 岗位信息") < prompt.index("- JD：")
    assert prompt.index("## 程序核算的薪资匹配") > prompt.index("- JD：")


def test_greeting_prompt_puts_shared_rules_before_the_job():
    template = greeter.GREETING_PROMPT
    assert template.index("## 要求") < template.index("## 我的背景")
    assert template.index("## 我的背景") < template.index("## 目标岗位")
    # 最近开头每生成一条就变化，必须留在最后。
    assert template.index("## 目标岗位") < template.index("## 最近开头")
    assert template.index("## 最近开头") < template.index("{critique_section}")


def test_resume_prompt_puts_the_master_resume_before_the_job():
    template = resume.RESUME_TAILOR_PROMPT
    assert template.index("## 候选人简历") < template.index("## 投递岗位")
    assert template.index("## 固定母版策略") < template.index("## 候选人简历")
