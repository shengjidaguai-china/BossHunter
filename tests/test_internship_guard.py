"""Internship-only searches fail closed without loosening sending safeguards."""

import json
import shutil
import sqlite3
import subprocess
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from bosshunter.ai.prefilter import quick_score
from bosshunter.collection.base import CollectorHooks
from bosshunter.collection.models import JobCandidate, PlatformCollectionRequest, classify_recruitment_type
from bosshunter.collection.platforms.boss import (
    JS_DETECT_COLLECTION_RISK, JS_DISPATCH_LIST_SCROLL, JS_EXTRACT_DETAIL, JS_EXTRACT_LIST,
    JS_IS_SCROLL_LIST, JS_VERIFY_INTERNSHIP_FILTER, BossBrowser, BossCollector, build_boss_filter_query,
)
from bosshunter.db import get_db, insert_job_if_new
from bosshunter.employment import (
    BOSS_INTERNSHIP_CARD, classify_employment, has_internship_card_tag,
    internship_only, internship_rejection,
)

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


def collect_fixture(title, jd, *, applied=True, config=None, filters=None, tags=None):
    row = {"title": title, "company": "测试企业", "url": "/job_detail/guard.html", "salary": "10-20K"}
    if tags is not None:
        row["tags"] = tags
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


CARD_TAGS = ["5天/周", "3个月", "本科"]


@pytest.mark.parametrize("tags,expected", [
    (CARD_TAGS, True), (["1-3年", "本科"], False), ([], False), (None, False),
    ("5天/周", False), (["五天/周"], False), (["5天/周."], False),
])
def test_internship_card_tag_pattern(tags, expected):
    assert has_internship_card_tag(tags) is expected


@pytest.mark.parametrize("title,jd,tags,saved", [
    ("软件测试", "负责功能测试与回归", CARD_TAGS, 1),
    ("软件测试", "负责功能测试与回归", ["\ue035天/周", "\ue033个月"], 1),  # 加密字体数字仍需解码后命中
    ("软件测试", "负责功能测试", ["1-3年", "本科"], 0),
    ("全职开发", "负责功能测试与回归", CARD_TAGS, 0),
    ("软件测试", "职位类型：全职", CARD_TAGS, 0),
    ("非实习测试", "负责功能测试与回归", CARD_TAGS, 0),
])
def test_card_internship_tag_stamps_evidence_only_when_verified(title, jd, tags, saved):
    _, items, events, _ = collect_fixture(title, jd, tags=tags)
    assert len(items) == saved
    if saved:
        assert items[0].employment_source == BOSS_INTERNSHIP_CARD
    else:
        assert any(e.get("increment_filtered") for e in events)


def test_card_internship_tag_needs_internship_only_scope():
    _, items, _, _ = collect_fixture("软件测试", "负责功能测试", tags=CARD_TAGS, filters={})
    assert len(items) == 1
    assert items[0].employment_source == ""


def test_persisted_card_evidence_is_one_internship_signal():
    # Neutral title: the card evidence alone classifies as internship.
    for source_platform in (None, "boss"):
        assert classify_employment({
            "title": "软件测试", "jd": "", "salary": "10-20K",
            "source_platform": source_platform, "employment_source": BOSS_INTERNSHIP_CARD,
        }) == "internship"
    # Conflicting title/JD signals still win the argument and block.
    assert classify_employment({
        "title": "全职开发", "jd": "", "source_platform": "boss",
        "employment_source": BOSS_INTERNSHIP_CARD,
    }) == "unknown"
    assert classify_employment({
        "title": "软件测试", "jd": "职位类型：全职", "source_platform": "boss",
        "employment_source": BOSS_INTERNSHIP_CARD,
    }) == "unknown"
    # A negated internship title is non-internship, not merely unverified.
    for title in ("非实习测试", "不接受实习"):
        job = {
            "title": title, "jd": "", "source_platform": "boss",
            "employment_source": BOSS_INTERNSHIP_CARD,
        }
        assert classify_employment(job) == "full_time"
        assert internship_rejection(job, CONFIG) == "仅实习：非实习岗位"
    # Evidence is BOSS-only and value-exact.
    assert classify_employment({
        "title": "软件测试", "jd": "", "source_platform": "zhilian",
        "employment_source": BOSS_INTERNSHIP_CARD,
    }) == "unknown"
    assert classify_employment({
        "title": "软件测试", "jd": "", "source_platform": "boss",
        "employment_source": "anything",
    }) == "unknown"


def test_merge_detail_keeps_employment_source():
    candidate = JobCandidate(
        platform="boss", source_job_id="merge", title="软件测试", company="测试企业",
        employment_source=BOSS_INTERNSHIP_CARD,
    )
    merged = BossCollector._merge_detail(candidate, {"jd": "负责功能测试"}, "https://www.zhipin.com/job_detail/merge.html")
    assert merged.employment_source == BOSS_INTERNSHIP_CARD


