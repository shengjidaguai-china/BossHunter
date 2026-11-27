"""Durable parent sessions; job identities remain owned by child run ledgers."""

from __future__ import annotations

import json
from pathlib import Path

from bosshunter.db import get_db


def create_session(db_path: Path, session_id: str, options: dict, state: dict) -> None:
    conn = get_db(db_path)
    try:
        conn.execute("INSERT INTO collection_sessions (id, status, options_json, state_json) VALUES (?, 'running', ?, ?)",
                     (session_id, json.dumps(options, ensure_ascii=False), json.dumps(state, ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()


def get_session(db_path: Path, session_id: str) -> dict | None:
    conn = get_db(db_path)
    try:
        row = conn.execute("SELECT * FROM collection_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["options"] = json.loads(result.pop("options_json"))
        result["state"] = json.loads(result.pop("state_json"))
        children = conn.execute("SELECT id, collected_job_ids_json, platform_states_json, boss_checkpoint_json FROM collection_runs WHERE session_id = ? ORDER BY session_round", (session_id,)).fetchall()
        result["collected_job_ids"] = list(dict.fromkeys(job_id for child in children for job_id in json.loads(child["collected_job_ids_json"])))
        result["runs"] = [child["id"] for child in children]
        result["city_totals"] = {}
        for child in children:
            for city, state in json.loads(child["boss_checkpoint_json"]).get("cities", {}).items():
                result["city_totals"][city] = result["city_totals"].get(city, 0) + int(state.get("new_total", 0))
        result["counts"] = {name: sum(int(json.loads(child["platform_states_json"]).get("boss", {}).get(name) or 0) for child in children)
                            for name in ("seen", "duplicate", "filtered", "parse_failed", "save_failed")}
        return result
    finally:
        conn.close()


def save_session(db_path: Path, session_id: str, state: dict, *, owner: str) -> None:
    conn = get_db(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT state_json FROM collection_sessions WHERE id = ?", (session_id,)).fetchone()
        current = json.loads(row[0]) if row else {}
        if current.get("owner") != owner:
            raise RuntimeError("持续采集执行所有权已变化")
        # A UI stop/continue request cannot be overwritten by an older worker snapshot.
        state["stop_requested"] = bool(state.get("stop_requested") or current.get("stop_requested"))
        state["continue_version"] = max(state.get("continue_version", 0), current.get("continue_version", 0))
        if state["stop_requested"] and state.get("status") == "completed":
            state.update(status="stopped", reason_code="user_stopped")
            if state.get("history"):
                state["history"][-1]["reason_code"] = "user_stopped"
        conn.execute("UPDATE collection_sessions SET status = ?, state_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (state.get("status", "running"), json.dumps(state, ensure_ascii=False), session_id))
        conn.commit()
    finally:
        conn.close()


def claim_session(db_path: Path, session_id: str, owner: str) -> dict:
    conn = get_db(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT state_json FROM collection_sessions WHERE id = ? AND status = 'running'", (session_id,)).fetchone()
        if row is None:
            raise ValueError("持续会话已结束或不存在")
        state = json.loads(row[0])
        state["owner"] = owner
        conn.execute("UPDATE collection_sessions SET state_json = ? WHERE id = ?", (json.dumps(state, ensure_ascii=False), session_id))
        conn.commit()
        return state
    finally:
        conn.close()


def request_session_action(db_path: Path, session_id: str, action: str) -> None:
    if action not in {"stop", "continue"}:
        raise ValueError("无效会话操作")
    conn = get_db(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT state_json FROM collection_sessions WHERE id = ? AND status = 'running'", (session_id,)).fetchone()
        if not row:
            raise ValueError("会话已结束或不存在")
        state = json.loads(row[0])
        if action == "stop":
            state["stop_requested"] = True
        else:
            if state.get("phase") != "waiting_user":
                raise ValueError("当前会话不在等待人工处理")
            state["continue_version"] = state.get("continue_version", 0) + 1
        conn.execute("UPDATE collection_sessions SET state_json = ? WHERE id = ?", (json.dumps(state, ensure_ascii=False), session_id))
        conn.commit()
    finally:
        conn.close()


def list_sessions(db_path: Path, *, active_only: bool = False) -> list[dict]:
    conn = get_db(db_path)
    try:
        rows = conn.execute("SELECT id FROM collection_sessions " + ("WHERE status = 'running' " if active_only else "") + "ORDER BY created_at DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    return [get_session(db_path, row[0]) for row in rows]
