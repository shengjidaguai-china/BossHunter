"""Scoring ownership, cooperative stop and reversible deletion through local routes."""

import io
import json
from threading import Event
from unittest.mock import Mock

import pytest
import yaml

from bosshunter import db as db_module
from bosshunter.ai import scorer
from bosshunter.scoring_run_store import get_scoring_run
from bosshunter.web import server
from bosshunter.web.tasks import WorkbenchTaskRunner

SCORE_RESPONSE = json.dumps(
	{
		"core_duties": {"score": 34, "evidence": "相关产品经验"},
		"transferable_evidence": {"score": 21, "evidence": "相关项目经验"},
		"hard_requirements": {"score": 12, "evidence": "满足要求"},
		"tools_industry": {"score": 7, "evidence": "熟悉工具"},
		"practical_fit": {"score": 8, "evidence": "城市薪资匹配"},
		"caps": [],
		"hard_gaps": [],
		"reason": "匹配",
	},
	ensure_ascii=False,
)


def request(path, body):
	encoded = json.dumps(body).encode()
	result = {}
	environ = {
		"REQUEST_METHOD": "POST",
		"PATH_INFO": path,
		"QUERY_STRING": "",
		"SERVER_NAME": "127.0.0.1",
		"SERVER_PORT": "8686",
		"wsgi.version": (1, 0),
		"wsgi.url_scheme": "http",
		"wsgi.input": io.BytesIO(encoded),
		"wsgi.errors": io.StringIO(),
		"wsgi.multithread": False,
		"wsgi.multiprocess": False,
		"wsgi.run_once": False,
		"CONTENT_LENGTH": str(len(encoded)),
		"CONTENT_TYPE": "application/json",
	}

	def respond(status, headers, exc_info=None):
		result["status"] = int(status.split()[0])

	response = server.app(environ, respond)
	try:
		payload = json.loads(b"".join(value.encode() if isinstance(value, str) else value for value in response))
	finally:
		if hasattr(response, "close"):
			response.close()
	return result["status"], payload


@pytest.fixture
def runtime(tmp_path, monkeypatch):
	for name, value in {
		"BASE_DIR": tmp_path,
		"DATA_DIR": tmp_path / "data",
		"RESUME_DIR": tmp_path / "data/resumes",
		"CONFIG_PATH": tmp_path / "config.yaml",
	}.items():
		monkeypatch.setattr(server, name, value)
	path = tmp_path / "data/bosshunter.db"
	monkeypatch.setattr(db_module, "DB_PATH", path)
	(tmp_path / "resume.md").write_text("测试简历：产品经理，负责人工智能产品设计。", encoding="utf-8")
	server.CONFIG_PATH.write_text(
		yaml.safe_dump(
			{
				"profile": {"resume_path": str(tmp_path / "resume.md")},
				"ai": {"scoring_concurrency": 1, "scoring_max_attempts": 1},
				"search": {"keywords": ["原关键词"], "cities": ["北京"]},
			},
			allow_unicode=True,
		),
		encoding="utf-8",
	)
	monkeypatch.setattr(server, "get_ai_api_key", lambda _: "offline-placeholder")
	ai = Mock(return_value=SCORE_RESPONSE)
	monkeypatch.setattr(scorer, "_call_claude", ai)
	runner = WorkbenchTaskRunner({"score": server._execute_score, "collect": server._execute_collect})
	monkeypatch.setattr(server, "task_runner", runner)
	db_module.get_db(path).close()
	yield path, runner, ai
	for task in runner.status()["tasks"]:
		if task["status"] in {"running", "stopping"}:
			runner.stop(task["id"])
	runner.wait(timeout=5)
	assert runner.status()["active"] is None


def seed_jobs(path, count, status="pending"):
	db = db_module.get_db(path)
	try:
		db.executemany(
			"INSERT INTO jobs(id,title,company,jd,status,score,salary,city) VALUES (?,?,?,?,?,80,'20-30K','北京')",
			[(str(i), "AI产品经理", "测试公司", "设计人工智能产品", status) for i in range(count)],
		)
		db.commit()
	finally:
		db.close()


