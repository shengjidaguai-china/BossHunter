import sqlite3
from unittest.mock import patch

import pytest

from bosshunter import db as job_db


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "jobs.db"
    conn = job_db.get_db(path)
    try:
        yield conn, path
    finally:
        conn.close()


def add_job(conn, job_id, status="pending", *, deleted=False):
    conn.execute(
        "INSERT INTO jobs (id, title, company, status, deleted_at) VALUES (?, 'Developer', 'Example', ?, ?)",
        (job_id, status, "2026-09-30 00:00:00" if deleted else None),
    )
    conn.commit()


def statuses(conn):
    return dict(conn.execute("SELECT id, status FROM jobs"))


def history(conn):
    return [dict(row) for row in conn.execute("SELECT job_id, action, detail FROM history ORDER BY id")]


@pytest.mark.parametrize("target", ["ready", "filtered", "skipped", "rejected"])
def test_manual_status_updates_active_job_and_history(database, target):
    conn, _ = database
    add_job(conn, "active")

    result = job_db.update_jobs_manual_status(conn, ["active"], target)

    assert result == {"requested_count": 1, "affected_count": 1, "unchanged": []}
    assert statuses(conn) == {"active": target}
    assert history(conn) == [{
        "job_id": "active", "action": "status_changed",
        "detail": f"用户手动将状态从 pending 修改为 {target}",
    }]
    assert not conn.in_transaction


@pytest.mark.parametrize("protected", ["sent", "replied", "resume_sent", "needs_resume", "follow_up_sent"])
def test_manual_status_rejects_whole_batch_with_protected_job(database, protected):
    conn, _ = database
    add_job(conn, "active")
    add_job(conn, "protected", protected)

    with pytest.raises(ValueError):
        job_db.update_jobs_manual_status(conn, ["active", "protected"], "ready")

    assert statuses(conn) == {"active": "pending", "protected": protected}
    assert history(conn) == []
    assert not conn.in_transaction


@pytest.mark.parametrize("deleted_status", ["pending", "ready"])
def test_manual_status_rejects_deleted_job_even_when_target_is_unchanged(database, deleted_status):
    conn, _ = database
    add_job(conn, "active")
    add_job(conn, "deleted", deleted_status, deleted=True)

    with pytest.raises(ValueError):
        job_db.update_jobs_manual_status(conn, ["active", "deleted"], "ready")

    assert statuses(conn) == {"active": "pending", "deleted": deleted_status}
    assert history(conn) == []
    assert not conn.in_transaction


def test_manual_status_missing_job_aborts_whole_batch(database):
    conn, _ = database
    add_job(conn, "active")

    with pytest.raises(ValueError):
        job_db.update_jobs_manual_status(conn, ["active", "missing"], "ready")

    assert statuses(conn) == {"active": "pending"}
    assert history(conn) == []
    assert not conn.in_transaction


def test_manual_status_deduplicates_ids_and_does_not_log_noop(database):
    conn, _ = database
    add_job(conn, "active")
    add_job(conn, "unchanged", "ready")

    result = job_db.update_jobs_manual_status(conn, ["active", "active", "unchanged"], "ready")

    assert result == {"requested_count": 2, "affected_count": 1, "unchanged": ["unchanged"]}
    assert statuses(conn) == {"active": "ready", "unchanged": "ready"}
    assert [row["job_id"] for row in history(conn)] == ["active"]


@pytest.mark.parametrize("target", ["sent", "", "invalid"])
def test_manual_status_rejects_invalid_target_without_writes(database, target):
    conn, _ = database
    add_job(conn, "active")

    with pytest.raises(ValueError):
        job_db.update_jobs_manual_status(conn, ["active"], target)

    assert statuses(conn) == {"active": "pending"}
    assert history(conn) == []
    assert not conn.in_transaction


@pytest.mark.parametrize("concurrent_status", ["sent", "replied"])
def test_manual_status_serializes_validation_with_other_database_writers(database, concurrent_status):
    conn, path = database
    add_job(conn, "active")
    other = sqlite3.connect(path, timeout=0)
    read_rows = job_db._job_rows_by_ids
    concurrent_write_succeeded = []

    def read_then_try_external_update(*args, **kwargs):
        rows = read_rows(*args, **kwargs)
        # Model a separate CLI/monitor connection writing after the status read.
        try:
            other.execute("UPDATE jobs SET status = ? WHERE id = 'active'", (concurrent_status,))
            other.commit()
            concurrent_write_succeeded.append(True)
        except sqlite3.OperationalError as exc:
            other.rollback()
            assert "locked" in str(exc)
            concurrent_write_succeeded.append(False)
        return rows

    try:
        with patch.object(job_db, "_job_rows_by_ids", side_effect=read_then_try_external_update):
            job_db.update_jobs_manual_status(conn, ["active"], "ready")

        assert concurrent_write_succeeded == [False], "A committed send/reply must not be overwritten"
        # The other writer can commit after the manual operation releases its lock.
        other.execute("UPDATE jobs SET status = ? WHERE id = 'active'", (concurrent_status,))
        other.commit()
        assert statuses(conn) == {"active": concurrent_status}
    finally:
        other.close()


def test_manual_status_rolls_back_batch_and_history_if_any_update_affects_no_row(database):
    conn, _ = database
    add_job(conn, "first")
    add_job(conn, "blocked")
    conn.execute("""
        CREATE TEMP TRIGGER skip_one_status_update BEFORE UPDATE OF status ON jobs
        WHEN OLD.id = 'blocked' BEGIN SELECT RAISE(IGNORE); END
    """)

    with pytest.raises(ValueError):
        job_db.update_jobs_manual_status(conn, ["first", "blocked"], "ready")

    assert statuses(conn) == {"first": "pending", "blocked": "pending"}
    assert history(conn) == []
    assert not conn.in_transaction
