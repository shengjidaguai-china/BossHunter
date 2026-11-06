"""Pre-filter module - hard filtering before LLM evaluation."""

import re
from bosshunter.employment import internship_rejection

from bosshunter.job_filters import matching_blocked_company, matching_deal_breaker


_INTERNSHIP_KEYWORDS = ("实习", "intern", "internship", "管培")
_ANONYMOUS_COMPANY_PATTERN = re.compile(
    r"^(?:[\u4e00-\u9fff]{2,4})?某.+(?:公司|企业|集团)$"
)


def quick_score(job: dict, config: dict) -> tuple[int, str]:
    """Apply hard filters before LLM scoring."""
    reason = internship_rejection(job, config)
    if reason:
        return 0, reason
    profile = config.get("profile", {})
    deal_breakers = profile.get("deal_breakers", [])
    jd_deal_breakers = profile.get("jd_deal_breakers", [])
    blocked_companies = profile.get("blocked_companies", [])
    title = job.get("title") or ""
    jd = job.get("jd") or ""
    company = str(job.get("company") or "").strip()

    blocked_company = matching_blocked_company(company, blocked_companies)
    if blocked_company:
        return 0, f"触发公司屏蔽: {blocked_company}"

    if _ANONYMOUS_COMPANY_PATTERN.search(company):
        return 0, "匿名公司岗位"

    breaker = matching_deal_breaker(title, deal_breakers)
    if breaker:
        return 0, f"触发排除词: {breaker}"

    jd_breaker = matching_deal_breaker(jd, jd_deal_breakers)
    if jd_breaker:
        return 0, f"触发JD排除词: {jd_breaker}"

    if not profile.get("allow_internship", False) and _contains_internship_signal(job):
        return 0, "实习/管培岗位"

    freshness_score, freshness_reason = freshness_filter_result(job, profile)
    if freshness_score <= 0:
        return 0, freshness_reason

    return salary_filter_result(str(job.get("salary") or ""), profile)


