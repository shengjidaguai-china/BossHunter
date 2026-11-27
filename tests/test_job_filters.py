import unittest

from bosshunter.ai.prefilter import quick_score
from bosshunter.job_filters import (
    classify_hr_active,
    hr_active_rank_score,
    matching_blocked_company,
    matching_deal_breaker,
    parse_monthly_salary_k,
)


class JobFilterTests(unittest.TestCase):
    def test_parse_common_monthly_salary_formats(self):
        self.assertEqual(parse_monthly_salary_k("10-15K"), (10.0, 15.0))
        self.assertEqual(parse_monthly_salary_k("8-13K·13薪"), (8.0, 13.0))
        self.assertEqual(parse_monthly_salary_k("12K"), (12.0, 12.0))

    def test_unconvertible_salary_formats_are_not_parsed(self):
        self.assertIsNone(parse_monthly_salary_k("150-200元/天"))
        self.assertIsNone(parse_monthly_salary_k("薪资面议"))

    def test_blocked_company_matches_case_insensitive_substring(self):
        matched = matching_blocked_company("某公司科技有限公司", ["某公司"])

        self.assertEqual(matched, "某公司")

    def test_blocked_company_ignores_empty_rules(self):
        matched = matching_blocked_company("某公司科技有限公司", ["", "  "])

        self.assertIsNone(matched)

    def test_quick_score_filters_existing_job_by_company(self):
        score, reason = quick_score(
            {"title": "产品经理", "company": "某公司科技有限公司", "salary": "20-30K"},
            {"profile": {"blocked_companies": ["某公司"]}},
        )

        self.assertEqual(score, 0)
        self.assertIn("某公司", reason)


class DealBreakerTests(unittest.TestCase):
    def test_returns_first_matching_keyword(self):
        result = matching_deal_breaker("需要996加班", ["外包", "996", "大小周"])

        self.assertEqual(result, "996")

    def test_matching_is_case_insensitive(self):
        result = matching_deal_breaker("需要OUTSOURCING", ["外包", "outsourcing"])

        self.assertEqual(result, "outsourcing")

    def test_no_match_returns_none(self):
        result = matching_deal_breaker("正常工作制", ["外包", "996"])

        self.assertIsNone(result)

    def test_empty_or_whitespace_keywords_are_skipped(self):
        result = matching_deal_breaker("996", ["", "  ", "996"])

        self.assertEqual(result, "996")

    def test_empty_keyword_list_returns_none(self):
        result = matching_deal_breaker("任意文本", [])

        self.assertIsNone(result)


class BlockedCompanyEdgeCaseTests(unittest.TestCase):
    def test_none_company_returns_none(self):
        result = matching_blocked_company(None, ["某公司"])

        self.assertIsNone(result)

    def test_empty_company_returns_none(self):
        result = matching_blocked_company("", ["某公司"])

        self.assertIsNone(result)

    def test_none_rules_returns_none(self):
        result = matching_blocked_company("某公司", None)

        self.assertIsNone(result)

    def test_no_match_returns_none(self):
        result = matching_blocked_company("正常公司", ["某公司"])

        self.assertIsNone(result)

    def test_matches_first_rule(self):
        result = matching_blocked_company("ABC科技", ["abc", "科技"])

        self.assertEqual(result, "abc")


class SalaryParseEdgeCaseTests(unittest.TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(parse_monthly_salary_k(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_monthly_salary_k(""))

    def test_decimal_k_range(self):
        self.assertEqual(parse_monthly_salary_k("10.5-15.5K"), (10.5, 15.5))

    def test_single_decimal_k(self):
        self.assertEqual(parse_monthly_salary_k("12.5K"), (12.5, 12.5))

    def test_reversed_range_is_normalized(self):
        self.assertEqual(parse_monthly_salary_k("15-10K"), (10.0, 15.0))

    def test_lowercase_k(self):
        self.assertEqual(parse_monthly_salary_k("10-15k"), (10.0, 15.0))


class HrActiveFilterTests(unittest.TestCase):
    def test_classify_hr_active_tiers(self):
        cases = [
            ("在线", "online"),
            ("刚刚活跃", "just_now"),
            ("今日活跃", "today"),
            ("1日内活跃", "today"),
            ("本周活跃", "week"),
            ("3日内活跃", "week"),
            ("两天内活跃", "week"),
            ("1周内活跃", "week"),
            ("本月活跃", "month"),
            ("十天内活跃", "month"),
            ("2周内活跃", "month"),
            ("1个月内活跃", "month"),
            ("2月内活跃", "older"),
            ("3个月内活跃", "older"),
            ("4月内活跃", "older"),
            ("半年前活跃", "older"),
            ("", "unknown"),
            ("   ", "unknown"),
            (None, "unknown"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(classify_hr_active(raw), expected)

    def test_hr_active_rank_score_orders_by_recency(self):
        ordered = [
            "在线",
            "刚刚活跃",
            "今日活跃",
            "3日内活跃",
            "本周活跃",
            "2周内活跃",
            "本月活跃",
            "2月内活跃",
            "4月内活跃",
            "半年前活跃",
            "",
        ]
        scores = [hr_active_rank_score(label) for label in ordered]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_quick_score_respects_min_hr_active_and_preserves_unknown(self):
        base_job = {"title": "全栈工程师", "company": "示例公司", "salary": "15-25K"}
        cfg_week = {"profile": {"min_hr_active": "week", "salary_min": 0}}

        for passing in ("在线", "刚刚活跃", "今日活跃", "3日内活跃", "本周活跃", "", None):
            with self.subTest(passing=passing):
                score, _ = quick_score({**base_job, "hr_active": passing}, cfg_week)
                self.assertEqual(score, 100)

        for blocked in ("2周内活跃", "本月活跃", "2月内活跃", "半年前活跃"):
            with self.subTest(blocked=blocked):
                score, reason = quick_score({**base_job, "hr_active": blocked}, cfg_week)
                self.assertEqual(score, 0)
                self.assertIn("招聘者活跃度低于要求", reason)

        # Default (empty min_hr_active) keeps older recruiters.
        score, _ = quick_score({**base_job, "hr_active": "半年前活跃"}, {"profile": {"salary_min": 0}})
        self.assertEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
