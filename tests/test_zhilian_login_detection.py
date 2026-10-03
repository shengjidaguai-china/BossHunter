"""Login calls to action must not hide readable jobs; real walls still stop."""

import json
from pathlib import Path
import shutil
import subprocess
import unittest

from bosshunter.collection.base import CollectionBlockedError
from bosshunter.collection.platforms.zhilian import JS_EXTRACT_LIST, parse_zhilian_list_html


class ZhilianLoginDetectionTests(unittest.TestCase):
    def test_live_list_script_distinguishes_sidebar_from_login_wall(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute the list script")
        cases = [
            ({"text": "立即登录", "jobs": True}, "ready"),
            ({"text": "登录查看更多相关职位", "jobs": True}, "ready"),
            ({"text": "扫码登录", "jobs": True}, "ready"),
            ({"text": "立即登录", "jobs": False}, "login_required"),
            ({"text": "扫码登录", "jobs": True, "dialog": True}, "login_required"),
            ({"text": "立即登录", "jobs": True, "path": "/login/"}, "login_required"),
            ({"text": "", "jobs": True, "path": "/login/"}, "login_required"),
            ({"text": "登录失效", "jobs": True}, "login_required"),
            ({"text": "验证码 立即登录", "jobs": True}, "blocked"),
            ({"text": "访问频繁", "jobs": True}, "blocked"),
            ({"text": "", "jobs": False}, "empty"),
        ]
        harness = """
const fs = require('node:fs'), vm = require('node:vm');
const {script, cases} = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(c => {
    const field = {textContent: '合成岗位', getAttribute: () => '/jobdetail/synthetic.htm'};
    const card = {querySelector: () => field, querySelectorAll: () => [],
        matches: () => false, getAttribute: () => 'synthetic'};
    const document = {body: {innerText: c.text},
        querySelectorAll: () => c.jobs ? [card] : [],
        querySelector: s => s.includes('[role="dialog"]') ? (c.dialog ? {} : null) : {}};
    return JSON.parse(vm.runInNewContext(script, {URL, document,
        window: {location: {href: 'https://www.zhaopin.com' + (c.path || '/sou/jl530/'),
            pathname: c.path || '/sou/jl530/'}}})).status;
});
process.stdout.write(JSON.stringify(results));
"""
        result = subprocess.run(
            [node, "-e", harness], input=json.dumps({"script": JS_EXTRACT_LIST, "cases": [c for c, _ in cases]}),
            capture_output=True, text=True, timeout=20, check=True,
        )
        for (case, expected), actual in zip(cases, json.loads(result.stdout), strict=True):
            with self.subTest(case=case):
                self.assertEqual(actual, expected)

    def test_saved_list_with_login_cta_is_readable_but_real_walls_stop(self):
        html = (Path(__file__).parent / "fixtures" / "zhilian_current_search.html").read_text(encoding="utf-8")
        expected = parse_zhilian_list_html(html)
        self.assertTrue(expected)
        self.assertEqual(parse_zhilian_list_html(html + "<aside>立即登录查看更多</aside>"), expected)
        for notice in (
            '<div role="dialog">扫码登录</div>', '<div class="login-dialog">立即登录</div>',
            '<p>验证码</p>', '<p>账号异常</p>', '<p>登录失效</p>',
        ):
            with self.subTest(notice=notice), self.assertRaises(CollectionBlockedError):
                parse_zhilian_list_html(html + notice)
