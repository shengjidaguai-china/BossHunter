"""Temporary DB and read-only risk responses for legacy offline browser fakes."""
import json
from pathlib import Path
import sqlite3
from unittest.mock import Mock

from bosshunter.collection.safety import PAGE_RISK_SCRIPT
from bosshunter.db import get_db


def install_safety_fixtures(monkeypatch, collector_cls, browser_cls):
    connections = []
    original_init = collector_cls.__init__
    original_browser_init = browser_cls.__init__

    def collector_init(self, *args, **kwargs):
        # Preserve explicit None to exercise the new fail-closed contract.
        if "safety_conn" not in kwargs or (kwargs["safety_conn"] is not None and not isinstance(kwargs["safety_conn"], sqlite3.Connection)):
            conn = get_db(Path(":memory:"))
            connections.append(conn)
            kwargs["safety_conn"] = conn
        original_init(self, *args, **kwargs)

    def browser_init(self, *args, **kwargs):
        original_browser_init(self, *args, **kwargs)
        evaluate = self.evaluate

        def evaluate_with_risk(target, script, **options):
            if script == PAGE_RISK_SCRIPT:
                return json.dumps({"collection_risk": ""})
            return evaluate(target, script, **options)

        self.evaluate = Mock(side_effect=evaluate_with_risk)

    monkeypatch.setattr(collector_cls, "__init__", collector_init)
    monkeypatch.setattr(browser_cls, "__init__", browser_init)
    return connections
