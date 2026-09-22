"""Shared job filtering helpers."""

import re

HR_ACTIVITY_FILTERS = {"", "1d", "3d", "7d", "30d", "unknown"}


def parse_hr_active_days(value: str | None) -> float | None:
    """Parse the platform label at collection time, not a live last-seen date.

    Range labels use their upper bound: 近7天活跃 does not establish activity
    within 3 days. Missing, vague or unrecognized labels remain unknown.
    """
    text = re.sub(r"\s+", "", str(value or ""))
    if text in {"在线", "当前在线", "刚刚活跃", "刚刚在线"}:
        return 0
    if text in {"今日活跃", "今天活跃"}:
        return 1
    if text in {"昨日活跃", "昨天活跃"}:
        return 2
    aliases = {"近一周活跃": 7, "本周活跃": 7, "近一个月活跃": 30, "本月活跃": 30}
    if text in aliases:
        return aliases[text]
    match = re.fullmatch(r"(?:近|最近)?([0-9]{1,4})(分钟|小时|天|日)(?:内|前)?活跃", text)
    if match:
        amount, unit = match.groups()
        return int(amount) / {"分钟": 1440, "小时": 24, "天": 1, "日": 1}[unit]
    return None


def validate_hr_activity_config(profile: dict) -> None:
    days = profile.get("hr_active_within_days", 0)
    if type(days) is not int or not 0 <= days <= 365:
        raise ValueError("hr_active_within_days 必须是 0-365 的整数（0 表示不限）")
    if not isinstance(profile.get("hr_active_keep_unknown", True), bool):
        raise ValueError("hr_active_keep_unknown 必须是布尔值")  # noqa: TRY004 - config errors use ValueError


def hr_activity_filter_reason(value: str | None, profile: dict) -> str | None:
    """Return a collection rejection reason; unknown activity is kept by default."""
    validate_hr_activity_config(profile)
    limit = profile.get("hr_active_within_days", 0)
    if not limit:
        return None
    days = parse_hr_active_days(value)
    if days is None:
        return None if profile.get("hr_active_keep_unknown", True) else "HR 活跃度未知"
    if days > limit:
        return f"HR 活跃时间不在近 {limit} 天内：{value}"
    return None


def validate_hr_activity_filter(value: str) -> str:
    if value not in HR_ACTIVITY_FILTERS:
        raise ValueError("hr_active_within 参数无效")
    return value


def matches_hr_activity(value: str | None, activity_filter: str) -> bool:
    if not activity_filter:
        return True
    days = parse_hr_active_days(value)
    if activity_filter == "unknown":
        return days is None
    return days is not None and days <= int(activity_filter[:-1])


def matching_deal_breaker(text: str, deal_breakers: list[str]) -> str | None:
    """Return the first deal-breaker keyword found in text."""
    text_lower = text.lower()
    for keyword in deal_breakers:
        cleaned_keyword = keyword.strip()
        if cleaned_keyword and cleaned_keyword.lower() in text_lower:
            return keyword
    return None


def matching_blocked_company(company: str, blocked_companies: list[str]) -> str | None:
    """Return the first blocked-company rule contained in a company name."""
    company_lower = str(company or "").strip().lower()
    for rule in blocked_companies or []:
        cleaned_rule = str(rule or "").strip()
        if cleaned_rule and cleaned_rule.lower() in company_lower:
            return cleaned_rule
    return None


def parse_monthly_salary_k(salary: str) -> tuple[float, float] | None:
    """Parse common monthly K salary labels into a comparable range."""
    normalized = str(salary or "").strip()
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*[kK]?\s*-\s*(\d+(?:\.\d+)?)\s*[kK]",
        normalized,
    )
    if range_match:
        low, high = (float(value) for value in range_match.groups())
        return (min(low, high), max(low, high))

    single_match = re.search(r"(\d+(?:\.\d+)?)\s*[kK](?!\w)", normalized)
    if single_match:
        value = float(single_match.group(1))
        return value, value
    return None
