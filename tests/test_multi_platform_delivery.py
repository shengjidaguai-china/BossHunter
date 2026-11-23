from threading import Event
from unittest.mock import patch

import pytest

from bosshunter.db import get_db
from bosshunter.executor import platform_delivery as delivery

from bosshunter.collection.capabilities import delivery_capabilities, platform_supports


def test_delivery_requires_local_opt_in_and_existing_space():
    for space, enabled in [(None, True), (7, False), (True, True), (7, "true")]:
        config = {"delivery": {"ego_task_space_id": space, "platforms": {"liepin": {"enabled": enabled}}}}
        assert not platform_supports("liepin", "deliver", config)
        assert not platform_supports("liepin", "monitor", config)


def test_delivery_capabilities_explain_confirmed_action():
    config = {"delivery": {"ego_task_space_id": 7, "platforms": {"liepin": {"enabled": True}}}}
    caps = delivery_capabilities(config)
    assert caps["liepin"] == {"enabled": True, "action_id": "apply_resume", "action_label": "投递简历"}
    assert caps["boss"]["action_id"] == "greeting"
    assert caps["51job"]["enabled"] is False

@pytest.fixture
def db(tmp_path):
    conn = get_db(tmp_path / "test.db")
    yield conn
    conn.close()


def job(db, platform, identifier, company):
    host = {"liepin": "www.liepin.com", "zhilian": "www.zhaopin.com", "boss": "www.zhipin.com"}[platform]
    record = {"id": identifier, "source_platform": platform, "company": company, "title": "工程师",
              "url": f"https://{host}/job/{identifier}"}
    db.execute("""INSERT INTO jobs(id, source_platform, company, title, url, status)
                  VALUES (:id, :source_platform, :company, :title, :url, 'approved')""", record)
    db.commit()
    return record


def config(job_id, platform="liepin", *, cross_platform_dedup=False):
    return {"delivery": {"ego_task_space_id": 7, "cross_platform_dedup": cross_platform_dedup,
                         "platforms": {"liepin": {"enabled": True}, "zhilian": {"enabled": True}}},
            "_workbench_job_ids": [job_id], "_workbench_expected_platforms": {job_id: platform},
            "_workbench_expected_actions": {job_id: "apply_resume"}}


def test_cross_platform_company_dedup_includes_boss_history(db):
    first = job(db, "boss", "old", "Ａ 公司")
    second = job(db, "liepin", "new", "a公司")
    db.execute("INSERT INTO history(job_id, action) VALUES (?, 'sent')", (first["id"],))
    db.commit()
    assert delivery.reserve_delivery(db, second, config("new", cross_platform_dedup=True)) == "duplicate_company"


def test_quota_independent_across_platforms(db):
    liepin = job(db, "liepin", "one", "公司甲")
    zhilian = job(db, "zhilian", "two", "公司乙")
    cfg = config("two", "zhilian")
    cfg["delivery"]["platforms"]["liepin"]["daily_limit"] = 1
    db.execute("INSERT INTO history(job_id, action) VALUES (?, 'sent')", (liepin["id"],))
    db.commit()
    assert delivery.daily_quota(cfg, "zhilian") == 10
    assert delivery.reserve_delivery(db, liepin, cfg) == "daily_limit"
    assert delivery.reserve_delivery(db, zhilian, cfg) is None
    assert delivery.sent_today(db, "zhilian") == 1


def test_first_send_requires_single_selected_job_and_no_parallel_pilot(db):
    first = job(db, "liepin", "one", "公司甲")
    second = job(db, "zhilian", "two", "公司乙")
    cfg = config("one")
    cfg["_workbench_job_ids"].append("two")
    assert delivery.reserve_delivery(db, first, cfg) == "single_confirmed_pilot_required"
    assert delivery.reserve_delivery(db, first, config("one")) is None
    assert delivery.reserve_delivery(db, second, config("two", "zhilian")) == "pilot_pending"


