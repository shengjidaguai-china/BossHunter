"""AI Resume - Generate tailored resume for specific jobs."""

import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from rich.console import Console

from bosshunter.ai.credentials import call_anthropic_text
from bosshunter.browser import close_tab, evaluate, new_tab, print_pdf, screenshot, wait_for_load
from bosshunter.cancellation import OperationCancelled, run_cancellable, stop_requested
from bosshunter.db import get_db

console = Console()

RESUME_COMPLETION_MARKER = "<!-- BOSSHUNTER_RESUME_DONE -->"
DEFAULT_RESUME_MAX_PAGES = 3
DEFAULT_RESUME_CHARS_PER_PAGE = 1400
JOB_OK_RESUME_VERSION = "job-ok-v3-master-preserving"
MASTER_RESUME_POLICY = """母版定制规则：
- 基础简历是事实与项目全集母版；默认完整保留全部项目和教育背景
- 只允许按 JD 调整求职方向、个人概述、项目顺序、关键词、表述和证据重点
- 项目必须按 JD 相关度重排，但不得删除、合并或虚构；若确需删减，必须先由候选人单独确认
- 每条核心经历按“任务/问题—个人行动—结果/验证边界”组织；来源缺少其中一项时不得补造
- 严格区分设计、实现、本地验证、真实环境验证、部署和业务结果，不得把团队成果改写成个人成果
"""

RESUME_TAILOR_PROMPT = """你是一位专业简历顾问。请输出一份正常投递用的 Markdown 简历。

规则：
1. 只输出简历正文，不输出任何前言、说明、备注、免责声明
2. 不要虚构任何信息，只能使用候选人简历中已有的内容
3. 只调整顺序、强调程度、措辞表达，保持简历整体结构完整
4. 相关优势只能自然融入个人优势、专业技能、工作经历、项目经历、个人总结等常规栏目
5. 不允许单独新增“岗位匹配亮点”“补充说明”等解释性栏目
6. 不允许把岗位要求里的职责写成候选人已经做过的经历
7. 输出中不得出现“以下内容基于”“基于原始简历”“原始简历事实”“未虚构”“针对该岗位”等过程性表达
8. 以 {resume_max_pages} 页以内作为篇幅优化目标；只能压缩重复表述，不得为了控页删除母版中的项目或教育背景
9. 项目经历必须按岗位相关度排序；弱相关项目可以精简，但必须保留项目标题和至少一条有事实来源的核心经历
10. 先在内部拆解岗位JD，尽可能覆盖岗位JD中的职责和要求；无法用候选人真实经历支撑的要求不要硬编
11. 不要输出JD逐条对照、覆盖情况、匹配说明，只把真实可支撑的匹配点自然写入简历正文
12. 必须围绕岗位标题和核心要求重排内容，首屏突出最相关经历，不要几乎照搬原简历
13. 使用 Job OK 投递结构并完整保留姓名、联系方式、求职方向、教育背景、个人概述、工作经历、项目经历和技能
14. 如果岗位涉及媒体、PR、公关、传播、科技记者，请优先突出已有的新媒体内容、品牌传播、媒体资源、专家访谈、公众号/视频号、技术型业务表达经验
15. 如果岗位涉及小红书、抖音、短视频、内容运营、AIGC内容、热点资讯、平台增长，请优先保留候选人已有的平台案例和量化结果，包括阅读/观看、点赞收藏、粉丝增长、用户群运营等真实证据
16. 必须输出完整简历，不得半句结束；最后一行单独输出 {completion_marker}，系统保存前会自动移除该行
17. 项目身份、本人角色、时间、成熟度、指标口径和事实边界必须可回溯到基础简历
18. 不得把团队成果改写为候选人的个人成果
19. 若完整保留项目后超过建议篇幅，应继续输出完整简历并交给人工审核，不得自行删项目
20. 第一行使用“# 姓名”，随后保留基础简历已有的联系方式，再写“求职方向：{target_direction}”
21. 二级标题统一使用“教育背景、个人概述、工作经历、项目经历、技能”，并按此顺序排列
22. 公司与职位使用三级标题；项目与工作要点使用紧凑项目符号
23. 在内部先把岗位要求映射到候选人简历中的原始证据；找不到证据的要求视为 needs_proof，不得写进最终简历
24. 最终简历中的每个事实性主张都必须能回溯到候选人简历，岗位 JD 不能作为候选人经历的事实来源

## 固定母版策略
{master_policy}

## Job OK 证据映射（系统从基础简历确定）
{evidence_packet}

只能使用标记为 supported 的来源证据。标记为 needs_proof 的要求不得写进最终简历。

## 投递岗位
- 职位：{title}
{target_company_line}
- 薪资：{salary}
- 学历要求：{education}
- 招聘类型：{recruitment_type}
- 核心要求：
{jd}

## 候选人简历
{resume}

## 目标公司写法
{target_company_instruction}

请直接输出 Markdown 简历正文：
"""

RESUME_RETRY_PROMPT = """{base_prompt}

上一次生成结果质量检查未通过，原因如下：
{quality_issues}

请重新生成一版。要求：
1. 以 {resume_max_pages} 页、正文非空白字符不超过 {resume_max_chars} 个作为优化目标；若与完整保留项目冲突，以保留项目为先
2. 优先压缩重复和解释性内容；不得删除或合并母版中的项目
3. 不要新增任何候选人原简历中没有的事实
4. 仍然必须保留基本信息、个人优势、工作经历、教育经历、相关技能
5. 最后一行仍然单独输出 {completion_marker}

请直接输出压缩后的 Markdown 简历正文：
"""

RESUME_ARTIFACT_PHRASES = [
    "以下内容基于",
    "基于原始简历",
    "根据原始简历",
    "根据岗位JD",
    "岗位匹配亮点",
    "匹配该岗位",
    "结合岗位要求",
    "补充说明",
    "原始简历事实",
    "不虚构",
    "未虚构",
    "本次优化",
    "调整后的简历",
    "定制简历",
    "以下为优化后的",
    "针对该岗位",
    "针对本岗位",
    "岗位中的",
    "高度相关",
    "字节岗位",
    "可迁移到",
    "岗位要求",
    "高度匹配",
    "高度贴合",
    "高度适配",
    "JD逐条对照",
    "岗位JD覆盖",
    "逐条对照",
    "覆盖情况",
    "匹配说明",
    "无法覆盖",
]

JOB_OK_SECTION_ALIASES = {
    "基本信息": "基本信息",
    "教育经历": "教育背景",
    "教育背景": "教育背景",
    "个人优势": "个人概述",
    "职业概述": "个人概述",
    "个人概述": "个人概述",
    "工作经历": "工作经历",
    "任职经历": "工作经历",
    "项目经历": "项目经历",
    "AI 产品项目": "项目经历",
    "AI产品项目": "项目经历",
    "产品与用户研究项目": "项目经历",
    "相关技能": "技能",
    "专业技能": "技能",
    "专业能力": "技能",
    "技能": "技能",
}
JOB_OK_SECTION_ORDER = ("教育背景", "个人概述", "工作经历", "项目经历", "技能")

