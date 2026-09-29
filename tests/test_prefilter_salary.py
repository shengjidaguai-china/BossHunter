import unittest


class PrefilterSalaryTests(unittest.TestCase):
    """_parse_salary_range_k — 覆盖 BOSS 的 K 写法与智联/前程无忧的元、千、万写法。"""

    def test_boss_k_format_unchanged(self):
        from bosshunter.ai.prefilter import _parse_salary_range_k

        self.assertEqual(_parse_salary_range_k("18-25K"), (18.0, 25.0))
        self.assertEqual(_parse_salary_range_k("7-11K·13薪"), (7.0, 11.0))
        self.assertEqual(_parse_salary_range_k("10-20K·15薪"), (10.0, 20.0))

    def test_yuan_monthly_range(self):
        from bosshunter.ai.prefilter import _parse_salary_range_k

        self.assertEqual(_parse_salary_range_k("8000-15000元"), (8.0, 15.0))
        self.assertEqual(_parse_salary_range_k("6000-9000元"), (6.0, 9.0))
        self.assertEqual(_parse_salary_range_k("5000-8000元·13薪"), (5.0, 8.0))
        self.assertEqual(_parse_salary_range_k("15000元"), (15.0, 15.0))

    def test_wan_and_qian_units(self):
        from bosshunter.ai.prefilter import _parse_salary_range_k

        self.assertEqual(_parse_salary_range_k("3-6万"), (30.0, 60.0))
        self.assertEqual(_parse_salary_range_k("1万-1.5万"), (10.0, 15.0))
        self.assertEqual(_parse_salary_range_k("8千-1.2万"), (8.0, 12.0))
        self.assertEqual(_parse_salary_range_k("5-8千元"), (5.0, 8.0))

    def test_yearly_salary_converted_to_monthly(self):
        from bosshunter.ai.prefilter import _parse_salary_range_k

        low, high = _parse_salary_range_k("25-38万/年")
        self.assertAlmostEqual(low, 250.0 / 12)
        self.assertAlmostEqual(high, 380.0 / 12)

    def test_unparsable_salary_still_returns_none(self):
        from bosshunter.ai.prefilter import _parse_salary_range_k

        self.assertIsNone(_parse_salary_range_k("面议"))
        self.assertIsNone(_parse_salary_range_k(""))
        # 没有单位也没有「元」字时无法判断币种，保持交给 AI 判断的原语义。
        self.assertIsNone(_parse_salary_range_k("15-25"))

    def test_quick_score_accepts_zhilian_yuan_salary(self):
        from bosshunter.ai.prefilter import quick_score

        config = {"profile": {"salary_min": 8, "salary_max": 15, "filter_unparsed_salary": True}}
        job = {"title": "初级评测与数据工程师", "company": "某某科技", "salary": "7000-14000元", "jd": ""}

        score, reason = quick_score(job, config)
        self.assertEqual(score, 100, reason)

    def test_quick_score_rejects_below_hard_floor(self):
        from bosshunter.ai.prefilter import quick_score

        config = {"profile": {"salary_min": 8, "salary_max": 15, "filter_unparsed_salary": True}}
        job = {"title": "助理网络安全测试工程师", "company": "某某汽车", "salary": "5000-7000元", "jd": ""}

        score, reason = quick_score(job, config)
        self.assertEqual(score, 0)
        self.assertIn("薪资低于硬性要求", reason)


if __name__ == "__main__":
    unittest.main()


class SalaryFilterResultTests(unittest.TestCase):
    """salary_filter_result — 采集增值层与 quick_score 共用的薪资硬过滤。"""

    def test_passes_when_within_range(self):
        from bosshunter.ai.prefilter import salary_filter_result

        profile = {"salary_min": 10, "salary_max": 20}
        self.assertEqual(salary_filter_result("12-18K", profile), (100, "预筛通过"))

    def test_blocked_below_hard_floor(self):
        from bosshunter.ai.prefilter import salary_filter_result

        score, reason = salary_filter_result("5-8K", {"salary_min": 10})
        self.assertEqual(score, 0)
        self.assertIn("薪资低于硬性要求", reason)

    def test_blocked_far_above_ceiling(self):
        from bosshunter.ai.prefilter import salary_filter_result

        score, reason = salary_filter_result("50-60K", {"salary_max": 20})
        self.assertEqual(score, 0)
        self.assertIn("薪资远超期望上限", reason)

    def test_above_ceiling_within_ratio_passes(self):
        from bosshunter.ai.prefilter import salary_filter_result

        # 25K ≤ 20K × 1.5，仍在可接受上浮范围内。
        self.assertEqual(salary_filter_result("25-28K", {"salary_max": 20})[0], 100)

    def test_unparsed_blocked_by_default(self):
        from bosshunter.ai.prefilter import salary_filter_result

        score, reason = salary_filter_result("面议", {"salary_min": 10})
        self.assertEqual(score, 0)
        self.assertIn("薪资面议/无法解析", reason)

    def test_unparsed_allowed_when_filter_disabled(self):
        from bosshunter.ai.prefilter import salary_filter_result

        score, reason = salary_filter_result("面议", {"filter_unparsed_salary": False})
        self.assertEqual(score, 100)
        self.assertIn("交由 AI 判断", reason)

    def test_no_thresholds_passes_parsed_salary(self):
        from bosshunter.ai.prefilter import salary_filter_result

        self.assertEqual(salary_filter_result("18-25K", {}), (100, "预筛通过"))
