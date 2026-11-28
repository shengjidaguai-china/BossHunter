"""Read job pages in the user's connected Chrome profile."""

from __future__ import annotations

import re
from collections.abc import Mapping
from threading import Event
from urllib.parse import parse_qsl, urlencode, urlsplit

from bosshunter import browser
from bosshunter.cities import get_city_map
from bosshunter.collection.base import CollectionError
from bosshunter.collection.models import JobCandidate, PlatformCollectionResult
from bosshunter.platform_safety import PlatformAccessGuard, PlatformSafetyStop

HOST = "www.shixiseng.com"
SEARCH_PATH = "/interns"
JOB_PATH = re.compile(r"/intern/(inn_[A-Za-z0-9]{1,80})")
SOURCE_HINT = "请在 BossHunter 连接的 Chrome 中登录实习僧，并保持实习僧标签页打开。"
SAFETY_STOP_HINT = "实习僧访问已达到页面额度或处于安全暂停。"
RISK_CHECK = r"""
const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
const displayed = el => {
    if (!visible(el)) return false;
    // The site preloads the challenge in a transparent wrapper before displaying it.
    for (let parent = el; parent; parent = parent.parentElement) {
        if (getComputedStyle(parent).opacity === '0') return false;
    }
    return true;
};
const text = el => el?.innerText?.trim() || '';
if (location.protocol !== 'https:' || location.host !== 'www.shixiseng.com') return {risk:'unexpected_page'};
if (document.readyState === 'loading') return {risk:'loading'};
const head = document.title + ' ' + (document.body?.innerText || '').slice(0, 500);
if (Array.from(document.querySelectorAll('iframe[src*="captcha"], [class*="captcha"], [id*="captcha"]')).some(displayed)
    || /安全验证|滑块验证|访问过于频繁|访问受限|请求被拦截|403 Forbidden/.test(head)) return {risk:'blocked'};
if (/^\/(?:user\/)?(?:login|signin)\b/.test(location.pathname)
    || Array.from(document.querySelectorAll('input[type="password"], input[placeholder*="短信验证码"]')).some(visible)
    || /登录后查看|登录后继续|登录失效/.test(head)) return {risk:'login_required'};
"""
READ_SESSION = (
    """(() => {
"""
    + RISK_CHECK
    + """
return {loggedIn: Array.from(document.querySelectorAll('.login-status .logined, .login-status.logined, .logined')).some(visible)};
})()"""
)
READ_RESULTS = (
    r"""(() => {
"""
    + RISK_CHECK
    + r"""
if (!/^\/interns\/?$/.test(location.pathname)) return {risk:'unexpected_page'};
if (/登录\s*[/／]\s*注册/.test(head)) return {risk:'login_required'};
const anchors = Array.from(document.querySelectorAll('a[href]')).filter(visible);
const cards = anchors.filter(a=>a.classList.contains('title'));
const links = (cards.length ? cards : anchors).filter(a=>/^https:\/\/www\.shixiseng\.com\/intern\/inn_[A-Za-z0-9]+(?:[?#]|$)/.test(a.href));
const jobs = [...new Set(links.map(a=>a.href))].slice(0,20);
const next = anchors.find(a=>a.rel === 'next' || /^(下一页|下页)$/.test(text(a)));
const empty = Array.from(document.querySelectorAll('p,span,div')).some(e=>visible(e) && /^(暂无相关职位|没有找到相关职位|没有找到符合条件的职位)$/.test(text(e)));
const titles = Object.fromEntries(links.filter(a=>a.classList.contains('title')).map(a=>[a.href,text(a)]));
return {url: location.href, jobs, titles, next:next?.href || '', empty};
})()"""
)
READ_DETAIL = (
    r"""(() => {
"""
    + RISK_CHECK
    + r"""
if (!/^\/intern\/inn_[A-Za-z0-9]+$/.test(location.pathname)) return {risk:'unexpected_page'};
const bodyLines = (document.body?.innerText || '').split(/\n/).map(x=>x.trim()).filter(Boolean);
const jdStart = bodyLines.findIndex(x=>/^职位描述\s*[:：]?$/.test(x));
const jdEnd = bodyLines.findIndex((x,i)=>i>jdStart && /^(投递要求|工作地点)\s*[:：]?$/.test(x));
const heading = Array.from(document.querySelectorAll('h1, h2')).find(e=>visible(e) && !/^(实习僧|职位描述)$/.test(text(e)));
const titleParts = document.title.split(/实习招聘-|招聘-|-实习僧$/);
const companyIndex = bodyLines.indexOf('公司简介');
const company = companyIndex >= 0 ? bodyLines[companyIndex + 1] || '' : '';
const addressIndex = bodyLines.findIndex(t=>/^工作地点\s*[:：]?$/.test(t));
const headingText = text(heading);
const properTitle = headingText && !/[\uE000-\uF8FF]/.test(headingText) ? headingText : (titleParts.length>=3 ? titleParts[0].trim() : '');
return {
  url:location.href, title:properTitle, company,
  facts: (jdStart >= 0 ? bodyLines.slice(Math.max(0,jdStart-18),jdStart) : bodyLines.slice(0,24))
    .filter(line => /[/／]\s*(?:天|日|周|小时|时)|实习\s*[0-9]+\s*个月|薪资面议/.test(line)).join(' '),
  address: addressIndex >= 0 ? bodyLines[addressIndex + 1] || '' : '',
  jd: jdStart >= 0 && jdEnd>jdStart ? bodyLines.slice(jdStart+1,jdEnd).join('\n').slice(0,12000) : ''
};
})()"""
)


