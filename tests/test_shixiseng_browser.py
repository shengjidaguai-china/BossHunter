"""Test the default Chrome path without connecting to a real recruitment account."""

import json
import shutil
import subprocess
from threading import Event
from unittest.mock import patch

import pytest
import test_web_api_routes as web_routes

from bosshunter.ai.prefilter import quick_score
from bosshunter.ai.scorer import _build_scoring_prompt
from bosshunter.collection.base import CollectionError, CollectorHooks
from bosshunter.collection.models import PlatformCollectionRequest
from bosshunter.collection.orchestrator import CollectionOrchestrator
from bosshunter.collection.platforms.shixiseng_browser import (
    READ_DETAIL,
    READ_RESULTS,
    READ_SESSION,
    BrowserShixisengCollector,
    build_candidate,
    job_url,
    next_results_page,
    search_url,
)
from bosshunter.db import get_active_platform_safety_lock, get_db, insert_job
from bosshunter.web import server
from bosshunter.web.preflight import check_browser_connection

BASE = "https://www.shixiseng.com"
SEARCH = BASE + "/interns?keyword=python"
JOB = BASE + "/intern/inn_sample"


class InstantEvent(Event):
    def wait(self, timeout=None):
        return self.is_set()


class FixtureRuntime:
    def __init__(self, risk=""):
        self.risk = risk
        self.created = 0
        self.opened = []
        self.closed = []

    def get_page_targets(self):
        return [{"id": "search", "url": SEARCH}]

    def new_tab(self, url):
        assert url == "about:blank"
        self.created += 1
        return "results" if self.created == 1 else "detail"

    def navigate(self, tab, url):
        assert tab == ("results" if "/interns?" in url else "detail")
        self.opened.append(url)
        return True

    def close_tab(self, tab):
        self.closed.append(tab)

    def wait_for_load(self, tab, timeout):
        return True

    def evaluate(self, tab, script, timeout):
        if script == READ_SESSION:
            assert tab == "search"
            return {"loggedIn": True}
        if script == READ_RESULTS:
            return {"url": SEARCH, "jobs": [JOB], "next": ""}
        assert tab == "detail" and script == READ_DETAIL
        if self.risk:
            return {"risk": self.risk}
        return {
            "url": JOB,
            "title": "Python 开发实习生",
            "company": "示例公司",
            "jd": "编写数据工具",
            "facts": "150-220/天 上海 本科 4 天／周 实习3个月",
        }


def test_browser_collection_checks_city_keyword_and_terms(tmp_path):
    db = get_db(tmp_path / "jobs.db")
    emitted = []
    hooks = CollectorHooks(
        InstantEvent(),
        lambda c: True,
        lambda c: not emitted.append(c),
        print,
        lambda **_: None,
        last_save_receipt=lambda: {"inserted": bool(emitted)},
    )
    runtime = FixtureRuntime()
    request = PlatformCollectionRequest("shixiseng", ["python"], ["上海"], {})
    with db:
        result = BrowserShixisengCollector({}, db, runtime=runtime).collect(request, hooks)
    assert result.status == "completed"
    [row] = emitted
    assert (row.salary, row.city, row.education) == ("150-220/天", "上海", "本科")
    assert "实习安排：4 天／周，实习3个月" in row.jd
    assert runtime.opened == [search_url("上海", "python"), JOB] and runtime.closed == ["results", "detail"]
    db.close()


def test_workbench_outcome_matches_the_saved_browser_jobs(tmp_path):
    config = {"_workbench_stop_event": InstantEvent(), "profile": {"allow_internship": True}}
    options = {
        "platform_order": ["shixiseng"],
        "platforms": {"shixiseng": {"cities": ["上海"], "keywords": ["Python"], "max_pages": 1}},
    }
    db_path = tmp_path / "jobs.db"

    def make_collector(config, conn):
        return BrowserShixisengCollector(config, conn, runtime=FixtureRuntime())

    def run():
        with patch("bosshunter.collection.orchestrator.BrowserShixisengCollector", side_effect=make_collector):
            return CollectionOrchestrator(config, db_path=db_path).run(options)

    first = run()
    assert first["status"] == "completed"
    assert first["collected_job_ids"] == ["shixiseng:inn_sample"]
    second = run()
    assert second["status"] == "completed_with_shortage"
    assert second["collected_job_ids"] == []


def test_restriction_stops_before_import_and_preserves_user_tab(tmp_path):
    db = get_db(tmp_path / "jobs.db")
    runtime = FixtureRuntime("blocked")
    hooks = CollectorHooks(
        InstantEvent(), lambda c: True, lambda c: pytest.fail("unexpected import"), print, lambda **_: None
    )
    with pytest.raises(CollectionError, match="访问限制"):
        BrowserShixisengCollector({}, db, runtime=runtime).collect(
            PlatformCollectionRequest("shixiseng", ["Python"], ["上海"], {}), hooks
        )
    assert runtime.opened == [search_url("上海", "Python"), JOB] and runtime.closed == ["results", "detail"]
    assert get_active_platform_safety_lock(db)
    db.close()


