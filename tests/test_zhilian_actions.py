from unittest import TestCase

from bosshunter.collection.capabilities import platform_supports


class NativeApplicationCapabilitiesTests(TestCase):
    def test_native_application_does_not_enable_monitoring(self):
        for platform in ("zhilian", "51job", "liepin"):
            for capability in ("collect", "score", "greet", "deliver"):
                self.assertTrue(platform_supports(platform, capability))
            self.assertFalse(platform_supports(platform, "monitor"))
        self.assertFalse(platform_supports("unknown", "deliver"))