ROLE_KEYWORD_GROUPS = [
    {
        "name": "媒体/PR/传播",
        "triggers": ("PR", "媒体", "公关", "传播", "记者", "舆情"),
        "required": ("PR", "媒体", "公关", "传播", "新闻稿", "采访", "公众号", "视频号", "品牌"),
    },
    {
        "name": "AI/科技",
        "triggers": ("AI", "人工智能", "AIGC", "大模型", "智能", "科技"),
        "required": ("AI", "人工智能", "AIGC", "大模型", "智能", "技术", "科技"),
    },
]

RECRUITER_JOB_MARKERS = (
    "猎头", "猎头顾问", "招聘顾问", "人才顾问", "寻访顾问",
    "代招", "代为招聘", "受客户委托", "为客户招聘", "推荐至客户", "rpo",
)
RECRUITER_COMPANY_PLACEHOLDER_RE = re.compile(
    r"某某公司|某(?:大型|知名|头部)(?:互联网|科技|人工智能|上市)?公司|"
    r"某互联网(?:大厂|公司)|客户公司|目标公司"
)
ANONYMIZED_TARGET_COMPANY_RE = re.compile(
    r"某(?:某|大型|知名|头部)?[^|｜，。；\n]{0,24}(?:公司|企业|集团)",
    re.I,
)


def _is_recruiter_job(job: dict | None) -> bool:
    """Return true only when the job contains explicit agency signals."""
    if not job:
        return False
    company = str(job.get("company") or "").strip()
    if ANONYMIZED_TARGET_COMPANY_RE.search(company):
        return True
    haystack = " ".join(
        str(job.get(key) or "")
        for key in ("title", "company", "hr_title", "company_industry", "jd")
    ).lower()
    return any(marker in haystack for marker in RECRUITER_JOB_MARKERS)


def _resume_target_context(job: dict) -> tuple[str, str, str]:
    """Build prompt fields without inventing a headhunter's client company."""
    title = str(job.get("title") or "目标岗位").strip()
    company = str(job.get("company") or "").strip()
    if _is_recruiter_job(job):
        return (
            "- 公司：猎头/代招岗位（客户公司未作为候选人事实提供）",
            "这是猎头或代招岗位。简历正文不得出现猎头机构、客户公司、某某公司、某大型公司、某知名公司等目标公司表述。",
            title,
        )
    target_direction = f"{title}｜{company}" if company else title
    return (
        f"- 公司：{company or '未提供'}",
        "这是企业直招岗位。目标公司只允许用于求职方向，不得改写成候选人的任职经历。",
        target_direction,
    )


def _remove_recruiter_company_references(markdown_text: str, job: dict | None) -> str:
    """Remove placeholder/client-company wording from recruiter-facing resumes."""
    if not _is_recruiter_job(job):
        return markdown_text
    company = str((job or {}).get("company") or "").strip()
    anonymized_company = bool(ANONYMIZED_TARGET_COMPANY_RE.search(company))
    cleaned_lines: list[str] = []
    before_sections = True
    for raw_line in markdown_text.splitlines():
        line = raw_line
        if line.startswith("## "):
            before_sections = False
        if company and (before_sections or anonymized_company):
            line = line.replace(company, "")
        line = RECRUITER_COMPANY_PLACEHOLDER_RE.sub("", line)
        line = re.sub(r"(?:目标|意向)公司\s*[：:]\s*(?:[｜|·,，、/]\s*)?", "", line)
        line = re.sub(r"[｜|·,，、/]\s*(?=$)", "", line).rstrip()
        if not re.fullmatch(r"\s*(?:目标|意向)公司\s*[：:]?\s*", line):
            cleaned_lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines)).strip() + "\n"

PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{[^{}\n]{1,100}\}\}"),
    re.compile(r"\$\{[^{}\n]{1,100}\}"),
    re.compile(r"\[[^\]\n]{0,80}(?:待填写|待补充|请填写|占位符|placeholder|todo|tbd|xxx)[^\]\n]{0,80}\]", re.I),
    re.compile(r"<[^<>\n]{0,80}(?:待填写|待补充|请填写|占位符|placeholder|todo|tbd|xxx)[^<>\n]{0,80}>", re.I),
    re.compile(r"\b(?:TODO|TBD|XXX)\b", re.I),
    re.compile(r"(?:待填写|待补充|请填写|占位符)(?:[：:][^\s，。；;\n]{0,40})?"),
]

FACT_TOKEN_PATTERNS = [
    re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"),
    re.compile(r"https?://[^\s)>）】]+", re.I),
    re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)(?:19|20)\d{2}(?:[./年-](?:0?[1-9]|1[0-2]))?(?:[./月-](?:0?[1-9]|[12]\d|3[01]))?(?:日)?(?!\d)"),
    re.compile(
        r"(?<![\w.])\d+(?:\.\d+)?(?:\s*[-~至到]\s*\d+(?:\.\d+)?)?\s*"
        r"(?:%|％|年|个月|月|天|人|次|篇|万|亿|元|K|k|W|w|倍|\+)(?!\w)"
    ),
]

JOB_OK_STOP_TOKENS = {
    "负责", "工作", "岗位", "要求", "相关", "经验", "能力", "进行",
    "以及", "具有", "具备", "优先", "能够", "熟悉", "良好", "以上",
    "公司", "团队", "产品", "经理", "项目",
}

JOB_OK_JD_META_PHRASES = (
    "感谢你关注", "非常抱歉", "提前投简历", "只看", "职位描述", "岗位描述",
    "以下是我司", "公司介绍", "暑假实习", "实习请提前",
)

JOB_OK_REQUIREMENT_SIGNALS = (
    "负责", "要求", "需要", "必须", "优先", "能力", "经验", "熟悉", "掌握",
    "具备", "能够", "能用", "会用", "学历", "专业", "本科", "硕士", "英语",
    "设计", "开发", "推动", "协调",
)

JOB_OK_CONCEPTS = {
    "data_metrics": ("数据指标", "指标体系", "核心指标", "转化指标", "埋点", "数据分析"),
    "cross_functional": ("跨团队", "跨部门", "研发协同", "协同研发", "项目协同"),
    "user_research": ("用户调研", "用户访谈", "需求调研", "用户研究", "用户洞察"),
    "ai_coding": ("ai撸代码", "ai开发", "独立开发", "typescript", "javascript", "python", "代码"),
    "end_to_end": ("从产品需求到开发", "从需求定义推进至", "从0到1", "独立完成", "研发协同"),
    "hands_on": ("动手能力", "独立开发", "自动化测试", "生产构建", "部署上线"),
    "english": ("英语", "英文", "海外资料"),
    "degree_master": ("硕士", "研究生"),
}

