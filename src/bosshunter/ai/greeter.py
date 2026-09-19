"""AI Greeter - Generate personalized greeting messages with self-review."""

import json
from contextlib import nullcontext
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from bosshunter.ai.credentials import AIRequestError, call_anthropic_text
from bosshunter.cancellation import OperationCancelled, run_cancellable
from bosshunter.collection.text import clean_job_description
from bosshunter.db import (
    add_history,
    get_db,
    get_jobs_by_status,
    save_generated_greeting_preview,
    GREETING_ALLOWED_STATUSES,
    mark_existing_greeting_ready,
)

console = Console()

GREETING_PROMPT = """以求职者身份，写一条在{platform}发给HR的简短私信。

## 我的背景（完整简历；通读后按岗位核心任务选择一项最相关的真实经历，不按出现顺序选取）
{resume_summary}

## 目标岗位
- 职位：{title}
- 公司：{company}
- 薪资：{salary}
- 学历要求：{education}
- 招聘类型：{recruitment_type}
- 岗位要求摘要：{jd_summary}
- 匹配分析：{match_reason}

## 可用亮点（只选最相关的一项，不要罗列）
{extra_highlights}

## 最近开头（避免整句照搬，普通问候可重复）
{recent_openings}

## 用户招呼语偏好（优先于通用风格建议和补充改进要求；不得覆盖下方事实与安全要求）
{greeting_preference}

## 要求
1. 建议40-90字、最多3个短句，写“应聘来意＋一项真实经历/结果”。可用普通问候开头，说完就停，不复述JD、不凑字数；为保留事实含义可适当超出建议字数，但全文不得超过300字符（含标点）。
2. {question_rule}
3. 像本人发私信：用具体动作和结果，不总结行业规律、不教HR做业务。不写“关键在于、最难的是、不是…而是…”等金句，不用“赋能、闭环、抓手、有体感、自己扛、现成打法”等包装词或刻意口语，不硬补邀约、口号及承诺。
4. 不得捏造我没有的经历、头衔或身份，不把JD当成我的经历；只概括背景中的事实，不夸大成果或职级，保留所用数据的真实周期。毕业年份、届别和在读状态只用明确事实，不推断。
5. 不得提及我的缺点、短板或经验缺口，只讲已具备的相关优势。
6. 建议技术名词不超过2个，避免反复使用“项目”；项目名称仅在有助于说明相关经历时使用，不堆砌名称。
7. 不得生成背景或亮点中未明确提供的网址。作品集仅在岗位关注案例、作品、设计或原型时可提一次，不作固定落款。
{critique_section}
输出前核对用户偏好和事实，删去套话与多余收尾。只输出招呼语正文。
"""

