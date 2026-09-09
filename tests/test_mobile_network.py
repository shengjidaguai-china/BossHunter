"""Tests for mobile deployment and network utilities."""

import unittest
from unittest.mock import patch

from click.testing import CliRunner
from bosshunter.main import cli
from bosshunter.web.network_utils import get_lan_ips, render_terminal_qr, print_mobile_banner


class MobileNetworkTests(unittest.TestCase):
    def test_get_lan_ips_returns_valid_list(self):
        ips = get_lan_ips()
        self.assertIsInstance(ips, list)
        self.assertTrue(len(ips) >= 1)
        # 确保返回的不是空字符串
        for ip in ips:
            self.assertTrue(len(ip) > 0)

    def test_render_terminal_qr_generates_ansi_matrix(self):
        url = "http://10.3.182.148:8686"
        qr_text = render_terminal_qr(url)
        self.assertIsInstance(qr_text, str)
        self.assertTrue(len(qr_text) > 0)
        # 检查是否包含 ANSI 空格背景色块
        self.assertIn("\033[40m  \033[0m", qr_text)
        self.assertIn("\033[47m  \033[0m", qr_text)

    def test_print_mobile_banner_outputs_links_and_qr(self):
        with patch("bosshunter.web.network_utils.get_lan_ips", return_value=["192.168.1.100"]):
            with patch("builtins.print") as mock_print:
                print_mobile_banner(host="0.0.0.0", port=8686, show_qr=True)
                printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list if call.args])
                self.assertIn("127.0.0.1:8686", printed_text)
                self.assertIn("192.168.1.100:8686", printed_text)
                self.assertIn("手机端访问", printed_text)

    def test_cli_web_options_support_host_and_mobile_flags(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["web", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--host", result.output)
        self.assertIn("0.0.0.0", result.output)
        self.assertIn("--no-qr", result.output)