_resume_failure_reasons: dict[str, str] = {}
_last_resume_api_error = ""


def _find_resume_artifacts(markdown_text: str) -> list[str]:
    """Find process-disclosure phrases that should not appear in a resume."""
    return [phrase for phrase in RESUME_ARTIFACT_PHRASES if phrase in markdown_text]


def _normalize_validation_token(token: str) -> str:
    return re.sub(r"\s+", "", token).lower()


def _extract_validation_tokens(text: str, patterns: list[re.Pattern]) -> list[str]:
    tokens: list[str] = []
    for pattern in patterns:
        tokens.extend(match.group(0).strip() for match in pattern.finditer(text or ""))
    return tokens


def _extract_placeholder_tokens(text: str) -> list[str]:
    tokens = _extract_validation_tokens(text, PLACEHOLDER_PATTERNS)
    return [
        token
        for token in tokens
        if not any(token != other and token in other for other in tokens)
    ]


def _find_new_placeholders(markdown_text: str, base_resume: str) -> list[str]:
    """Return placeholders introduced or rewritten by the model.

    Placeholders already present verbatim in the source resume are an accepted
    baseline. Rewording one creates a new token and is therefore blocked.
    """
    base_counts = Counter(
        _normalize_validation_token(token)
        for token in _extract_placeholder_tokens(base_resume)
    )
    seen_counts: Counter[str] = Counter()
    introduced: list[str] = []
    for token in _extract_placeholder_tokens(markdown_text):
        normalized = _normalize_validation_token(token)
        seen_counts[normalized] += 1
        if seen_counts[normalized] > base_counts[normalized] and token not in introduced:
            introduced.append(token)
    return introduced


def _find_new_fact_tokens(markdown_text: str, base_resume: str) -> list[str]:
    """Return fact-sensitive values that do not exist in the source resume."""
    base_tokens = {
        _normalize_validation_token(token)
        for token in _extract_validation_tokens(base_resume, FACT_TOKEN_PATTERNS)
    }
    introduced: list[str] = []
    for token in _extract_validation_tokens(markdown_text, FACT_TOKEN_PATTERNS):
        normalized = _normalize_validation_token(token)
        if normalized not in base_tokens and token not in introduced:
            introduced.append(token)
    return introduced


def _markdown_section(markdown_text: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\s*{re.escape(heading)}\s*$\n?(.*?)(?=^\s*##\s+|\Z)"
    )
    match = pattern.search(markdown_text or "")
    return match.group(1) if match else ""


def _project_section(markdown_text: str) -> str:
    """Return the first conventional project section from a resume."""
    for heading in ("## 项目经历", "## 项目经验", "## 代表项目"):
        section = _markdown_section(markdown_text, heading)
        if section:
            return section
    return ""


def _resume_project_headings(markdown_text: str) -> list[str]:
    """Extract explicitly named projects from the project section."""
    return [
        re.sub(r"\s+", " ", heading).strip()
        for heading in re.findall(r"(?m)^\s*###\s+(.+?)\s*$", _project_section(markdown_text))
        if heading.strip()
    ]


def _project_identity(heading: str) -> str:
    """Build a stable project identity while allowing role/date edits."""
    title = re.sub(r"[*_`#]", "", heading or "")
    title = re.split(r"\s*[|｜]\s*", title, maxsplit=1)[0]
    title = re.sub(
        r"(?:19|20)\d{2}(?:[./年-]\d{1,2})?(?:\s*[-至—~]\s*(?:至今|(?:19|20)\d{2}(?:[./年-]\d{1,2})?))?",
        "",
        title,
    )
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())


def _project_identity_matches(source_heading: str, candidate_heading: str) -> bool:
    source = _project_identity(source_heading)
    candidate = _project_identity(candidate_heading)
    if not source or not candidate:
        return False
    return source in candidate or candidate in source or SequenceMatcher(None, source, candidate).ratio() >= 0.78


def _find_project_preservation_issues(markdown_text: str, base_resume: str) -> list[str]:
    """Block silent deletion of named projects from the master resume."""
    source_projects = _resume_project_headings(base_resume)
    if not source_projects:
        return []
    candidate_projects = _resume_project_headings(markdown_text)
    missing = [
        source
        for source in source_projects
        if not any(_project_identity_matches(source, candidate) for candidate in candidate_projects)
    ]
    issues: list[str] = []
    if len(candidate_projects) < len(source_projects):
        issues.append(
            "母版项目保留校验失败："
            f"基础简历有 {len(source_projects)} 个项目，当前版本只有 {len(candidate_projects)} 个；"
            "如需删减项目，请先单独确认"
        )
    if missing:
        issues.append("母版项目保留校验失败：缺少项目：" + "、".join(missing[:8]))
    return issues


def _find_missing_core_facts(markdown_text: str, base_resume: str) -> list[str]:
    """Keep fact-like contact/basic-info values from the source resume."""
    source_basic_info = _markdown_section(base_resume, "## 基本信息")
    if not source_basic_info:
        return []
    source_tokens = _extract_validation_tokens(source_basic_info, FACT_TOKEN_PATTERNS)
    generated_keys = {
        _normalize_validation_token(token)
        for token in _extract_validation_tokens(markdown_text, FACT_TOKEN_PATTERNS)
    }
    return [
        token
        for token in source_tokens
        if _normalize_validation_token(token) not in generated_keys
    ]


def _find_blocking_integrity_issues(
    markdown_text: str,
    base_resume: str,
) -> list[str]:
    """Return issues that must prevent a resume from being marked ready."""
    issues: list[str] = []

    missing_core_facts = _find_missing_core_facts(markdown_text, base_resume)
    if missing_core_facts:
        issues.append(
            "事实完整性校验失败：缺少基础简历中的关键信息："
            + ", ".join(missing_core_facts[:8])
        )

    new_facts = _find_new_fact_tokens(markdown_text, base_resume)
    if new_facts:
        issues.append(
            "事实完整性校验失败：模型新增了原始简历中不存在的数据："
            + ", ".join(new_facts[:8])
        )

    new_placeholders = _find_new_placeholders(markdown_text, base_resume)
    if new_placeholders:
        issues.append(
            "占位符校验失败：模型新增或改写了占位符："
            + ", ".join(new_placeholders[:8])
        )
    base_sections = _canonical_resume_sections(base_resume)
    candidate_sections = _canonical_resume_sections(markdown_text)
    for section in ("教育背景", "项目经历"):
        if section in base_sections and section not in candidate_sections:
            issues.append(f"母版结构校验失败：不得删除基础简历中的{section}")
    issues.extend(_find_project_preservation_issues(markdown_text, base_resume))
    return issues


