"""Exercise task admission and large scoring runs through real local routes.

Only external collection and AI responses are simulated; config, SQLite,
selection, background scoring and recovery use their normal implementations.
"""

import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier, Event
from unittest.mock import Mock

import pytest
import yaml

from bosshunter import db as db_module
from bosshunter.ai import scorer
from bosshunter.ai.credentials import AIRequestError
from bosshunter.collection.models import JobCandidate, PlatformCollectionResult
from bosshunter.collection.platforms.boss import BossCollector
from bosshunter.scoring_run_store import get_scoring_run
from bosshunter.web import server, tasks
from bosshunter.web.tasks import TaskAlreadyRunningError, WorkbenchTaskRunner


SCORE_RESPONSE = json.dumps({
    "core_duties": {"score": 34, "evidence": "相关产品经验"},
    "transferable_evidence": {"score": 21, "evidence": "相关项目经验"},
    "hard_requirements": {"score": 12, "evidence": "满足要求"},
    "tools_industry": {"score": 7, "evidence": "熟悉工具"},
    "practical_fit": {"score": 8, "evidence": "城市薪资匹配"},
    "caps": [], "hard_gaps": [], "reason": "匹配",
}, ensure_ascii=False)


def request(path, body):
    encoded = json.dumps(body).encode()
    result = {}
    environ = {
        "REQUEST_METHOD": "POST", "PATH_INFO": path, "QUERY_STRING": "",
        "SERVER_NAME": "127.0.0.1", "SERVER_PORT": "8686",
        "wsgi.version": (1, 0), "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(encoded), "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(encoded)), "CONTENT_TYPE": "application/json",
    }

    def respond(status, headers, exc_info=None):
        result["status"] = int(status.split()[0])

    response = server.app(environ, respond)
    try:
        payload = json.loads(b"".join(
            value.encode() if isinstance(value, str) else value for value in response
        ))
    finally:
        if hasattr(response, "close"):
            response.close()
    return result["status"], payload


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for name, value in {
        "BASE_DIR": tmp_path, "DATA_DIR": tmp_path / "data",
        "RESUME_DIR": tmp_path / "data/resumes", "CONFIG_PATH": tmp_path / "config.yaml",
    }.items():
        monkeypatch.setattr(server, name, value)
    path = tmp_path / "data/bosshunter.db"
    monkeypatch.setattr(db_module, "DB_PATH", path)
    (tmp_path / "resume.md").write_text("测试简历：产品经理，负责人工智能产品设计。")
    server.CONFIG_PATH.write_text(yaml.safe_dump({
        "profile": {"resume_path": str(tmp_path / "resume.md")},
        "ai": {"scoring_concurrency": 1, "scoring_max_attempts": 1},
        "search": {"keywords": ["原关键词"], "cities": ["北京"]},
    }, allow_unicode=True))
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
            "INSERT INTO jobs(id,title,company,jd,status,score,salary,city) "
            "VALUES (?,?,?,?,?,80,'20-30K','北京')",
            [(str(i), "AI产品经理", "测试公司", "设计人工智能产品", status) for i in range(count)],
        )
        db.commit()
    finally:
        db.close()


def assert_all_scored(path, count):
    db = db_module.get_db(path)
    try:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE score=82 AND status='ready'").fetchone()[0] == count
    finally:
        db.close()


def collection_options(keyword="AI", auto_score=False):
    return {"platform_order": ["boss"], "auto_score": auto_score, "platforms": {
        "boss": {"keywords": [keyword], "cities": ["北京"], "max_pages": 1},
    }}


def test_rejected_start_preserves_saved_config_and_running_options(runtime):
    _, runner, _ = runtime
    entered, release = Event(), Event()
    seen = []

    def blocked_executor(task, config):
        seen.append(config)
        # Settings must already be saved before the worker starts.
        assert server.load_config(server.CONFIG_PATH)["platforms"]["boss"]["search"]["keywords"] == ["原任务"]
        entered.set()
        assert release.wait(timeout=10)

    runner._executors["collect"] = blocked_executor
    try:
        status, first = request("/api/workbench/task", {
            "mode": "collect", "options": collection_options("原任务"),
        })
        assert status == 200, first
        assert entered.wait(timeout=2)
        saved = server.CONFIG_PATH.read_bytes()
        status, rejected = request("/api/workbench/task", {
            "mode": "collect", "options": collection_options("被拒绝的新任务"),
        })
        assert status == 409, rejected
        assert server.CONFIG_PATH.read_bytes() == saved
        assert len(seen) == len(runner.status()["tasks"]) == 1
        assert seen[0]["_collection_options"]["platforms"]["boss"]["keywords"] == ["原任务"]
    finally:
        release.set()
        runner.wait(timeout=2)
    assert runner.status()["last_task"]["status"] == "completed"


def test_failed_config_save_does_not_start_or_reserve_task(runtime, monkeypatch):
    _, runner, _ = runtime
    executor = Mock()
    runner._executors["collect"] = executor
    saved = server.CONFIG_PATH.read_bytes()
    with monkeypatch.context() as patcher:
        patcher.setattr(server, "_write_config", Mock(side_effect=OSError("模拟保存失败")))
        status, failed = request("/api/workbench/task", {
            "mode": "collect", "options": collection_options(),
        })
    assert status == 500 and "模拟保存失败" in failed["error"]
    assert server.CONFIG_PATH.read_bytes() == saved
    assert runner.status()["tasks"] == []
    executor.assert_not_called()
    status, started = request("/api/workbench/task", {"mode": "collect", "options": collection_options()})
    assert status == 200, started
    runner.wait(timeout=2)
    executor.assert_called_once()