def test_session_blocks_a_visible_challenge_but_ignores_the_transparent_preload():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    setup = """
const location = {protocol: 'https:', host: 'www.shixiseng.com', pathname: '/'};
const getComputedStyle = el => ({visibility: 'visible', opacity: el.opacity});
const element = (opacity, parentElement = null) => ({opacity, parentElement, getClientRects: () => [1]});
const container = element('0');
const frame = element('1', container);
const document = {
    title: '实习僧', readyState: 'complete', body: {innerText: ''},
    querySelectorAll: selector => selector.includes('captcha') ? [container, frame] :
        selector.includes('.logined') ? [element('1')] : [],
};
"""
    script = setup + f"""
const readSession = () => {READ_SESSION};
const preloaded = readSession();
container.opacity = '1';
const visible = readSession();
console.log(JSON.stringify([preloaded, visible]));
"""
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True, timeout=5)
    assert json.loads(result.stdout) == [{"loggedIn": True}, {"risk": "blocked"}]


def test_links_must_remain_on_site_and_in_the_same_search():
    assert job_url(JOB + "?ref=1") == ("inn_sample", JOB)
    assert not job_url("https://www.shixiseng.com.example.org/intern/inn_sample")
    assert not job_url(BASE.replace("https://", "https://other@") + "/intern/inn_sample")
    assert next_results_page(SEARCH, SEARCH + "&page=2") == SEARCH + "&page=2"
    assert not next_results_page(SEARCH, SEARCH.replace("python", "java") + "&page=2")
    assert not next_results_page(SEARCH, SEARCH + "&page=2&keyword=other")


def test_browser_preflight_uses_existing_shixiseng_tab():
    diagnostics = {"runtime": True, "chrome": True, "targets": FixtureRuntime().get_page_targets()}
    with patch("bosshunter.web.preflight.run_browser_diagnostics", return_value=diagnostics):
        checks = check_browser_connection({}, {"platform_order": ["shixiseng"]})
    assert any(row["id"] == "shixiseng_tab" and row["status"] == "pass" for row in checks)


def test_detail_with_missing_fields_keeps_exact_platform_identity(tmp_path):
    class MissingDetail(FixtureRuntime):
        def evaluate(self, tab, script, timeout):
            if script == READ_RESULTS:
                return {"url": SEARCH, "jobs": [JOB], "titles": {JOB: "结果卡标题"}}
            if script == READ_DETAIL:
                return {"url": JOB}
            return super().evaluate(tab, script, timeout)

    db = get_db(tmp_path / "jobs.db")
    rows = []
    hooks = CollectorHooks(InstantEvent(), lambda _: True, lambda job: not rows.append(job), print,
                           lambda **_: None, last_save_receipt=lambda: {"inserted": True})
    try:
        result = BrowserShixisengCollector({}, db, runtime=MissingDetail()).collect(
            PlatformCollectionRequest("shixiseng", ["Python"], ["上海"], {}), hooks,
        )
        assert result.status == "completed"
        [job] = rows
        assert (job.url, job.storage_id, job.title, job.company) == (JOB, "shixiseng:inn_sample", "结果卡标题", "公司未知")
        assert (job.jd, job.salary, job.city) == ("", "", "")
    finally:
        db.close()


@pytest.mark.parametrize("salary", ["200 元/天", "900元／周", "30元/小时"])
def test_preserved_nonmonthly_units_skip_the_monthly_threshold_in_scoring(salary):
    candidate = build_candidate({"url": JOB, "title": "Python 实习", "company": "示例公司", "facts": salary}, ["全国"], "Python")
    job = candidate.as_job_record()
    config = {"profile": {"allow_internship": True, "salary_min": 15, "filter_unparsed_salary": True}}
    assert job["salary"] == salary
    assert quick_score(job, config)[0] == 100
    assert "岗位使用非月薪单位" in _build_scoring_prompt(job, "合成简历", config)
    assert quick_score(job, {"profile": {"allow_internship": False}})[0] == 0


def test_workbench_search_and_manual_sent_reuse_the_existing_routes(tmp_path):
    old_base = server.BASE_DIR
    server.set_base_dir(tmp_path)
    job = build_candidate({"url": JOB, "title": "Python 实习", "company": "示例公司", "facts": "200 元/天"},
                          ["全国"], "Python").as_job_record()
    db = get_db(server.DATA_DIR / "bosshunter.db")
    try:
        insert_job(db, job)
        insert_job(db, web_routes._job("boss-sample"))
    finally:
        db.close()

    client = web_routes.WebApiRouteTests()
    try:
        status, _, response = client._request("/api/jobs/search?source_platform=shixiseng")
        assert status.startswith("200")
        [row] = json.loads(response)["items"]
        assert (row["id"], row["url"], row["salary"]) == (job["id"], JOB, "200 元/天")
        payload = {"job_ids": [job["id"]]}
        assert client._request("/api/jobs/manual-sent", "POST", payload)[0].startswith("400")
        status, _, response = client._request("/api/jobs/manual-sent", "POST", {**payload, "confirmed": True})
        assert status.startswith("200") and json.loads(response)["affected_count"] == 1
    finally:
        server.set_base_dir(old_base)
