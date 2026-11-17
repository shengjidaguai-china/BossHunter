"""Persistence for independent, recoverable AI scoring runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bosshunter.db import get_db


TERMINAL_RUN_STATUSES = {"completed", "completed_with_errors", "failed", "stopped"}


def _json_text(value: Any, default: Any) -> str:
	try:
		return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
	except (TypeError, ValueError):
		return json.dumps(default, ensure_ascii=False, separators=(",", ":"))


def _decode(value: Any, default: Any) -> Any:
	try:
		return json.loads(value) if value else default
	except (TypeError, json.JSONDecodeError):
		return default


def _public_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
	if not row:
		return None
	result = dict(row)
	result["options"] = _decode(result.pop("options_json", "{}"), {})
	result["remaining_job_ids"] = _decode(result.pop("remaining_job_ids_json", "[]"), [])
	result["progress"] = _decode(result.pop("progress_json", "{}"), {})
	result["recoverable"] = result.get("status") == "paused" and bool(result["remaining_job_ids"])
	return result


def create_scoring_run(
	db_path: Path,
	*,
	run_id: str,
	options: dict[str, Any],
	job_ids: list[str],
) -> dict[str, Any]:
	db = get_db(db_path)
	try:
		db.execute(
			"""INSERT INTO scoring_runs
               (id, status, options_json, remaining_job_ids_json, progress_json)
               VALUES (?, 'pending', ?, ?, ?)""",
			(
				run_id,
				_json_text(options, {}),
				_json_text(job_ids, []),
				_json_text({"selected": len(job_ids), "completed": 0}, {}),
			),
		)
		db.commit()
		return get_scoring_run(db_path, run_id) or {}
	finally:
		db.close()


def update_scoring_run(
	db_path: Path,
	run_id: str,
	*,
	status: str | None = None,
	task_id: str | None = None,
	remaining_job_ids: list[str] | None = None,
	progress: dict[str, Any] | None = None,
	pause_reason: str | None = None,
	error: str | None = None,
) -> dict[str, Any] | None:
	sets = ["updated_at = CURRENT_TIMESTAMP"]
	params: list[Any] = []
	for column, value in (("status", status), ("task_id", task_id), ("pause_reason", pause_reason), ("error", error)):
		if value is not None:
			# A late checkpoint must not undo an explicit request to end the run.
			if column == "status" and value != "stopped":
				sets.append("status = CASE WHEN status = 'stopping' THEN status ELSE ? END")
			else:
				sets.append(f"{column} = ?")
			params.append(str(value)[:1000])
	if remaining_job_ids is not None:
		sets.append("remaining_job_ids_json = ?")
		params.append(_json_text(remaining_job_ids, []))
	if progress is not None:
		sets.append("progress_json = ?")
		params.append(_json_text(progress, {}))
	if status in TERMINAL_RUN_STATUSES:
		sets.append("finished_at = CURRENT_TIMESTAMP")
	elif status == "running":
		sets.extend(["finished_at = NULL", "pause_reason = NULL", "error = NULL"])
	params.append(run_id)
	where = "id = ?"
	if status is not None:
		# Terminal records are immutable to late worker callbacks; retain history.
		where += " AND status NOT IN ('completed', 'completed_with_errors', 'failed', 'stopped')"
	db = get_db(db_path)
	try:
		db.execute(f"UPDATE scoring_runs SET {', '.join(sets)} WHERE {where}", params)
		db.commit()
	finally:
		db.close()
	return get_scoring_run(db_path, run_id)


def get_scoring_run(db_path: Path, run_id: str) -> dict[str, Any] | None:
	db = get_db(db_path)
	try:
		row = db.execute("SELECT * FROM scoring_runs WHERE id = ?", (run_id,)).fetchone()
		return _public_row(dict(row)) if row else None
	finally:
		db.close()


def list_scoring_runs(db_path: Path, *, limit: int | None = 20, status: str | None = None) -> list[dict[str, Any]]:
	db = get_db(db_path)
	try:
		params = [status] if status else []
		if limit is not None:
			params.append(max(1, min(int(limit), 100)))
		rows = db.execute(
			"SELECT * FROM scoring_runs " + ("WHERE status = ? " if status else "")
			+ "ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'stopping' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END, created_at DESC"
			+ (" LIMIT ?" if limit is not None else ""),
			params,
		).fetchall()
		return [_public_row(dict(row)) or {} for row in rows]
	finally:
		db.close()


def mark_orphaned_scoring_runs_paused(db_path: Path) -> int:
	db = get_db(db_path)
	try:
		cursor = db.execute(
			"""UPDATE scoring_runs
               SET status = 'paused', pause_reason = '应用已重启，可从剩余岗位继续', updated_at = CURRENT_TIMESTAMP
               WHERE status IN ('pending', 'running', 'stopping')"""
		)
		db.commit()
		return cursor.rowcount
	finally:
		db.close()
