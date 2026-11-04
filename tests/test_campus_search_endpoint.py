"""A campus profile must search BOSS's 校园 channel, not the social-hire feed.

Verified against the live site on 2026-10-13: /web/geek/job?query=...&city=...
returns postings tagged 3-5年 / 5-10年 (社招), while
/web/geek/jobs?city=...&query=...&experience=102 returns 在校/应届 postings
including "【2027年校招】..." — the latter is what the 校园 tab searches.
"""

from bosshunter.collection.platforms.boss import (
    CAMPUS_EXPERIENCE,
    CAMPUS_SEARCH_URL,
    SEARCH_URL,
    build_boss_filter_query,
    is_campus_mode,
)


def test_campus_mode_only_for_pure_campus_profile():
    assert is_campus_mode({"profile": {"recruitment_type": "campus"}}) is True
    assert is_campus_mode({"profile": {"recruitment_type": "CAMPUS"}}) is True
    assert is_campus_mode({"profile": {"recruitment_type": " campus "}}) is True


def test_social_and_both_profiles_keep_the_wide_feed():
    # "both" means the user also wants experienced postings, so do not narrow it.
    assert is_campus_mode({"profile": {"recruitment_type": "both"}}) is False
    assert is_campus_mode({"profile": {"recruitment_type": "experienced"}}) is False
    assert is_campus_mode({"profile": {}}) is False
    assert is_campus_mode({"profile": {"recruitment_type": None}}) is False


def test_missing_or_malformed_config_is_not_campus():
    assert is_campus_mode({}) is False
    assert is_campus_mode({"profile": "nonsense"}) is False
    assert is_campus_mode({"profile": None}) is False


def test_endpoints_differ_in_path_and_experience_param():
    assert "/web/geek/jobs?" in CAMPUS_SEARCH_URL
    assert "/web/geek/job?" in SEARCH_URL
    # 单数端点不能被误用为校招端点
    assert "/web/geek/jobs?" not in SEARCH_URL


def test_campus_filter_pins_experience_to_fresh_graduates():
    filters = {
        "job_type": ["全职"],
        "experience": ["经验不限", "1-3年", "3-5年"],
        "degree": ["本科"],
    }
    effective = {**filters, "experience": [CAMPUS_EXPERIENCE]}

    query = build_boss_filter_query(effective)

    assert "experience=102" in query, "应届生 必须编码为 102"
    # 社招经验档位必须被彻底移除，否则会把社招岗位重新放回来
    for social_value in ("101", "104", "105"):
        assert f"experience={social_value}" not in query


def test_campus_mode_must_drop_job_type():
    """jobType=1901 与 experience=102 同时发送时 BOSS 返回空结果集。

    2026-10-13 实测（广州 / C++ / /web/geek/jobs）：
      jobType=1901 单独        -> 15 张卡片
      experience=102 单独      -> 15 张卡片
      degree=203 单独          -> 15 张卡片
      jobType=1901 + 102       -> 0 张卡片
    校招/应届岗位不属于「全职」这个 jobType，校园频道自身也不带 jobType。
    """
    from bosshunter.collection.platforms.boss import BossCollector

    campus_filters = BossCollector.campus_filters(
        {"job_type": ["全职"], "experience": ["1-3年"], "degree": ["本科"]}
    )

    assert "job_type" not in campus_filters, "校招模式必须剔除 job_type"
    assert campus_filters["experience"] == [CAMPUS_EXPERIENCE]
    assert campus_filters["degree"] == ["本科"], "其它筛选应原样保留"

    query = build_boss_filter_query(campus_filters)
    assert "jobType=" not in query, "请求串里不能出现 jobType"
    assert "experience=102" in query


def test_campus_filters_tolerate_missing_or_odd_filters():
    from bosshunter.collection.platforms.boss import BossCollector

    assert BossCollector.campus_filters(None) == {"experience": [CAMPUS_EXPERIENCE]}
    assert BossCollector.campus_filters({}) == {"experience": [CAMPUS_EXPERIENCE]}
    assert BossCollector.campus_filters("nonsense") == {"experience": [CAMPUS_EXPERIENCE]}


def test_campus_url_carries_city_and_keyword():
    url = CAMPUS_SEARCH_URL.format(city_code="101280100", keyword="C%2B%2B")
    assert url.startswith("https://www.zhipin.com/web/geek/jobs?")
    assert "city=101280100" in url
    assert "query=C%2B%2B" in url