def _set_resume_failure_reason(job_id: str, reason: str) -> None:
    _resume_failure_reasons[str(job_id)] = str(reason).strip() or "未知原因"


def get_last_resume_failure_reason(job_id: str) -> str:
    """Return the latest in-process failure reason for monitor history."""
    return _resume_failure_reasons.get(str(job_id), "")


def _strip_completion_marker(markdown_text: str) -> tuple[str | None, str | None]:
    """Return any non-empty resume body, removing the optional completion marker."""
    marker_issue = None
    if RESUME_COMPLETION_MARKER not in markdown_text:
        marker_issue = "生成结果缺少完成标记，可能不完整"
    body = markdown_text.split(RESUME_COMPLETION_MARKER, 1)[0].strip()
    if not body:
        return None, "生成结果为空"
    return f"{body}\n", marker_issue


def _find_resume_quality_issues(
    markdown_text: str,
    base_resume: str,
    job: dict | None = None,
    max_chars: int | None = None,
    max_pages: int = DEFAULT_RESUME_MAX_PAGES,
) -> list[str]:
    """Find issues that make a generated resume unsafe to mark as ready."""
    issues: list[str] = []
    stripped = markdown_text.strip()

    if not stripped.startswith("#"):
        issues.append("生成结果不像 Markdown 简历正文")

    if max_chars and _resume_content_length(markdown_text) > max_chars:
        issues.append(f"简历内容过长，默认应控制在 {max_pages} 页以内")

    generated_sections = _canonical_resume_sections(markdown_text)
    for section in _required_sections_from_base(base_resume):
        if section not in generated_sections:
            issues.append(f"缺少基础简历中的常规栏目：{section}")

    last_line = _last_content_line(markdown_text)
    if _looks_abrupt(last_line):
        issues.append("简历末尾疑似半句截断")

    if _is_nearly_unchanged(markdown_text, base_resume):
        issues.append("生成结果与原始简历几乎一致，定制化不足")

    if job:
        job_text = " ".join(str(job.get(key) or "") for key in ("title", "company", "company_industry", "jd"))
        for group in ROLE_KEYWORD_GROUPS:
            if any(token in job_text for token in group["triggers"]):
                if not any(token in markdown_text for token in group["required"]):
                    issues.append(f"未体现岗位关键词方向：{group['name']}")

    return issues


def _job_ok_match_tokens(text: str) -> set[str]:
    """Build dependency-free matching tokens for Chinese and ASCII resume text."""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"\s+", "", normalized)
    ascii_tokens = {
        token
        for token in re.findall(r"[a-z][a-z0-9+.#-]{1,}", normalized)
        if len(token) >= 2
    }
    chinese_tokens: set[str] = set()
    for run in re.findall(r"[\u4e00-\u9fff]+", normalized):
        chinese_tokens.update(run[index:index + 2] for index in range(max(0, len(run) - 1)))
        chinese_tokens.update(token for token in JOB_OK_STOP_TOKENS if token in run)
    tokens = (ascii_tokens | chinese_tokens) - JOB_OK_STOP_TOKENS
    for concept, phrases in JOB_OK_CONCEPTS.items():
        if any(phrase in normalized for phrase in phrases):
            tokens.add(f"concept:{concept}")
    return tokens


def _job_ok_requirements(job: dict, limit: int = 8) -> list[str]:
    """Extract a compact, ordered set of JD requirements for evidence review."""
    jd = unicodedata.normalize("NFKC", str(job.get("jd") or "")).strip()
    jd = re.split(r"(?:我们有个)?面试题", jd, maxsplit=1)[0]
    chunks: list[tuple[int, int, str]] = []
    chunk_index = 0
    for part in re.split(r"[\r\n；;。，,）)]+|(?=\d+[.)、])", jd):
        cleaned = re.sub(r"^\s*(?:[-*•·]|\d+[.)、]|[（(]?\d+[）)])\s*", "", part).strip()
        cleaned = re.split(r"以下是我司|公司信息", cleaned, maxsplit=1)[0].strip()
        cleaned = re.sub(r"https?://\S+", "", cleaned, flags=re.I).strip()
        if len(cleaned) < 4 or any(phrase in cleaned for phrase in JOB_OK_JD_META_PHRASES):
            continue
        signal_score = sum(signal in cleaned.lower() for signal in JOB_OK_REQUIREMENT_SIGNALS)
        if signal_score:
            chunks.append((signal_score, chunk_index, cleaned[:160]))
            chunk_index += 1
    unique: list[str] = []
    seen: set[str] = set()
    for _, _, chunk in sorted(chunks, key=lambda item: (-item[0], item[1])):
        key = re.sub(r"\s+", "", chunk).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
        if len(unique) >= limit:
            break
    return unique


def _job_ok_evidence_lines(base_resume: str) -> list[str]:
    """Return exact source-resume lines that are safe to cite as evidence."""
    evidence: list[str] = []
    seen: set[str] = set()
    for raw_line in (base_resume or "").splitlines():
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)、])\s*", "", raw_line).strip()
        if not line or line.startswith("#") or line == "---" or len(line) < 6 or line in seen:
            continue
        seen.add(line)
        evidence.append(line[:400])
    return evidence


def _job_ok_evidence_map(job: dict, base_resume: str, tailored_resume: str) -> list[dict[str, object]]:
    """Map JD requirements only to exact source-resume evidence."""
    evidence_tokens = [(line, _job_ok_match_tokens(line)) for line in _job_ok_evidence_lines(base_resume)]
    tailored_normalized = re.sub(r"\s+", "", tailored_resume or "").lower()
    mapped: list[dict[str, object]] = []
    for requirement in _job_ok_requirements(job):
        requirement_tokens = _job_ok_match_tokens(requirement)
        best_line = ""
        best_overlap: set[str] = set()
        for line, tokens in evidence_tokens:
            overlap = requirement_tokens & tokens
            if len(overlap) > len(best_overlap):
                best_line = line
                best_overlap = overlap
        has_concept_match = any(token.startswith("concept:") for token in best_overlap)
        if len(best_overlap) < 3 and not has_concept_match:
            mapped.append({"requirement": requirement, "label": "needs_proof", "evidence": "", "matched_tokens": []})
            continue
        source_normalized = re.sub(r"\s+", "", best_line).lower()
        label = "use_as_is" if source_normalized in tailored_normalized else "rewrite"
        mapped.append({
            "requirement": requirement,
            "label": label,
            "evidence": best_line,
            "matched_tokens": sorted(best_overlap),
        })
    return mapped