class ScrollListBrowser:
    """Scroll列表 fixture：JS_EXTRACT_LIST 按 JS_DISPATCH_LIST_SCROLL 换批次。"""

    def __init__(self, batches, *, verify_results=(True,)):
        self.batches = batches
        self.page = 0
        self.verify_results = list(verify_results)
        self.detail_jds = []

    def new_tab(self, *_args, **_kwargs):
        return "worker"

    def navigate(self, _target, _url):
        return True

    def close_tab(self, _target):
        return True

    def scroll(self, *_args, **_kwargs):
        return True

    def wait_for_load(self, *_args, **_kwargs):
        return True

    def evaluate(self, _target, script):
        if script == JS_IS_SCROLL_LIST:
            return True
        if script == JS_DISPATCH_LIST_SCROLL:
            self.page = min(self.page + 1, len(self.batches) - 1)
            return True
        if script == JS_VERIFY_INTERNSHIP_FILTER:
            return self.verify_results.pop(0) if self.verify_results else True
        if script == JS_DETECT_COLLECTION_RISK:
            return json.dumps({"risk": None})
        if script == JS_EXTRACT_LIST:
            return json.dumps(self.batches[self.page])
        if script == JS_EXTRACT_DETAIL:
            return json.dumps({"title": "软件测试", "company": "测试企业", "jd": "负责功能测试"})
        return "{}"


def scroll_fixture(batches, *, verify_results=(True,)):
    browser = ScrollListBrowser(batches, verify_results=verify_results)
    items = []
    hooks = CollectorHooks(
        stop_event=None, on_list_candidate=lambda _c: True, on_parse_failed=lambda _r: None,
        on_candidate=lambda candidate: items.append(candidate) or True,
        on_event=lambda **_values: None,
    )
    throttle = MagicMock()
    throttle.wait.return_value = False
    request = PlatformCollectionRequest(
        "boss", ["Go"], ["深圳"], {"深圳": "101280600"}, max_pages=len(batches),
        filters={"job_type": ["实习"]},
    )
    with patch("bosshunter.collection.platforms.boss.time.sleep"):
        result = BossCollector(
            browser=browser, config=deepcopy(CONFIG),
            throttle_factory=lambda **_kw: throttle, sleep=lambda _s: None,
        ).collect(request, hooks)
    return result, items


def scroll_card(job_id, tags=CARD_TAGS):
    return {
        "title": "软件测试", "company": "测试企业", "url": f"/job_detail/{job_id}.html",
        "salary": "10-20K", "tags": tags,
    }


@pytest.mark.parametrize("recheck", [False, None, "true", {}, 0])
def test_scroll_batch_recheck_stops_before_new_cards(recheck):
    batches = [[scroll_card("scroll-a")], [scroll_card("scroll-a"), scroll_card("scroll-b")]]
    result, items = scroll_fixture(batches, verify_results=[True, recheck])
    assert result.reason_code == "internship_filter_not_applied"
    assert [c.source_job_id for c in items] == ["scroll-a"]


def test_scroll_batch_recheck_passes_and_keeps_stamping_evidence():
    batches = [[scroll_card("scroll-a")], [scroll_card("scroll-a"), scroll_card("scroll-b")]]
    result, items = scroll_fixture(batches, verify_results=[True, True])
    assert result.status == "completed"
    assert [c.source_job_id for c in items] == ["scroll-a", "scroll-b"]
    assert all(c.employment_source == BOSS_INTERNSHIP_CARD for c in items)


# --- 发送与展示：数据库里持久化的卡片证据在日志之外重新起作用 ---

@pytest.mark.parametrize("evidence,blocked", [
    (BOSS_INTERNSHIP_CARD, []),
    ("", ["card-evidence"]),
])
def test_sender_knows_persisted_card_evidence(evidence, blocked):
    from bosshunter.executor.sender import send_greetings

    config = deepcopy(CONFIG)
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = {"cnt": 0}
    with patch("bosshunter.executor.sender.get_db", return_value=db), \
         patch("bosshunter.executor.sender.PlatformAccessGuard"), \
         patch("bosshunter.executor.sender.get_jobs_ready_to_send", return_value=[
             {
                 "id": "card-evidence", "title": "软件测试", "company": "测试企业", "jd": "",
                 "salary": "10-20K", "greeting": "你好",
                 "source_platform": "boss", "employment_source": evidence,
             },
         ]), patch("bosshunter.executor.sender._send_greeting_once", return_value=({}, None)) as send:
        send_greetings(config, force=True)
    assert config["_workbench_send_report"]["employment_blocked_ids"] == blocked
    if evidence:
        send.assert_called_once()
    else:
        send.assert_not_called()


def test_web_dashboard_reads_persisted_card_evidence():
    from bosshunter.web import server

    job = {
        "id": "web-card", "title": "软件测试", "jd": "", "salary": "10-20K",
        "source_platform": "boss", "employment_source": BOSS_INTERNSHIP_CARD,
    }
    with patch.object(server, "load_config") as load:
        displayed = server._serialize_job(job, config=CONFIG)
    assert displayed["employment_type"] == "internship"
    assert displayed["employment_review"] == ""
    load.assert_not_called()


