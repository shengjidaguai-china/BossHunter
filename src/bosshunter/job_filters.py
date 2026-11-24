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


_SEPARATOR_RE = re.compile(r"[\s\-_·/、,，.]+")


def _squash(value: str) -> str:
    """Drop separators so "AI-Infra" also matches the keyword "ai infra"."""
    return _SEPARATOR_RE.sub("", str(value or "").lower())


def matching_deal_breaker(text: str, deal_breakers: list[str]) -> str | None:
    """Return the first deal-breaker keyword found in text.

    Substring match, case-insensitive, with a separator-insensitive fallback so
    "AI Infra" / "AI-Infra" / "ai_infra" are treated as the same rule.
    """
    text_lower = str(text or "").lower()
    squashed_text = _squash(text_lower)
    for keyword in deal_breakers or []:
        cleaned_keyword = str(keyword or "").strip()
        if not cleaned_keyword:
            continue
        lowered = cleaned_keyword.lower()
        if lowered in text_lower:
            return keyword
        squashed_keyword = _squash(lowered)
        if squashed_keyword and squashed_keyword in squashed_text:
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
