"""Regression coverage for component health versus Chrome readiness."""

import io
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from rich.console import Console

from bosshunter.browser.diagnostics import print_browser_diagnostics, run_browser_diagnostics
from bosshunter.web.preflight import check_browser_connection


class BrowserConnectionStateTests(unittest.TestCase):
    def test_connection_states_reach_web_and_cli(self):
        cases = [
            # name, health, targets, node, startup error, runtime ready, expected message
            ("chrome disconnected", {"runtime": "bosshunter"}, None, True, None, True, "没有连接到"),
            ("existing runtime without node", {"runtime": "bosshunter"}, None, False, None, True, "没有连接到"),
            ("component unreachable", None, None, True, None, False, "无法连接 BossHunter"),
            ("node missing", None, None, False, None, False, "缺少可用的 Node.js"),
            ("foreign service", {"runtime": "other"}, None, True, None, False, "端口被其他程序占用"),
            ("process startup failed", None, None, True, OSError("cannot spawn"), False, "进程启动失败"),
            ("connected without tabs", {"runtime": "bosshunter"}, [], True, None, True, "Google Chrome 已连接"),
        ]
        for name, health, targets, node, startup_error, runtime_ready, message in cases:
            with self.subTest(name=name), ExitStack() as stack:
                prefix = "bosshunter.browser.diagnostics."
                stack.enter_context(patch(prefix + "check_node_available", return_value={"available": node}))
                stack.enter_context(patch(prefix + "ensure_runtime", return_value=False, side_effect=startup_error))
                stack.enter_context(patch(prefix + "runtime_health", return_value=health))
                target_probe = stack.enter_context(patch(prefix + "runtime_targets", return_value=targets))
                boss = stack.enter_context(patch(prefix + "find_boss_tab", return_value=None))
                zhilian = stack.enter_context(patch(prefix + "find_zhilian_tab", return_value=None))
                result = run_browser_diagnostics({})
                self.assertEqual(result["runtime"], runtime_ready)
                self.assertEqual(result["chrome"], targets is not None)
                if not runtime_ready:
                    target_probe.assert_not_called()
                if targets is None:
                    boss.assert_not_called()
                    zhilian.assert_not_called()
                if runtime_ready and targets is None:
                    self.assertEqual(result["errors"], ["Chrome is not connected to Browser Runtime."])

                with patch("bosshunter.web.preflight.run_browser_diagnostics", return_value=result):
                    checks = check_browser_connection({})
                self.assertTrue(any(message in check["message"] for check in checks), checks)
                runtime_check = next(check for check in checks if check["id"] == "browser_runtime")
                self.assertEqual(runtime_check["status"], "pass" if runtime_ready else "error")
                if not runtime_ready:
                    self.assertFalse(any(check["id"] == "chrome_connection" for check in checks))

                output = io.StringIO()
                with patch(prefix + "run_browser_diagnostics", return_value=result):
                    ready = print_browser_diagnostics({}, Console(file=output, width=160))
                self.assertEqual(ready, runtime_ready and targets is not None)
                if not runtime_ready:
                    self.assertIn("暂未检测 Chrome", output.getvalue())
                elif targets is None:
                    self.assertIn("已启动，但未能连接 Chrome", output.getvalue())