_CN_DIGITS = {"零": "0", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5",
              "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}


def _normalize_numerals(text: str) -> str:
    """Turn 两月内 / 三日内 style Chinese numerals before 日/天/周/月 into digits."""
    return re.sub(r"[零一二两三四五六七八九十](?=\s*(?:日|天|周|个月|月)[内前]?\s*(?:活跃|在线))", lambda m: _CN_DIGITS[m.group(0)], text)


def hr_active_level(hr_active: str) -> int | None:
    """Rank an HR activity label: 3 = online/just now, 2 = within ~3 days, 1 = within a month, 0 = stale.

    Returns None when the label is empty or unrecognised (unknown, not stale).
    """
    text = str(hr_active or "").strip()
    if not text:
        return None
    text = _normalize_numerals(text)
    # "X前在线" / "X前活跃": the age is what matters, not the word 在线.
    ago = re.search(r"(\d+)\s*(分钟|小时|天|日|周|个月|月|年)\s*前", text)
    if ("在线" in text or "活跃" in text) and "半年前" in text:
        return 0
    if ago and ("在线" in text or "活跃" in text):
        number, unit = int(ago.group(1)), ago.group(2)
        if unit in ("分钟", "小时"):
            return 3
        if unit in ("天", "日"):
            return 3 if number <= 1 else 2 if number <= 3 else 1
        if unit == "周" or (unit in ("月", "个月") and number <= 1):
            return 1
        return 0
    if "在线" in text or "刚刚" in text or "分钟" in text or "小时" in text:
        return 3
    if "今日" in text or "今天" in text:
        return 3
    match = re.search(r"(\d+)\s*(日|天)内?活跃", text)
    if match:
        return 2 if int(match.group(1)) <= 3 else 1
    if "本周" in text or re.search(r"\d+\s*周内?活跃", text):
        return 1
    if "本月" in text or re.search(r"\d+\s*(月|个月)内?活跃", text):
        return 1
    if "半年" in text or "很久" in text or "月前" in text or "年前" in text:
        return 0
    return None


def update_label_days(label: str) -> float | None:
    """Days encoded in a '90天前更新' / '3小时前更新' / '今天更新' label; None when not recognised."""
    text = str(label or "")
    if "刚刚" in text or "今天" in text or "今日" in text:
        return 0.0
    if "昨天" in text:
        return 1.0
    match = re.search(r"(\d+)\s*(分钟|小时|天|日|周|个月|月|年)\s*前", text)
    if not match:
        return None
    number, unit = int(match.group(1)), match.group(2)
    return number * {"分钟": 1 / 1440, "小时": 1 / 24, "天": 1, "日": 1, "周": 7, "个月": 30, "月": 30, "年": 365}[unit]


def freshness_filter_result(job: dict, profile: dict) -> tuple[int, str]:
    """Hard filters on how long ago the posting was refreshed and on HR activity; both are off unless configured."""
    max_update_days = _as_number(profile.get("max_job_update_days", 0))
    updated_days = job.get("updated_days")
    if max_update_days > 0 and isinstance(updated_days, (int, float)) and updated_days > max_update_days:
        return 0, f"岗位已 {updated_days:g} 天未更新（上限 {max_update_days:g} 天）"

    min_level = int(_as_number(profile.get("hr_active_min_level", 0)))
    if min_level > 0:
        level = hr_active_level(str(job.get("hr_active") or ""))
        if level is None:
            if not _as_bool(profile.get("hr_active_unknown_pass", True)):
                return 0, "HR 活跃度未知，已过滤"
        elif level < min_level:
            return 0, f"HR 活跃度不足: {job.get('hr_active')}"

    return 100, "预筛通过"


def salary_filter_result(salary: str, profile: dict) -> tuple[int, str]:
    """薪资硬过滤，采集增值层与 quick_score 共用同一条规则。

    返回 (score, reason)：score=0 表示拦截并携带原因，score=100 表示通过。
    """
    salary_min = _as_number(profile.get("salary_min", 0))
    salary_max = _as_number(profile.get("salary_max", 0))
    parsed_salary = _parse_salary_range_k(str(salary or ""))
    if parsed_salary is None:
        if _as_bool(profile.get("filter_unparsed_salary", True)):
            return 0, "薪资面议/无法解析，已过滤"
        return 100, "薪资面议/无法解析（已关闭过滤，交由 AI 判断）"

    job_salary_min, job_salary_max = parsed_salary
    if salary_min > 0 and job_salary_max < salary_min:
        return 0, f"薪资低于硬性要求: {_format_k(job_salary_max)}K < {_format_k(salary_min)}K"

    salary_ceil_ratio = max(_as_number(profile.get("salary_ceil_ratio", 1.5)), 1.0)
    if salary_max > 0 and job_salary_min > salary_max * salary_ceil_ratio:
        return 0, (
            f"薪资远超期望上限: 报价下限 {_format_k(job_salary_min)}K > "
            f"{_format_k(salary_max)}K × {salary_ceil_ratio:g}"
        )

    return 100, "预筛通过"



def _contains_internship_signal(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    return any(keyword.lower() in title for keyword in _INTERNSHIP_KEYWORDS)


def _parse_salary_range_k(salary: str) -> tuple[float, float] | None:
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[kK]?\s*-\s*(\d+(?:\.\d+)?)\s*[kK]", salary)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return low, max(low, high)

    cn_range = _parse_cn_salary_range_k(salary)
    if cn_range:
        return cn_range

    single_match = re.search(r"(\d+(?:\.\d+)?)\s*[kK]", salary)
    if single_match:
        value = float(single_match.group(1))
        return value, value

    return None


_CN_RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(千|万|[wW])?\s*[-~—]\s*(\d+(?:\.\d+)?)\s*(千|万|[wW])?\s*元?"
    r"|(\d+(?:\.\d+)?)\s*(千|万|[wW])?\s*元"
)
_YEARLY_RE = re.compile(r"/\s*(?:年|12\s*个月)|年薪")


def _cn_amount_to_k(value: str, unit: str | None) -> float:
    amount = float(value)
    if unit in ("万", "w", "W"):
        return amount * 10
    if unit == "千":
        return amount
    return amount / 1000


def _parse_cn_salary_range_k(salary: str) -> tuple[float, float] | None:
    """Parse 元/千/万 monthly ranges used by 智联 and 前程无忧 into K units."""
    match = _CN_RANGE_RE.search(salary)
    if not match:
        return None

    if match.group(1):
        # 「1-2万」只在末位带单位，首位沿用末位单位。
        low_unit = match.group(2) or match.group(4)
        if not (low_unit or match.group(4) or "元" in match.group(0)):
            # 无单位也无「元」字（如 "15-25"）不足以判断币种，交给 AI 判断。
            return None
        low = _cn_amount_to_k(match.group(1), low_unit)
        high = _cn_amount_to_k(match.group(3), match.group(4))
    else:
        low = high = _cn_amount_to_k(match.group(5), match.group(6))

    if low <= 0:
        return None
    if _YEARLY_RE.search(salary):
        low /= 12
        high /= 12
    return min(low, high), max(low, high)


def _as_number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "是"}
    return True


def _format_k(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)
