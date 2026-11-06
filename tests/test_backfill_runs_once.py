"""Guards that the v1_4 data backfill runs once per database instead of on every connection.

`get_db()` is called by every request handler and task worker. `_migrate_v1_4`
keeps the original value when no keyword matches (and `recruitment_type`
defaults to 'unknown', which its CASE also returns), so every row stayed
eligible for its WHERE clause. The backfill therefore rewrote the whole `jobs`
table on each new connection, which both slows requests as the job pool grows
and races with concurrent writers.
"""

import sqlite3

import bosshunter.db as db_module
from bosshunter.db import get_db


LEGACY_SCHEMA = """
CREATE TABLE jobs (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, salary TEXT, city TEXT,
    experience TEXT, jd TEXT, hr_name TEXT, hr_title TEXT, hr_active TEXT, company_size TEXT,
    company_industry TEXT, url TEXT, score INTEGER DEFAULT 0, score_reason TEXT, greeting TEXT,
    status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
    action TEXT NOT NULL, detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
    detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _build_legacy_database(db_path):
    raw = sqlite3.connect(db_path)
    try:
        raw.executescript(LEGACY_SCHEMA)
        raw.execute(
            "INSERT INTO jobs (id, title, company, jd, status, score, greeting) "
            "VALUES ('campus', '产品经理', '某公司', '要求本科及以上学历，2027届校招', 'ready', 80, '你好')"
        )
        raw.execute(
            "INSERT INTO jobs (id, title, company, jd, status, score, greeting) "
            "VALUES ('social', '算法工程师', '另一公司', '硕士优先，社招', 'ready', 85, '您好')"
        )
        raw.commit()
    finally:
        raw.close()


def _backfill_runs(conn):
    return [
        row[0]
        for row in conn.execute("SELECT name FROM schema_migrations WHERE name = 'v1_4'").fetchall()
    ]


def test_backfill_is_recorded_after_first_open(tmp_path):
    db = get_db(tmp_path / "first.db")
    try:
        assert _backfill_runs(db) == ["v1_4"]
    finally:
        db.close()


def test_reopening_database_does_not_rewrite_jobs(tmp_path, monkeypatch):
    db_path = tmp_path / "reopen.db"
    first = get_db(db_path)
    try:
        first.execute(
            "INSERT INTO jobs (id, title, company, jd, status) "
            "VALUES ('a', '产品经理', '某公司', '负责AI产品设计', 'ready')"
        )
        first.commit()
    finally:
        first.close()

    calls = []
    original = db_module._migrate_v1_4
    monkeypatch.setattr(
        db_module, "_migrate_v1_4", lambda conn: (calls.append("v1_4"), original(conn))[1]
    )

    reopened = get_db(db_path)
    try:
        assert calls == ["v1_4"]
        assert reopened.total_changes == 0
    finally:
        reopened.close()


def test_skipped_backfill_is_retried_on_the_next_connection(tmp_path, monkeypatch):
    db_path = tmp_path / "retry.db"
    with monkeypatch.context() as scoped:
        scoped.setattr(db_module, "_migrate_v1_4", lambda conn: None)
        get_db(db_path).close()

    db = get_db(db_path)
    try:
        assert _backfill_runs(db) == ["v1_4"]
    finally:
        db.close()


def test_legacy_database_is_upgraded_once_and_keeps_inferred_fields(tmp_path):
    db_path = tmp_path / "legacy.db"
    _build_legacy_database(db_path)

    db = get_db(db_path)
    try:
        assert _backfill_runs(db) == ["v1_4"]
        rows = {
            row["id"]: (row["education"], row["recruitment_type"], row["score"])
            for row in db.execute(
                "SELECT id, education, recruitment_type, score FROM jobs"
            ).fetchall()
        }
    finally:
        db.close()

    assert rows["campus"] == ("本科", "campus", 80)
    assert rows["social"] == ("硕士", "experienced", 85)

    reopened = get_db(db_path)
    try:
        assert reopened.total_changes == 0
    finally:
        reopened.close()
