"""A nationwide search must file each job under its real workplace city.

BOSS's list endpoint accepts city=100010000 ("全国") and then returns rows from
every city. The collector used to stamp every one of them with the *search*
city, so a nationwide run stored all jobs as city="全国" -- which silently broke
the configured priority-city send order (nothing could match 广州/深圳/佛山/上海
any more, leaving a plain score sort).

The list rows already carry the real workplace ("广州·黄埔区·大沙"), so the
collector now reads it. Real city searches keep their old behaviour.
"""

from bosshunter.collection.platforms.boss import (
    BossCollector,
    location_city,
    resolve_list_city,
)

NATIONWIDE_CODE = "100010000"


def test_location_city_takes_the_segment_before_the_first_separator():
    assert location_city("广州·黄埔区·大沙") == "广州"
    assert location_city("深圳·南山区") == "深圳"
    assert location_city("上海") == "上海"
    assert location_city(" 北京 ") == "北京"


def test_location_city_handles_missing_values():
    assert location_city("") == ""
    assert location_city(None) == ""
    assert location_city("   ") == ""


def test_nationwide_search_stores_the_rows_own_city_and_its_code():
    city, code = resolve_list_city("全国", "广州·黄埔区·大沙", NATIONWIDE_CODE)

    assert city == "广州"
    assert code == "101280100", "应回填该城市真实的 BOSS 编码，便于后续按城市查询"


def test_nationwide_search_covers_priority_cities():
    for location, expected in [
        ("广州·天河区", "广州"),
        ("深圳·南山区", "深圳"),
        ("佛山·禅城区", "佛山"),
        ("上海·徐汇区", "上海"),
    ]:
        city, _ = resolve_list_city("全国", location, NATIONWIDE_CODE)
        assert city == expected


def test_real_city_search_is_unchanged():
    """Searching 广州 keeps 广州 even if a stray row is located elsewhere."""
    city, code = resolve_list_city("广州", "深圳·南山区", "101280100")

    assert city == "广州"
    assert code == "101280100"


def test_nationwide_row_without_location_falls_back_to_the_search_city():
    city, code = resolve_list_city("全国", "", NATIONWIDE_CODE)

    assert city == "全国"
    assert code == NATIONWIDE_CODE


def test_unknown_city_keeps_the_search_city_code():
    city, code = resolve_list_city("全国", "某某市·中心区", NATIONWIDE_CODE)

    assert city == "某某市"
    assert code == NATIONWIDE_CODE, "城市表里没有的市名不能瞎编编码"


def test_list_candidate_uses_the_row_location_for_nationwide_searches():
    raw = {
        "title": "C++开发工程师",
        "company": "示例科技",
        "salary": "15-25K",
        "experience": "在校/应届",
        "education": "本科",
        "location": "深圳·南山区·科技园",
        "url": "/job_detail/abc123.html",
    }

    candidate = BossCollector._list_candidate(raw, "全国", NATIONWIDE_CODE, "C++")

    assert candidate is not None
    assert candidate.city == "深圳"
    assert candidate.city_code == "101280600"


def test_list_candidate_keeps_behaviour_for_a_real_city_search():
    raw = {
        "title": "C++开发工程师",
        "company": "示例科技",
        "location": "佛山·禅城区",
        "url": "/job_detail/def456.html",
    }

    candidate = BossCollector._list_candidate(raw, "广州", "101280100", "C++")

    assert candidate is not None
    assert candidate.city == "广州"
    assert candidate.city_code == "101280100"