def test_end_waits_for_live_scorer_then_unlocks_and_retains_history(runtime, monkeypatch):
	from bosshunter.scoring_run_store import create_scoring_run, update_scoring_run

	path, runner, ai = runtime
	seed_jobs(path, 1)
	create_scoring_run(path, run_id="end-live", options={}, job_ids=["0"])
	update_scoring_run(path, "end-live", status="running")
	entered, release = Event(), Event()

	def blocked_score(config, **kwargs):
		entered.set()
		assert release.wait(5)
		config["_workbench_score_checkpoint"]({"status": "paused", "remaining_job_ids": ["0"]})

	monkeypatch.setattr(scorer, "score_jobs", blocked_score)
	task = runner.start("score", {"_score_run_id": "end-live", "_score_options": {"job_ids": ["0"]}})
	update_scoring_run(path, "end-live", task_id=task["id"])
	try:
		assert entered.wait(2)
		status, result = request("/api/scoring/runs/end-live/end", {})
		assert status == 202 and result["status"] == "stopping"
		status, _ = request("/api/jobs/soft-delete", {"job_ids": ["0"], "confirmed": True})
		assert status == 409
	finally:
		release.set()
		runner.wait(timeout=5)
	run = get_scoring_run(path, "end-live")
	assert run["status"] == "stopped"
	assert run["remaining_job_ids"] == ["0"]
	assert request("/api/jobs/soft-delete", {"job_ids": ["0"], "confirmed": True})[0] == 200
	db = db_module.get_db(path)
	try:
		assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
		assert db.execute("SELECT COUNT(*) FROM history WHERE action='soft_deleted'").fetchone()[0] == 1
	finally:
		db.close()
	ai.assert_not_called()


def test_resume_paused_run_skips_recycled_job(runtime):
	from bosshunter.scoring_run_store import create_scoring_run, update_scoring_run

	path, runner, ai = runtime
	seed_jobs(path, 2)
	create_scoring_run(path, run_id="resume-deleted", options={}, job_ids=["0", "1"])
	update_scoring_run(path, "resume-deleted", status="paused")
	assert request("/api/jobs/soft-delete", {"job_ids": ["0"], "confirmed": True})[0] == 200
	status, result = request("/api/scoring/runs/resume-deleted/resume", {})
	assert status == 200, result
	runner.wait(timeout=5)
	assert ai.call_count == 1
	assert get_scoring_run(path, "resume-deleted")["status"] == "completed"
	db = db_module.get_db(path)
	try:
		row = db.execute("SELECT deleted_at,status FROM jobs WHERE id='0'").fetchone()
		assert row[0] is not None and row[1] == "pending"
		assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 2
	finally:
		db.close()


def test_idle_end_request_is_settled_before_delete(runtime):
	from bosshunter.scoring_run_store import create_scoring_run, update_scoring_run

	path, _runner, ai = runtime
	seed_jobs(path, 1)
	create_scoring_run(path, run_id="end-race", options={}, job_ids=["0"])
	update_scoring_run(path, "end-race", status="stopping")
	assert request("/api/jobs/soft-delete", {"job_ids": ["0"], "confirmed": True})[0] == 200
	assert get_scoring_run(path, "end-race")["status"] == "stopped"
	assert get_scoring_run(path, "end-race")["remaining_job_ids"] == ["0"]
	ai.assert_not_called()


def test_ending_unowned_paused_run_does_not_stop_other_score_worker(runtime):
	from bosshunter.scoring_run_store import create_scoring_run, update_scoring_run

	path, runner, _ai = runtime
	create_scoring_run(path, run_id="old-paused", options={}, job_ids=["old"])
	update_scoring_run(path, "old-paused", status="paused")
	entered, release = Event(), Event()
	runner._executors["score"] = lambda task, config: (entered.set(), release.wait(5))
	task = runner.start("score", {})
	try:
		assert entered.wait(2)
		assert request("/api/scoring/runs/old-paused/end", {})[0] == 200
		active = runner.status()["active"]
		assert active["id"] == task["id"]
		assert active["stop_requested"] is False
		assert active["status"] == "running"
	finally:
		release.set()
		runner.wait(timeout=5)


def test_worker_return_without_checkpoint_is_recoverable(runtime, monkeypatch):
	from bosshunter.scoring_run_store import create_scoring_run, update_scoring_run

	path, runner, _ai = runtime
	create_scoring_run(path, run_id="early-return", options={}, job_ids=["remaining"])
	update_scoring_run(path, "early-return", status="running")
	monkeypatch.setattr(scorer, "score_jobs", lambda *args, **kwargs: None)
	runner.start("score", {"_score_run_id": "early-return"})
	runner.wait(timeout=5)
	run = get_scoring_run(path, "early-return")
	assert run["status"] == "paused"
	assert run["remaining_job_ids"] == ["remaining"]