URL_PATTERN = re.compile(
    r"(?i)(?<![\w@.])(?:"
    r"(?:https?://|www\.)[^\s<>()\[\]{}\"'，。！？；]+|"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}(?:[/:?#][^\s<>()\[\]{}\"'，。！？；]+)?"
    r")"
)

REVIEW_PROMPT = """请评估以下{platform}招呼语的质量。

## 岗位
{title} @ {company}

## 招呼语
{greeting}

## 用户招呼语偏好
{greeting_preference}
必须遵守用户的表达偏好；它优先于通用风格建议，但不能覆盖真实经历与安全要求。已经符合偏好时，不为差异化强行改写。
{question_review_rule}

## 评估维度（每项1-10分）
1. 自然度：是否像普通求职者发的简短私信；“您好”等普通问候不扣分，说教、行业金句和故作熟络应扣分
2. 相关性：是否针对该岗位突出匹配点
3. 差异化：是否有具体且相关的个人经历支撑；不奖励猎奇开头、夸张承诺或华丽辞藻
4. 克制度：是否只讲一个匹配点，避免项目名和术语堆叠、固定作品集落款和求职套话；40-90字是建议，不为凑字数或省字删除必要事实

请严格按JSON格式输出，不要输出其他内容：
{{"naturalness": 8, "relevance": 7, "differentiation": 6, "restraint": 8, "avg": 7.25, "critique": "改进建议（20字内）"}}
"""


def _get_resume_text(config: dict) -> str:
    """Read the full resume for local-only validation."""
    resume_path = Path(config.get("profile", {}).get("resume_path", "./resume.md"))
    if not resume_path.exists():
        return ""
    return resume_path.read_text(encoding="utf-8")


def _get_resume_summary(config: dict) -> str:
    """Keep the complete factual source so relevant evidence can come from any section."""
    return _get_resume_text(config)


_GRADUATION_RANGE_RE = re.compile(
    r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*(?:月)?\s*(?:至|到|-|—|~|～)\s*"
    r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*(?:月)?"
)
_MISSING_SUFFIX_RE = re.compile(r"\s*[|｜]\s*缺失[:：].*$", re.S)


def _parse_graduation_context(resume_content: str) -> str:
    """Extract explicit graduation timing from the education section."""
    text = str(resume_content or "")
    section_start = text.find("教育经历")
    if section_start < 0:
        return ""
    section = text[section_start:section_start + 800]
    match = _GRADUATION_RANGE_RE.search(section)
    if not match:
        return ""

    end_year = int(match.group(3))
    end_month = int(match.group(4))
    graduation_class = f"{end_year} 届"
    graduated = (date.today().year, date.today().month) >= (end_year, end_month)
    status = "已毕业" if graduated else "在读/未毕业"
    return (
        f"教育经历明确显示：{match.group(1)} 年 {int(match.group(2))} 月至 "
        f"{end_year} 年 {end_month} 月；{status}，{graduation_class}。"
        "生成招呼语时必须严格使用该毕业信息，不得改写为其他届别或状态。"
    )


def _positive_match_reason(score_reason: str) -> str:
    """Remove the persisted missing-gaps suffix before greeting generation."""
    return _MISSING_SUFFIX_RE.sub("", str(score_reason or "")).strip()


def _call_claude(
    prompt: str,
    config: dict,
    max_tokens: int | None = None,
    *,
    purpose: str = "greeting",
) -> str | None:
    """Call Claude API and return response text."""
    ai_cfg = config.get("ai", {}) if isinstance(config.get("ai"), dict) else {}
    default_key = "greeting_review_max_tokens" if purpose == "greeting_review" else "greeting_max_tokens"
    default_tokens = 4096 if purpose == "greeting_review" else 8192
    token_limit = max_tokens if max_tokens is not None else ai_cfg.get(default_key, default_tokens)
    try:
        token_limit = max(128, min(int(token_limit or default_tokens), 65536))
    except (TypeError, ValueError):
        token_limit = default_tokens
    return run_cancellable(
        lambda: call_anthropic_text(
            prompt,
            config,
            token_limit,
            timeout=ai_cfg.get(
                f"{purpose}_timeout_seconds",
                ai_cfg.get("greeting_timeout_seconds", ai_cfg.get("timeout_seconds", 180)),
            ),
            purpose=purpose,
        ),
        config,
    )


def _truncate_prompt_text(text: str, limit: int) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    marker = "\n...[为适配模型上下文已裁剪]...\n"
    available = max(limit - len(marker), 2)
    head = max(int(available * 0.7), 1)
    return f"{text[:head]}{marker}{text[-(available - head):]}"


def _normalize_url(value: str) -> str:
    candidate = str(value or "").strip().rstrip(".,;:!?，。！？；、)]}）】》")
    if candidate.lower().startswith("www."):
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if not parsed.netloc:
        return candidate.lower().rstrip("/")
    path = parsed.path.rstrip("/")
    suffix = f"?{parsed.query}" if parsed.query else ""
    suffix += f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{parsed.netloc.lower()}{path}{suffix}"


def _extract_urls(text: str) -> set[str]:
    return {
        normalized
        for match in URL_PATTERN.findall(str(text or ""))
        if (normalized := _normalize_url(match))
    }


def _has_untrusted_greeting_url(greeting: str, resume_text: str, config: dict) -> bool:
    generated_urls = _extract_urls(greeting)
    if not generated_urls:
        return False
    trusted_urls = _extract_urls(resume_text)
    trusted_urls.update(_extract_urls(_get_resume_text(config)))
    portfolio_url = str(config.get("profile", {}).get("portfolio_url", "") or "").strip()
    if portfolio_url:
        trusted_urls.add(_normalize_url(portfolio_url))
    return not generated_urls.issubset(trusted_urls)


def _notify(config: dict, message: str, *, error: bool = False) -> None:
    console.print(f"[{'red' if error else 'yellow'}]{message}[/{'red' if error else 'yellow'}]")
    callback = config.get("_workbench_log")
    if callable(callback):
        callback(message)


def _json_greeting_text(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        for item in value:
            nested = _json_greeting_text(item)
            if nested:
                return nested
        return None
    if not isinstance(value, dict):
        return None
    for key in ("greeting", "message", "text", "content"):
        nested = _json_greeting_text(value.get(key))
        if nested:
            return nested
    for key in ("data", "result", "output"):
        nested = _json_greeting_text(value.get(key))
        if nested:
            return nested
    return None


def _normalize_greeting_response(response: str | None) -> str | None:
    """Accept common provider wrappers while rejecting non-answer payloads."""
    if not isinstance(response, str):
        return None
    greeting = response.strip()
    if not greeting:
        return None

    fenced = re.fullmatch(
        r"```(?:json|text|markdown|md)?\s*(.*?)\s*```",
        greeting,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        greeting = fenced.group(1).strip()

    parsed_greeting = None
    structured_response = greeting.startswith("{") or greeting.startswith("[")
    if structured_response:
        try:
            parsed = json.loads(greeting)
        except (json.JSONDecodeError, TypeError):
            return None
        parsed_greeting = _json_greeting_text(parsed)
    else:
        decoder = json.JSONDecoder()
        for index, char in enumerate(greeting):
            if char not in "[{":
                continue
            try:
                parsed, _ = decoder.raw_decode(greeting[index:])
            except (json.JSONDecodeError, TypeError):
                continue
            parsed_greeting = _json_greeting_text(parsed)
            if parsed_greeting:
                break
    if structured_response and parsed_greeting is None:
        return None
    if parsed_greeting is not None:
        greeting = parsed_greeting

    greeting = re.sub(
        r"^\s*(?:最终)?(?:打招呼语|招呼语|消息内容|回复)\s*[:：]\s*",
        "",
        greeting,
        count=1,
        flags=re.IGNORECASE,
    )
    greeting = greeting.strip().strip('"\'“”‘’').strip()
    if not greeting:
        return None
    if re.fullmatch(r"(?is)(?:抱歉|无法|不能).{0,80}", greeting):
        return None

    return greeting.strip() or None


def _opening_signature(greeting: str, limit: int = 24) -> str:
    """Return a compact first-clause signature for batch-level diversity."""
    text = " ".join(str(greeting or "").split())
    for separator in ("，", "。", "！", "？", "——", "—", "-"):
        text = text.split(separator, 1)[0]
    return text[:limit]


def _greeting_style_issues(
    greeting: str,
    recent_openings: list[str] | None = None,
) -> list[str]:
    """Return advisory style notes; never reject or rewrite a draft."""
    issues = []
    if greeting.count("项目") > 1:
        issues.append("不要反复强调项目，整条消息最多出现一次“项目”")
    if len(greeting) > 90:
        issues.append("建议精简到40-90字，只保留一个匹配点，不删事实所需的限定信息")

    first_sentence = re.split(r"[。！？]", greeting, maxsplit=1)[0]
    if any(phrase in first_sentence for phrase in (
        "真正的门槛", "关键在于", "关键在", "最难的是", "最后拼的是", "靠的是真实感",
    )) or re.search(r"不是.{1,30}(?:而是|是让)", first_sentence):
        issues.append("去掉行业说教或金句开头，直接说明来意和一项真实经历")

    clichés = (
        "挺有共鸣", "挺兴奋", "一直在做", "正好是我", "从0到1",
        "完整闭环", "完整落地", "快速上手", "期待进一步沟通",
        "有手感", "有实际手感", "有体感", "有实际体感", "自己扛", "现成打法", "聊十分钟",
    )
    used_clichés = [phrase for phrase in clichés if phrase in greeting]
    if used_clichés:
        issues.append(f"去掉求职套话：{'、'.join(used_clichés[:3])}")

    lower_greeting = greeting.lower()
    technical_concepts = [
        any(term in lower_greeting for term in ("agent", "tool calling", "memory")),
        any(term in lower_greeting for term in ("rag", "知识库")),
        "prompt" in lower_greeting,
        "工作流" in greeting and "agent" not in lower_greeting,
        any(term in lower_greeting for term in ("大模型", "llm")),
        "mcp" in lower_greeting,
    ]
    if sum(technical_concepts) > 2:
        issues.append("技术名词最多保留2个，只留下与岗位最相关的能力证据")

    weakness_markers = (
        "经验不足",
        "缺乏",
        "短板",
        "不足",
        "还在学习",
        "仍在学习",
        "正在学习",
        "没有做过",
        "但缺",
        "尚需",
        "需要适应",
    )
    if any(marker in greeting for marker in weakness_markers):
        issues.append("不要暴露缺点、短板或经验缺口，只保留已经具备的优势")

    opening = _opening_signature(greeting)
    if len(opening) > 6 and opening in set(recent_openings or []):
        issues.append("本批次已使用相同开头，请换一种自然切入方式")
    return issues


def _parse_review_response(response: str | None) -> dict | None:
    if not isinstance(response, str) or not response.strip():
        return None
    decoder = json.JSONDecoder()
    for index, char in enumerate(response):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(response[index:])
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue
        try:
            avg = float(parsed.get("avg"))
        except (TypeError, ValueError):
            continue
        if not 1 <= avg <= 10:
            continue
        parsed["avg"] = avg
        parsed["critique"] = str(parsed.get("critique") or "")
        return parsed
    return None


def _platform_label(job: dict) -> str:
    return {
        "boss": "BOSS直聘",
        "zhilian": "智联招聘",
        "51job": "前程无忧",
        "liepin": "猎聘",
    }.get(str(job.get("source_platform") or "boss"), "招聘平台")


def _review_greeting(
    greeting: str,
    job: dict,
    config: dict,
    max_tokens: int | None = None,
) -> dict | None:
    """Self-evaluate a greeting. Returns scores dict or None on failure."""
    prompt = REVIEW_PROMPT.format(
        platform=_platform_label(job),
        title=job["title"],
        company=job["company"],
        greeting=greeting,
        greeting_preference=_truncate_prompt_text(
            config.get("profile", {}).get("greeting_preference", "") or "（无额外偏好）", 500,
        ),
        question_review_rule=(
            "该用户明确要求不提问，不得建议补问句或反问。"
            if _has_no_question_preference(config)
            else "是否提问依据用户偏好与沟通需要；不得仅因包含问句或没有问句扣分，也不要求固定使用问句收尾。"
        ),
    )
    response = _call_claude(prompt, config, max_tokens, purpose="greeting_review")
    return _parse_review_response(response)


def _generate_greeting_once(
    job: dict,
    resume_summary: str,
    config: dict,
    critique: str = "",
    *,
    compact: bool = False,
    max_tokens: int | None = None,
    recent_openings: list[str] | None = None,
    failure_feedback: list[str] | None = None,
) -> str | None:
    """Generate a single greeting attempt."""
    jd_limit = 250 if compact else 500
    jd_summary = _truncate_prompt_text(clean_job_description(job.get("jd", "")), jd_limit) or "无详细描述"
    critique_section = f"\n## 补充改进要求\n- {critique}\n" if critique else ""

    # Build extra highlights from config (portfolio URL, personal strengths, etc.)
    profile_cfg = config.get("profile", {})
    highlights = profile_cfg.get("extra_highlights", [])
    portfolio_url = profile_cfg.get("portfolio_url", "")
    highlight_lines = [f"- {h}" for h in highlights]
    portfolio_context = f"{job.get('title', '')} {job.get('jd', '')}".lower()
    portfolio_requested = any(
        keyword in portfolio_context
        for keyword in ("作品集", "案例", "case", "原型", "交互设计", "视觉设计")
    )
    if portfolio_url and portfolio_requested:
        highlight_lines.append(f"- 个人作品集网址：{portfolio_url}")
    extra_highlights = "\n".join(highlight_lines) if highlight_lines else "（无额外亮点配置）"

    prompt = GREETING_PROMPT.format(
        platform=_platform_label(job),
        resume_summary=resume_summary,
        title=job["title"],
        company=job["company"],
        salary=job["salary"] or "面议",
        education=job.get("education", "") or "未识别",
        recruitment_type={"campus": "校招", "experienced": "社招"}.get(
            job.get("recruitment_type", ""), "未识别"
        ),
        jd_summary=jd_summary,
        match_reason=_truncate_prompt_text(_positive_match_reason(job.get("score_reason", "")), 240),
        critique_section=critique_section,
        extra_highlights=_truncate_prompt_text(extra_highlights, 500),
        recent_openings=(
            "\n".join(f"- {opening}" for opening in (recent_openings or [])[-8:])
            or "（暂无）"
        ),
        greeting_preference=_truncate_prompt_text(
            profile_cfg.get("greeting_preference", "") or "（无额外偏好）",
            500,
        ),
        question_rule=(
            "【本次必须不提问】全文只用陈述句，不用问号、反问或以吗/呢收尾；"
            "不询问是否、能否、可否沟通，也不使用‘方便聊聊’式试探邀约。"
            "说完应聘来意和真实经历即可结束，无需追加互动问题。"
            if _has_no_question_preference(config)
            else "是否提问依据用户偏好与沟通需要；可以自然陈述，也可以提出简短且与岗位相关的问题，不强制使用或禁止问句。"
        ),
    )

    ai_cfg = config.get("ai", {}) if isinstance(config.get("ai"), dict) else {}
    token_limit = max_tokens if max_tokens is not None else ai_cfg.get("greeting_max_tokens", 8192)
    response = _call_claude(prompt, config, token_limit)
    greeting = _normalize_greeting_response(response)
    if greeting and _has_untrusted_greeting_url(greeting, resume_summary, config):
        if failure_feedback is not None:
            failure_feedback.append("上一稿包含来源未提供的网址；重新生成时删除这些网址，只使用已提供的真实信息。")
        _notify(
            config,
            f"{job['company']}｜{job['title']} 的招呼语包含未提供的网址，已拒绝并重试。",
        )
        return None
    return greeting


def _has_no_question_preference(config: dict) -> bool:
    preference = str(config.get("profile", {}).get("greeting_preference", ""))
    # Only a clear global prohibition; e.g. “不主动询问薪资” is not a ban on all questions.
    return bool(re.search(
        r"(?:^|[，,。；;\s])(?:请)?(?:不要问问题|不要提问|不提问|不问问题|不用问句|不要问句)(?=$|[，,。；;！!\s])",
        preference,
    ))


def _violates_no_question_preference(greeting: str, config: dict) -> bool:
    if not _has_no_question_preference(config):
        return False
    sentences = re.split(r"[。！!\n]", greeting)
    return any(re.search(r"[?？]|(?:吗|么|呢)[…\s]*$|是否|能否|可否|方便.{0,8}(?:聊聊|沟通)", sentence) for sentence in sentences)


def _generate_with_token_retry(
    job: dict,
    resume_summary: str,
    config: dict,
    critique: str = "",
    recent_openings: list[str] | None = None,
) -> str | None:
    """Retry incomplete or rejected drafts with feedback, and handle token limits."""

    failure_feedback: list[str] = []

    def _retry_critique() -> str:
        return "\n- ".join(part for part in [critique, *failure_feedback] if part)

    def _once_or_none(*args, **kwargs):
        failure_feedback.clear()
        try:
            return _generate_greeting_once(*args, **kwargs, failure_feedback=failure_feedback)
        except AIRequestError as exc:
            # 空响应用保持"空结果"语义：转成 None 走既有的按配置重试与岗位级失败记录，
            # 不中断整批（#101 回归：整批暂停仅留给鉴权/额度/限流/网络等服务级故障）。
            if exc.kind == "empty_response":
                return None
            raise

    try:
        result = _once_or_none(
            job,
            resume_summary,
            config,
            critique,
            recent_openings=recent_openings,
        )
        if result:
            return result
        ai_cfg = config.get("ai", {}) if isinstance(config.get("ai"), dict) else {}
        try:
            max_attempts = max(1, min(int(ai_cfg.get("greeting_max_attempts", 2) or 2), 3))
        except (TypeError, ValueError):
            max_attempts = 2
        for attempt in range(2, max_attempts + 1):
            retry_critique = _retry_critique()
            reason = "招呼语包含未提供的网址" if failure_feedback else "未返回完整招呼语"
            _notify(
                config,
                f"{job['company']}｜{job['title']} {reason}，正在重试（{attempt}/{max_attempts}）。",
            )
            result = _once_or_none(
                job,
                resume_summary,
                config,
                retry_critique,
                recent_openings=recent_openings,
            )
            if result:
                return result
        return None
    except AIRequestError as exc:
        if exc.kind == "output_truncated":
            _notify(config, f"{job['company']}｜{job['title']} 的招呼语回答被截断，正在增大输出 Token 上限后重试。")
            compact = False
            ai_cfg = config.get("ai", {}) if isinstance(config.get("ai"), dict) else {}
            try:
                configured_tokens = int(ai_cfg.get("greeting_max_tokens", 8192) or 8192)
            except (TypeError, ValueError):
                configured_tokens = 8192
            retry_max_tokens = min(
                max(configured_tokens * 2, 600),
                65536,
            )
        elif exc.kind == "output_limit":
            _notify(config, f"{job['company']}｜{job['title']} 正在降低单次输出 Token 上限后重试招呼语。")
            compact = False
            retry_max_tokens = 160
        elif exc.kind == "context_limit":
            _notify(config, f"{job['company']}｜{job['title']} 内容较长，保留完整简历、缩减辅助上下文后重试招呼语。")
            compact = True
            retry_max_tokens = 160
        else:
            raise

    try:
        return _once_or_none(
            job,
            resume_summary,
            config,
            _retry_critique(),
            compact=compact,
            max_tokens=retry_max_tokens,
            recent_openings=recent_openings,
        )
    except AIRequestError as retry_exc:
        if retry_exc.kind in {"output_truncated", "output_limit", "context_limit"}:
            _notify(
                config,
                f"已跳过 {job['company']}｜{job['title']}：调整单次 Token 请求后仍失败。",
            )
            return None
        raise


def greeting_config_error(config: dict) -> str:
    profile = config.get("profile", {})
    enabled = profile.get("ai_greeting_enabled", True)
    fixed = profile.get("fixed_greeting", "")
    if not isinstance(enabled, bool):
        return "AI 招呼语开关必须为开启或关闭"
    if not isinstance(fixed, str):
        return "固定招呼语必须是文本"
    if len(fixed.strip()) > 300:
        return "固定招呼语不能超过300字"
    if not enabled and not fixed.strip():
        return "关闭 AI 招呼语后，请先填写固定招呼语"
    return ""


def generate_greetings(config: dict, job_ids: list[str] | None = None, db_path=None) -> int:
    """Generate greetings for approved jobs (or specific job_ids) with optional self-review.

    Returns count generated. When ``job_ids`` is provided, only those jobs are
    processed regardless of their current status, which lets the dashboard
    generate greetings for pending-confirmation jobs without sending them.
    ``db_path`` lets web callers pin the runtime database; without it the
    module-level default (CWD-relative) is used for CLI compatibility.
    """
    error = greeting_config_error(config)
    if error:
        config["_workbench_greeting_report"] = {
            "generated_count": 0, "skipped_existing": 0, "failed_count": 0, "pause_reason": error,
        }
        _notify(config, error, error=True)
        return 0
    ai_enabled = config.get("profile", {}).get("ai_greeting_enabled", True)
    fixed_greeting = config.get("profile", {}).get("fixed_greeting", "").strip()
    db = get_db(db_path)
    if job_ids is None:
        jobs = get_jobs_by_status(db, "approved")
    elif job_ids:
        placeholders = ",".join("?" for _ in job_ids)
        rows = db.execute(
            f"SELECT * FROM jobs WHERE deleted_at IS NULL AND id IN ({placeholders}) ORDER BY score DESC",
            [str(job_id) for job_id in job_ids],
        ).fetchall()
        jobs = [dict(row) for row in rows]
    else:
        # 显式传入空列表 = 不处理任何岗位，而不是退回"全部 approved"。
        jobs = []
    _workbench_job_ids = {str(job_id) for job_id in config.get("_workbench_job_ids", [])}
    if _workbench_job_ids:
        jobs = [job for job in jobs if str(job["id"]) in _workbench_job_ids]
    allowed_jobs = [
        job
        for job in jobs
        if str(job.get("status") or "approved") in GREETING_ALLOWED_STATUSES
    ]
    conflict_ids = [
        str(job["id"])
        for job in jobs
        if str(job.get("status") or "approved") not in GREETING_ALLOWED_STATUSES
    ]
    jobs = allowed_jobs
    # A version choice resolves review, but does not authorize this batch to send it.
    pending_review_ids = {str(job["id"]) for job in jobs if job.get("greeting_selection") == "pending"}
    config["_workbench_pending_review_ids"] = pending_review_ids

    requested_count = len(jobs)
    force_regenerate = bool(config.get("_workbench_regenerate"))
    existing_jobs = (
        []
        if force_regenerate
        else [job for job in jobs if str(job.get("greeting") or "").strip()]
    )
    if not force_regenerate:
        jobs = [job for job in jobs if not str(job.get("greeting") or "").strip()]
    config["_workbench_greeting_report"] = {
        "requested_count": requested_count,
        "generated_count": 0,
        "skipped_existing": len(existing_jobs),
        "failed_count": 0,
        "conflict_ids": conflict_ids,
    }
    preserved_existing = 0
    for job in existing_jobs:
        # Keep manually edited text intact while making the job eligible for delivery.
        # The expected text makes a concurrent manual edit win over this stale snapshot.
        if mark_existing_greeting_ready(
            db,
            job["id"],
            expected_greeting=str(job.get("greeting") or ""),
            expected_status=str(job.get("status") or "approved"),
        ):
            preserved_existing += 1
        else:
            # CAS 失败必须上报为冲突：岗位状态或招呼语在读取后已变更，不能静默丢失。
            config["_workbench_greeting_report"].setdefault("conflict_ids", []).append(str(job["id"]))
            _notify(
                config,
                f"{job['company']}｜{job['title']} 的状态或招呼语已变更，保留操作未执行。",
            )
    config["_workbench_greeting_report"]["skipped_existing"] = preserved_existing
    if preserved_existing:
        _notify(config, f"已保留 {preserved_existing} 个岗位现有的招呼语，不会用 AI 覆盖。")

    if not jobs:
        if not preserved_existing:
            console.print("[yellow]没有已确认的岗位可生成招呼语。请先运行 `bosshunter confirm`，或使用 `bosshunter run` 执行完整流程。[/yellow]")
        db.close()
        return 0

    resume_summary = _get_resume_summary(config) if ai_enabled else ""
    if ai_enabled and not resume_summary:
        console.print("[red]无法读取简历[/red]")
        # 缺简历属于服务级阻断：写入 pause_reason 让后台任务按零产出失败语义上报，
        # 而不是伪装成"完成，产出 0"。
        config["_workbench_greeting_report"]["pause_reason"] = "无法读取简历：请先在配置面板上传简历后重试"
        db.close()
        return 0
    graduation_context = _parse_graduation_context(resume_summary)
    if graduation_context:
        resume_summary = f"{graduation_context}\n\n{resume_summary}"

    ai_cfg = config.get("ai", {})
    review_threshold = ai_cfg.get("greeting_review_threshold", 7.0)
    style_suggestions_enabled = ai_enabled and ai_cfg.get("greeting_style_suggestions", False) is not False

    recent_rows = db.execute(
        """
        SELECT greeting
        FROM jobs
        WHERE greeting IS NOT NULL AND trim(greeting) != ''
        ORDER BY updated_at DESC
        LIMIT 20
        """
    ).fetchall()
    recent_openings = [
        opening
        for row in recent_rows
        if (opening := _opening_signature(str(row["greeting"] or "")))
    ]

    count = 0
    failed = 0
    pause_reason = ""
    stop_event = config.get("_workbench_stop_event")
    cancelled = False
    workbench_log = config.get("_workbench_log")

    def _report_job_progress(current_job: dict, current_index: int) -> None:
        # Background-task progress only: the CLI already renders a progress bar,
        # so per-job lines are surfaced solely through the workbench log channel.
        if callable(workbench_log):
            workbench_log(
                f"生成招呼语 ({current_index}/{len(jobs)})：{current_job['company']}｜{current_job['title']}"
            )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"生成招呼语 (0/{len(jobs)})", total=len(jobs))

        for index, job in enumerate(jobs, start=1):
            if stop_event is not None and stop_event.is_set():
                break
            activity_guard = config.get("_workbench_greeting_activity")
            with activity_guard(job["id"], "generating") if callable(activity_guard) else nullcontext(True) as acquired:
                if not acquired:
                    config["_workbench_greeting_report"].setdefault("conflict_ids", []).append(str(job["id"]))
                    progress.update(task, advance=1)
                    continue
                if callable(activity_guard):
                    row = db.execute("SELECT * FROM jobs WHERE id = ? AND deleted_at IS NULL", (job["id"],)).fetchone()
                    if row is None or row["status"] not in GREETING_ALLOWED_STATUSES:
                        progress.update(task, advance=1)
                        continue
                    job = dict(row)
                if job.get("greeting_reviewed_at") and str(job.get("greeting") or "").strip():
                    config["_workbench_greeting_report"]["skipped_existing"] += 1
                    _notify(
                        config,
                        f"{job['company']}｜{job['title']} 的招呼语已人工确认，本轮不会覆盖。",
                    )
                    progress.update(task, advance=1, description=f"生成招呼语 ({index}/{len(jobs)})")
                    continue
                try:
                    greeting = (
                        _generate_with_token_retry(job, resume_summary, config, "", recent_openings)
                        if ai_enabled else fixed_greeting
                    )
                except OperationCancelled:
                    cancelled = True
                    break
                except AIRequestError as exc:
                    pause_reason = str(exc)
                    break

                original_issues = []
                if greeting and ai_enabled:
                    original_issues = _greeting_style_issues(greeting, recent_openings)
                    if len(greeting) > 300:
                        original_issues.append("超过300字符，建议发送前精简；草稿已完整保留")
                    if _violates_no_question_preference(greeting, config):
                        original_issues.append("可能不符合你的‘不提问’偏好，请确认或编辑；草稿已保留")
                    if style_suggestions_enabled:
                        try:
                            # Review is optional advice: one call, no rewrite or review retry.
                            review = _review_greeting(greeting, job, config)
                            if review is None:
                                _notify(config, f"{job['company']}｜{job['title']} 的质量检查返回格式无法识别，已保留招呼语。")
                            elif review.get("avg", 10) < review_threshold and review.get("critique"):
                                original_issues.append(str(review["critique"]))
                        except OperationCancelled:
                            # Save the completed draft before honoring cancellation.
                            cancelled = True
                        except AIRequestError:
                            style_suggestions_enabled = False
                            _notify(config, "质量检查暂不可用，本批跳过后续检查；已生成内容照常保留，继续生成其他岗位。")

                if not greeting:
                    failed += 1
                    if not pause_reason and not (stop_event is not None and stop_event.is_set()):
                        add_history(db, job["id"], "greeting_failed", "AI 未返回完整招呼语，岗位保留为待生成")
                        _notify(config, f"已跳过 {job['company']}｜{job['title']}：AI 未返回完整招呼语，岗位保留为待生成。")
                    _report_job_progress(job, index)
                    progress.update(task, advance=1, description=f"生成招呼语 ({index}/{len(jobs)})")
                    if pause_reason:
                        break
                    continue

                saved = save_generated_greeting_preview(
                    db,
                    job["id"],
                    original=greeting,
                    optimized=None,
                    style_issues=original_issues,
                    selected_greeting=greeting,
                    selection="generated",
                    expected_greeting=str(job.get("greeting") or ""),
                    expected_status=str(job.get("status") or "approved"),
                )
                if not saved:
                    config["_workbench_greeting_report"].setdefault("conflict_ids", []).append(str(job["id"]))
                    _report_job_progress(job, index)
                    _notify(
                        config,
                        f"{job['company']}｜{job['title']} 的状态或招呼语已变化，生成结果未覆盖现有招呼语。",
                    )
                    progress.update(task, advance=1, description=f"生成招呼语 ({index}/{len(jobs)})")
                    continue
                opening = _opening_signature(greeting)
                if opening:
                    recent_openings.append(opening)
                count += 1
                _report_job_progress(job, index)
                progress.update(task, advance=1, description=f"生成招呼语 ({index}/{len(jobs)})")

                if cancelled or (stop_event is not None and stop_event.is_set()):
                    break

    db.close()
    if pause_reason:
        remaining = max(len(jobs) - count, 0)
        _notify(
            config,
            f"招呼语生成已安全暂停：{pause_reason}。已生成内容已保存，剩余 {remaining} 个岗位下次运行会继续处理。",
            error=True,
        )
    if failed:
        _notify(config, f"本轮有 {failed} 个岗位未生成招呼语并保留为待处理，可稍后重试。")
    config["_workbench_greeting_report"].update({
        "generated_count": count,
        "failed_count": failed,
    })
    if pause_reason:
        # 服务级故障（鉴权/额度/限流等）必须显性上报，供后台任务据此区分 completed/failed。
        config["_workbench_greeting_report"]["pause_reason"] = pause_reason
    return count
