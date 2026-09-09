"""Regressions reproduced against BOSS's September 2026 search page."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock

from bosshunter.collection.base import CollectorHooks
from bosshunter.collection.models import PlatformCollectionRequest
from bosshunter.collection.orchestrator import CollectionOrchestrator
from bosshunter.collection.platforms.boss import (
    BossBrowser, BossCollector, JS_DETECT_COLLECTION_RISK, JS_EXTRACT_DETAIL,
    JS_EXTRACT_LIST, JS_IS_SCROLL_LIST, JS_DISPATCH_LIST_SCROLL, decode_boss_text,
)
from bosshunter.collection.registry import CollectorRegistry
from bosshunter.collection_run_store import get_collection_run, boss_combo_key
from bosshunter.db import get_db, count_platform_access_today


def card(job_id, salary="\ue033\ue036-\ue036\ue031K·\ue032\ue036薪"):
    # Captured textContent for the visible salary 25-50K·15薪.
    return {"title": "AI运营", "company": "测试公司", "salary": salary,
            "url": f"/job_detail/{job_id}.html"}


class SearchBrowser:
    def __init__(self, batches, *, scrolling=True):
        self.batches = batches
        self.scrolling = scrolling
        self.page = 0
        self.urls = {}
        self.opens = []
        self.scrolls = 0
        self.scroll_events = 0
        self.closed = []

    def open(self, url, **_):
        target = f"tab-{len(self.urls)}"
        self.urls[target] = url
        self.opens.append(url)
        return target

    def navigate(self, target, url):
        self.urls[target] = url
        self.opens.append(url)
        return True

    def scroll(self, target, **kwargs):
        assert "/job_detail/" not in self.urls[target], "Search must keep its own tab"
        if kwargs.get("direction") == "bottom":
            self.scrolls += 1
        return True

    def evaluate(self, target, script):
        if script == JS_IS_SCROLL_LIST:
            return self.scrolling
        if script == JS_DISPATCH_LIST_SCROLL:
            # Hidden tabs may move without delivering a native scroll event.
            assert self.scrolls > self.scroll_events
            self.scroll_events += 1
            self.page = min(self.page + 1, len(self.batches) - 1)
            return True
        if script == JS_DETECT_COLLECTION_RISK:
            return '{"risk": null}'
        if script == JS_EXTRACT_LIST:
            assert "/job_detail/" not in self.urls[target]
            return json.dumps(self.batches[self.page])
        if script == JS_EXTRACT_DETAIL:
            assert "/job_detail/" in self.urls[target]
            return json.dumps({"title": "AI运营", "company": "测试公司", "jd": "负责AI运营",
                               "salary": "\ue033\ue036-\ue036\ue031K·\ue032\ue036薪"})
        return None

    def browser(self):
        return BossBrowser(new_tab=self.open, navigate=self.navigate, evaluate=self.evaluate,
                           scroll=self.scroll, close_tab=self.closed.append,
                           wait_for_load=lambda *_, **__: True)


class BossSearchRegressionTests(TestCase):
    def collector(self, browser, conn=None, **config):
        return BossCollector(browser=browser.browser(), safety_conn=conn, sleep=lambda _: None,
                             throttle_factory=lambda **_: Mock(wait=lambda _: False), config=config)

    def hooks(self):
        self.seen = []
        self.saved = []
        self.errors = []
        self.checkpoints = []
        self.events = []
        return CollectorHooks(None, lambda c: self.seen.append(c) or True,
                              lambda c: self.saved.append(c) or True, self.errors.append,
                              lambda **event: self.events.append(event),
                              on_page_complete=lambda *args: self.checkpoints.append(args))

    def test_visible_salary_survives_prefilter_and_is_saved_as_digits(self):
        browser = SearchBrowser([[card("new-job")]])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            config = {"profile": {"salary_min": 13, "salary_max": 25,
                                  "salary_ceil_ratio": 1, "filter_unparsed_salary": True}}
            registry = CollectorRegistry({"boss": lambda: self.collector(browser, **config)})
            result = CollectionOrchestrator(config, db_path=path, registry=registry).run({
                "platform_order": ["boss"], "platforms": {"boss": {
                    "keywords": ["AI"], "cities": ["北京"], "max_pages": 1,
                }},
            })
            self.assertEqual(result["collected_job_ids"], ["new-job"])
            with get_db(path) as conn:
                row = conn.execute("SELECT salary FROM jobs WHERE id='new-job'").fetchone()
                self.assertEqual(row["salary"], "25-50K·15薪")
        self.assertEqual(decode_boss_text("\ue031\ue032\ue033\ue034\ue035\ue036\ue037\ue038\ue039\ue03a"), "0123456789")
        self.assertEqual(decode_boss_text("面议"), "面议")

    def test_unknown_font_is_parse_failure_not_salary_rejection(self):
        browser = SearchBrowser([[card("new-job", "\ue123-\ue124K")]])
        result = self.collector(browser, profile={"filter_unparsed_salary": True}).collect(
            PlatformCollectionRequest("boss", ["AI"], ["北京"], {}, max_pages=7), self.hooks())
        self.assertEqual(result.reason_code, "salary_decode_failed")
        self.assertEqual(self.saved, [])
        self.assertEqual(self.checkpoints, [])
        self.assertFalse(any(e.get("increment_filtered") for e in self.events))
        self.assertEqual(len(self.errors), 1)

    def test_scroll_appends_only_new_ids_and_keeps_search_open_during_details(self):
        browser = SearchBrowser([[card("a")], [card("a"), card("b")],
                                 [card("a"), card("b"), card("c")]])
        with tempfile.TemporaryDirectory() as tmp:
            conn = get_db(Path(tmp) / "jobs.db")
            self.addCleanup(conn.close)
            result = self.collector(browser, conn).collect(
                PlatformCollectionRequest("boss", ["AI"], ["北京"], {}, max_pages=3), self.hooks())
            self.assertEqual(result.status, "completed")
            self.assertEqual([c.source_job_id for c in self.seen], ["a", "b", "c"])
            self.assertEqual(len(self.saved), 3)
            self.assertEqual(browser.scrolls, 2)
            self.assertEqual(browser.scroll_events, 2)
            self.assertEqual(len([u for u in browser.opens if "/job_detail/" not in u]), 1)
            self.assertEqual(count_platform_access_today(conn, stage="collection", action="search_page"), 3)
            self.assertEqual([x[2] for x in self.checkpoints], [1, 2, 3])
            self.assertEqual(len(browser.closed), 2)

    def test_ignored_page_parameter_does_not_count_same_cards_seven_times(self):
        browser = SearchBrowser([[card("a"), card("b")]], scrolling=False)
        result = self.collector(browser).collect(
            PlatformCollectionRequest("boss", ["AI"], ["北京"], {}, max_pages=7), self.hooks())
        self.assertEqual(result.reason_code, "repeated_search_page")
        self.assertEqual(len(self.seen), 2)
        self.assertEqual(len(self.saved), 2)
        self.assertEqual([x[2] for x in self.checkpoints], [1])
        self.assertEqual(len([u for u in browser.opens if "/job_detail/" not in u]), 2)

    def test_stalled_scroll_leaves_checkpoint_at_last_verified_batch(self):
        browser = SearchBrowser([[card("a")]])
        result = self.collector(browser).collect(
            PlatformCollectionRequest("boss", ["AI"], ["北京"], {}, max_pages=7), self.hooks())
        self.assertEqual(result.reason_code, "search_page_not_advanced")
        self.assertEqual(len(self.seen), 1)
        self.assertEqual(browser.scrolls, 1)
        self.assertEqual([x[2] for x in self.checkpoints], [1])

    def test_resume_rebuilds_scroll_list_without_reprocessing_completed_batch(self):
        browser = SearchBrowser([[card("a")], [card("a"), card("b")],
                                 [card("a"), card("b"), card("c")]])
        hooks = self.hooks()
        hooks.completed_page = lambda *_: 1
        result = self.collector(browser).collect(
            PlatformCollectionRequest("boss", ["AI"], ["北京"], {}, max_pages=3), hooks)
        self.assertEqual(result.status, "completed")
        self.assertEqual([c.source_job_id for c in self.seen], ["b", "c"])
        self.assertEqual([x[2] for x in self.checkpoints], [2, 3])

    def test_scroll_respects_daily_limit_before_loading_more(self):
        browser = SearchBrowser([[card("a")], [card("a"), card("b")]])
        with tempfile.TemporaryDirectory() as tmp:
            conn = get_db(Path(tmp) / "jobs.db")
            self.addCleanup(conn.close)
            result = self.collector(browser, conn, collection={"daily_search_page_limit": 1}).collect(
                PlatformCollectionRequest("boss", ["AI"], ["北京"], {}, max_pages=3), self.hooks())
            self.assertEqual(result.reason_code, "daily_search_page_limit")
            self.assertEqual(browser.scrolls, 0)
            self.assertEqual(len(self.seen), 1)

    def test_stalled_run_remains_resumable_and_saves_only_remaining_new_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.db"
            browser = SearchBrowser([[card("a")]])
            registry = CollectorRegistry({"boss": lambda: self.collector(browser)})
            options = {"platform_order": ["boss"], "platforms": {"boss": {
                "keywords": ["AI"], "cities": ["北京"], "max_pages": 2,
            }}}
            first = CollectionOrchestrator({}, db_path=path, registry=registry).run(options)
            saved = get_collection_run(path, first["run_id"])
            self.assertTrue(saved["can_resume"])
            self.assertEqual(saved["boss_checkpoint"]["pages"], {boss_combo_key("北京", "AI"): 1})
            browser = SearchBrowser([[card("a")], [card("a"), card("b")]])
            resumed = CollectionOrchestrator({}, db_path=path, registry=registry).run({"resume_run_id": first["run_id"]})
            self.assertEqual(resumed["collected_job_ids"], ["a", "b"])
            self.assertEqual(resumed["platforms"]["boss"]["seen"], 2)
            self.assertFalse(get_collection_run(path, first["run_id"])["can_resume"])
