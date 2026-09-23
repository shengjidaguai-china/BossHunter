"""Run the BOSS page-risk script against representative browser URLs."""

import json
import shutil
import subprocess
import unittest

from bosshunter.collection.platforms.boss import JS_DETECT_COLLECTION_RISK

_NODE_HARNESS = """
const fs = require('node:fs');
const vm = require('node:vm');
const { script, cases } = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(({ url, title, body, hasContent, captcha }) => {
    const document = {
        title: title || '岗位列表',
        body: { innerText: body || '' },
        querySelector: (selector) => selector.startsWith('.job-card-wrap')
            ? (hasContent === false ? null : {})
            : (captcha ? {} : null),
    };
    return JSON.parse(vm.runInNewContext(script, {
        URL,
        document,
        location: { href: url },
    }));
});
process.stdout.write(JSON.stringify(results));
"""


class BossRiskDetectionTests(unittest.TestCase):
    def test_url_and_page_evidence(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute the browser risk script")

        base = "https://www.zhipin.com/web/geek/job"
        normal = {"risk": None}
        blocked_url = {"risk": "blocked", "evidence": "blocked_url"}
        cases = [
            ("normal search", {"url": base}, normal),
            ("redirected search path", {"url": "https://www.zhipin.com/web/geek/jobs?salary=403"}, normal),
            ("salary 403 at end", {"url": f"{base}?salary=403"}, normal),
            ("salary 403 before another filter", {"url": f"{base}?salary=403&city=101010100"}, normal),
            ("salary 403 after another filter", {"url": f"{base}?city=101010100&salary=403"}, normal),
            ("other numeric filter", {"url": f"{base}?city=403"}, normal),
            ("numeric search term", {"url": f"{base}?query=403"}, normal),
            ("encoded numeric search term", {"url": f"{base}?query=%34%30%33"}, normal),
            ("error word as search term", {"url": f"{base}?query=forbidden"}, normal),
            ("error phrase as search term", {"url": f"{base}?query=access-denied"}, normal),
            ("error phrase with spaces", {"url": f"{base}?query=403%20Forbidden"}, normal),
            ("numeric parameter name", {"url": f"{base}?403=value"}, normal),
            ("return URL containing 403", {"url": f"{base}?return_url=https%3A%2F%2Fexample.com%2F403"}, normal),
            ("non-error status", {"url": f"{base}?status=open"}, normal),
            ("non-error code", {"url": f"{base}?code=4030"}, normal),
            ("numeric fragment", {"url": f"{base}#403"}, normal),
            ("word fragment", {"url": f"{base}#forbidden"}, normal),
            ("job identifier", {"url": "https://www.zhipin.com/job_detail/403.html"}, normal),
            ("job identifier containing 403", {"url": "https://www.zhipin.com/job_detail/abc403def.html"}, normal),
            ("403 path", {"url": "https://www.zhipin.com/403"}, blocked_url),
            ("nested forbidden path", {"url": "https://www.zhipin.com/error/forbidden/"}, blocked_url),
            ("access denied path", {"url": "https://www.zhipin.com/access-denied"}, blocked_url),
            ("code 403", {"url": f"{base}?code=403"}, blocked_url),
            ("status 403", {"url": f"{base}?status=403"}, blocked_url),
            ("encoded status", {"url": f"{base}?status=%34%30%33"}, blocked_url),
            ("error forbidden", {"url": f"{base}?error=forbidden"}, blocked_url),
            ("error code", {"url": f"{base}?error_code=access-denied"}, blocked_url),
            ("salary plus real error", {"url": f"{base}?salary=403&code=403"}, blocked_url),
            (
                "blocked title",
                {"url": base, "title": "403 Forbidden"},
                {"risk": "blocked", "evidence": "blocked_title"},
            ),
            (
                "salary filter on a real 403 page",
                {"url": f"{base}?salary=403", "title": "403 Forbidden", "hasContent": False},
                {"risk": "blocked", "evidence": "blocked_title"},
            ),
            (
                "blocked page",
                {"url": base, "body": "403 Forbidden", "hasContent": False},
                {"risk": "blocked", "evidence": "blocked_page"},
            ),
            (
                "captcha route",
                {"url": "https://www.zhipin.com/captcha"},
                {"risk": "captcha", "evidence": "captcha_url"},
            ),
            (
                "verify route",
                {"url": "https://www.zhipin.com/verify"},
                {"risk": "captcha", "evidence": "captcha_url"},
            ),
            (
                "security check route",
                {"url": "https://www.zhipin.com/security-check"},
                {"risk": "captcha", "evidence": "captcha_url"},
            ),
            ("captcha element", {"url": base, "captcha": True}, {"risk": "captcha", "evidence": "captcha_element"}),
            (
                "salary filter with captcha element",
                {"url": f"{base}?salary=403", "captcha": True},
                {"risk": "captcha", "evidence": "captcha_element"},
            ),
            (
                "captcha page",
                {"url": base, "body": "请完成验证码", "hasContent": False},
                {"risk": "captcha", "evidence": "captcha_page"},
            ),
            (
                "login route",
                {"url": "https://www.zhipin.com/web/user/login"},
                {"risk": "login_required", "evidence": "login_url"},
            ),
            (
                "rate limit page",
                {"url": base, "body": "操作频繁，请稍后再试", "hasContent": False},
                {"risk": "rate_limit", "evidence": "rate_limit_page"},
            ),
        ]
        payload = {"script": JS_DETECT_COLLECTION_RISK, "cases": [case for _, case, _ in cases]}
        result = subprocess.run(
            [node, "-e", _NODE_HARNESS],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        for (name, _, expected), observed in zip(cases, actual, strict=True):
            with self.subTest(name=name):
                self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
