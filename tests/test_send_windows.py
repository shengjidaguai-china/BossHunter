"""Offline regression tests: no browser connection or real outbound actions."""

from datetime import datetime
from threading import Event
from unittest.mock import patch

import pytest
import yaml

from bosshunter.config import load_config, save_config
from bosshunter.db import get_db, insert_job, update_job_greeting, update_job_status
from bosshunter.executor import monitor, sender
from bosshunter.throttle import SendWindowChecker
from bosshunter.web.tasks import WorkbenchTaskRunner

INVALID_WINDOWS = [
    None, {}, "09:00-16:00", [None], [123], [""], ["garbage"],
    ["9:00-16:00"], ["09:00:00-16:00"], ["09:00-24:00"], ["09:60-16:00"],
    ["09:00-09:00"], ["16:00-09:00"], ["23:00-01:00"],
    ["09:00-12:00", "09:00-12:00"], ["09:00-12:00", "11:00-16:00"],
    ["09:00-16:00", "10:00-12:00"], ["09:00-16:00", "bad"],
]


@pytest.mark.parametrize("windows", INVALID_WINDOWS)
def test_invalid_windows_fail_closed_before_write_or_execution(tmp_path, windows):
    path = tmp_path / "config.yaml"
    config = {"throttle": {"send_windows": windows}}
    with pytest.raises(ValueError):
        SendWindowChecker(windows)
    with pytest.raises(ValueError):
        save_config(config, path)
    assert not path.exists()
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)
    executed = Event()
    runner = WorkbenchTaskRunner({"monitor": lambda *_: executed.set()})
    with pytest.raises(ValueError):
        runner.start("monitor", config)
    assert not executed.is_set()
    assert runner.status()["tasks"] == []
    with patch.object(sender, "get_db") as database:
        with pytest.raises(ValueError):
            sender.send_greetings(config, force=True)
        database.assert_not_called()


@pytest.mark.parametrize("minute,active,finished", [
    (539, False, False), (540, True, False), (719, True, False), (720, False, False),
    (839, False, False), (840, True, False), (959, True, False), (960, False, True),
])
def test_boundaries_and_final_deadline(minute, active, finished):
    checker = SendWindowChecker(["14:00-16:00", "09:00-12:00"])
    with patch.object(checker, "_current_minutes", return_value=minute):
        assert checker.is_active() is active
        assert checker.latest_end_time_reached() is finished
    # The scheduler deliberately uses naive local wall-clock time, as the YAML has no timezone.
    assert checker.latest_end_datetime(datetime(2026, 10, 8, 10, 0, 59)) == datetime(2026, 10, 8, 16)  # noqa: DTZ001


def test_adjacent_and_empty_windows_keep_legacy_behavior(tmp_path):
    checker = SendWindowChecker([" 12:00 - 16:00 ", "09:00-12:00"])
    with patch.object(checker, "_current_minutes", return_value=720):
        assert checker.is_active()
    empty = SendWindowChecker([])
    assert empty.is_active()
    assert empty.latest_end_datetime() is None
    assert not empty.latest_end_time_reached()
    path = tmp_path / "config.yaml"
    save_config({"throttle": {"send_windows": []}}, path)
    assert load_config(path)["throttle"]["send_windows"] == []


def test_yaml_round_trip_and_last_window_task_admission(tmp_path):
    windows = ["14:00-16:00", "09:00-12:00"]
    path = tmp_path / "config.yaml"
    save_config({"throttle": {"send_windows": windows}}, path)
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["throttle"]["send_windows"] == windows
    config = load_config(path)
    assert config["throttle"]["send_windows"] == windows
    executed = Event()
    runner = WorkbenchTaskRunner({"monitor": lambda *_: executed.set()})
    now = datetime(2026, 10, 8, 16)  # noqa: DTZ001 - same local wall-clock boundary as the scheduler
    with patch("bosshunter.web.tasks.datetime") as clock, patch("bosshunter.throttle.datetime") as window_clock:
        clock.now.return_value = now
        window_clock.now.return_value = now
        result = runner.start("monitor", config)
    assert result["status"] == "stopped"
    assert result["deadline_at"] == "2026-10-08T16:00:00"
    assert not executed.is_set()