def site_url(value):
    try:
        url = urlsplit(str(value or ""))
        if url.scheme == "https" and url.netloc == HOST:
            return url
    except ValueError:
        pass
    return None


def target_id(target):
    return str(target.get("targetId") or target.get("id") or "")


def platform_tabs(targets):
    return [row for row in targets if isinstance(row, Mapping) and target_id(row) and site_url(row.get("url"))]


def search_url(city: str, keyword: str) -> str:
    return f"https://{HOST}{SEARCH_PATH}?" + urlencode({"keyword": keyword, "city": city, "type": "intern"})


def job_url(value):
    url = site_url(value)
    match = JOB_PATH.fullmatch(url.path) if url else None
    return (match[1], f"https://{HOST}{url.path}") if match else None


def next_results_page(current, following):
    """Follow only a visible next link with the same search parameters."""
    a, b = site_url(current), site_url(following)
    if not a or not b or b.path.rstrip("/") != SEARCH_PATH:
        return ""
    before, after = parse_qsl(a.query), parse_qsl(b.query)
    if len(before) != len(dict(before)) or len(after) != len(dict(after)):
        return ""
    old, new = dict(before), dict(after)
    for key in ("page", "p"):
        left, right = old.get(key, "1"), new.get(key, "")
        if (
            re.fullmatch(r"[0-9]{1,4}", left)
            and re.fullmatch(r"[0-9]{1,4}", right)
            and int(right) == int(left) + 1
            and {k: v for k, v in old.items() if k != key} == {k: v for k, v in new.items() if k != key}
        ):
            return following
    return ""


def read_page(runtime, tab, script, guard=None):
    raw = runtime.evaluate(tab, script, timeout=5)
    if not isinstance(raw, dict):
        raise CollectionError("selector_changed", "未读取到实习僧网页所需内容。")
    if raw.get("risk") == "blocked":
        if guard:
            guard.lock("shixiseng_browser_blocked")
        raise CollectionError("restricted_page", "实习僧网页出现访问限制，已停止。")
    if raw.get("risk") == "login_required":
        raise CollectionError("login_required", SOURCE_HINT)
    if raw.get("risk"):
        raise CollectionError("selector_changed", "实习僧网页未就绪或结构不匹配，已停止。")
    return raw


def build_candidate(raw, cities, keyword, *, fallback_title=""):
    if not (identity := job_url(raw.get("url"))):
        return None
    title, company, jd, facts, address = (
        str(raw.get(k) or "").strip() for k in ("title", "company", "jd", "facts", "address")
    )
    def visible_name(value):
        return value if len(value) <= 200 and not any("\ue000" <= char <= "\uf8ff" for char in value) else ""

    title = visible_name(title) or visible_name(fallback_title) or "职位名称待核对"
    company = visible_name(company) or "公司未知"
    city = ""
    city_options = dict.fromkeys([*(name for name in cities if name != "全国"), *get_city_map()])
    for name in city_options:
        base = re.escape(name.removesuffix("市"))
        if re.match(rf"^{base}(?:市)?(?:[\/·]|$)", address) or re.search(
            rf"(?<![\u4e00-\u9fff]){base}(?:市)?(?![\u4e00-\u9fff])", facts
        ):
            city = name
            break
    if city and "全国" not in cities and city not in cities:
        return None
    pay = re.search(r"(?<![\d.])\d+(?:\.\d+)?(?:\s*[-–~至]\s*\d+(?:\.\d+)?)?\s*(?:元\s*)?[/／]\s*(?:天|日|周|小时|时)", facts)
    salary = pay[0] if pay else "薪资面议" if "薪资面议" in facts else ""
    days = re.search(r"(?<![0-9])([1-7])\s*天\s*[/／]\s*周", facts)
    month = re.search(r"实习\s*([1-9][0-9]?)\s*个月", facts)
    degree = re.search(r"(?<![\u4e00-\u9fff])(大专|本科|硕士|博士|不限)(?![\u4e00-\u9fff])", facts)
    terms = [match[0] for match in (days, month) if match]
    if terms:
        jd = f"实习安排：{'，'.join(terms)}\n{jd}"
    return JobCandidate(
        platform="shixiseng",
        source_job_id=identity[0],
        url=identity[1],
        title=title,
        company=company,
        jd=jd,
        city=city,
        source_keyword=keyword,
        salary=salary,
        education=degree[1] if degree else "",
    )


