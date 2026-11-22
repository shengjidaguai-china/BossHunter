"""Conservative employment-type checks, independent of campus/social recruitment."""

import re
from collections.abc import Mapping
from typing import Any, Literal

EmploymentType = Literal["internship", "full_time", "part_time", "unknown"]
_EXPLICIT_TYPE = re.compile(r"(?:职位|岗位|工作|招聘|用工)(?:类型|性质)\s*[:：]\s*(实习|全职|兼职)")
_TYPE_NAMES: dict[str, EmploymentType] = {"实习": "internship", "全职": "full_time", "兼职": "part_time"}
# Words that describe a candidate's past internship, not the role being hired.
# Optional spaces cover "实习 经验" the same as "实习经验".
_CANDIDATE_INTERN_TAIL = r"[\s　]*(?:经历|经验|背景)"
# A refusal verb is cancelled when it is itself negated: 不拒绝 / 不会拒绝 / 并不禁止.
_NEGATED_REFUSAL = re.compile(r"(?:并不|不会|不再|没有|并未|并非|不|未)[\s　]*$")
# Refusal verbs. A short modifier may sit before 实习 ("在校实习", "谢绝 实习生").
# The modifier cannot cross a sentence break, and 实习经历/经验/背景 stays a candidate condition.
_REFUSAL = r"谢绝|拒绝|拒收|婉拒|严禁|禁止|不录用|不招聘|不招收?|不接受"
_REFUSAL_GAP = r"(?:[\s　]|[\u4e00-\u9fff]){0,6}?"
_JOB_TYPE_DENIAL = re.compile(
    rf"(?:{_REFUSAL}){_REFUSAL_GAP}实习(?!{_CANDIDATE_INTERN_TAIL})|非实习(?!{_CANDIDATE_INTERN_TAIL})"
)
# Affirmative full-time role. 接受全职 means "also acceptable", and 非/不是/并非 negates it.
_EXCLUSIVE_FULL_TIME_JOB = re.compile(
    r"只招正式|(?<!不是)(?<!并非)(?<!非)(?<!接受)(?:全职岗位|正式岗位)"
)
# The JD offers internship as a role, so a full-time phrase is not exclusive.
_JD_ALSO_INTERNSHIP = re.compile(
    rf"(?:或|和|及|与)实习(?!{_CANDIDATE_INTERN_TAIL})|实习或|实习亦可|亦可实习|也招实习|"
    rf"也?欢迎实习(?!{_CANDIDATE_INTERN_TAIL})|"
    rf"(?<!不)接受实习(?!{_CANDIDATE_INTERN_TAIL})"
)

# BOSS search-card tag such as 「5天/周」 or 「3个月」; the collector stamps
# BOSS_INTERNSHIP_CARD into employment_source only when the internship-only
# search filter has been verified, so classify_employment can treat the
# persisted evidence as one internship signal alongside title/JD signals.
BOSS_INTERNSHIP_CARD = "boss_internship_card"
_INTERNSHIP_CARD_TAG = re.compile(r"^\s*\d+\s*(?:天/周|个月)\s*$")


def _has_job_type_denial(text: str) -> bool:
    """True when a refusal targets the internship role, not a negated refusal verb."""
    for match in _JOB_TYPE_DENIAL.finditer(text):
        if _NEGATED_REFUSAL.search(text[:match.start()]):
            continue
        return True
    return False


def _exclusive_full_time_jd(jd: str) -> bool:
    """True when the JD states a full-time role and does not also accept internship."""
    return bool(_EXCLUSIVE_FULL_TIME_JOB.search(jd)) and not _JD_ALSO_INTERNSHIP.search(jd)


def has_internship_card_tag(tags) -> bool:
    """卡片标签里有「X天/周」或「X个月」。"""
    return any(
        isinstance(tag, str) and _INTERNSHIP_CARD_TAG.fullmatch(tag)
        for tag in (tags or [])
    )


def classify_employment(job: Mapping[str, Any]) -> EmploymentType:
    """Require positive evidence; contradictory title/JD signals remain unknown."""
    title = str(job.get("title") or "")
    jd = str(job.get("jd") or "")
    # A negative internship statement must not become positive internship evidence.
    # The same denial in the JD outranks a search-card tag.
    denies_internship = _has_job_type_denial(title) or _has_job_type_denial(jd)
    signals: set[EmploymentType] = set()
    if denies_internship or re.search(r"全职|正式岗", title) or _exclusive_full_time_jd(jd):
        signals.add("full_time")
    if not denies_internship and re.search(r"实习|\bintern(?:ship)?\b", title, re.I):
        signals.add("internship")
    if re.search(r"兼职", title):
        signals.add("part_time")
    if (str(job.get("source_platform") or "boss") == "boss"
            and job.get("employment_source") == BOSS_INTERNSHIP_CARD
            and not denies_internship):
        signals.add("internship")
    signals.update(_TYPE_NAMES[match] for match in _EXPLICIT_TYPE.findall(jd))
    # Daily pay, campus recruitment and past internship experience are not proof.
    return next(iter(signals)) if len(signals) == 1 else "unknown"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def internship_only(config: Mapping[str, Any]) -> bool:
    """Only the explicit BOSS internship-only filter enables this guard.

    Platform filters override legacy search filters, including an empty mapping.
    Mixed selections must not accidentally turn into an internship-only search.
    """
    boss = _mapping(_mapping(_mapping(config.get("platforms")).get("boss")).get("search"))
    filters = boss.get("filters") if "filters" in boss else _mapping(config.get("search")).get("filters")
    value = _mapping(filters).get("job_type", [])
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        return False
    return {item.strip() for item in value} == {"实习"}


def internship_config_error(config: Mapping[str, Any]) -> str:
    """An internship search never overrides the user's acceptance preference."""
    if internship_only(config) and _mapping(config.get("profile")).get("allow_internship") is not True:
        return "仅实习筛选与未开启“接受实习/管培岗位”冲突：请开启该设置或取消仅实习筛选"
    return ""


def internship_rejection(job: Mapping[str, Any], config: Mapping[str, Any]) -> str:
    if str(job.get("source_platform") or "boss") != "boss":
        return ""
    conflict = internship_config_error(config)
    if conflict:
        return conflict
    kind = classify_employment(job)
    if kind == "internship" and _mapping(config.get("profile")).get("allow_internship") is not True:
        return "实习/管培岗位"  # preserve the existing prefilter rejection message
    if not internship_only(config):
        return ""
    if kind == "internship":
        return ""
    if kind in {"full_time", "part_time"}:
        return "仅实习：非实习岗位"
    return "仅实习：职位类型待核实，禁止自动投递"