def test_concurrent_runner_starts_only_persist_winning_settings(tmp_path):
    gate, release = Barrier(3), Event()
    saved = tmp_path / "settings.txt"
    writes, executed = [], []

    def execute(task, config):
        executed.append(config["keyword"])
        assert release.wait(timeout=10)

    runner = WorkbenchTaskRunner({"collect": execute})

    def start(keyword):
        def persist():
            writes.append(keyword)
            saved.write_text(keyword)
        gate.wait(timeout=2)
        try:
            runner.start("collect", {"keyword": keyword}, before_start=persist)
            return keyword
        except TaskAlreadyRunningError:
            return None

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.submit(start, "第一项"), pool.submit(start, "第二项")
            gate.wait(timeout=2)
            winners = [value for value in (first.result(timeout=2), second.result(timeout=2)) if value]
        assert len(winners) == 1
        assert writes == winners
        assert saved.read_text() == winners[0]
    finally:
        release.set()
        runner.wait(timeout=2)
    assert executed == winners


def test_expired_start_does_not_persist_settings(monkeypatch):
    monkeypatch.setattr(tasks, "_deadline_from_config", lambda *_: datetime.now() - timedelta(seconds=1))
    persist, execute = Mock(), Mock()
    runner = WorkbenchTaskRunner({"full": execute})
    task = runner.start("full", {}, before_start=persist)
    assert task["status"] == "stopped"
    persist.assert_not_called()
    execute.assert_not_called()


@pytest.mark.parametrize("scope", ["pending", "all_scored"])
def test_all_scoring_completes_1001_jobs(runtime, scope):
    path, runner, ai = runtime
    seed_jobs(path, 1001, "scored" if scope == "all_scored" else "pending")
    options = {"scope": scope, "limit": None, "force_rescore": scope == "all_scored"}
    status, preview = request("/api/scoring/preview", {"options": options})
    assert status == 200 and preview["eligible_jobs"] == 1001
    status, started = request("/api/scoring/start", {"options": options})
    assert status == 200, started
    runner.wait(timeout=30)
    run = get_scoring_run(path, started["run"]["id"])
    assert run["status"] == runner.status()["last_task"]["status"] == "completed"
    assert run["remaining_job_ids"] == []
    assert ai.call_count == 1001
    assert_all_scored(path, 1001)


@pytest.mark.parametrize("endpoint", ["preview", "start"])
def test_manual_selection_rejects_1001_ids_but_accepts_1000(runtime, endpoint):
    path, runner, ai = runtime
    seed_jobs(path, 1001)
    options = {"scope": "selected", "job_ids": [str(i) for i in range(1001)]}
    status, rejected = request(f"/api/scoring/{endpoint}", {"options": options})
    assert status == 400 and rejected["error"] == "一次最多选择 1000 个岗位"
    assert runner.status()["tasks"] == []
    ai.assert_not_called()
    options["job_ids"].pop()
    status, accepted = request(f"/api/scoring/{endpoint}", {"options": options})
    assert status == 200, accepted
    if endpoint == "start":
        runner.wait(timeout=30)
        assert runner.status()["last_task"]["status"] == "completed"
        assert_all_scored(path, 1000)
    else:
        assert accepted["eligible_jobs"] == 1000


def test_resume_handles_1001_remaining_jobs_without_rescoring_completed_job(runtime):
    path, runner, ai = runtime
    seed_jobs(path, 1002)
    ai.side_effect = [SCORE_RESPONSE, AIRequestError("token_quota", "模拟额度耗尽", 429)]
    status, started = request("/api/scoring/start", {"scope": "pending", "limit": None})
    assert status == 200, started
    runner.wait(timeout=30)
    run_id = started["run"]["id"]
    paused = get_scoring_run(path, run_id)
    assert paused["status"] == "paused"
    assert len(paused["remaining_job_ids"]) == 1001
    assert ai.call_count == 2
    ai.side_effect = None
    status, resumed = request(f"/api/scoring/runs/{run_id}/resume", {})
    assert status == 200, resumed
    runner.wait(timeout=30)
    finished = get_scoring_run(path, run_id)
    assert finished["status"] == "completed" and finished["remaining_job_ids"] == []
    assert ai.call_count == 1003  # One success + one quota pause + 1001 remaining jobs.
    assert_all_scored(path, 1002)


def test_collection_auto_scores_1001_new_jobs(runtime, monkeypatch):
    path, runner, ai = runtime

    def collect(self, collection_request, hooks):
        for i in range(1001):
            hooks.on_candidate(JobCandidate(
                "boss", str(i), "AI产品经理", "测试公司", salary="20-30K", city="北京",
                jd="设计人工智能产品", url=f"https://example.invalid/job_detail/{i}.html",
            ))
        hooks.on_page_complete("北京", "AI", 1)
        return PlatformCollectionResult("boss", "completed", "search_exhausted", "模拟搜索完毕")

    monkeypatch.setattr(BossCollector, "collect", collect)
    status, started = request("/api/workbench/task", {
        "mode": "collect", "options": collection_options(auto_score=True),
    })
    assert status == 200, started
    runner.wait(timeout=30)
    assert runner.status()["last_task"]["status"] == "completed"
    assert ai.call_count == 1001
    assert_all_scored(path, 1001)
