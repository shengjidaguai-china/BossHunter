from unittest import TestCase

from bosshunter.collection.city_yield import CityYieldTracker, normalize_city_policy


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class CityYieldTests(TestCase):
    def setUp(self):
        self.clock = Clock()
        self.tracker = CityYieldTracker(normalize_city_policy(), clock=self.clock)

    def insert(self, *times):
        for index, value in enumerate(times):
            self.tracker.record_inserted(str(index), value)

    def test_first_check_and_exact_threshold(self):
        self.insert(*([550000] * 5))
        self.clock.value = 599.999
        self.assertEqual(self.tracker.evaluate_due(), "continue")
        self.clock.value = 600
        self.assertEqual(self.tracker.evaluate_due(), "continue")
        self.assertEqual(self.tracker.state["last_window_new"], 5)
        self.assertEqual(self.tracker.state["next_check_ms"], 900000)

    def test_early_burst_cannot_rescue_later_window(self):
        self.insert(*([100000] * 100))
        self.clock.value = 600
        self.assertEqual(self.tracker.evaluate_due(), "low_yield")
        self.assertEqual(self.tracker.state["new_total"], 100)

    def test_left_open_right_closed_and_late_event(self):
        self.insert(300000, 300001, 600000, 600001)
        self.clock.value = 620
        self.assertEqual(self.tracker.evaluate_due(), "low_yield")
        self.assertEqual(self.tracker.state["last_window_new"], 2)

    def test_continuous_checks_have_no_fifteen_minute_deadline(self):
        for deadline in (600, 900, 1200, 1500):
            self.insert(*([deadline * 1000 - 1] * 5))
            self.clock.value = deadline
            self.assertEqual(self.tracker.evaluate_due(), "continue")
            self.assertEqual(self.tracker.state["window_events"], [])
        self.clock.value = 1800
        self.assertEqual(self.tracker.evaluate_due(), "low_yield")

    def test_resume_preserves_active_time_and_events(self):
        self.clock.value = 570
        self.insert(*([560000] * 4))
        saved = self.tracker.snapshot()
        self.clock.value = 10000
        resumed = CityYieldTracker(normalize_city_policy(), saved, clock=self.clock)
        self.clock.value += 30
        self.assertEqual(resumed.elapsed_ms(), 600000)
        self.assertEqual(resumed.evaluate_due(), "low_yield")

    def test_timing_gap_is_not_low_yield(self):
        self.clock.value = 900
        self.assertEqual(self.tracker.evaluate_due(), "timing_gap")
        saved = self.tracker.snapshot()
        saved["new_total"] = 12
        resumed = CityYieldTracker(normalize_city_policy(), saved, clock=self.clock)
        self.assertEqual(resumed.elapsed_ms(), 0)
        self.assertEqual(resumed.state["new_total"], 12)
        self.assertEqual(resumed.state["next_check_ms"], 600000)

    def test_prospective_transaction_state_does_not_mutate_memory(self):
        prospective = self.tracker.with_insert("pending", 500000)
        self.assertEqual(prospective["new_total"], 1)
        self.assertEqual(self.tracker.state["new_total"], 0)

    def test_disabled_policy_never_judges_yield(self):
        tracker = CityYieldTracker(normalize_city_policy({"enabled": False}), clock=self.clock)
        self.clock.value = 99999
        self.assertEqual(tracker.evaluate_due(), "continue")

    def test_strict_parameters_and_boundaries(self):
        for field in ("warmup_minutes", "window_minutes", "min_new_jobs"):
            for invalid in (True, False, 0, -1, "5", 1.5, None, float("nan"), float("inf")):
                with self.subTest(field=field, value=invalid), self.assertRaises(ValueError):
                    normalize_city_policy({field: invalid})
        for invalid in ("true", 1, None):
            with self.subTest(enabled=invalid), self.assertRaises(ValueError):
                normalize_city_policy({"enabled": invalid})
        for invalid in ({"warmup_minutes": 1, "window_minutes": 2}, {"typo": 1}, []):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                normalize_city_policy(invalid)
        self.assertEqual(normalize_city_policy({"min_new_jobs": 1000})["min_new_jobs"], 1000)
