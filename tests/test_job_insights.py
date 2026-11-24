"""Filter analytics: role buckets, reason buckets and aggregation."""

import pytest

from bosshunter.job_insights import (
    REASON_HISTORY,
    REASON_MANUAL,
    REASON_PRE_FILTER,
    REASON_SCORE,
    UNKNOWN_CATEGORY,
    build_filter_stats,
    classify_filter_reason,
    classify_job_title,
)


@pytest.mark.parametrize("title,expected", [
    ("AI Agent 算法实习生", "算法 / AI 研究"),
    ("大模型算法工程师", "算法 / AI 研究"),
    ("人工智能实习生", "算法 / AI 研究"),
    ("AI 智能体研发实习生", "研发 / 开发"),
    ("后端开发实习生", "研发 / 开发"),
    ("测试开发实习生", "测试 / 运维 / 安全"),
    ("数据采集工程师", "数据"),
    ("视频剪辑实习生（AI视频生成/AIGC方向）", "内容制作 / 影视"),
    ("AI短剧编剧实习生", "内容制作 / 影视"),
    ("FDE 机器人部署实习生", "交付 / 实施 / IT"),
    ("用户增长产品经理", "产品"),
    ("新媒体运营实习生", "运营 / 内容"),
    ("大客户销售代表", "销售 / 市场 / 商务"),
    ("UI 设计师", "设计"),
    ("人事助理", "职能 / 其他"),
    ("神秘岗位", UNKNOWN_CATEGORY),
    ("", UNKNOWN_CATEGORY),
    (None, UNKNOWN_CATEGORY),
])
def test_title_categories(title, expected):
    assert classify_job_title(title) == expected


@pytest.mark.parametrize("job,expected", [
    ({"filter_reason": "预筛不通过：命中否决词「算法」"}, REASON_PRE_FILTER),
    ({"filter_reason": "AI 评分 41 分，低于阈值 70"}, REASON_SCORE),
    ({"filter_reason": "薪资远低于期望"}, REASON_MANUAL),
    ({"filter_reason": "", "score_reason": "预筛不通过: 薪资不匹配"}, REASON_PRE_FILTER),
    ({"filter_reason": "", "score_reason": "【否决词：算法】职责30/40"}, REASON_PRE_FILTER),
    ({"filter_reason": "", "score_reason": "职责20/40 · 证据10/25", "score": 41}, REASON_SCORE),
    ({"filter_reason": "", "score_reason": ""}, REASON_HISTORY),
])
def test_reason_categories(job, expected):
    assert classify_filter_reason(job) == expected


def _job(job_id, title, score, reason="", filter_reason=""):
    return {
        "id": job_id, "title": title, "company": "测试公司", "city": "广州",
        "salary": "200-300元/天", "score": score, "score_reason": reason,
        "filter_reason": filter_reason, "url": "", "created_at": "2026-11-23 10:00:00",
    }


def test_build_filter_stats_groups_and_sorts_by_count():
    jobs = [
        _job("1", "算法实习生", 30, filter_reason="AI 评分 30 分，低于阈值 70"),
        _job("2", "算法研究员", 55, filter_reason="AI 评分 55 分，低于阈值 70"),
        _job("3", "后端开发实习生", 0, filter_reason="预筛不通过：命中否决词「研发」"),
        _job("4", "新媒体运营", 12, filter_reason="AI 评分 12 分，低于阈值 70"),
    ]
    stats = build_filter_stats(jobs)
    assert stats["total"] == 4
    assert stats["categories"][0]["category"] == "算法 / AI 研究"
    assert stats["categories"][0]["count"] == 2
    assert stats["categories"][0]["share"] == 50.0
    assert stats["categories"][0]["avg_score"] == 42.5
    # 样本按分数从高到低
    assert [row["id"] for row in stats["categories"][0]["samples"]] == ["2", "1"]
    reasons = {item["reason"]: item["count"] for item in stats["reasons"]}
    assert reasons[REASON_SCORE] == 3
    assert reasons[REASON_PRE_FILTER] == 1
    bands = {item["band"]: item["count"] for item in stats["score_bands"]}
    assert bands["0 分（预筛）"] == 1
    assert bands["1-29 分"] == 1


def test_build_filter_stats_handles_empty_input():
    stats = build_filter_stats([])
    assert stats["total"] == 0
    assert stats["categories"] == []
    assert stats["top_companies"] == []


def test_samples_are_limited_and_companies_ranked():
    jobs = [_job(str(index), "产品经理", 40 + index, filter_reason="AI 评分低") for index in range(8)]
    stats = build_filter_stats(jobs, sample_limit=3)
    assert len(stats["categories"][0]["samples"]) == 3
    assert stats["top_companies"][0] == {"company": "测试公司", "count": 8}