class BrowserShixisengCollector:
    platform = "shixiseng"

    def __init__(self, config, conn, *, runtime=browser):
        self.runtime = runtime
        self.guard = PlatformAccessGuard(conn, config, "collect", platform=self.platform)

    def collect(self, request, hooks):
        stop = hooks.stop_event or Event()
        stopped = PlatformCollectionResult(self.platform, "stopped", "user_stopped", "实习僧采集已停止")
        details = {}
        handled = set()
        saved = 0
        try:
            self.guard.ensure_unlocked()
            tabs = platform_tabs(self.runtime.get_page_targets())
            if not tabs:
                raise CollectionError("search_tab_required", SOURCE_HINT)
            # The signed-in header is a visible signal. Do not inspect cookies or saved credentials.
            session = read_page(self.runtime, target_id(tabs[0]), READ_SESSION, self.guard)
            if session.get("loggedIn") is not True:
                raise CollectionError("login_required", SOURCE_HINT)
            for city in request.cities:
                for keyword in request.keywords:
                    url = search_url(city, keyword)
                    for page in range(1, request.max_pages + 1):
                        if stop.wait(2):
                            return stopped
                        hooks.on_event(phase="searching", city=city, keyword=keyword, page=page)
                        hits = self._open_and_read(url, READ_RESULTS, "search", 20)
                        if not site_url(hits.get("url")) or not isinstance(hits.get("jobs"), list):
                            raise CollectionError("selector_changed", "未识别实习僧结果页。")
                        if not hits["jobs"]:
                            if hits.get("empty") is True:
                                break
                            raise CollectionError("selector_changed", "未找到可识别的岗位链接，已停止。")
                        titles = hits.get("titles") if isinstance(hits.get("titles"), dict) else {}
                        detail_failure = None
                        kept_from_list = 0
                        for link in hits["jobs"][:10]:
                            if stop.is_set():
                                return stopped
                            if not (identity := job_url(link)) or identity[0] in handled:
                                continue
                            if detail_failure is None:
                                try:
                                    if identity[0] not in details:
                                        if stop.wait(2):
                                            return stopped
                                        detail = self._open_and_read(identity[1], READ_DETAIL, "detail", 60)
                                        if job_url(detail.get("url")) != identity:
                                            raise CollectionError("selector_changed", "详情页与预期岗位不一致。")
                                        details[identity[0]] = detail
                                except PlatformSafetyStop as exc:
                                    detail_failure = CollectionError(exc.reason, SAFETY_STOP_HINT)
                                except CollectionError as exc:
                                    detail_failure = exc
                            if stop.is_set():
                                return stopped
                            if detail_failure is not None:
                                # Only preserve recognized cards already read. Do not open another page.
                                if link not in titles:
                                    continue
                                detail = {"url": identity[1]}
                            else:
                                detail = details[identity[0]]
                            candidate = build_candidate(detail, [city], keyword, fallback_title=str(titles.get(link) or "").strip())
                            if not candidate:
                                continue
                            handled.add(identity[0])
                            if not hooks.on_list_candidate(candidate):
                                continue
                            if not hooks.on_candidate(candidate):
                                return stopped
                            if not hooks.can_checkpoint():
                                raise CollectionError("persistence_error", "保存实习僧岗位失败，已停止。")
                            receipt = hooks.last_save_receipt() if hooks.last_save_receipt else {}
                            if receipt.get("inserted"):
                                saved += 1
                                if detail_failure is not None:
                                    kept_from_list += 1
                        if detail_failure is not None:
                            if kept_from_list:
                                raise CollectionError(
                                    detail_failure.code, f"{detail_failure.message}已保留 {kept_from_list} 条列表岗位。",
                                ) from detail_failure
                            raise detail_failure
                        url = next_results_page(hits["url"], hits.get("next"))
                        if not url:
                            break
            if not saved:
                return PlatformCollectionResult(
                    self.platform,
                    "completed_with_shortage",
                    "no_new_jobs",
                    "实习僧未新增岗位，请核对关键词、城市与实习条件。",
                )
            return PlatformCollectionResult(self.platform, "completed", "completed", "实习僧网页采集结束")
        except PlatformSafetyStop as exc:
            raise CollectionError(exc.reason, SAFETY_STOP_HINT) from None

    def _open_and_read(self, url, script, action, limit):
        self.guard.reserve(action, daily_limit=limit)
        # A fresh tab can report about:blank as complete before the requested navigation commits.
        tab = self.runtime.new_tab("about:blank")
        if not tab:
            raise CollectionError("browser_disconnected", "无法打开实习僧页面。")
        try:
            if not self.runtime.navigate(tab, url):
                raise CollectionError("selector_changed", "无法加载实习僧页面。")
            if not self.runtime.wait_for_load(tab, timeout=8):
                raise CollectionError("selector_changed", "实习僧页面未完成加载。")
            return read_page(self.runtime, tab, script, self.guard)
        finally:
            self.runtime.close_tab(tab)
