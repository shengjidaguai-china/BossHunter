"""Narrow, credential-free configuration contract for local agents.

Natural-language interpretation belongs to the caller. This module only accepts
validated structured preferences, so an agent cannot accidentally change AI
credentials, delivery settings, or platform safety limits.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


AGENT_API_VERSION = "v1"
PLATFORMS = ("boss", "zhilian", "51job", "liepin")
_TEXT_LIST_FIELDS = ("keywords", "cities", "deal_breakers", "jd_deal_breakers", "blocked_companies")
_OPTIONAL_TEXT_FIELDS = ("education", "recruitment_type")
_ALLOWED_FIELDS = frozenset(
    (*_TEXT_LIST_FIELDS, *_OPTIONAL_TEXT_FIELDS, "salary", "allow_internship", "score_threshold", "platform_order", "max_pages")
)
_MAX_AGENT_EVALUATIONS = 10
_GREETING_URL_PATTERN = re.compile(r"(?i)(?:https?://|www\.|[a-z0-9-]+\.[a-z]{2,})(?:/[^\s]*)?")


class AgentRequestError(ValueError):
    """Raised when an agent submits a request outside the safe contract."""


def validate_agent_evaluations(value: Any, threshold: int) -> list[dict[str, Any]]:
    """Validate Agent-authored scores and greetings before a database mutation."""
    if not isinstance(value, list) or not value:
        raise AgentRequestError("evaluations 必须是非空数组")
    if len(value) > _MAX_AGENT_EVALUATIONS:
        raise AgentRequestError(f"每次最多提交 {_MAX_AGENT_EVALUATIONS} 个岗位评估")

    from bosshunter.ai.scorer import build_score_trace, validate_structured_score_payload

    evaluations: list[dict[str, Any]] = []
    seen_job_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) - {"job_id", "score", "greeting"}:
            raise AgentRequestError("每个评估只能包含 job_id、score 和 greeting")
        job_id = item.get("job_id")
        if not isinstance(job_id, str) or not (job_id := job_id.strip()) or len(job_id) > 200:
            raise AgentRequestError("job_id 必须是非空且不超过 200 字的字符串")
        if job_id in seen_job_ids:
            raise AgentRequestError("同一岗位不能重复提交评分")
        seen_job_ids.add(job_id)

        score_result = validate_structured_score_payload(item.get("score"))
        if score_result is None:
            raise AgentRequestError("score 必须符合 BossHunter 的完整结构化评分格式")

        passed = score_result.score >= threshold
        greeting_value = item.get("greeting")
        if passed:
            greeting = _validated_agent_greeting(greeting_value)
        elif greeting_value is not None:
            raise AgentRequestError("未达到通过线的岗位不能附带 greeting")
        else:
            greeting = ""

        evaluations.append({
            "job_id": job_id,
            "score": score_result.score,
            "reason": score_result.reason,
            "trace": build_score_trace(score_result),
            "greeting": greeting,
            "passed": passed,
        })
    return evaluations


def _validated_agent_greeting(value: Any) -> str:
    if not isinstance(value, str):
        raise AgentRequestError("通过岗位必须提供 greeting 字符串")
    greeting = " ".join(value.split())
    if not 20 <= len(greeting) <= 150:
        raise AgentRequestError("greeting 必须在 20-150 字之间")
    if _GREETING_URL_PATTERN.search(greeting):
        raise AgentRequestError("greeting 不能包含网址；请由用户在确认时自行补充")
    return greeting


def agent_preferences(config: dict[str, Any]) -> dict[str, Any]:
    """Return the editable preference view without exposing credentials."""
    profile = config.get("profile") if isinstance(config.get("profile"), dict) else {}
    search = config.get("search") if isinstance(config.get("search"), dict) else {}
    collection = config.get("collection") if isinstance(config.get("collection"), dict) else {}
    scoring = config.get("scoring") if isinstance(config.get("scoring"), dict) else {}
    platforms = config.get("platforms") if isinstance(config.get("platforms"), dict) else {}

    platform_order = [
        platform for platform in collection.get("default_order", []) if platform in PLATFORMS
    ]
    if not platform_order:
        platform_order = [platform for platform in PLATFORMS if isinstance(platforms.get(platform), dict) and platforms[platform].get("enabled")]

    max_pages: dict[str, int] = {}
    for platform in PLATFORMS:
        platform_config = platforms.get(platform) if isinstance(platforms.get(platform), dict) else {}
        platform_search = platform_config.get("search") if isinstance(platform_config.get("search"), dict) else {}
        value = platform_search.get("max_pages", search.get("max_pages", 3))
        try:
            max_pages[platform] = int(value)
        except (TypeError, ValueError):
            max_pages[platform] = 3

    return {
        "keywords": _string_list(search.get("keywords")),
        "cities": _string_list(search.get("cities")) or _string_list(profile.get("target_cities")),
        "salary": {
            "min": _number(profile.get("salary_min"), 0),
            "max": _number(profile.get("salary_max"), 0),
        },
        "deal_breakers": _string_list(profile.get("deal_breakers")),
        "jd_deal_breakers": _string_list(profile.get("jd_deal_breakers")),
        "blocked_companies": _string_list(profile.get("blocked_companies")),
        "education": str(profile.get("education") or ""),
        "recruitment_type": str(profile.get("recruitment_type") or ""),
        "allow_internship": bool(profile.get("allow_internship", False)),
        "score_threshold": _number(scoring.get("threshold"), 71),
        "platform_order": platform_order,
        "max_pages": max_pages,
    }


def apply_preferences(config: dict[str, Any], preferences: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate and apply an agent preference patch without mutating ``config``."""
    if not isinstance(preferences, dict) or not preferences:
        raise AgentRequestError("preferences 必须是非空对象")

    unexpected = sorted(set(preferences) - _ALLOWED_FIELDS)
    if unexpected:
        raise AgentRequestError(f"Agent 不能修改这些字段：{'、'.join(unexpected)}")

    updated = deepcopy(config)
    profile = _mapping(updated, "profile")
    search = _mapping(updated, "search")
    collection = _mapping(updated, "collection")
    scoring = _mapping(updated, "scoring")
    platforms = _mapping(updated, "platforms")

    for field in ("keywords", "cities"):
        if field in preferences:
            search[field] = _validated_string_list(field, preferences[field])

    for field in ("deal_breakers", "jd_deal_breakers", "blocked_companies"):
        if field in preferences:
            profile[field] = _validated_string_list(field, preferences[field])

    for field in _OPTIONAL_TEXT_FIELDS:
        if field in preferences:
            profile[field] = _validated_optional_text(field, preferences[field])

    if "cities" in preferences:
        cities = list(search["cities"])
        profile["target_cities"] = cities

    if "salary" in preferences:
        salary = preferences["salary"]
        if not isinstance(salary, dict) or set(salary) - {"min", "max"}:
            raise AgentRequestError("salary 只能包含 min 和 max")
        if "min" not in salary or "max" not in salary:
            raise AgentRequestError("salary 必须同时包含 min 和 max")
        minimum = _validated_number("salary.min", salary["min"], 0, 200)
        maximum = _validated_number("salary.max", salary["max"], 0, 200)
        if maximum and minimum > maximum:
            raise AgentRequestError("salary.min 不能大于 salary.max")
        profile["salary_min"] = minimum
        profile["salary_max"] = maximum

    if "allow_internship" in preferences:
        if not isinstance(preferences["allow_internship"], bool):
            raise AgentRequestError("allow_internship 必须是布尔值")
        profile["allow_internship"] = preferences["allow_internship"]

    if "score_threshold" in preferences:
        scoring["threshold"] = _validated_number("score_threshold", preferences["score_threshold"], 0, 100)

    platform_order = _validated_platform_order(preferences["platform_order"]) if "platform_order" in preferences else [
        platform for platform in collection.get("default_order", []) if platform in PLATFORMS
    ]
    if "platform_order" in preferences:
        collection["default_order"] = platform_order
        for platform in PLATFORMS:
            platform_config = _nested_mapping(platforms, platform)
            platform_config["enabled"] = platform in platform_order

    target_platforms = platform_order or ["boss"]
    if "keywords" in preferences or "cities" in preferences or "max_pages" in preferences:
        for platform in target_platforms:
            platform_search = _nested_mapping(_nested_mapping(platforms, platform), "search")
            if "keywords" in preferences:
                platform_search["keywords"] = list(search["keywords"])
            if "cities" in preferences:
                platform_search["cities"] = list(search["cities"])
                city_codes = platform_search.get("city_codes")
                if isinstance(city_codes, dict):
                    platform_search["city_codes"] = {
                        city: code for city, code in city_codes.items() if city in search["cities"]
                    }

    if "max_pages" in preferences:
        max_pages = _validated_max_pages(preferences["max_pages"], target_platforms)
        search["max_pages"] = max_pages[target_platforms[0]]
        for platform, value in max_pages.items():
            _nested_mapping(_nested_mapping(platforms, platform), "search")["max_pages"] = value

    return updated, _changes(config, updated)