def _job_ok_table_text(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def _build_job_ok_resume_review(
    job: dict,
    base_resume: str,
    tailored_resume: str,
    warnings: list[str] | None = None,
    resume_filename: str = "",
) -> str:
    """Build a local evidence review that is never sent with the resume."""
    mappings = _job_ok_evidence_map(job, base_resume, tailored_resume)
    supported = [item for item in mappings if item["label"] != "needs_proof"]
    missing = [item for item in mappings if item["label"] == "needs_proof"]
    use_as_is = [item for item in supported if item["label"] == "use_as_is"]
    rewrites = [item for item in supported if item["label"] == "rewrite"]
    lines = [
        "# Job OK 简历审查报告", "",
        "> 本报告仅用于本地人工审查，不随简历发送。所有“来源证据”均逐字取自基础简历。", "",
        "## JD 匹配诊断", "",
        f"- 目标岗位：{job.get('company') or '未提供'} / {job.get('title') or '未提供'}",
        f"- 已映射证据：{len(supported)}/{len(mappings)} 条要求",
        f"- 可直接使用：{len(use_as_is)} 条",
        f"- 建议改写：{len(rewrites)} 条",
        f"- 缺失证据：{len(missing)} 条", "",
        "## 最强可用证据", "",
        "| 标签 | JD 要求 | 基础简历来源证据 |", "| --- | --- | --- |",
    ]
    if supported:
        for item in supported:
            lines.append(
                f"| `{item['label']}` | {_job_ok_table_text(item['requirement'])} | {_job_ok_table_text(item['evidence'])} |"
            )
    else:
        lines.append("| `needs_proof` | 暂无可安全映射的要求 | 未找到来源证据 |")
    lines.extend(["", "## 缺失证据与待确认问题", ""])
    if missing:
        for item in missing:
            requirement = _job_ok_table_text(item["requirement"])
            lines.extend([
                f"- `needs_proof`：{requirement}",
                f"  - `ask_user`：你是否有可核验的项目、职责、方法或结果可以支撑“{requirement}”？",
            ])
    else:
        lines.append("- 未发现需要补证的已提取要求。")
    lines.extend(["", "## 改写建议", ""])
    if rewrites:
        for item in rewrites:
            lines.append(
                f"- `rewrite`：围绕“{_job_ok_table_text(item['requirement'])}”重写“{_job_ok_table_text(item['evidence'])}”；只可使用基础简历已有的动作、方法和结果。"
            )
    else:
        lines.append("- 暂无需要改写的已映射证据。")
    lines.extend([
        "- `remove`：任何无法回溯到基础简历的事实性主张都应从投递版删除。", "",
        "## 目标简历版本说明", "",
        f"- 投递版文件：{resume_filename or '未提供'}",
        "- 母版策略：默认保留全部项目和教育背景，仅按 JD 调整表述、证据重点和项目顺序。",
        "- 删减权限：系统不自动删除或合并项目；如确需删减，必须先由候选人单独确认。",
        "- 叙事结构：核心经历采用任务/问题—个人行动—结果/验证边界，缺少证据时不补造。",
        "- 证据边界：岗位 JD 仅用于排序和匹配，不作为候选人经历的事实来源。",
    ])
    if warnings:
        lines.append("- 当前质量提示：")
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.append("- 当前质量提示：未发现阻断性事实问题。")
    lines.extend(["", "## 面试追问风险", ""])
    if missing:
        lines.extend(
            f"- 对“{_job_ok_table_text(item['requirement'])}”暂无简历证据，面试前应补证或明确不主张。"
            for item in missing
        )
    else:
        lines.append("- 已提取要求均找到基础简历证据；仍需本人确认职责边界与量化结果口径。")
    return "\n".join(lines).rstrip() + "\n"


def _build_job_ok_evidence_packet(job: dict, base_resume: str) -> str:
    """Give the model an explicit evidence boundary before it rewrites anything."""
    mappings = _job_ok_evidence_map(job, base_resume, "")
    if not mappings:
        return "- 未提取到明确要求：只能重排基础简历中的原有内容。"
    lines: list[str] = []
    for index, item in enumerate(mappings, start=1):
        requirement = _job_ok_table_text(item["requirement"])
        evidence = _job_ok_table_text(item["evidence"])
        if item["label"] == "needs_proof":
            lines.append(f"{index}. [needs_proof] {requirement}｜不得写入简历")
        else:
            lines.append(f"{index}. [supported] {requirement}｜来源证据：{evidence}")
    return "\n".join(lines)


def _canonical_resume_sections(markdown_text: str) -> set[str]:
    headings = re.findall(r"(?m)^\s*##\s+(.+?)\s*$", markdown_text or "")
    return {JOB_OK_SECTION_ALIASES.get(heading.strip(), heading.strip()) for heading in headings}


def _normalize_job_ok_resume_structure(markdown_text: str) -> str:
    """Normalize known headings and order without inventing or deleting facts."""
    text = (markdown_text or "").strip()
    first_section = re.search(r"(?m)^\s*##\s+", text)
    if not first_section:
        return f"{text}\n" if text else ""
    preamble = text[:first_section.start()].strip()
    sections: dict[str, list[str]] = {}
    unknown_order: list[str] = []
    matches = list(re.finditer(r"(?m)^\s*##\s+(.+?)\s*$", text))
    for index, match in enumerate(matches):
        raw_heading = match.group(1).strip()
        canonical = JOB_OK_SECTION_ALIASES.get(raw_heading, raw_heading)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[match.end():end].strip()
        if canonical == "基本信息":
            if content:
                preamble = "\n\n".join(part for part in (preamble, content) if part)
            continue
        if canonical not in sections:
            sections[canonical] = []
            if canonical not in JOB_OK_SECTION_ORDER:
                unknown_order.append(canonical)
        if content:
            sections[canonical].append(content)
    parts = [preamble] if preamble else []
    for heading in (*JOB_OK_SECTION_ORDER, *unknown_order):
        contents = sections.get(heading, [])
        if contents:
            parts.append(f"## {heading}\n\n" + "\n\n".join(contents))
    return "\n\n".join(parts).strip() + "\n"


def _required_sections_from_base(base_resume: str) -> list[str]:
    present = _canonical_resume_sections(base_resume)
    return [section for section in JOB_OK_SECTION_ORDER if section in present]


def _last_content_line(markdown_text: str) -> str:
    for line in reversed(markdown_text.splitlines()):
        stripped = line.strip()
        if stripped and stripped != "---":
            return stripped
    return ""


def _looks_abrupt(line: str) -> bool:
    if not line:
        return True
    if line.startswith("#"):
        return True
    if len(line) < 12:
        return True
    if line[-1] in "。.!！?？；;)）]】》\"'”’":
        return False
    if re.search(r"(，|、|及|和|与|围绕|包括|病例|技术|项目)$", line):
        return True
    return False


def _is_nearly_unchanged(markdown_text: str, base_resume: str) -> bool:
    base = _normalize_resume_for_similarity(base_resume)
    tailored = _normalize_resume_for_similarity(markdown_text)
    if len(base) < 500 or len(tailored) < 500:
        return False
    return SequenceMatcher(None, base, tailored).ratio() >= 0.985


def _normalize_resume_for_similarity(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _resume_content_length(markdown_text: str) -> int:
    return len(re.sub(r"\s+", "", markdown_text))


def _resume_max_pages_from_config(config: dict) -> int:
    ai_cfg = config.get("ai", {}) if isinstance(config, dict) else {}
    return _positive_int(ai_cfg.get("resume_max_pages"), DEFAULT_RESUME_MAX_PAGES)


def _resume_max_chars_from_config(config: dict, max_pages: int) -> int:
    ai_cfg = config.get("ai", {}) if isinstance(config, dict) else {}
    return _positive_int(ai_cfg.get("resume_max_chars"), max_pages * DEFAULT_RESUME_CHARS_PER_PAGE)


def _positive_int(value: object, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def _pdf_page_count(pdf_path: Path) -> int | None:
    """Return PDF page count when it can be determined."""
    if not pdf_path.exists():
        return None

    try:
        from pypdf import PdfReader

        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        pass

    try:
        data = pdf_path.read_bytes()
    except OSError:
        return None

    count = len(re.findall(rb"/Type\s*/Page\b", data))
    return count or None


def _resume_fingerprint(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _resume_metadata_path(resume_path: Path) -> Path:
    return resume_path.with_suffix(".job-ok-meta.json")


def is_job_ok_resume_current(job: dict, config: dict) -> bool:
    """Return whether an artifact matches the current renderer, JD and base resume."""
    if str(job.get("status") or "") == "resume_sent":
        return True
    output_path = Path(str(job.get("resume_path") or ""))
    if not str(job.get("resume_path") or "") or not output_path.exists():
        return False
    base_path = Path(str(config.get("profile", {}).get("resume_path") or ""))
    if not base_path.exists():
        return False
    try:
        metadata = json.loads(_resume_metadata_path(output_path).read_text(encoding="utf-8"))
        base_resume = base_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    return (
        metadata.get("version") == JOB_OK_RESUME_VERSION
        and metadata.get("job_id") == str(job.get("id") or "")
        and metadata.get("jd_sha256") == _resume_fingerprint(str(job.get("jd") or ""))
        and metadata.get("base_resume_sha256") == _resume_fingerprint(base_resume)
    )


def _write_resume_metadata(output_path: Path, job: dict, base_resume: str) -> None:
    metadata = {
        "version": JOB_OK_RESUME_VERSION,
        "policy": "master-preserving-jd-tailoring",
        "job_id": str(job.get("id") or ""),
        "jd_sha256": _resume_fingerprint(str(job.get("jd") or "")),
        "base_resume_sha256": _resume_fingerprint(base_resume),
        "artifact": output_path.name,
    }
    _resume_metadata_path(output_path).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _call_claude(prompt: str, config: dict) -> str | None:
    """Call Claude API and return response text."""
    global _last_resume_api_error
    _last_resume_api_error = ""
    try:
        ai_cfg = config.get("ai", {}) if isinstance(config, dict) else {}
        max_tokens = int(ai_cfg.get("resume_max_tokens") or 8000)
        return run_cancellable(
            lambda: call_anthropic_text(prompt, config, max_tokens),
            config,
        )
    except OperationCancelled:
        raise
    except Exception as e:
        _last_resume_api_error = str(e)
        console.print(f"[red]API 调用失败: {e}[/red]")
        return None


def _resume_html(markdown_text: str, *, image_mode: bool = False) -> str:
    """Build the deterministic Job OK layout shared by PDF and PNG."""
    import markdown2

    html_body = markdown2.markdown(markdown_text, extras=["tables", "fenced-code-blocks"])
    page_rule = "@page { size: A4; margin: 0; }" if image_mode else "@page { size: A4; margin: 9mm 11mm; }"
    sheet_style = """
    html, body { margin: 0; padding: 0; background: #fff; }
    [data-resume-sheet] { width: 210mm; min-height: 297mm; padding: 9mm 11mm; background: #fff; }
    """ if image_mode else ""
    rendered_body = (
        f'<main data-resume-sheet>{html_body}<span data-resume-end aria-hidden="true"></span></main>'
        if image_mode else html_body
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    {page_rule}
    * {{ box-sizing: border-box; }}
    {sheet_style}
    body {{
        font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 8.4pt; line-height: 1.32; margin: 0; color: #20242a;
    }}
    h1 {{ font-size: 21.5pt; line-height: 1.05; color: #1f4e79; margin: 0 0 2.5mm; }}
    h2 {{ font-size: 10.5pt; color: #1f4e79; margin: 3.2mm 0 1.5mm; padding-bottom: .8mm; border-bottom: .7pt solid #b8c7d9; break-after: avoid; }}
    h3 {{ font-size: 9.1pt; color: #20242a; margin: 1.8mm 0 .8mm; break-after: avoid; }}
    p {{ margin: 0 0 1.3mm; }}
    ul, ol {{ padding-left: 4.6mm; margin: .6mm 0 1.5mm; }}
    li {{ margin: 0 0 .7mm; }}
    h3, li, table, blockquote {{ break-inside: avoid; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1.2mm 0; font-size: 8pt; }}
    th, td {{ border: .5pt solid #b8c7d9; padding: 1mm 1.5mm; text-align: left; }}
    th {{ background: #edf3f8; color: #1f4e79; }}
</style>
</head>
<body>
{rendered_body}
</body>
</html>"""


def _render_pdf(markdown_text: str, output_path: Path) -> bool:
    """Render markdown to PDF via Chrome CDP.

    If Chrome is unavailable, keep the UTF-8 Markdown instead of producing a
    PDF with missing CJK glyphs through a font-less fallback renderer.
    """
    full_html = _resume_html(markdown_text)

    # Strategy 1: Use Chrome CDP to print PDF (preferred, no extra deps)
    if _render_pdf_via_cdp(full_html, output_path):
        return True
    return False


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    """Read PNG dimensions without adding a Pillow dependency."""
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _render_png(markdown_text: str, output_path: Path) -> bool:
    """Render an A4 PNG from the same editable Markdown source."""
    return _render_png_via_cdp(_resume_html(markdown_text, image_mode=True), output_path)


def _render_png_via_cdp(html_content: str, output_path: Path) -> bool:
    """Capture the complete A4 resume sheet through the background runtime."""
    import tempfile
    import time

    temp_html = Path(tempfile.gettempdir()) / f"bosshunter_resume_{id(output_path)}.html"
    target_id = None
    try:
        temp_html.write_text(html_content, encoding="utf-8")
        target_id = new_tab(temp_html.as_uri(), background=True)
        if not target_id:
            return False
        time.sleep(2)
        geometry = evaluate(
            target_id,
            """(() => {
                const sheet = document.querySelector('[data-resume-sheet]');
                const end = document.querySelector('[data-resume-end]');
                if (!sheet || !end) return null;
                const sheetRect = sheet.getBoundingClientRect();
                const endRect = end.getBoundingClientRect();
                return {width: sheetRect.width, height: sheetRect.height,
                        endInside: endRect.bottom <= sheetRect.bottom + 1};
            })()""",
        )
        if not isinstance(geometry, dict) or not geometry.get("endInside"):
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not screenshot(target_id, output_path, selector="[data-resume-sheet]"):
            return False
        dimensions = _png_dimensions(output_path)
        if dimensions is None:
            return False
        width, height = dimensions
        css_width = float(geometry.get("width") or 0)
        css_height = float(geometry.get("height") or 0)
        if css_width <= 0 or css_height <= 0 or width < 700 or height <= width:
            return False
        return abs((height / width) - (css_height / css_width)) <= 0.04
    except Exception:
        return False
    finally:
        if target_id:
            close_tab(target_id)
        temp_html.unlink(missing_ok=True)


def _render_pdf_via_cdp(html_content: str, output_path: Path) -> bool:
    """Use Browser Runtime Page.printToPDF via the Python browser facade."""
    import tempfile
    import time

    # The Browser Runtime is a separate process and may have a different
    # working directory. Always send it an absolute destination so a relative
    # resume_output_dir cannot create the PDF somewhere else.
    output_path = output_path.expanduser().resolve()
    temp_html = Path(tempfile.gettempdir()) / "bosshunter_resume.html"
    temp_html.write_text(html_content, encoding="utf-8")
    file_url = f"file:///{temp_html.as_posix()}"

    try:
        for attempt in range(2):
            target_id = None
            try:
                target_id = new_tab(file_url, background=True)
                if target_id and wait_for_load(target_id, timeout=10):
                    # Give Chrome a brief turn to resolve system fonts after
                    # the document load event before printing the page.
                    time.sleep(0.25)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.unlink(missing_ok=True)
                    if print_pdf(target_id, output_path):
                        if output_path.exists() and output_path.stat().st_size > 0:
                            return True
            except Exception:
                pass
            finally:
                if target_id:
                    close_tab(target_id)
            if attempt == 0:
                time.sleep(0.5)
        return False
    finally:
        temp_html.unlink(missing_ok=True)


def _resume_generation_source(config: dict, fallback: str = "configured_ai") -> str:
    ai_cfg = config.get("ai", {}) if isinstance(config, dict) else {}
    identity = f"{ai_cfg.get('base_url', '')} {ai_cfg.get('model', '')}".lower()
    return "deepseek" if "deepseek" in identity else fallback


def _safe_resume_basename(job: dict) -> str:
    safe_company = "".join(c for c in str(job.get("company") or "") if c not in r'\/:*?"<>|')[:20]
    safe_title = "".join(c for c in str(job.get("title") or "") if c not in r'\/:*?"<>|')[:20]
    return f"{safe_company}_{safe_title}_{job['id']}"


def _save_resume_artifacts(
    db,
    job: dict,
    config: dict,
    base_resume: str,
    tailored_md: str,
    delivery_warnings: list[str],
    *,
    source: str,
) -> Path:
    """Persist editable Markdown and deterministic PDF/PNG derivatives."""
    output_dir = Path(config.get("profile", {}).get("resume_output_dir", "./data/resumes"))
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = _safe_resume_basename(job)

    md_path = output_dir / f"{base_name}.md"
    md_path.write_text(tailored_md, encoding="utf-8")
    review_path = output_dir / f"{base_name}.job-ok-review.md"
    review_path.write_text(
        _build_job_ok_resume_review(
            job,
            base_resume,
            tailored_md,
            delivery_warnings,
            md_path.name,
        ),
        encoding="utf-8",
    )

    image_path = output_dir / f"{base_name}.png"
    image_ready = _render_png(tailored_md, image_path)
    if not image_ready:
        image_path.unlink(missing_ok=True)

    pdf_path = output_dir / f"{base_name}.pdf"
    pdf_ready = _render_pdf(tailored_md, pdf_path)
    if pdf_ready:
        pdf_pages = _pdf_page_count(pdf_path)
        max_pages = _resume_max_pages_from_config(config)
        if pdf_pages and pdf_pages > max_pages:
            console.print(f"[yellow]PDF 共 {pdf_pages} 页，超过 {max_pages} 页建议篇幅，仍保留并等待审核[/yellow]")
    preferred_path = pdf_path if pdf_ready else md_path
    review_status = "needs_review" if image_ready else "render_error"
    failure_reason = None if image_ready else "图片简历渲染失败，请检查后台浏览器后重新渲染"

    db.execute(
        """
        UPDATE jobs
        SET resume_path = ?, resume_source_path = ?, resume_image_path = ?,
            resume_review_status = ?, resume_generation_source = ?,
            resume_failure_reason = ?, resume_reviewed_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND deleted_at IS NULL
        """,
        (
            str(preferred_path),
            str(md_path),
            str(image_path) if image_ready else None,
            review_status,
            source,
            failure_reason,
            str(job["id"]),
        ),
    )
    db.commit()
    _write_resume_metadata(preferred_path, job, base_resume)
    console.print(f"[green]✓ Job OK 审查报告: {review_path}[/green]")
    if image_ready:
        console.print(f"[green]✓ 图片简历已生成: {image_path}[/green]")
    if pdf_ready:
        console.print(f"[green]✓ PDF 已生成: {pdf_path}[/green]")
    else:
        console.print(f"[yellow]PDF 渲染失败，已保留 Markdown: {md_path}[/yellow]")
    return preferred_path


def save_resume_draft(
    job_id: str,
    markdown_text: str,
    config: dict,
    *,
    source: str = "human_edit",
) -> Path:
    """Validate an edited draft, then regenerate reviewable artifacts."""
    candidate = _normalize_job_ok_resume_structure(str(markdown_text or "").strip())
    if not candidate:
        raise ValueError("图片简历内容不能为空")

    db = get_db()
    try:
        row = db.execute("SELECT * FROM jobs WHERE id = ? AND deleted_at IS NULL", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        job = dict(row)
        candidate = _remove_recruiter_company_references(candidate, job)
        base_path = Path(str(config.get("profile", {}).get("resume_path") or ""))
        if not base_path.exists():
            raise ValueError("基础简历文件不存在")
        base_resume = base_path.read_text(encoding="utf-8")
        blocking_issues = _find_blocking_integrity_issues(candidate, base_resume)
        if blocking_issues:
            raise ValueError("；".join(blocking_issues))
        max_pages = _resume_max_pages_from_config(config)
        max_chars = _resume_max_chars_from_config(config, max_pages)
        warnings = _find_resume_quality_issues(
            candidate,
            base_resume,
            job,
            max_chars=max_chars,
            max_pages=max_pages,
        )
        return _save_resume_artifacts(
            db,
            job,
            config,
            base_resume,
            candidate,
            warnings,
            source=source,
        )
    finally:
        db.close()


def generate_tailored_resume(job_id: str, config: dict) -> Path | None:
    """Generate a tailored resume for a specific job.

    Returns path to generated file, or None on failure.
    """
    global _last_resume_api_error
    _resume_failure_reasons.pop(str(job_id), None)
    _last_resume_api_error = ""
    db = get_db()

    def fail(reason: str) -> None:
        _set_resume_failure_reason(job_id, reason)
        console.print(f"[red]定制简历生成失败：{reason}[/red]")
        try:
            db.execute(
                """
                UPDATE jobs
                SET resume_review_status = 'needs_codex',
                    resume_failure_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND deleted_at IS NULL
                """,
                (reason, job_id),
            )
            db.commit()
        except Exception:
            pass
        db.close()
        return None

    # Get job info
    row = db.execute("SELECT * FROM jobs WHERE id = ? AND deleted_at IS NULL", (job_id,)).fetchone()
    if not row:
        return fail(f"未找到岗位 ID：{job_id}")

    job = dict(row)

    # Load base resume
    resume_path = Path(config.get("profile", {}).get("resume_path", "./resume.md"))
    if not resume_path.exists():
        return fail(f"基础简历文件不存在：{resume_path}")

    try:
        resume_text = resume_path.read_text(encoding="utf-8")
    except OSError as exc:
        return fail(f"无法读取基础简历：{exc}")
    resume_max_pages = _resume_max_pages_from_config(config)
    resume_max_chars = _resume_max_chars_from_config(config, resume_max_pages)

    # Generate tailored resume via AI
    console.print(f"[bold]为 {job['company']} - {job['title']} 生成定制简历...[/bold]")

    target_company_line, target_company_instruction, target_direction = _resume_target_context(job)
    base_prompt = RESUME_TAILOR_PROMPT.format(
        title=job["title"],
        target_company_line=target_company_line,
        target_company_instruction=target_company_instruction,
        salary=job["salary"] or "面议",
        education=job.get("education", "") or "未识别",
        recruitment_type={"campus": "校招", "experienced": "社招"}.get(
            job.get("recruitment_type", ""), "未识别"
        ),
        jd=job["jd"][:2000] if job["jd"] else "无详细描述",
        resume=resume_text,
        resume_max_pages=resume_max_pages,
        completion_marker=RESUME_COMPLETION_MARKER,
        master_policy=MASTER_RESUME_POLICY,
        target_direction=target_direction,
        evidence_packet=_build_job_ok_evidence_packet(job, resume_text),
    )

    tailored_md = None
    prompt = base_prompt
    for attempt in range(2):
        try:
            raw_tailored_md = _call_claude(prompt, config)
        except OperationCancelled:
            db.close()
            raise
        if stop_requested(config):
            db.close()
            raise OperationCancelled("用户已请求停止")
        if not raw_tailored_md:
            if _last_resume_api_error:
                return fail(f"AI 服务调用失败：{_last_resume_api_error}")
            return fail("AI 服务未返回简历内容，请检查模型配置或稍后重试")

        candidate_md, marker_issue = _strip_completion_marker(raw_tailored_md)
        if not candidate_md:
            return fail(marker_issue or "生成结果为空")
        candidate_md = _normalize_job_ok_resume_structure(candidate_md)
        candidate_md = _remove_recruiter_company_references(candidate_md, job)

        artifacts = _find_resume_artifacts(candidate_md)
        quality_issues = _find_resume_quality_issues(
            candidate_md,
            resume_text,
            job,
            max_chars=resume_max_chars,
            max_pages=resume_max_pages,
        )
        blocking_issues = _find_blocking_integrity_issues(
            candidate_md,
            resume_text,
        )
        overlong = any(issue.startswith("简历内容过长") for issue in quality_issues)
        if attempt == 0 and (overlong or blocking_issues):
            retry_issues = [*blocking_issues, *quality_issues]
            issue_text = "; ".join(dict.fromkeys(retry_issues))
            console.print(f"[yellow]生成结果校验未通过，尝试修正一次：{issue_text}[/yellow]")
            prompt = RESUME_RETRY_PROMPT.format(
                base_prompt=base_prompt,
                quality_issues=issue_text,
                resume_max_pages=resume_max_pages,
                resume_max_chars=resume_max_chars,
                completion_marker=RESUME_COMPLETION_MARKER,
            )
            continue
        if blocking_issues:
            return fail("；".join(blocking_issues))

        delivery_warnings = list(quality_issues)
        if artifacts:
            delivery_warnings.append(f"包含定制过程性措辞：{', '.join(artifacts)}")
        if marker_issue:
            delivery_warnings.append(marker_issue)
        if delivery_warnings:
            console.print(
                f"[yellow]生成结果存在质量提示，仍保留并提供下载: {'; '.join(delivery_warnings)}[/yellow]"
            )
        tailored_md = candidate_md
        break

    if not tailored_md:
        return fail("生成结果未通过校验")
    if stop_requested(config):
        db.close()
        raise OperationCancelled("用户已请求停止")

    result = _save_resume_artifacts(
        db,
        job,
        config,
        resume_text,
        tailored_md,
        delivery_warnings,
        source=_resume_generation_source(config),
    )
    db.close()
    _resume_failure_reasons.pop(str(job_id), None)
    return result


def generate_all_resumes(config: dict) -> int:
    """Generate tailored resumes for all scored jobs. Returns count generated."""
    db = get_db()
    threshold = config.get("scoring", {}).get("threshold", 60)

    # Get scored jobs without resume
    rows = db.execute(
        "SELECT id FROM jobs WHERE deleted_at IS NULL AND status IN ('scored', 'ready', 'approved') AND score >= ? AND resume_path IS NULL",
        (threshold,)
    ).fetchall()

    if not rows:
        console.print("[yellow]没有需要生成简历的岗位[/yellow]")
        db.close()
        return 0

    db.close()
    count = 0
    for row in rows:
        result = generate_tailored_resume(row["id"], config)
        if result:
            count += 1

    console.print(f"\n[green]✓ 共生成 {count} 份定制简历[/green]")
    return count
