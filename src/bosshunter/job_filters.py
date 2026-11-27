"""Shared job filtering helpers."""

import re

CITY_SEPARATOR = "·"


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


_HR_ACTIVE_NOISE = ("来自boss直聘", "boss直聘", "kanzhun", "直聘", "boss", "来自")
_HR_ACTIVE_DAY_PATTERNS = (
    (re.compile(r"(\d+)\s*日内"), 1),
    (re.compile(r"(\d+)\s*周内"), 7),
    (re.compile(r"(\d+)\s*月内"), 30),
    (re.compile(r"(\d+)\s*年内"), 365),
)


def parse_hr_active_days(value: str) -> int | None:
    """Parse BOSS 招聘者活跃度文案为“最多多少天前活跃”，无法识别时返回 None。

    BOSS 详情页会把渠道水印插进文案（如「刚刚kanzhun活跃」「2直聘月内活跃」），
    先剔除这些噪声再匹配。未知活跃度返回 None，由调用方决定是否保留。
    """
    text = str(value or "").strip().lower()
    for noise in _HR_ACTIVE_NOISE:
        text = text.replace(noise, "")
    text = text.replace(" ", "")
    if not text:
        return None
    if "刚刚" in text or "今日" in text:
        return 0
    for pattern, unit_days in _HR_ACTIVE_DAY_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1)) * unit_days
    if "本周" in text:
        return 7
    if "本月" in text:
        return 30
    if "半年前" in text:
        # 半年前 = 超过半年，避免与「近半年活跃」在 180 天阈值上混淆。
        return 181
    if "半年" in text:
        return 180
    return None


def hr_active_limit_days(profile: dict) -> int:
    """Return the configured maximum HR inactivity in days (0 = 不限制)."""
    try:
        value = int(profile.get("hr_active_max_days", 0) or 0)
    except (TypeError, ValueError):
        return 0
    return max(value, 0)


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