def _mapping(root: dict[str, Any], key: str) -> dict[str, Any]:
    value = root.get(key)
    if not isinstance(value, dict):
        value = {}
        root[key] = value
    return value


def _nested_mapping(root: dict[str, Any], key: str) -> dict[str, Any]:
    return _mapping(root, key)


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value] if isinstance(value, list) else []


def _number(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _validated_string_list(field: str, value: Any) -> list[str]:
    if not isinstance(value, list):
        raise AgentRequestError(f"{field} 必须是字符串列表")
    if len(value) > 30:
        raise AgentRequestError(f"{field} 最多包含 30 项")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise AgentRequestError(f"{field} 只能包含字符串")
        cleaned = item.strip()
        if not cleaned or len(cleaned) > 120:
            raise AgentRequestError(f"{field} 包含空值或过长文本")
        if cleaned not in result:
            result.append(cleaned)
    return result


def _validated_optional_text(field: str, value: Any) -> str:
    if not isinstance(value, str) or len(value.strip()) > 60:
        raise AgentRequestError(f"{field} 必须是不超过 60 字的文本")
    return value.strip()


def _validated_number(field: str, value: Any, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise AgentRequestError(f"{field} 必须是数字")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise AgentRequestError(f"{field} 必须是数字") from exc
    if not minimum <= result <= maximum:
        raise AgentRequestError(f"{field} 必须在 {minimum}-{maximum} 之间")
    return result


def _validated_platform_order(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AgentRequestError("platform_order 必须是非空平台列表")
    if any(not isinstance(platform, str) or platform not in PLATFORMS for platform in value):
        raise AgentRequestError("platform_order 只支持 boss、zhilian、51job、liepin")
    if len(set(value)) != len(value):
        raise AgentRequestError("platform_order 不能重复")
    return list(value)


def _validated_max_pages(value: Any, target_platforms: list[str]) -> dict[str, int]:
    if isinstance(value, dict):
        unknown = sorted(set(value) - set(PLATFORMS))
        if unknown:
            raise AgentRequestError(f"max_pages 包含不支持的平台：{'、'.join(unknown)}")
        result = {}
        for platform in target_platforms:
            if platform not in value:
                raise AgentRequestError(f"max_pages 缺少 {platform}")
            result[platform] = _validated_number(f"max_pages.{platform}", value[platform], 1, 10)
        return result
    page_count = _validated_number("max_pages", value, 1, 10)
    return {platform: page_count for platform in target_platforms}


def _changes(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            next_path = f"{path}.{key}" if path else str(key)
            result.extend(_changes(before.get(key), after.get(key), next_path))
        return result
    if before != after:
        return [{"path": path, "before": before, "after": after}]
    return []
