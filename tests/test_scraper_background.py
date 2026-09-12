import json
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, call, patch

from bosshunter.scraper.jobs import scrape_jobs
from bosshunter.web.server import _execute_collect
from bosshunter.web.tasks import WorkbenchTask
from bosshunter.collection.models import JobCandidate, PlatformCollectionResult
from bosshunter.collection.orchestrator import CollectionOrchestrator
from bosshunter.collection.registry import CollectorRegistry


class ScraperBackgroundTests(unittest.TestCase):
    def test_collection_options_report_automatic_scoring_to_workbench(self):
        task = WorkbenchTask(id="auto-score-task", mode="collect", label="单独采集")
        config = {"_collection_options": {
            "platform_order": ["boss"], "auto_score": True,
            "platforms": {"boss": {"keywords": ["AI"], "cities": ["北京"], "max_pages": 1}},
        }}
        candidate = JobCandidate(platform="boss", source_job_id="new-scoring-job",
                                 title="AI运营", company="测试公司", city="北京", jd="负责运营",
                                 url="https://example.test/job_detail/new-scoring-job.html")

        def collect(_request, hooks):
            if hooks.on_list_candidate(candidate):
                hooks.on_candidate(candidate)
            return PlatformCollectionResult("boss", "completed", "search_exhausted", "采集结束")

        registry = CollectorRegistry({"boss": lambda: MagicMock(collect=collect)})

        def score_with_progress(score_config, **options):
            self.assertEqual(options["job_ids"], ["new-scoring-job"])
            self.assertEqual(task.progress["outcome"], "scoring")
            self.assertTrue(any("开始 AI 评分" in log for log in task.logs))
            score_config["_workbench_score_progress"]({
                "completed": 1, "total": 1, "scored": 1, "filtered": 0, "failed": 0,
            })
            score_config["_workbench_log"]("评分结果已保存")
            return 1, 0

        with tempfile.TemporaryDirectory() as tmp:
            def orchestrator(collect_config, **kwargs):
                return CollectionOrchestrator(collect_config, db_path=Path(tmp) / "jobs.db",
                                              task_id=kwargs["task_id"], registry=registry)

            with patch("bosshunter.web.server.CollectionOrchestrator", side_effect=orchestrator), \
                 patch("bosshunter.ai.scorer.score_jobs", side_effect=score_with_progress) as score:
                _execute_collect(task, config)

        score.assert_called_once()
        self.assertEqual(task.metrics["collect_new"], 1)
        self.assertEqual(task.metrics["ai_completed"], 1)
        self.assertEqual(task.metrics["ai_total"], 1)
        self.assertEqual(task.metrics["ai_passed"], 1)
        self.assertEqual(task.metrics["ai_failed"], 0)
        self.assertIn("AI 评分进度 1/1：通过 1，过滤 0，失败 0", task.logs)
        self.assertIn("评分结果已保存", task.logs)

    def test_stopped_collection_does_not_open_a_search_page(self):
        db = MagicMock()
        stop_event = Event()
        stop_event.set()
        config = {
            "profile": {"target_cities": ["北京"], "deal_breakers": []},
            "search": {"max_pages": 1},
            "_workbench_stop_event": stop_event,
        }

        with patch("bosshunter.scraper.jobs.get_db", return_value=db), \
             patch("bosshunter.scraper.jobs.new_tab") as new_tab:
            count = scrape_jobs(config, ["AI"])

        self.assertEqual(count, 0)
        new_tab.assert_not_called()
        db.close.assert_called_once_with()

    def test_workbench_passes_its_stop_event_into_collection(self):
        task = WorkbenchTask(id="task-1", mode="collect", label="单独采集")
        config = {"search": {"keywords": ["AI"]}}

        def scrape_with_progress(collect_config, _keywords, *, collected_job_ids=None):
            collect_config["_workbench_collect_progress"]({"seen": 9, "new": 3, "duplicate": 4})
            collected_job_ids.extend(["new-1", "new-2", "new-3"])
            return 3

        def score_with_progress(score_config):
            score_config["_workbench_score_progress"]({
                "completed": 3,
                "total": 3,
                "scored": 2,
                "filtered": 1,
                "failed": 0,
            })
            return (2, 1)

        with patch("bosshunter.scraper.jobs.scrape_jobs", side_effect=scrape_with_progress) as scrape, \
             patch("bosshunter.ai.scorer.score_jobs", side_effect=score_with_progress):
            _execute_collect(task, config)

        collection_config = scrape.call_args.args[0]
        self.assertIs(collection_config["_workbench_stop_event"], task.stop_requested)
        self.assertEqual(task.metrics["collect_seen"], 9)
        self.assertEqual(task.metrics["collect_new"], 3)
        self.assertEqual(task.metrics["collect_duplicate"], 4)
        self.assertEqual(task.metrics["ai_passed"], 2)
        self.assertEqual(task.metrics["ai_filtered"], 1)
        self.assertEqual(task.metrics["ai_failed"], 0)
        self.assertEqual(task.snapshot()["metrics"], task.metrics)

    def test_scraper_reports_seen_new_and_duplicate_counts(self):
        db = MagicMock()
        progress = MagicMock()
        progress.add_task.return_value = "task-1"
        progress_context = MagicMock()
        progress_context.__enter__ = MagicMock(return_value=progress)
        progress_context.__exit__ = MagicMock(return_value=False)
        updates = []
        collected_job_ids = []
        jobs = [
            {"title": "Existing", "company": "Example", "salary": "10-15K", "experience": "", "url": "/job_detail/existing.html"},
            {"title": "New", "company": "Example", "salary": "10-15K", "experience": "", "url": "/job_detail/new.html"},
        ]
        detail = {"title": "New", "company": "Example", "salary": "10-15K", "jd": "客户交付"}
        config = {
            "profile": {"target_cities": ["北京"], "deal_breakers": []},
            "search": {"max_pages": 1},
            "_workbench_collect_progress": updates.append,
        }

        with patch("bosshunter.scraper.jobs.get_db", return_value=db), \
             patch("bosshunter.collection.platforms.boss.PlatformAccessGuard") as guard_cls, \
             patch("bosshunter.scraper.jobs.Progress", return_value=progress_context), \
             patch("bosshunter.scraper.jobs.PageThrottle") as throttle_cls, \
             patch("bosshunter.scraper.jobs.new_tab", return_value="worker-target"), \
             patch("bosshunter.scraper.jobs.navigate", return_value=True), \
             patch("bosshunter.scraper.jobs.evaluate", side_effect=[
                 json.dumps({"risk": None}), False, json.dumps(jobs),
                 json.dumps({"risk": None}), json.dumps(detail),
             ]), \
             patch("bosshunter.scraper.jobs.wait_for_load"), \
             patch("bosshunter.scraper.jobs.scroll"), \
             patch("bosshunter.scraper.jobs.close_tab"), \
             patch("bosshunter.scraper.jobs.job_exists", side_effect=[True, False]), \
             patch("bosshunter.scraper.jobs.matching_deal_breaker", return_value=False), \
             patch("bosshunter.scraper.jobs.insert_job"), \
             patch("bosshunter.scraper.jobs.time.sleep"):
            throttle_cls.return_value.wait.return_value = None
            guard_cls.return_value.ensure_unlocked.return_value = None
            count = scrape_jobs(config, ["AI"], collected_job_ids=collected_job_ids)

        self.assertEqual(count, 1)
        self.assertEqual(len(collected_job_ids), 1)
        self.assertEqual(updates[-1], {
            "seen": 2, "new": 1, "duplicate": 1, "filtered": 0,
            "parse_failed": 0, "save_failed": 0, "search_pages": 1,
        })

    def test_search_and_detail_pages_reuse_one_background_worker_tab(self):
        db = MagicMock()
        progress = MagicMock()
        progress.add_task.return_value = "task-1"
        progress_context = MagicMock()
        progress_context.__enter__ = MagicMock(return_value=progress)
        progress_context.__exit__ = MagicMock(return_value=False)

        jobs = [{
            "title": "AI Product Manager",
            "company": "Example",
            "salary": "20-30K",
            "experience": "3-5 years",
            "url": "/job_detail/background-job.html",
        }]
        detail = {
            "title": "AI Product Manager",
            "company": "Example",
            "salary": "20-30K",
            "experience": "3-5 years",
            "jd": "Build AI products",
        }

        config = {
            "profile": {"target_cities": ["北京"], "deal_breakers": []},
            "search": {"max_pages": 1},
        }

        with patch("bosshunter.scraper.jobs.get_db", return_value=db), \
             patch("bosshunter.collection.platforms.boss.PlatformAccessGuard") as guard_cls, \
             patch("bosshunter.scraper.jobs.Progress", return_value=progress_context), \
             patch("bosshunter.scraper.jobs.PageThrottle") as throttle_cls, \
             patch(
                 "bosshunter.scraper.jobs.new_tab",
                 return_value="worker-target",
             ) as new_tab, \
             patch("bosshunter.scraper.jobs.navigate", return_value=True) as navigate, \
             patch(
                 "bosshunter.scraper.jobs.evaluate",
                 side_effect=[
                     json.dumps({"risk": None}), False, json.dumps(jobs),
                     json.dumps({"risk": None}), json.dumps(detail),
                 ],
             ), \
             patch("bosshunter.scraper.jobs.wait_for_load"), \
             patch("bosshunter.scraper.jobs.scroll"), \
             patch("bosshunter.scraper.jobs.close_tab"), \
             patch("bosshunter.scraper.jobs.job_exists", return_value=False), \
             patch("bosshunter.scraper.jobs.matching_deal_breaker", return_value=False), \
             patch("bosshunter.scraper.jobs.insert_job"), \
             patch("bosshunter.scraper.jobs.time.sleep"):
            throttle_cls.return_value.wait.return_value = None
            guard_cls.return_value.ensure_unlocked.return_value = None
            count = scrape_jobs(config, ["AI"])

        self.assertEqual(count, 1)
        new_tab.assert_called_once_with(
            "https://www.zhipin.com/web/geek/job?query=AI&city=101010100",
            background=True,
        )
        throttle_cls.assert_called_once_with(delay_min=3.0, delay_max=7.5)
        navigate.assert_called_once_with(
            "worker-target",
            "https://www.zhipin.com/job_detail/background-job.html",
        )


if __name__ == "__main__":
    unittest.main()
