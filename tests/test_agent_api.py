import unittest

from bosshunter.agent_api import AgentRequestError, agent_preferences, apply_preferences
from bosshunter.config import load_config


class AgentPreferencesTests(unittest.TestCase):
    def test_apply_preferences_updates_search_and_profile_without_touching_ai(self):
        config = load_config()
        config["ai"]["api_key"] = "private-key-must-not-be-exposed"

        updated, changes = apply_preferences(config, {
            "keywords": ["AI 应用工程师", "Python 后端"],
            "cities": ["杭州", "南京"],
            "salary": {"min": 20, "max": 35},
            "deal_breakers": ["外包", "996"],
            "score_threshold": 78,
            "platform_order": ["boss"],
            "max_pages": 2,
        })

        self.assertEqual(updated["search"]["keywords"], ["AI 应用工程师", "Python 后端"])
        self.assertEqual(updated["profile"]["target_cities"], ["杭州", "南京"])
        self.assertEqual(updated["profile"]["salary_min"], 20)
        self.assertEqual(updated["profile"]["salary_max"], 35)
        self.assertEqual(updated["platforms"]["boss"]["search"]["max_pages"], 2)
        self.assertFalse(updated["platforms"]["zhilian"]["enabled"])
        self.assertEqual(updated["ai"]["api_key"], "private-key-must-not-be-exposed")
        self.assertTrue(any(change["path"] == "profile.salary_min" for change in changes))
        self.assertFalse(any(change["path"].startswith("ai.") for change in changes))

    def test_agent_preferences_does_not_return_ai_credentials(self):
        config = load_config()
        config["ai"]["api_key"] = "private-key-must-not-be-exposed"

        preferences = agent_preferences(config)

        self.assertNotIn("ai", preferences)
        self.assertNotIn("private-key-must-not-be-exposed", str(preferences))

    def test_credentials_and_delivery_settings_are_rejected(self):
        for patch in (
            {"api_key": "not-allowed"},
            {"throttle": {"daily_limit": 200}},
            {"auto_score": True},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(AgentRequestError):
                    apply_preferences(load_config(), patch)

    def test_salary_range_and_page_limit_are_validated(self):
        with self.assertRaisesRegex(AgentRequestError, "salary.min"):
            apply_preferences(load_config(), {"salary": {"min": 40, "max": 20}})
        with self.assertRaisesRegex(AgentRequestError, "max_pages"):
            apply_preferences(load_config(), {"max_pages": 11})


if __name__ == "__main__":
    unittest.main()
