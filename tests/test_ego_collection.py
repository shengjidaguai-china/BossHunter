from unittest.mock import patch

import pytest

from bosshunter.collection.orchestrator import CollectionOrchestrator
from bosshunter.web.preflight import collect_preflight_checks


OPTIONS = {"platform_order": ["boss"], "platforms": {"boss": {"cities": ["无锡"], "keywords": ["AI"]}}}


def test_collect_preflight_uses_ego_without_probing_chrome():
    with patch("bosshunter.web.preflight.check_browser_connection") as chrome:
        checks = collect_preflight_checks("collect", {"collection": {"ego_task_space_id": False}}, OPTIONS)
    chrome.assert_not_called()
    assert any(check["status"] == "error" and "ego_task_space_id" in check["message"] for check in checks)


def test_invalid_ego_space_fails_before_opening_the_collection_database(tmp_path):
    db_path = tmp_path / "jobs.db"
    with patch("bosshunter.collection.orchestrator.BossCollector", side_effect=RuntimeError("unexpected collector")), pytest.raises(ValueError, match="ego_task_space_id"):
        CollectionOrchestrator({"collection": {"ego_task_space_id": "new-space"}}, db_path=db_path).run(OPTIONS)
    assert not db_path.exists()


def test_collect_passes_task_space_to_default_collector(tmp_path):
    from bosshunter.collection.models import PlatformCollectionResult

    with (
        patch("bosshunter.collection.orchestrator.EgoTaskSpace") as adapter,
        patch("bosshunter.collection.orchestrator.BossCollector") as collector,
    ):
        collector.return_value.collect.return_value = PlatformCollectionResult("boss", "completed")
        config = {"collection": {"ego_task_space_id": 7}}
        result = CollectionOrchestrator(config, db_path=tmp_path / "jobs.db").run(OPTIONS)

    adapter.from_config.return_value.check.assert_called_once()
    assert collector.call_args.kwargs["browser"] is adapter.from_config.return_value
    assert result["platforms"]["boss"]["status"] == "completed_with_shortage"
