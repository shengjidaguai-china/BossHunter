"""Internship-only searches fail closed without loosening sending safeguards."""

import json
import shutil
import subprocess
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from bosshunter.ai.prefilter import quick_score
from bosshunter.collection.base import CollectorHooks
from bosshunter.collection.models import PlatformCollectionRequest, classify_recruitment_type
from bosshunter.collection.platforms.boss import (
    JS_DETECT_COLLECTION_RISK, JS_EXTRACT_DETAIL, JS_EXTRACT_LIST,
    JS_VERIFY_INTERNSHIP_FILTER, BossBrowser, BossCollector, build_boss_filter_query,
)
from bosshunter.employment import classify_employment, internship_only, internship_rejection

CONFIG = {
    "profile": {"allow_internship": True, "filter_unparsed_salary": False},
    "platforms": {"boss": {"search": {"filters": {"job_type": ["实习"]}}}},
}


@pytest.mark.parametrize("title,jd,expected", [
    ("Go实习生", "开发", "internship"),
    ("Backend intern", "work", "internship"),
    ("后端开发", "职位类型：实习", "internship"),
    ("校招开发", "应届生", "unknown"),
    ("Java开发", "有实习经历优先", "unknown"),
    ("非实习后端", "开发", "full_time"),
    ("不接受实习", "开发", "full_time"),
    ("实习生", "职位类型：全职", "unknown"),
    ("实习生", "岗位性质：兼职", "unknown"),
    ("全职开发", "岗位性质：实习", "unknown"),
    ("兼职开发", "岗位性质：实习", "unknown"),
    ("开发", "岗位性质：实习\n职位类型：全职", "unknown"),
    ("实习/全职开发", "开发", "unknown"),
    ("兼职开发", "", "part_time"),
    ("开发", "职位类型：兼职", "part_time"),
    ("开发", "200元/天，有实习经历优先", "unknown"),
])
def test_classify(title, jd, expected):
    job = {"title": title, "jd": jd, "salary": "10-20K"}
    assert classify_employment(job) == expected
    assert bool(internship_rejection(job, CONFIG)) == (expected != "internship")
    assert (quick_score(job, CONFIG)[0] > 0) == (expected == "internship")


@pytest.mark.parametrize("filters,expected", [
    ({"job_type": ["实习"]}, True), ({"job_type": "实习"}, True),
    ({"job_type": [" 实习 ", "实习"]}, True),
    ({"job_type": ["实习", "全职"]}, False), ({"job_type": []}, False),
    ({"job_type": ["实习", None]}, False), ({}, False), (None, False),
])
def test_scope_and_legacy_precedence(filters, expected):
    legacy = {"search": {"filters": {"job_type": ["实习"]}}}
    assert internship_only(legacy)
    config = {**legacy, "platforms": {"boss": {"search": {"filters": filters}}}}
    assert internship_only(config) is expected


@pytest.mark.parametrize("platform", ["zhilian", "51job", "liepin"])
def test_guard_does_not_apply_to_other_platforms(platform):
    assert not internship_rejection({"title": "全职", "source_platform": platform}, CONFIG)


def test_recruitment_type_is_not_employment_type():
    assert not internship_rejection({"title": "全职"}, {})
    assert classify_recruitment_type("Go实习生") == "unknown"
    assert classify_recruitment_type("校招Go实习生") == "campus"
    assert classify_recruitment_type("社招开发") == "experienced"


@pytest.mark.parametrize("label,code", [("全职", "1901"), ("兼职", "1903"), ("实习", "1902")])
def test_job_type_query_codes(label, code):
    assert build_boss_filter_query({"job_type": [label]}) == f"jobType={code}"


