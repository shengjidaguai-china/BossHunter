import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

from bosshunter.ai.prefilter import freshness_filter_result, hr_active_level, quick_score, update_label_days
from bosshunter.collection.models import JobCandidate, PlatformCollectionResult
from bosshunter.collection.orchestrator import CollectionOrchestrator
from bosshunter.collection.registry import CollectorRegistry


@pytest.mark.parametrize(
    "label,expected",
    [
        ("在线", 3),
        ("刚刚活跃", 3),
        ("今日活跃", 3),
        ("3日内活跃", 2),
        ("2天内活跃", 2),
        ("三日内活跃", 2),
        ("本周活跃", 1),
        ("本月活跃", 1),
        ("2周前活跃", 1),
        ("半年前活跃", 0),
        ("3月前活跃", 0),
        ("", None),
        ("未知文案", None),
    ],
)
def test_hr_active_level(label, expected):
    assert hr_active_level(label) == expected


@pytest.mark.parametrize("label,expected", [("今天更新", 0.0), ("昨天更新", 1.0), ("90天前更新", 90.0), ("2周前更新", 14.0), ("无", None)])
def test_update_label_days(label, expected):
    assert update_label_days(label) == expected


def test_filters_are_off_by_default():
    assert freshness_filter_result({"hr_active": "半年前活跃", "updated_days": 400}, {})[0] == 100


def test_update_age_filter():
    profile = {"max_job_update_days": 30}
    assert freshness_filter_result({"updated_days": 45}, profile)[0] == 0
    assert freshness_filter_result({"updated_days": 5}, profile)[0] == 100
    assert freshness_filter_result({"updated_days": None}, profile)[0] == 100     # unknown passes
    assert freshness_filter_result({}, profile)[0] == 100


def test_hr_activity_filter_and_unknown_handling():
    profile = {"hr_active_min_level": 2}
    assert freshness_filter_result({"hr_active": "在线"}, profile)[0] == 100
    assert freshness_filter_result({"hr_active": "3日内活跃"}, profile)[0] == 100
    assert freshness_filter_result({"hr_active": "本月活跃"}, profile)[0] == 0
    assert freshness_filter_result({"hr_active": ""}, profile)[0] == 100
    strict = {**profile, "hr_active_unknown_pass": False}
    assert freshness_filter_result({"hr_active": ""}, strict)[0] == 0


def test_quick_score_applies_freshness_filter():
    config = {"profile": {"hr_active_min_level": 3, "filter_unparsed_salary": False}}
    stale = {"title": "Agent 工程师", "company": "某科技有限公司X", "salary": "20-30K", "hr_active": "本月活跃"}
    fresh = {**stale, "hr_active": "在线"}
    assert quick_score(stale, config)[0] == 0
    assert quick_score(fresh, config)[0] == 100


def _candidate(source_id, platform="51job", city="北京", hr_active="", updated_days=None):
    return JobCandidate(
        platform=platform, source_job_id=source_id, title=f"岗位{source_id}", company=f"公司{source_id}号", city=city,
        city_code="101010100", jd="负责岗位相关工作", url=f"https://example.test/{platform}/{source_id}",
        hr_active=hr_active, updated_days=updated_days,
    )


class _Collector:
    def __init__(self, platform, candidates):
        self.platform, self.candidates = platform, candidates

    def collect(self, request, hooks):
        for candidate in self.candidates:
            if hooks.on_list_candidate(candidate):
                hooks.on_candidate(candidate)
        return PlatformCollectionResult(self.platform, "completed", "search_exhausted", "ok")


class CollectionFilterTests(TestCase):
    def _run(self, config, candidates, platform="51job"):
        registry = CollectorRegistry({platform: lambda: _Collector(platform, candidates)})
        options = {"platform_order": [platform], "auto_score": False, "platforms": {platform: {
            "keywords": ["AI"], "cities": ["北京"], "city_codes": {"北京": "101010100"}, "max_pages": 1, "sort": "default"}}}
        with tempfile.TemporaryDirectory() as tmp:
            return CollectionOrchestrator(config, db_path=Path(tmp) / "c.db", registry=registry).run(options)["platforms"][platform]

    def test_inactive_hr_and_stale_postings_are_filtered_before_they_are_stored(self):
        config = {"profile": {"hr_active_min_level": 2, "max_job_update_days": 30}}
        state = self._run(config, [
            _candidate("1", hr_active="刚刚活跃", updated_days=2),
            _candidate("2", hr_active="3月前活跃", updated_days=2),
            _candidate("3", hr_active="刚刚活跃", updated_days=90),
            _candidate("4"),                                           # nothing known: passes
        ])
        self.assertEqual(state["new"], 2)
        self.assertEqual(state["filtered"], 2)
        reasons = " ".join(record["reason"] for record in state["filter_records"])
        self.assertIn("HR 活跃度不足", reasons)
        self.assertIn("未更新", reasons)

    def test_non_boss_posting_outside_the_searched_city_is_dropped(self):
        state = self._run({}, [_candidate("1", city="北京·海淀区"), _candidate("2", city="上海·浦东新区"), _candidate("3", city="")])
        self.assertEqual(state["new"], 2)                              # unknown location passes
        self.assertEqual(state["filtered"], 1)
        self.assertIn("不在目标城市", state["filter_records"][0]["reason"])
