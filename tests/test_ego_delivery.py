from threading import Thread
from unittest.mock import patch

import pytest

from bosshunter import browser
from bosshunter.browser.ego import EgoTaskSpace, EgoTaskSpaceError


CONFIG = {"delivery": {"ego_task_space_id": 7}}


def test_delivery_scope_routes_facade_without_starting_runtime_and_restores_it():
    with patch("bosshunter.browser.EgoTaskSpace.from_config") as factory, patch("bosshunter.browser.ensure_runtime") as runtime:
        adapter = factory.return_value
        adapter.new_tab.return_value = "p2"
        with browser.delivery_browser(CONFIG):
            assert browser.new_tab("https://www.zhipin.com") == "p2"
            browser.evaluate("p2", "document.title")
            browser.click_at("p2", "1,2")
            browser.type_text("p2", "example")
            browser.press_key("p2", "SelectAll")
            browser.get_page_info("p2")
            browser.close_tab("p2")
        factory.assert_called_once_with(CONFIG, section="delivery")
        adapter.check.assert_called_once()
        adapter.evaluate.assert_called_once_with("p2", "document.title", 30)
        runtime.assert_not_called()
        runtime.return_value = False
        assert browser.new_tab("about:blank") is None
        runtime.assert_called_once()


def test_default_delivery_does_not_inherit_collection_space():
    assert EgoTaskSpace.from_config({"collection": {"ego_task_space_id": 19}}, section="delivery") is None


@pytest.mark.parametrize("value", [False, True, 0, -1, "7", 7.5])
def test_invalid_delivery_space_fails_closed(value):
    with patch("bosshunter.browser.ensure_runtime") as runtime, pytest.raises(ValueError, match="delivery.ego_task_space_id"):
        with browser.delivery_browser({"delivery": {"ego_task_space_id": value}}):
            browser.new_tab("about:blank")
    runtime.assert_not_called()


def test_unavailable_space_does_not_fall_back_to_runtime():
    with patch.object(EgoTaskSpace, "check", side_effect=EgoTaskSpaceError("user control")), patch("bosshunter.browser.ensure_runtime") as runtime:
        with pytest.raises(EgoTaskSpaceError):
            with browser.delivery_browser(CONFIG):
                browser.new_tab("about:blank")
        runtime.assert_not_called()


def test_delivery_scope_is_nested_and_does_not_leak_to_other_threads():
    with patch("bosshunter.browser.EgoTaskSpace.from_config") as factory, patch("bosshunter.browser.ensure_runtime", return_value=False):
        adapter = factory.return_value
        adapter.new_tab.return_value = "p2"
        other = []
        with browser.delivery_browser(CONFIG):
            with browser.delivery_browser(CONFIG):
                assert browser.new_tab("about:blank") == "p2"
            thread = Thread(target=lambda: other.append(isinstance(browser._client(), browser.RuntimeClient)))
            thread.start()
            thread.join()
            assert browser.new_tab("about:blank") == "p2"
        assert other == [True]
        adapter.check.assert_called_once()


def test_sender_and_monitor_entrypoints_use_delivery_scope(tmp_path):
    from bosshunter.executor import monitor, sender
    from threading import Event

    stopped = Event()
    stopped.set()
    with patch.object(EgoTaskSpace, "check") as check, patch.object(EgoTaskSpace, "_call", return_value=True), patch("bosshunter.browser.ensure_runtime") as runtime:
        assert sender.send_greetings({**CONFIG, "_workbench_stop_event": stopped}, db_path=tmp_path / "jobs.db") == 0
        assert monitor.monitor_and_send_resumes({**CONFIG, "_workbench_stop_event": stopped})["replied"] == 0
        monitor.close_monitor_chat_target({**CONFIG, "_monitor_runtime_state": {"chat_target_id": "p3"}})
    assert check.call_count == 2
    runtime.assert_not_called()


def test_monitor_preflight_uses_delivery_space_only():
    from bosshunter.web.preflight import _check_workflow_browser

    with patch.object(EgoTaskSpace, "check") as check, patch("bosshunter.web.preflight.check_browser_connection") as chrome:
        checks = _check_workflow_browser("monitor", CONFIG, None)
    check.assert_called_once()
    chrome.assert_not_called()
    assert checks[0]["status"] == "pass"


def test_ego_delivery_bridge_covers_real_input_and_page_info():
    adapter = EgoTaskSpace(7)
    with patch.object(adapter, "_call", return_value=True) as call:
        assert adapter.click_at("p2", "10,20")
        call.assert_called_with("click_at", label="p2", selector="10,20")
        adapter.info("p2")
        call.assert_called_with("info", label="p2")


def test_monitor_cancellable_page_reads_keep_delivery_backend():
    from threading import Event
    from bosshunter.cancellation import run_cancellable

    with patch("bosshunter.browser.EgoTaskSpace.from_config") as factory, patch("bosshunter.browser.ensure_runtime") as runtime:
        factory.return_value.info.return_value = {"ready": "complete"}
        config = {**CONFIG, "_workbench_stop_event": Event()}
        with browser.delivery_browser(config):
            assert run_cancellable(lambda: browser.get_page_info("p3"), config) == {"ready": "complete"}
        factory.return_value.info.assert_called_once_with("p3")
        runtime.assert_not_called()


def test_monitor_reply_scan_updates_replied_using_ego(tmp_path):
    from bosshunter.db import get_db, insert_job, update_job_status
    from bosshunter.executor import monitor

    path = tmp_path / "jobs.db"
    job = {"id": "fixture", "company": "Example", "title": "Engineer", "hr_name": "HR", "source_platform": "boss"}
    db = get_db(path)
    insert_job(db, job)
    update_job_status(db, "fixture", "sent")
    db.close()
    conversation = {"company": "Example", "hr_name": "HR", "has_reply": True, "last_direction": "hr", "last_message": "请介绍一下项目"}
    with (
        patch("bosshunter.browser.EgoTaskSpace.from_config") as factory,
        patch("bosshunter.browser.ensure_runtime") as runtime,
        patch.object(monitor, "get_db", side_effect=lambda: get_db(path)),
        patch.object(monitor, "_wait_or_stop", return_value=False),
        patch.object(monitor, "_wait_for_page_or_stop", return_value=True),
    ):
        adapter = factory.return_value
        adapter.new_tab.return_value = "p3"
        adapter.evaluate.side_effect = lambda target, expression, timeout=30: [conversation] if expression == monitor.JS_EXTRACT_CHAT_LIST else {"risk": None}
        found = monitor.check_replies(CONFIG)
        assert found[0]["job"]["id"] == "fixture"
        adapter.new_tab.assert_called_once()
        adapter.close_tab.assert_called_once_with("p3")
        runtime.assert_not_called()
    db = get_db(path)
    assert db.execute("SELECT status FROM jobs WHERE id='fixture'").fetchone()["status"] == "replied"
    assert db.execute("SELECT COUNT(*) FROM history WHERE action='hr_reply_detected'").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM history WHERE action='sent'").fetchone()[0] == 0
    db.close()