def collect_fixture(title, jd, *, applied=True, config=None, filters=None):
    row = {"title": title, "company": "测试企业", "url": "/job_detail/guard.html", "salary": "10-20K"}
    items, events, scripts = [], [], []

    def evaluate(_target, script):
        scripts.append(script)
        if script == JS_VERIFY_INTERNSHIP_FILTER:
            return applied
        if script == JS_DETECT_COLLECTION_RISK:
            return json.dumps({"risk": None})
        if script == JS_EXTRACT_LIST:
            return json.dumps([row])
        if script == JS_EXTRACT_DETAIL:
            return json.dumps({**row, "jd": jd})
        return "{}"

    browser = BossBrowser(
        new_tab=lambda *_a, **_kw: "fixture", close_tab=lambda _t: True,
        evaluate=evaluate, navigate=lambda *_a: True,
        scroll=lambda *_a, **_kw: True, wait_for_load=lambda *_a, **_kw: True,
    )
    hooks = CollectorHooks(
        stop_event=None, on_list_candidate=lambda _c: True, on_parse_failed=lambda _r: None,
        on_candidate=lambda candidate: items.append(candidate) or True,
        on_event=lambda **values: events.append(values),
    )
    throttle = MagicMock()
    throttle.wait.return_value = False
    request = PlatformCollectionRequest(
        "boss", ["Go"], ["深圳"], {"深圳": "101280600"}, max_pages=1,
        filters=filters if filters is not None else {"job_type": ["实习"]},
    )
    with patch("bosshunter.collection.platforms.boss.time.sleep"):
        result = BossCollector(
            browser=browser, config=config if config is not None else CONFIG,
            throttle_factory=lambda **_kw: throttle, sleep=lambda _s: None,
        ).collect(request, hooks)
    return result, items, events, scripts


@pytest.mark.parametrize("title,jd,count", [
    ("Go实习生", "开发", 1), ("正式开发", "开发", 0),
    ("后端开发", "职位类型：实习", 1), ("校招开发", "有实习经历优先", 0),
    ("实习生", "岗位性质：兼职", 0),
])
def test_collector_waits_for_detail_then_guards(title, jd, count):
    _, items, events, scripts = collect_fixture(title, jd)
    assert JS_EXTRACT_DETAIL in scripts  # type missing on card must reach JD
    assert len(items) == count
    assert sum(bool(e.get("increment_filtered")) for e in events) == 1 - count


@pytest.mark.parametrize("applied", [False, None, "true", {}])
def test_unconfirmed_filter_stops_before_reading_candidates(applied):
    result, items, _, scripts = collect_fixture("Go实习生", "开发", applied=applied)
    assert result.reason_code == "internship_filter_not_applied"
    assert items == []
    assert JS_EXTRACT_LIST not in scripts
    assert JS_EXTRACT_DETAIL not in scripts


def test_request_filter_not_stale_saved_filter_controls_collection():
    _, items, _, scripts = collect_fixture("全职开发", "开发", filters={})
    assert len(items) == 1
    assert JS_VERIFY_INTERNSHIP_FILTER not in scripts
    config = {"profile": {"allow_internship": True}}
    _, items, _, _ = collect_fixture("全职开发", "开发", config=config)
    assert items == []


def test_other_prefilter_settings_and_input_config_are_preserved():
    config = deepcopy(CONFIG)
    config["profile"]["salary_min"] = 30
    original = deepcopy(config)
    _, items, _, scripts = collect_fixture("Go实习生", "开发", config=config)
    assert items == []
    assert JS_EXTRACT_DETAIL not in scripts
    assert config == original


@pytest.mark.parametrize("title,jd", [
    ("校招工程师", "有实习经历优先"), ("全职开发", "开发"),
    ("实习生", "岗位性质：兼职"),
])
def test_sender_blocks_historical_nonintern_before_browser(title, jd):
    from bosshunter.executor.sender import send_greetings

    config = deepcopy(CONFIG)
    with patch("bosshunter.executor.sender.get_db", return_value=MagicMock()), \
         patch("bosshunter.executor.sender.PlatformAccessGuard"), \
         patch("bosshunter.executor.sender.get_jobs_ready_to_send", return_value=[
             {"id": "old", "title": title, "jd": jd, "source_platform": "boss"},
         ]), patch("bosshunter.executor.sender._send_greeting_once") as send:
        assert send_greetings(config, force=True) == 0
        assert config["_workbench_send_report"]["employment_blocked_ids"] == ["old"]
        send.assert_not_called()


