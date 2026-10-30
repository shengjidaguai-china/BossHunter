import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

from bosshunter.collection.models import JobCandidate, PlatformCollectionResult
from bosshunter.collection.orchestrator import CollectionOrchestrator
from bosshunter.collection.registry import CollectorRegistry
from bosshunter.company_dedup import approved_within, company_key, cooldown_days, same_company
from bosshunter.db import add_history, get_db, insert_job_if_new


@pytest.mark.parametrize("a,b", [
    ("华为", "华为技术有限公司"),
    ("上海华为技术有限公司", "华为"),
    ("华为云计算", "华为"),
    ("万宝盛华", "上海万宝盛华信息科技"),
])
def test_company_variants_are_the_same(a, b):
    assert same_company(a, b)


@pytest.mark.parametrize("a,b", [
    ("华为", "美团"),
    ("字节跳动", "跳动网络"),
    ("", "华为"),
    ("某", "某某科技有限公司"),
    ("中国银行", "招商银行"),
    ("上海银行", "招商银行"),
])
def test_different_companies_are_not_merged(a, b):
    assert not same_company(a, b)


def test_company_key_strips_region_and_legal_suffix():
    assert company_key("上海华为技术有限公司") == "华为技术"
    assert company_key("中国") == "中国"
    assert company_key("中国银行") == "中国银行"


def test_cooldown_days_is_clamped():
    assert cooldown_days(None) == 1
    assert cooldown_days({"automation": {"company_cooldown_days": 7}}) == 7
    assert cooldown_days({"automation": {"company_cooldown_days": 999}}) == 60
    assert cooldown_days({"automation": {"company_cooldown_days": "x"}}) == 1


def test_approved_within_lists_recently_sent_companies(tmp_path):
    conn = get_db(tmp_path / "t.db")
    insert_job_if_new(conn, {"id": "a", "title": "t", "company": "华为技术有限公司", "jd": "x" * 100})
    add_history(conn, "a", "sent")
    assert [item["company"] for item in approved_within(conn, 1)] == ["华为技术有限公司"]
    conn.close()


def _candidate(source_id: str, company: str, platform: str = "51job") -> JobCandidate:
    return JobCandidate(
        platform=platform, source_job_id=source_id, title=f"岗位{source_id}", company=company, city="北京",
        city_code="101010100", jd="负责岗位相关工作", url=f"https://example.test/{platform}/{source_id}",
    )


class _Collector:
    def __init__(self, platform, candidates):
        self.platform, self.candidates = platform, candidates

    def collect(self, request, hooks):
        for candidate in self.candidates:
            if hooks.on_list_candidate(candidate):
                hooks.on_candidate(candidate)
        return PlatformCollectionResult(self.platform, "completed", "search_exhausted", "ok")


DEDUP_ON = {"automation": {"collect_company_dedup": True}}


def _run(config, db_path, candidates):
    registry = CollectorRegistry({"51job": lambda: _Collector("51job", candidates)})
    options = {"platform_order": ["51job"], "auto_score": False, "platforms": {"51job": {
        "keywords": ["AI"], "cities": ["北京"], "city_codes": {"北京": "101010100"}, "max_pages": 1, "sort": "default"}}}
    return CollectionOrchestrator(config, db_path=db_path, registry=registry).run(options)


class CollectionCompanyDedupTests(TestCase):
    def test_company_already_applied_to_or_in_the_pool_is_not_collected_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "c.db"
            conn = get_db(db_path)
            insert_job_if_new(conn, {"id": "boss1", "title": "t", "company": "华为技术有限公司", "jd": "x" * 100})
            add_history(conn, "boss1", "sent")                      # applied to on another platform
            insert_job_if_new(conn, {"id": "p1", "title": "t", "company": "美团", "jd": "x" * 100})   # waiting in the pool
            conn.close()
            result = _run(DEDUP_ON, db_path, [
                _candidate("1", "上海华为"), _candidate("2", "美团科技有限公司"),
                _candidate("3", "新公司"), _candidate("4", "新公司有限公司"),
            ])
            state = result["platforms"]["51job"]
            self.assertEqual(state["new"], 1)                        # only the first of the two 新公司 postings
            self.assertEqual(state["filtered"], 3)
            reasons = " ".join(record["reason"] for record in state["filter_records"])
            self.assertIn("近期已投递", reasons)
            self.assertIn("岗位池", reasons)

    def test_dedup_is_off_unless_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "c.db"
            conn = get_db(db_path)
            insert_job_if_new(conn, {"id": "p1", "title": "t", "company": "美团", "jd": "x" * 100})
            conn.close()
            result = _run({}, db_path, [_candidate("2", "美团")])
            self.assertEqual(result["platforms"]["51job"]["new"], 1)