def test_sender_rechecks_after_delay_and_leaves_deferred_job_ready(tmp_path):
    db_path = tmp_path / "jobs.db"
    db = get_db(db_path)
    for number in range(2):
        job_id = str(number)
        insert_job(db, {"id": job_id, "title": "Test", "company": "Test", "url": "https://www.zhipin.com/test"})
        update_job_status(db, job_id, "ready")
        update_job_greeting(db, job_id, "Test greeting")
    db.close()
    config = {"throttle": {"send_windows": ["09:00-12:00", "14:00-16:00"], "day_off_probability": 0}}
    current = [719]
    def wait(*_):
        current[0] = 720
        return False
    with patch.object(SendWindowChecker, "_current_minutes", side_effect=lambda: current[0]), \
            patch.object(sender.RequestThrottle, "wait", side_effect=wait), \
            patch.object(sender, "_send_greeting_once", return_value=({"success": True}, None)) as outbound:
        assert sender.send_greetings(config, db_path=db_path) == 1
    assert outbound.call_count == 1
    assert config["_workbench_send_report"]["stop_reason"] == "outside_window"
    assert config["_workbench_send_report"]["failed_count"] == 0
    db = get_db(db_path)
    assert db.execute("SELECT count(*) FROM jobs WHERE status='ready'").fetchone()[0] == 1
    db.close()


def test_browsing_across_boundary_cannot_click_contact():
    checker = SendWindowChecker(["09:00-12:00"])
    current = [719]
    def wait(*_):
        current[0] = 720
        return False
    with patch.object(checker, "_current_minutes", side_effect=lambda: current[0]), \
            patch.object(sender, "get_page_targets", return_value=[]), \
            patch.object(sender, "new_tab", return_value="test-tab"), \
            patch.object(sender, "close_tab"), \
            patch.object(sender, "_sleep_or_stop", side_effect=wait), \
            patch.object(sender, "evaluate", return_value={"success": True}) as browser:
        result, _ = sender._send_greeting_once(
            {"url": "https://www.zhipin.com/test"}, "test", {"_send_window_checker": checker},
        )
    assert result["error"] == "outside_window"
    # The only evaluation reads page state; no contact click or message submission.
    assert browser.call_count == 1


def test_monitor_cannot_send_after_generation_crosses_window_end():
    with patch.object(SendWindowChecker, "_current_minutes", return_value=960), \
            patch.object(monitor, "evaluate") as outbound:
        assert not monitor._send_message_in_chat("test", "test", {"throttle": {"send_windows": ["09:00-16:00"]}})
    outbound.assert_not_called()


def test_popup_detection_crossing_boundary_cannot_confirm_greeting():
    checker = SendWindowChecker(["09:00-12:00"])
    with patch.object(checker, "_current_minutes", return_value=720), \
            patch.object(sender, "_detect_greet_popup", return_value={"success": True}), \
            patch.object(sender, "_is_preset_greeting_popup", return_value=True), \
            patch.object(sender, "_confirm_preset_greeting") as confirm:
        result = sender._handle_greet_popup("test", "test", window_checker=checker)
    assert result["error"] == "outside_window"
    confirm.assert_not_called()


def test_chat_navigation_crossing_boundary_cannot_submit_message():
    checker = SendWindowChecker(["09:00-12:00"])
    current = [719]
    def navigate(*_, **kwargs):
        current[0] = 720
        return {"success": True}
    with patch.object(checker, "_current_minutes", side_effect=lambda: current[0]), \
            patch.object(sender, "get_page_targets", return_value=[]), \
            patch.object(sender, "new_tab", return_value="test-tab"), \
            patch.object(sender, "close_tab"), \
            patch.object(sender, "evaluate", return_value={"success": True}), \
            patch.object(sender, "_sleep_or_stop", return_value=False), \
            patch.object(sender, "_click_chat_button", return_value={"success": True}), \
            patch.object(sender, "_handle_greet_popup", return_value={"success": True}), \
            patch.object(sender, "_wait_for_chat_page", side_effect=navigate), \
            patch.object(sender, "_message_delivery_state", return_value="missing"), \
            patch.object(sender, "_submit_chat_message_background") as submit:
        result, _ = sender._send_greeting_once(
            {"url": "https://www.zhipin.com/test"}, "test",
            {"_send_window_checker": checker, "browse_before_greet": False},
        )
    assert result["error"] == "outside_window"
    submit.assert_not_called()
