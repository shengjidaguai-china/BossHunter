"""Shared job filtering helpers."""

import re

CITY_SEPARATOR = "·"


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
