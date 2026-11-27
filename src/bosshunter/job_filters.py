"""Shared job filtering helpers."""

import re

CITY_SEPARATOR = "·"

HR_ACTIVE_TIERS = (
    "online",
    "just_now",
    "today",
    "week",
    "month",
    "older",
    "unknown",
)

MIN_HR_ACTIVE_LEVELS = ("online", "just_now", "today", "week", "month")

MIN_HR_ACTIVE_LABELS: dict[str, str] = {
    "online": "在线",
    "just_now": "刚刚活跃",
    "today": "今日活跃",
    "week": "本周内活跃",
    "month": "本月内活跃",
}

_HR_ACTIVE_TIER_RANK: dict[str, int] = {
    "online": 5,
    "just_now": 4,
    "today": 3,
    "week": 2,
    "month": 1,
    "older": 0,
    "unknown": -1,
}

_HR_ACTIVE_DURATION_RE = re.compile(
    r"^([0-9一二两三四五六七八九十]+)\s*(日|天|周|个?月)内活跃$"
)

_CN_DIGITS: dict[str, int] = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def _parse_cn_or_arabic_int(token: str) -> int | None:
    cleaned = token.strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)
    if cleaned == "十":
        return 10
    if "十" in cleaned:
        parts = cleaned.split("十", 1)
        tens = 1 if parts[0] == "" else _CN_DIGITS.get(parts[0])
        ones = 0 if parts[1] == "" else _CN_DIGITS.get(parts[1])
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    if len(cleaned) == 1 and cleaned in _CN_DIGITS:
        return _CN_DIGITS[cleaned]
    return None


def classify_hr_active(hr_active: str | None) -> str:
    """Classify a platform hr_active label into a canonical activity tier."""
    text = str(hr_active or "").strip()
    if not text:
        return "unknown"
    if text == "在线":
        return "online"
    if text == "刚刚活跃":
        return "just_now"
    if text == "今日活跃":
        return "today"
    if text == "本周活跃":
        return "week"
    if text == "本月活跃":
        return "month"
    if text in {"半年前活跃", "年前活跃"}:
        return "older"

    match = _HR_ACTIVE_DURATION_RE.match(text)
    if match:
        amount = _parse_cn_or_arabic_int(match.group(1))
        unit = match.group(2)
        if amount is None or amount <= 0:
            return "unknown"
        if unit in {"日", "天"}:
            if amount <= 1:
                return "today"
            if amount <= 7:
                return "week"
            if amount <= 31:
                return "month"
            return "older"
        if unit == "周":
            if amount <= 1:
                return "week"
            if amount <= 4:
                return "month"
            return "older"
        if unit in {"月", "个月"}:
            return "month" if amount <= 1 else "older"
    return "unknown"


def hr_active_rank_score(hr_active: str | None) -> int:
    """Return a monotonic recency score (higher = more recently active)."""
    text = str(hr_active or "").strip()
    tier = classify_hr_active(text)
    if tier == "unknown":
        return -1
    if tier == "online":
        return 1_000_000
    if tier == "just_now":
        return 900_000
    if tier == "today":
        return 800_000

    match = _HR_ACTIVE_DURATION_RE.match(text)
    if match:
        amount = _parse_cn_or_arabic_int(match.group(1)) or 0
        unit = match.group(2)
        if unit in {"日", "天"}:
            return max(100_001, 750_000 - amount * 1_000)
        if unit == "周":
            return max(100_001, 750_000 - amount * 7_000)
        if unit in {"月", "个月"}:
            return max(100_001, 750_000 - amount * 30_000)

    if tier == "week":
        return 743_000
    if tier == "month":
        return 720_000
    if text == "半年前活跃":
        return 100_000
    return 50_000


def hr_active_filter_result(hr_active: str | None, profile: dict) -> tuple[int, str]:
    """Filter jobs by minimum recruiter activity level when configured.

    Jobs without an activity label (e.g. non-BOSS platforms) pass automatically.
    """
    min_level = str(profile.get("min_hr_active") or "").strip()
    if not min_level or min_level not in MIN_HR_ACTIVE_LABELS:
        return 100, ""
    tier = classify_hr_active(hr_active)
    if tier == "unknown":
        return 100, ""
    if _HR_ACTIVE_TIER_RANK[tier] < _HR_ACTIVE_TIER_RANK[min_level]:
        label = str(hr_active or "").strip()
        required = MIN_HR_ACTIVE_LABELS[min_level]
        return 0, f"招聘者活跃度低于要求: {label}（要求: {required}）"
    return 100, ""


def job_keyword_match_clause(keyword: str) -> tuple[str, list[str]]:
    """Build a literal substring match across the searchable job fields."""
    # Escape backslashes first so user input cannot become LIKE syntax.
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    columns = ("title", "company", "jd", "score_reason")
    clause = " OR ".join(f"{column} LIKE ? ESCAPE '\\'" for column in columns)
    return f"({clause})", [pattern] * len(columns)


def city_base_name(city: str) -> str:
	"""Return the city part of a platform label such as 上海·浦东新区."""
	return str(city or "").strip().split(CITY_SEPARATOR)[0].strip()


def city_match_clause(cities: list[str]) -> tuple[str, list[str]]:
	"""Build a SQL condition matching whole cities, district-suffixed labels included."""
	clauses: list[str] = []
	params: list[str] = []
	for city in cities:
		base = city_base_name(city)
		if not base:
			continue
		clauses.append("TRIM(COALESCE(city, '')) = ? OR TRIM(COALESCE(city, '')) LIKE ?")
		params.extend([base, f"{base}{CITY_SEPARATOR}%"])
	return f"({' OR '.join(clauses)})", params


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
