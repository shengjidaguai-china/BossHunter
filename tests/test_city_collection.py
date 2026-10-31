from contextlib import closing
from copy import deepcopy
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from bosshunter.cities import get_city_map
from bosshunter.collection.base import CollectorHooks
from bosshunter.collection.models import PlatformCollectionRequest, PlatformCollectionResult
from bosshunter.collection.orchestrator import CollectionOrchestrator, normalize_collection_options
from bosshunter.collection.platforms.boss import BossCollector, JS_DETECT_COLLECTION_RISK
from bosshunter.collection.registry import CollectorRegistry
from bosshunter.collection_run_store import get_collection_run
from bosshunter.db import get_db, get_active_platform_safety_lock
from test_boss_search_regressions import SearchBrowser, card
from test_city_yield import Clock


def collector(browser, conn=None, **extra):
    return BossCollector(browser=browser.browser(), safety_conn=conn, sleep=lambda _: None,
                         throttle_factory=lambda **_: Mock(wait=lambda _: False), **extra)


class CityCollectionTests(TestCase):
    def test_no_ids_skips_remaining_keywords_and_visits_next_city(self):
        browser = SearchBrowser([[card("a")]])
        states = {}
        hooks = CollectorHooks(None, lambda _: True, lambda _: True, lambda _: None, lambda **_: None,
                               on_city_state=lambda city, state: states.update({city: state}))
        result = collector(browser).collect(PlatformCollectionRequest("boss", ["A", "B"], ["北京", "上海"], {}, max_pages=2), hooks)
        search_urls = [url for url in browser.opens if "job_detail" not in url]
        self.assertEqual(len(search_urls), 2)
        self.assertIn("101010100", search_urls[0])
        self.assertIn("101020100", search_urls[1])
        self.assertTrue(all("query=A" in url for url in search_urls))
        self.assertEqual(states["北京"]["status"], "yielded_no_ids")
        self.assertEqual(states["北京"]["next_keyword_index"], 1)
        self.assertEqual(result.status, "completed_with_shortage")

    def test_repeated_pages_also_switch_city(self):
        browser = SearchBrowser([[card("a")]], scrolling=False)
        hooks = CollectorHooks(None, lambda _: True, lambda _: True, lambda _: None, lambda **_: None)
        result = collector(browser).collect(PlatformCollectionRequest("boss", ["A", "B"], ["北京", "上海"], {}, max_pages=3), hooks)
        search_urls = [url for url in browser.opens if "job_detail" not in url]
        self.assertEqual(len(search_urls), 4)
        self.assertEqual(set(result.city_results), {"北京", "上海"})

    def test_captcha_during_stagnation_stops_before_next_city(self):
        class RiskBrowser(SearchBrowser):
            def evaluate(self, target, script):
                if script == JS_DETECT_COLLECTION_RISK and self.scrolls:
                    return '{"risk":"captcha","evidence":"test"}'
                return super().evaluate(target, script)
        browser = RiskBrowser([[card("a")]])
        with tempfile.TemporaryDirectory() as tmp, closing(get_db(Path(tmp) / "jobs.db")) as conn:
            hooks = CollectorHooks(None, lambda _: True, lambda _: True, lambda _: None, lambda **_: None)
            result = collector(browser, conn).collect(PlatformCollectionRequest("boss", ["A"], ["北京", "上海"], {}, max_pages=2), hooks)
            self.assertEqual(result.reason_code, "captcha")
            self.assertEqual(get_active_platform_safety_lock(conn)["reason"], "captcha")
            self.assertFalse(any("101020100" in url for url in browser.opens))

    def test_low_yield_counts_receipts_and_resets_only_on_city_switch(self):
        clock = Clock()
        browser = SearchBrowser([[card("a"), card("b")]])
        receipt = {"sequence": 0, "inserted": False}
        context = {}
        def save(candidate):
            clock.value += 600
            receipt.update(sequence=receipt["sequence"] + 1, inserted=True, job_id=candidate.storage_id,
                           search_city=context["city"], event_elapsed_ms=context["tracker"].elapsed_ms())
            return True
        hooks = CollectorHooks(None, lambda _: True, save, lambda _: None, lambda **_: None,
                               last_save_receipt=lambda: receipt, on_city_start=lambda city, tracker: context.update(city=city, tracker=tracker))
        result = collector(browser, clock=clock).collect(PlatformCollectionRequest("boss", ["A", "B"], ["北京", "上海"], {},
                                                   city_yield_policy={"enabled": True}), hooks)
        self.assertEqual([s["status"] for s in result.city_results.values()], ["low_yield", "low_yield"])
        self.assertTrue(all(s["new_total"] == 1 for s in result.city_results.values()))

    def test_job_and_city_ledger_roll_back_together(self):
        browser = SearchBrowser([[card("new")]])
        registry = CollectorRegistry({"boss": lambda: collector(browser)})
        from bosshunter.collection.orchestrator import save_city_state as real_save
        def fail_ledger(*args, **kwargs):
            if kwargs.get("commit") is False:
                raise RuntimeError("ledger unavailable")
            return real_save(*args, **kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            with patch("bosshunter.collection.orchestrator.save_city_state", side_effect=fail_ledger):
                result = CollectionOrchestrator({}, db_path=path, registry=registry).run({"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["A"], "cities": ["北京"], "max_pages": 1}}})
            with closing(get_db(path)) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)
            self.assertEqual(result["platforms"]["boss"]["reason_code"], "persistence_error")
            self.assertEqual(get_collection_run(path, result["run_id"])["collected_job_ids"], [])
        self.assertTrue(browser.closed)

    def test_ui_failure_keeps_committed_job_and_city_event(self):
        browser = SearchBrowser([[card("new")]])
        registry = CollectorRegistry({"boss": lambda: collector(browser)})
        def broken_ui(state):
            if state.get("new"):
                raise RuntimeError("UI unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            result = CollectionOrchestrator({"_workbench_collect_progress": broken_ui}, db_path=path, registry=registry).run({"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["A"], "cities": ["北京"], "max_pages": 1}}})
            run = get_collection_run(path, result["run_id"])
            self.assertEqual(run["collected_job_ids"], ["new"])
            self.assertEqual(run["boss_checkpoint"]["cities"]["北京"]["new_total"], 1)
            self.assertEqual(len(run["boss_checkpoint"]["cities"]["北京"]["window_events"]), 1)
        self.assertTrue(browser.closed)

    def test_city_aliases_keep_first_occurrence_and_order(self):
        options = normalize_collection_options({}, {"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["A"], "cities": ["上海", "北京", "上海市"]}}})
        self.assertEqual(options["platforms"]["boss"]["cities"], ["上海", "北京"])

    def test_existing_search_skips_unknown_region_without_blocking_valid_cities(self):
        cities = ["深圳", "浙江", "杭州", "成都", "南京", "北京", "上海"]
        config = {"search": {"keywords": ["AI"], "cities": cities},
                  "platforms": {"boss": {"search": {"keywords": ["AI"], "cities": cities}}}}
        original = deepcopy(config)
        options = normalize_collection_options(config)
        boss = options["platforms"]["boss"]
        self.assertEqual(boss["cities"], cities)
        self.assertNotIn("浙江", boss["city_codes"])
        self.assertEqual(boss["city_codes"]["杭州"], "101210100")
        self.assertEqual(config, original)
        browser = SearchBrowser([[card("one")]])
        registry = CollectorRegistry({"boss": lambda: collector(browser)})
        logs = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            result = CollectionOrchestrator({"_workbench_log": logs.append}, db_path=path, registry=registry).run(options)
            self.assertFalse(get_collection_run(path, result["run_id"])["can_resume"])
        search_urls = [url for url in browser.opens if "job_detail" not in url]
        self.assertEqual(len(search_urls), 6)
        self.assertTrue(any("浙江" in log and "跳过" in log for log in logs))
        self.assertNotEqual(result["platforms"]["boss"]["reason_code"], "no_valid_city")

    def test_full_offline_catalog_and_city_suffix_are_used(self):
        with patch("bosshunter.cities.httpx.get") as network:
            options = normalize_collection_options({}, {"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["AI"], "cities": ["温州", "温州市", "宁波"]}}})
        boss = options["platforms"]["boss"]
        self.assertEqual(boss["cities"], ["温州", "宁波"])
        self.assertEqual(boss["city_codes"]["温州"], "101210700")
        network.assert_not_called()

    def test_every_city_offered_by_the_catalog_is_accepted_for_collection(self):
        catalog = get_city_map()
        options = normalize_collection_options({}, {"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["AI"], "cities": list(catalog)}}})
        self.assertEqual(options["platforms"]["boss"]["city_codes"], catalog)

    def test_all_unknown_regions_still_rejected_with_names(self):
        with self.assertRaisesRegex(ValueError, "浙江.*不存在的城市"):
            normalize_collection_options({}, {"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["AI"], "cities": ["浙江", "不存在的城市"]}}})

    def test_explicit_region_code_preserves_region_and_order(self):
        options = normalize_collection_options({}, {"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["AI"], "cities": ["浙江", "杭州"], "city_codes": {"浙江": "101210000"}}}})
        self.assertEqual(options["platforms"]["boss"]["cities"], ["浙江", "杭州"])
        self.assertEqual(options["platforms"]["boss"]["city_codes"]["浙江"], "101210000")

    def test_timing_gap_remains_stopped_and_preserves_its_reason(self):
        fake = Mock()
        fake.collect.return_value = PlatformCollectionResult("boss", "stopped", "timing_gap", "计时中断")
        registry = CollectorRegistry({"boss": lambda: fake})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            result = CollectionOrchestrator({}, db_path=path, registry=registry).run({"platform_order": ["boss"], "platforms": {"boss": {"keywords": ["A"], "cities": ["北京"]}}})
            saved = get_collection_run(path, result["run_id"])
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(saved["stop_reason"], "timing_gap")