def test_cancel_and_risk_do_not_submit_or_retry(db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    record = job(db, "liepin", "one", "公司甲")
    cfg = config("one")
    stop = Event()
    cfg["_workbench_stop_event"] = stop
    stop.set()
    with patch.object(delivery.EgoTaskSpace, "from_config") as factory:
        browser = factory.return_value
        assert delivery.submit_resume(db, record, cfg)["error"] == "stopped"
        browser.new_tab.assert_not_called()
        stop.clear()
        browser.new_tab.return_value = "tab"
        browser.evaluate.return_value = {"error": "captcha"}
        assert delivery.submit_resume(db, record, cfg)["error"] == "captcha"
        assert browser.evaluate.call_count == 1
        assert "liepin 检测到 captcha" in (tmp_path / "需要扫码.txt").read_text()
        assert "任务空间 7" in (tmp_path / "需要扫码.txt").read_text()


def test_missing_ego_never_uses_runtime_or_browser(db):
    record = job(db, "liepin", "one", "公司甲")
    with patch.object(delivery.EgoTaskSpace, "from_config") as factory:
        assert delivery.submit_resume(db, record, {})["error"] == "platform_disabled"
        factory.assert_not_called()


def test_readonly_reply_identity_and_event_idempotency(db):
    record = job(db, "liepin", "one", "公司甲")
    db.execute("UPDATE jobs SET status='sent'")
    db.commit()
    incoming = {"direction": "incoming", "message": "可以聊一下吗", "url": record["url"]}
    for row in [{**incoming, "direction": "outgoing"}, {**incoming, "url": "https://www.liepin.com/job/other"}]:
        assert delivery.record_replies(db, "liepin", [record], [row]) == 0
    # Login prevented verifying a Liepin inbox row on the real account.
    assert delivery.record_replies(db, "liepin", [record], [incoming]) == 0
    assert db.execute("SELECT status FROM jobs").fetchone()[0] == "sent"


def test_confirmed_online_resume_uses_external_adapter_without_greeting(db, tmp_path):
    from bosshunter.executor.sender import send_greetings
    record = job(db, "liepin", "pilot", "公司甲")
    db.execute("UPDATE jobs SET status='approved', greeting_selection='pending' WHERE id='pilot'")
    db.commit()
    cfg = config("pilot")
    cfg["_workbench_expected_actions"] = {"pilot": "apply_resume"}
    with patch("bosshunter.browser.ego.EgoTaskSpace.check"), patch.object(
        delivery, "submit_resume", return_value={"success": True}
    ) as submit, patch("bosshunter.executor.sender._send_greeting_once") as boss_send:
        assert send_greetings(cfg, force=True, db_path=tmp_path / "test.db") == 1
        assert submit.call_args.args[1]["id"] == record["id"]
        boss_send.assert_not_called()
    assert db.execute("SELECT status FROM jobs").fetchone()[0] == "sent"
    assert [r[0] for r in db.execute("SELECT action FROM history")] == ["sent"]


def test_second_probe_after_cancel_never_submits(db):
    record = job(db, "liepin", "one", "公司甲")
    cfg = config("one")
    stop = Event()
    cfg["_workbench_stop_event"] = stop
    def probe(*args):
        stop.set()
        return {"found": True}
    with patch.object(delivery.EgoTaskSpace, "from_config") as factory:
        browser = factory.return_value
        browser.evaluate.side_effect = probe
        result = delivery.submit_resume(db, record, cfg)
        assert result["error"] == "stopped"
        assert result["uncertain"] is False
        assert browser.evaluate.call_count == 1


def test_confirmed_action_change_blocks_dispatch(db, tmp_path):
    from bosshunter.executor.sender import send_greetings
    job(db, "liepin", "pilot", "公司甲")
    db.execute("UPDATE jobs SET status='approved' WHERE id='pilot'")
    db.commit()
    cfg = config("pilot")
    cfg["_workbench_expected_actions"] = {"pilot": "greeting"}
    with patch("bosshunter.browser.ego.EgoTaskSpace.check"), patch.object(delivery, "submit_resume") as submit:
        assert send_greetings(cfg, force=True, db_path=tmp_path / "test.db") == 0
        submit.assert_not_called()
    assert cfg["_workbench_send_report"]["stop_reason"] == "confirmed_action_changed"


@pytest.mark.parametrize("platform, control, label", [
    ("zhilian", "button.a-button", "立即投递"),
    ("51job", "div.apply-btn-new.big", "立即投递"),
    ("liepin", 'a[data-selector="apply-job"]', "投简历"),
])
def test_observed_dom_control_is_unique_and_receipt_required(platform, control, label):
    import json
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for offline DOM fixture")
    job_info = {"platform": platform, "origin": "https://example.test", "path": "/job/123.html",
                "title": "工程师", "company": "公司", "phase": "probe"}
    fixtures = {"expected": job_info, "selector": control, "label": label, "script": delivery._APPLY_SCRIPT}
    script = r"""
const f = FIXTURES, assert = require('node:assert/strict');
global.location = {origin:f.expected.origin, pathname:f.expected.path};
global.getComputedStyle = () => ({visibility:'visible'});
let clicked = 0;
const el = {innerText:f.label,id:'123',getClientRects:()=>[{}],getAttribute:()=>null,click:()=>clicked++};
let controls = [el];
global.document = {body:{innerText:'工程师 公司'},querySelectorAll:q => q === f.selector ? controls : []};
const run = phase => eval(f.script.replace('EXPECTED_JOB', JSON.stringify({...f.expected, phase})));
assert.deepEqual(run('probe'), {found:true});
assert.equal(clicked, 0);
controls.push(el);
assert.equal(run('submit').error, 'application_control_unverified');
assert.equal(clicked, 0);
controls = [el];
assert.deepEqual(run('submit'), {found:true});
assert.equal(clicked, 1);
assert.equal(run('receipt').receipt, false);
el.innerText = '已投递';
assert.equal(run('receipt').receipt, true);
global.location.pathname = '/different';
assert.equal(run('submit').error, 'job_identity_mismatch');
"""
    subprocess.run([node, "-"], input=script.replace("FIXTURES", json.dumps(fixtures)),
                   text=True, check=True, capture_output=True)


def test_changed_platform_with_same_action_rejected_before_dispatch(db, tmp_path):
    from bosshunter.executor.sender import send_greetings
    job(db, "liepin", "pilot", "公司甲")
    db.execute("UPDATE jobs SET status='approved' WHERE id='pilot'")
    db.commit()
    cfg = config("pilot")
    cfg["_workbench_expected_actions"] = {"pilot": "apply_resume"}
    cfg["_workbench_expected_platforms"] = {"pilot": "zhilian"}
    with patch("bosshunter.browser.ego.EgoTaskSpace.check"), patch.object(delivery, "submit_resume") as submit:
        assert send_greetings(cfg, force=True, db_path=tmp_path / "test.db") == 0
        submit.assert_not_called()
    assert cfg["_workbench_send_report"]["stop_reason"] == "confirmed_platform_changed"


def test_legacy_boss_sent_status_without_history_blocks_external_company(db):
    job(db, "boss", "old", "公司甲")
    db.execute("UPDATE jobs SET status='resume_sent' WHERE id='old'")
    db.commit()
    record = job(db, "liepin", "new", "公司甲")
    assert delivery.reserve_delivery(db, record, config("new", cross_platform_dedup=True)) == "duplicate_company"


def test_site_verified_manual_confirmation_resolves_uncertain_pilot(db):
    from bosshunter.db import mark_external_jobs_sent
    first = job(db, "liepin", "pilot", "公司甲")
    second = job(db, "zhilian", "next", "公司乙")
    assert delivery.reserve_delivery(db, first, config("pilot")) is None
    db.execute("UPDATE jobs SET status='error' WHERE id='pilot'")
    db.commit()
    mark_external_jobs_sent(db, ["pilot"], confirmed=True)
    assert delivery.sent_today(db, "liepin") == 1
    assert delivery.reserve_delivery(db, second, config("next")) is None


def test_zhilian_feedback_requires_site_job_id_title_company_and_positive_status(db):
    record = job(db, "zhilian", "local", "招聘公司")
    db.execute("UPDATE jobs SET status='sent', source_job_id='CC123J456'")
    db.commit()
    record["source_job_id"] = "CC123J456"
    row = {"url": "http://jobs.zhaopin.com/CC123J456.htm?tracking=1", "title": record["title"],
           "company": record["company"], "time": "2026-11-16 11:38:43", "message": "企业对你有意",
           "direction": "incoming", "kind": "platform_feedback"}
    for changes in ({"company": "其他公司"}, {"title": "其他职位"}, {"message": "被查看"}, {"time": ""}):
        assert delivery.record_replies(db, "zhilian", [record], [{**row, **changes}]) == 0
    assert delivery.record_replies(db, "zhilian", [record], [row]) == 1
    assert delivery.record_replies(db, "zhilian", [record], [row]) == 0
    assert "平台反馈" in db.execute("SELECT detail FROM history").fetchone()[0]


def test_duplicate_does_not_spend_last_platform_slot(db, tmp_path):
    from bosshunter.executor.sender import send_greetings
    job(db, "boss", "history", "同公司")
    job(db, "liepin", "pilot", "首投公司")
    job(db, "liepin", "duplicate", "同公司")
    job(db, "liepin", "eligible", "另一公司")
    db.execute("UPDATE jobs SET status='sent' WHERE id IN ('history','pilot')")
    db.execute("UPDATE jobs SET score=99 WHERE id='duplicate'")
    db.execute("INSERT INTO history(job_id,action,created_at) VALUES('pilot','sent','2026-01-01')")
    db.commit()
    cfg = config("duplicate", cross_platform_dedup=True)
    cfg["delivery"]["platforms"]["liepin"]["daily_limit"] = 1
    cfg["_workbench_job_ids"] = ["duplicate", "eligible"]
    cfg["_workbench_expected_platforms"] = {key: "liepin" for key in cfg["_workbench_job_ids"]}
    cfg["_workbench_expected_actions"] = {key: "apply_resume" for key in cfg["_workbench_job_ids"]}
    with patch("bosshunter.browser.ego.EgoTaskSpace.check"), patch.object(
        delivery, "submit_resume", return_value={"success": True}
    ) as submit:
        assert send_greetings(cfg, force=True, db_path=tmp_path / "test.db") == 1
        assert submit.call_args.args[1]["id"] == "eligible"
    assert cfg["_workbench_send_report"]["skipped_ids"] == {"duplicate": "duplicate_company"}


def test_rejection_after_probe_blocks_click_and_preserves_status(db, tmp_path):
    from bosshunter.executor.sender import send_greetings
    job(db, "liepin", "pilot", "公司甲")
    cfg = config("pilot")
    def reject_after_probe(*args):
        db.execute("UPDATE jobs SET status='rejected' WHERE id='pilot'")
        db.commit()
        return {"found": True}
    with patch("bosshunter.browser.ego.EgoTaskSpace.check"), patch.object(
        delivery.EgoTaskSpace, "from_config"
    ) as factory:
        browser = factory.return_value
        browser.evaluate.side_effect = reject_after_probe
        assert send_greetings(cfg, force=True, db_path=tmp_path / "test.db") == 0
        assert browser.evaluate.call_count == 1
    assert db.execute("SELECT status FROM jobs").fetchone()[0] == "rejected"
    assert db.execute("SELECT COUNT(*) FROM history").fetchone()[0] == 0


def test_failed_enabled_online_resume_without_greeting_visible(db):
    from bosshunter.db import get_jobs_with_send_errors
    job(db, "liepin", "pilot", "公司甲")
    db.execute("UPDATE jobs SET status='error'")
    db.commit()
    assert not get_jobs_with_send_errors(db)
    assert [r["id"] for r in get_jobs_with_send_errors(db, resume_platforms=("liepin",))] == ["pilot"]


def test_already_applied_report_protects_company_without_counting_pilot(db, tmp_path):
    from bosshunter.executor.sender import send_greetings
    job(db, "liepin", "pilot", "公司甲")
    cfg = config("pilot")
    with patch("bosshunter.browser.ego.EgoTaskSpace.check"), patch.object(
        delivery, "submit_resume", return_value={"success": False, "error": "already_applied"}
    ):
        assert send_greetings(cfg, force=True, db_path=tmp_path / "test.db") == 0
    assert db.execute("SELECT action FROM history").fetchone()[0] == "prior_application"
    assert delivery.first_application_pending(db)
    assert delivery.sent_today(db, "liepin") == 0
    other = job(db, "zhilian", "other", "公司甲")
    assert delivery.reserve_delivery(db, other, config("other", "zhilian", cross_platform_dedup=True)) == "duplicate_company"


def test_unverified_feedback_cannot_emit_reply_or_open_liepin(db):
    cfg = config("pilot")
    cfg["delivery"]["platforms"]["51job"] = {"enabled": True}
    with patch.object(delivery.EgoTaskSpace, "from_config") as factory:
        assert delivery.observe_replies(db, cfg, "liepin", [{"id": "ignored"}]) == 0
        factory.assert_not_called()
        browser = factory.return_value
        browser.new_tab.return_value = "owned"
        browser.evaluate.return_value = {"state": "unverified_rows", "rows": [{"direction": "incoming"}]}
        assert delivery.observe_replies(db, cfg, "51job", [{"id": "ignored"}]) == 0
        browser.new_tab.assert_called_once_with("https://i.51job.com/userset/my_apply.php")
        browser.close_tab.assert_called_once_with("owned")
        assert browser.evaluate.call_count == 1
    assert db.execute("SELECT COUNT(*) FROM history").fetchone()[0] == 0


def test_zhi_feedback_guard_halts_before_reading_or_mutating_jobs(db, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cfg = config("pilot", "zhilian")
    with patch.object(delivery.EgoTaskSpace, "from_config") as factory:
        browser = factory.return_value
        browser.evaluate.return_value = "captcha"
        with pytest.raises(delivery.PlatformSafetyStop, match="captcha"):
            delivery.observe_replies(db, cfg, "zhilian", [{"id": "ignored"}])
        assert browser.evaluate.call_count == 1
    assert "zhilian" in (tmp_path / "需要扫码.txt").read_text()


def test_monitoring_capabilities_match_verified_event_parsers():
    cfg = config("pilot")
    cfg["delivery"]["platforms"]["51job"] = {"enabled": True}
    assert platform_supports("zhilian", "monitor", cfg)
    assert platform_supports("51job", "inspect_feedback", cfg)
    assert not platform_supports("51job", "monitor", cfg)
    assert not platform_supports("liepin", "monitor", cfg)
    assert not platform_supports("liepin", "inspect_feedback", cfg)


def test_external_full_preflight_never_falls_back_to_runtime():
    from bosshunter.web.preflight import _check_workflow_browser
    with patch("bosshunter.web.preflight.normalize_collection_options", return_value={"platform_order": ["liepin"]}), patch(
        "bosshunter.web.preflight.check_browser_connection"
    ) as runtime, patch("bosshunter.browser.ego.EgoTaskSpace.check") as ego_check:
        assert _check_workflow_browser("full", {}, {})[0]["status"] == "error"
        assert _check_workflow_browser("full", config("pilot"), {})[0]["status"] == "pass"
        runtime.assert_not_called()
        ego_check.assert_called_once()


@pytest.mark.parametrize(("prior", "candidate", "duplicate"), [
    ("合成科技有限公司", "合成科技", True),
    ("合成（ＡＩ）技术股份有限公司", "合成-ai 技术", True),
    ("合成科技（上海）有限公司", "合成科技（苏州）有限公司", False),
    ("合成科技有限公司", "合成科技文化传媒有限责任公司", False),
])
def test_complete_company_names_across_platforms(db, prior, candidate, duplicate):
    job(db, "boss", "historical", prior)
    db.execute("UPDATE jobs SET status='sent' WHERE id='historical'")
    db.commit()
    target = job(db, "liepin", "pilot", candidate)
    expected = "duplicate_company" if duplicate else None
    assert delivery.reserve_delivery(db, target, config("pilot", cross_platform_dedup=True)) == expected


@pytest.mark.parametrize("enabled", [None, False, True])
@pytest.mark.parametrize("action", ["sent", "manual_sent", "delivery_reserved", "prior_application"])
def test_cross_platform_company_dedup_switch(db, enabled, action):
    job(db, "boss", "old", "同公司有限公司")
    db.execute("INSERT INTO history(job_id, action) VALUES ('old', ?)", (action,))
    db.commit()
    target = job(db, "liepin", "new", "同公司")
    cfg = config("new", cross_platform_dedup=enabled)
    if enabled is None:
        cfg["delivery"].pop("cross_platform_dedup")
    assert delivery.reserve_delivery(db, target, cfg) == ("duplicate_company" if enabled else None)


@pytest.mark.parametrize("enabled", [None, False, True])
@pytest.mark.parametrize("platform", ["boss", "liepin"])
@pytest.mark.parametrize("action", ["sent", "manual_sent", "delivery_reserved", "prior_application"])
def test_same_platform_job_history_always_blocks_retry(db, enabled, platform, action):
    target = job(db, platform, "same", "同公司")
    # A previous confirmed external application lets this test isolate dedup from the pilot gate.
    job(db, "zhilian", "pilot", "首投公司")
    db.execute("INSERT INTO history(job_id, action) VALUES ('pilot', 'sent')")
    db.execute("INSERT INTO history(job_id, action) VALUES ('same', ?)", (action,))
    db.commit()
    cfg = config("same", platform, cross_platform_dedup=enabled)
    if enabled is None:
        cfg["delivery"].pop("cross_platform_dedup")
    assert delivery.reserve_delivery(db, target, cfg) == "duplicate_company"
    assert db.execute("SELECT COUNT(*) FROM history WHERE job_id='same'").fetchone()[0] == 1


@pytest.mark.parametrize("enabled", [False, True])
def test_uncertain_first_application_still_blocks_automatic_retry(db, enabled):
    target = job(db, "liepin", "same", "同公司")
    cfg = config("same", cross_platform_dedup=enabled)
    assert delivery.reserve_delivery(db, target, cfg) is None
    assert delivery.reserve_delivery(db, target, cfg) == "pilot_pending"
    assert db.execute("SELECT COUNT(*) FROM history WHERE job_id='same'").fetchone()[0] == 1


@pytest.mark.parametrize("enabled", [None, False, True])
def test_cross_platform_dedup_config_loading(tmp_path, enabled):
    from bosshunter.config import DEFAULTS, load_config
    path = tmp_path / "config.yaml"
    path.write_text("delivery: {}\n" if enabled is None else
                    f"delivery:\n  cross_platform_dedup: {str(enabled).lower()}\n")
    assert DEFAULTS["delivery"]["cross_platform_dedup"] is False
    assert load_config(path)["delivery"]["cross_platform_dedup"] is (enabled is True)
