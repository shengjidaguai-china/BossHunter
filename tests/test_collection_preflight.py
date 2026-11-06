from unittest import TestCase
from unittest.mock import patch

from bosshunter.web.preflight import collect_preflight_checks
from bosshunter.web.server import _preflight_messages


class CollectionPreflightTests(TestCase):
    def test_unknown_region_is_an_actionable_warning_when_other_cities_are_valid(self):
        config = {"search": {"keywords": ["AI"], "cities": ["深圳", "浙江", "杭州"]}}
        with patch("bosshunter.web.preflight.check_browser_connection", return_value=[]):
            checks = collect_preflight_checks("collect", config)
        self.assertFalse(any(check["status"] == "error" for check in checks))
        warnings = [check for check in checks if check["status"] == "warning"]
        self.assertTrue(any("浙江" in str(check) and "跳过" in str(check) for check in warnings))

    def test_all_unknown_regions_block_start_with_specific_names(self):
        config = {"search": {"keywords": ["AI"], "cities": ["浙江"]}}
        with patch("bosshunter.web.preflight.check_browser_connection", return_value=[]):
            checks = collect_preflight_checks("collect", config)
        self.assertTrue(any(check["status"] == "error" and "浙江" in check["message"] for check in checks))

    def test_pure_collection_does_not_call_ai_even_when_ai_configured(self):
        options = {
            "platform_order": ["boss"],
            "auto_score": False,
            "platforms": {
                "boss": {
                    "keywords": ["AI"],
                    "cities": ["北京"],
                    "city_codes": {},
                    "max_pages": 1,
                    "sort": "default",
                },
            },
        }
        with patch("bosshunter.web.preflight.check_ai_connection") as check_ai, patch(
            "bosshunter.web.preflight.check_browser_connection",
            return_value=[{"id": "browser", "status": "pass", "message": "ok", "detail": "ok", "action": ""}],
        ):
            checks = collect_preflight_checks("collect", {"ai": {"api_key": "saved-but-not-used"}}, options)

        check_ai.assert_not_called()
        self.assertTrue(any(check["id"] == "ai_connection" and check["status"] == "pass" for check in checks))

    def test_full_flow_accepts_enabled_zhilian_platform_adapter(self):
        messages = _preflight_messages("full", {
            "search": {"keywords": ["人力"], "cities": ["深圳"]},
            "profile": {},
            "platforms": {
                "boss": {"enabled": True, "search": {"keywords": ["人力"], "cities": ["深圳"]}},
                "zhilian": {"enabled": True, "search": {"keywords": ["人力"], "cities": ["深圳"]}},
            },
            "collection": {"default_order": ["boss"]},
        })

        self.assertFalse(any("智联只能单独采集和评分" in message for message in messages))