def _db_job_record(**overrides):
    record = {
        "id": "card-db", "title": "软件测试", "company": "测试企业", "salary": "10-20K",
        "city": "深圳", "jd": "负责功能测试", "url": "/job_detail/card-db.html",
        "source_platform": "boss", "source_job_id": "card-db",
        "employment_source": BOSS_INTERNSHIP_CARD,
    }
    record.update(overrides)
    return record


def test_db_round_trip_releases_persisted_card_evidence(tmp_path):
    conn = get_db(tmp_path / "jobs.db")
    try:
        assert insert_job_if_new(conn, _db_job_record())
        row = dict(conn.execute("SELECT * FROM jobs WHERE id = 'card-db'").fetchone())
        assert row["employment_source"] == BOSS_INTERNSHIP_CARD
        assert internship_rejection(row, CONFIG) == ""
    finally:
        conn.close()


@pytest.mark.parametrize("overrides", [
    {"source_platform": "zhilian", "source_job_id": "card-zl"},
    {"employment_source": "anything"},
])
def test_db_persists_only_whitelisted_card_evidence(tmp_path, overrides):
    conn = get_db(tmp_path / "jobs.db")
    try:
        job = _db_job_record(**overrides)
        assert insert_job_if_new(conn, job)
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job["id"],)).fetchone()
        assert row["employment_source"] is None
    finally:
        conn.close()


def test_employment_source_migration_adds_null_column_and_is_idempotent(tmp_path):
    from bosshunter.db import _init_tables

    db_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(db_path)
    legacy.executescript(
        """
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL,
            salary TEXT, city TEXT, experience TEXT, jd TEXT, hr_name TEXT,
            hr_title TEXT, hr_active TEXT, company_size TEXT, company_industry TEXT,
            url TEXT, score INTEGER DEFAULT 0, score_reason TEXT, greeting TEXT,
            status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO jobs (id, title, company, city, url, score, greeting, status)
        VALUES ('legacy', 'Legacy Job', 'Legacy Co', '北京', 'https://example.com/legacy', 77, 'hello', 'ready');
        """
    )
    legacy.commit()
    legacy.close()
    db = get_db(db_path)
    try:
        _init_tables(db)
        assert insert_job_if_new(db, _db_job_record())
        legacy_row = dict(db.execute("SELECT * FROM jobs WHERE id = 'legacy'").fetchone())
        assert legacy_row["recruitment_type"] == "unknown"
    finally:
        db.close()
    # A second connection repeats the column migration and the one-time v1.4 backfill.
    # Neither may drop the new column, null out saved evidence, or rewrite campus/social fields.
    db = get_db(db_path)
    try:
        _init_tables(db)
        legacy_row = dict(db.execute("SELECT * FROM jobs WHERE id = 'legacy'").fetchone())
        evidence_row = dict(db.execute("SELECT * FROM jobs WHERE id = 'card-db'").fetchone())
    finally:
        db.close()
    assert "employment_source" in legacy_row
    assert legacy_row["employment_source"] is None
    assert legacy_row["title"] == "Legacy Job"
    assert legacy_row["recruitment_type"] == "unknown"
    assert evidence_row["employment_source"] == BOSS_INTERNSHIP_CARD


def test_list_extractor_returns_full_card_tags_for_evidence():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for the DOM fixture")
    # Execute the real collector JS against bounded DOM fixtures, not a live site.
    code = r'''
const assert = require('node:assert/strict');
const script = SCRIPT;
function el(text) {
    return {
        textContent: text,
        getAttribute: (name) => (name === 'href' ? CARD_HREF : null),
    };
}
const tags = ["5天/周", "3个月", "本科"].map(el);
const box = {
    querySelector: (sel) => box["q" + sel] ?? null,
    querySelectorAll: (sel) => box["a" + sel] ?? null,
};
box["q.job-name"] = el("软件测试");
box["q.job-salary"] = el("10-20K");
box["a.tag-list li"] = tags;
box["q.boss-name"] = el("测试企业");
box["q.company-location"] = el("深圳");
// 没有独立的 .job-card-box 节点时，wrap 自身被当作 box 使用。
const wrap = {
    querySelector: (sel) => (sel === '.job-card-box' ? null : box["q" + sel] ?? null),
    querySelectorAll: (sel) => box["a" + sel] ?? [],
};
const wraps = [wrap];
global.document = {querySelectorAll: () => wraps};
const job = JSON.parse(eval(script))[0];
assert.equal(job.title, "软件测试");
assert.equal(job.salary, "10-20K");
// 现有取法不动：前两个标签仍是 experience/education。
assert.equal(job.experience, "5天/周");
assert.equal(job.education, "3个月");
// #308：完整标签列表进入采集器，供卡片实习证据 stamped 使用。
assert.deepEqual(job.tags, ["5天/周", "3个月", "本科"]);
console.log("internship card tags DOM: ok");
'''.replace("SCRIPT", json.dumps(JS_EXTRACT_LIST)).replace("CARD_HREF", json.dumps("/job_detail/card.html"))
    result = subprocess.run([node, "-e", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "internship card tags DOM: ok"
