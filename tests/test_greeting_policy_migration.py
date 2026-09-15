import unittest

from bosshunter.ai import greeter


class GreetingPolicyMigrationTests(unittest.TestCase):
    def test_prompt_requires_product_suggestion_and_fact_grounded_self_recommendation(self):
        self.assertIn("产品判断或建议", greeter.GREETING_PROMPT)
        self.assertIn("信息不足时写成待验证的场景假设", greeter.GREETING_PROMPT)
        self.assertIn("自然带出一条自荐理由", greeter.GREETING_PROMPT)
        self.assertIn("不得写具体项目名称", greeter.GREETING_PROMPT)
        self.assertIn("不得出现曾任职公司的名称", greeter.GREETING_PROMPT)
        self.assertIn("去 AI 味内嵌步骤", greeter.GREETING_PROMPT)
        self.assertIn("建议质量", greeter.REVIEW_PROMPT)
        self.assertIn("自荐可信度", greeter.REVIEW_PROMPT)

    def test_single_optional_project_reference_is_allowed(self):
        issues = greeter._greeting_style_issues(
            "可以先验证知识命中率，我做过相关项目落地，使用Agent工作流和RAG架构。"
        )
        self.assertEqual(issues, [])

    def test_template_and_fixed_skeleton_trigger_rewrite(self):
        opening_issues = greeter._greeting_style_issues(
            "贵司岗位强调知识库建设，我做过相关评测，可以参与效果验证。"
        )
        skeleton_issues = greeter._greeting_style_issues(
            "建议先整理失败样本，我做过相关评测，希望有机会进一步沟通。"
        )
        self.assertTrue(any("模板化开头" in issue for issue in opening_issues))
        self.assertTrue(any("固定骨架" in issue for issue in skeleton_issues))

    def test_missing_suggestion_or_evidence_triggers_rewrite(self):
        missing_suggestion = greeter._greeting_style_issues("我做过相关评测设计，能够参与效果验证。")
        missing_evidence = greeter._greeting_style_issues("建议先验证转人工率，再逐步扩大使用范围。")
        self.assertTrue(any("具体产品或业务建议" in issue for issue in missing_suggestion))
        self.assertTrue(any("自荐理由" in issue for issue in missing_evidence))


if __name__ == "__main__":
    unittest.main()