def test_browser_filter_check_requires_url_and_one_selected_internship():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for the DOM fixture")
    # Execute the real collector JS against bounded DOM fixtures, not a live site.
    code = r'''
const assert = require('node:assert/strict');
const script = SCRIPT;
const intern = {textContent:' 实习 ', getAttribute: () => 'jobType-1902'};
function check(query, selected) {
    global.location = {href: 'https://www.zhipin.com/web/geek/job?' + query};
    global.document = {querySelectorAll: () => selected};
    return eval(script);
}
assert.equal(check('jobType=1902', [intern]), true);
assert.equal(check('jobType=2', [intern]), false);
assert.equal(check('jobType=1902', []), false);
assert.equal(check('jobType=1902', [intern, intern]), false);
assert.equal(check('jobType=1902', [{textContent:'全职',getAttribute:()=> 'jobType-1901'}]), false);
console.log('internship DOM guard: ok');
'''.replace("SCRIPT", json.dumps(JS_VERIFY_INTERNSHIP_FILTER))
    result = subprocess.run([node, "-e", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "internship DOM guard: ok"


def test_web_employment_hint_does_not_rewrite_historical_recruitment_type():
    from bosshunter.web import server

    job = {"id": "old", "title": "实习生", "jd": "职位类型：兼职", "recruitment_type": "campus"}
    with patch.object(server, "load_config") as load:
        displayed = server._serialize_job(job, config=CONFIG)
    assert displayed["employment_type"] == "unknown"
    assert "待核实" in displayed["employment_review"]
    assert displayed["recruitment_type"] == "campus"
    assert "employment_type" not in job
    load.assert_not_called()


def test_legacy_scraper_counts_employment_filter_events():
    from bosshunter.scraper.jobs import scrape_jobs
    from bosshunter.collection.models import PlatformCollectionResult

    updates = []
    config = {**deepcopy(CONFIG), "profile": {"target_cities": ["深圳"]},
              "_workbench_collect_progress": updates.append}

    def collect(_request, hooks):
        hooks.on_event(message="仅实习：非实习岗位", increment_filtered=True)
        return PlatformCollectionResult("boss", "completed", "search_exhausted", "fixture")

    with patch("bosshunter.scraper.jobs.get_db", return_value=MagicMock()), \
         patch("bosshunter.scraper.jobs.BossCollector.collect", side_effect=collect):
        assert scrape_jobs(config, ["Go"]) == 0
    assert updates[-1]["filtered"] == 1


@pytest.mark.parametrize("acceptance", [False, None, "false"])
def test_disabled_acceptance_stops_internship_search_before_browser(acceptance):
    config = deepcopy(CONFIG)
    config["profile"]["allow_internship"] = acceptance
    result, items, _, scripts = collect_fixture("后端开发", "职位类型：实习", config=config)
    assert result.reason_code == "internship_config_conflict"
    assert "接受实习" in result.message
    assert items == []
    assert scripts == []


def test_default_disabled_acceptance_cannot_start_internship_search():
    result, items, _, scripts = collect_fixture("后端开发", "职位类型：实习", config={})
    assert result.reason_code == "internship_config_conflict"
    assert items == scripts == []


def test_disabled_acceptance_is_checked_after_detail_without_only_filter():
    config = deepcopy(CONFIG)
    config["profile"]["allow_internship"] = False
    result, items, events, scripts = collect_fixture("后端开发", "职位类型：实习", config=config, filters={})
    assert JS_EXTRACT_DETAIL in scripts  # generic list title passed, JD is authoritative
    assert items == []
    assert any(e.get("increment_filtered") and e["message"] == "实习/管培岗位" for e in events)
    assert internship_rejection({"title": "后端开发", "jd": "职位类型：实习"}, config)


@pytest.mark.parametrize("filters", [{"job_type": ["实习"]}, {}])
def test_sender_blocks_detail_only_internship_when_acceptance_disabled(filters):
    from bosshunter.executor.sender import send_greetings

    config = deepcopy(CONFIG)
    config["profile"]["allow_internship"] = False
    config["platforms"]["boss"]["search"]["filters"] = filters
    with patch("bosshunter.executor.sender.get_db", return_value=MagicMock()), \
         patch("bosshunter.executor.sender.PlatformAccessGuard"), \
         patch("bosshunter.executor.sender.get_jobs_ready_to_send", return_value=[{
             "id": "historical", "title": "后端开发", "jd": "职位类型：实习", "source_platform": "boss",
         }]), patch("bosshunter.executor.sender._send_greeting_once") as send:
        assert send_greetings(config, force=True) == 0
        assert config["_workbench_send_report"]["employment_blocked_ids"] == ["historical"]
        send.assert_not_called()


@pytest.mark.parametrize("source", ["saved", "dialog", "legacy"])
def test_collection_start_rejects_conflicting_effective_filters(source):
    from bosshunter.collection.orchestrator import normalize_collection_options

    config = {"profile": {"allow_internship": False, "target_cities": ["深圳"]}}
    search = {"keywords": ["Go"], "cities": ["深圳"], "filters": {"job_type": ["实习"]}}
    raw = None
    if source == "saved":
        config["platforms"] = {"boss": {"search": search}}
    elif source == "dialog":
        raw = {"platform_order": ["boss"], "platforms": {"boss": search}}
    else:
        config["search"] = search
    original = deepcopy(config)
    with pytest.raises(ValueError, match="接受实习"):
        normalize_collection_options(config, raw)
    assert config == original
    config["profile"]["allow_internship"] = True
    assert normalize_collection_options(config, raw)["platforms"]["boss"]["filters"] == {"job_type": ["实习"]}


def test_disabled_acceptance_does_not_block_full_time_or_other_platforms():
    config = deepcopy(CONFIG)
    config["profile"]["allow_internship"] = False
    assert not internship_rejection({"title": "实习生", "source_platform": "zhilian"}, config)
    result, items, _, _ = collect_fixture("后端开发", "职位类型：全职", config=config, filters={})
    assert len(items) == 1


@pytest.mark.parametrize("mode", ["collect", "full"])
def test_web_start_returns_actionable_conflict_without_scheduling(mode):
    import test_web_api_routes as web_tests
    from bosshunter.web import server

    config = deepcopy(CONFIG)
    config["profile"]["allow_internship"] = False
    options = {"platform_order": ["boss"], "platforms": {"boss": {
        "keywords": ["Go"], "cities": ["深圳"], "filters": {"job_type": ["实习"]},
    }}}
    runner = MagicMock()
    with patch.object(server, "load_config", return_value=config), \
         patch.object(server, "task_runner", runner):
        status, _, body = web_tests.WebApiRouteTests()._request(
            "/api/workbench/task", method="POST", json_body={"mode": mode, "options": options},
        )
    assert status.startswith("400"), body
    assert "接受实习" in json.loads(body)["error"]
    runner.start.assert_not_called()


def test_detail_guard_keeps_acceptance_after_startup_check():
    # Exercise the detail defense independently: bypass only the startup validator
    # to emulate an older entry point, not the shared employment guard.
    config = deepcopy(CONFIG)
    config["profile"]["allow_internship"] = False
    with patch("bosshunter.collection.platforms.boss.internship_config_error", return_value=""):
        _, items, events, scripts = collect_fixture("后端开发", "职位类型：实习", config=config)
    assert JS_EXTRACT_DETAIL in scripts
    assert items == []
    assert any(e.get("increment_filtered") and "接受实习" in e["message"] for e in events)
    assert quick_score({"title": "后端开发", "jd": "职位类型：实习", "salary": "10-20K"}, config)[0] == 0
