"""AI Resume - Generate tailored resume for specific jobs."""

import json
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from html import unescape
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
MASTER_RESUME_POLICY = """母版定制规则：
- 基础简历是事实与项目全集母版；默认完整保留全部项目和教育背景
- 只允许按 JD 调整个人概述、项目顺序、关键词、表述和证据重点
- 项目不得删除、合并或虚构；若确需删减，必须先由候选人单独确认
- 经历按“任务/问题—个人行动—结果/验证边界”组织；来源缺少的内容不得补造
- 严格区分设计、实现、本地验证、真实环境验证、部署和业务结果
"""

RESUME_TAILOR_PROMPT = """你是一位专业简历顾问。请输出一份正常投递用的 Markdown 简历。

写作前先完成经历挖掘（仅用于组织正文，不输出分析过程）：
- 先逐条拆解目标岗位的职责、必备能力、经验限定、成果要求和加分项，再查找候选人证据；深挖方向由这个岗位决定，不预设所有岗位都突出管理、运营或付费。以让招聘方判断能否胜任、是否值得约面试为目标，不以堆叠岗位关键词代替证明。
- 通读完整母版，按每段经历提取本人身份、面对的问题、决策与行动、协作对象、管理机制、交付物和结果；不要只摘职位名称、工具或数字。
- 按 JD 的实际任务寻找证据，允许跨行业、创业、自媒体、社区和开源经历提供能力证明。例如组织维护团队、分配职责、协调审核与版本交付，能够证明团队组织和交付管理；不能仅因没有企业管理者职称，就判断没有管理经验。
- 区分“有能力证据”与“满足全部限定条件”：管理行动、团队规模、管理年限、雇佣关系、销售指标是不同维度。只缺某个维度时，应保留已经证实的管理能力，不能整体否定，也不能补造缺少的条件。
- 深挖成果背后的动作：内容定位与选题、用户研究、招募与分工、资源协调、质量审核、问题处理、付费产品实践和数据复盘；只能从母版已记载的行动展开，不从“创始人”等头衔推断未记载的职责。
- 为每项要求选择最强的真实经历，建立“要求—来源经历—本人行动—结果”的对应，区分直接证据、部分证据和无证据，再决定首屏和经历要点。争取每条要求都有真实支撑，岗位最关键的证据优先；不因缺少单项限定就忽略已有能力，也不为凑齐覆盖率编造条件。与岗位直接相关的成果不能被弱相关的技术工具或开源热度挤掉。
- 检查是否遗漏母版里已存在的相关证据。正文让招聘方通过具体经历看见能力，不使用“可迁移、匹配该岗位”等自我解释，不改变原工作的真实职位与行业。

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
13. 使用正常投递结构并完整保留基本信息、个人优势、工作经历、项目经历、教育经历、相关技能
14. 如果岗位涉及媒体、PR、公关、传播、科技记者，请优先突出已有的新媒体内容、品牌传播、媒体资源、专家访谈、公众号/视频号、技术型业务表达经验
15. 如果岗位涉及小红书、抖音、短视频、内容运营、AIGC内容、热点资讯、平台增长，请优先保留候选人已有的平台案例和量化结果，包括阅读/观看、点赞收藏、粉丝增长、用户群运营等真实证据
16. 必须输出完整简历，不得半句结束；最后一行单独输出 {completion_marker}，系统保存前会自动移除该行
17. 项目身份、本人角色、时间、成熟度、指标口径和事实边界必须可回溯到基础简历
18. 不得把团队成果改写为候选人的个人成果
19. 若完整保留项目后超过建议篇幅，应继续输出完整简历并交给人工审核，不得自行删项目
20. 第一行使用“# 姓名”，随后保留基础简历已有的联系方式；不要新增“求职方向”“目标公司”“应聘岗位”等投递标签，不把招聘公司的名称或职位包装为候选人的个人定位
21. 社招将个人概述放在联系方式之后，教育背景放在经历之后；校招可将教育背景前置。母版中独立的社媒案例、荣誉等栏目与成果也必须保留；将最相关的经历栏目紧接个人概述，例如内容运营岗位优先展示社媒案例，不应将其埋在弱相关技术项目之后
22. 公司与职位使用三级标题；项目与工作要点使用紧凑项目符号
23. 在内部选出岗位最重要的三项要求，逐项找到母版中的具体行动和结果，再撰写概述；概述用最多三条简短要点呈现最强的相关证据，不写泛泛的自我评价或“可带领团队实现业绩”等无事实支撑的承诺
24. 必须区分内容曝光、粉丝增长、线索、成交和收入；不得将播放量改成获客或销售业绩，不得将社区协作改成正式团队管理年限，不得将路演改成融资或资本市场经验，不得将其他行业经验改成目标行业实操
25. 每个数字必须保留其所属公司、项目、平台、个人参与范围，以及来源明确的达成周期或测量窗口；不可跨经历拼接因果。增长、付费、交付等成果应写清“多久做到多少”，不能遗漏已有时间信息；来源未提供周期时不得推算或编造，不得把某项成果的周期移用到另一指标，也不得把期间累计改成每月常态。优先呈现与岗位相关的真实成果，其他成就仍保留在所属经历中，不因相关性弱而删除
26. 用具体的动作和结果表达竞争优势，不堆砌“赋能、闭环、抓手、深度洞察”等空话；同一经历不要在概述与正文反复展开。不输出“数据统计截至某日”或“数据更新”说明，但必须保留证明增长速度、执行效率的成果达成周期，以及保证指标含义准确的测量窗口

## 固定母版策略
{master_policy}

## 投递岗位
- 职位：{title}
- 公司：{company}
- 薪资：{salary}
- 学历要求：{education}
- 招聘类型：{recruitment_type}
- 核心要求：
{jd}

## 候选人简历
{resume}

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
6. 修复上述具体问题，按岗位核心要求重排真实证据；不能只改标题或增加关键词，也不能靠编造能力来提高匹配度

请直接输出修正后的完整 Markdown 简历正文：
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

REQUIRED_RESUME_SECTIONS = [
    "## 基本信息",
    "## 个人优势",
    "## 工作经历",
    "## 教育经历",
    "## 相关技能",
]

BACKGROUND_SECTION_ALIASES = {
    "工作经历": ("工作经历", "工作经验", "职业经历", "职业经验", "任职经历", "实习经历", "实习经验"),
    "教育经历": ("教育", "学历", "学习经历"),
}

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
    "代招", "代为招聘", "受客户委托", "为客户招聘", "rpo",
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


def _remove_generated_target_header(markdown_text: str) -> str:
    """Drop generated application labels, preserving all experience sections."""
    lines = []
    in_header = True
    for line in markdown_text.splitlines():
        if re.match(r"^\s*#{2,6}\s+", line):
            in_header = False
        label = re.sub(r"[*_`]", "", line).strip()
        if in_header and re.match(r"^(?:[-+]\s+)?(?:求职方向|目标公司|意向公司|应聘岗位)\s*[：:]", label):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


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
    headings = re.findall(
        r"(?m)^##\s+(?:项目经历|项目经验|代表项目|代表性[^\n]*?(?:项目|案例))\s*$",
        markdown_text,
    )
    for heading in headings:
        section = _markdown_section(markdown_text, heading.strip())
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
    """Keep contacts regardless of their location or section title."""
    source_basic_info = _markdown_section(base_resume, "## 基本信息")
    source_tokens = _extract_validation_tokens(source_basic_info, FACT_TOKEN_PATTERNS)
    # Contacts may be directly below the name. Project links elsewhere are not contacts.
    header = re.split(r"(?m)^\s*##\s+", base_resume, maxsplit=1)[0]
    source_tokens.extend(_extract_validation_tokens(header, FACT_TOKEN_PATTERNS[:3]))
    source_tokens.extend(_extract_validation_tokens(base_resume, [FACT_TOKEN_PATTERNS[0], FACT_TOKEN_PATTERNS[2]]))
    generated_keys = {
        _normalize_validation_token(token)
        for token in _extract_validation_tokens(markdown_text, FACT_TOKEN_PATTERNS)
    }
    return [
        token
        for token in dict.fromkeys(source_tokens)
        if _normalize_validation_token(token) not in generated_keys
    ]


def _resume_sections(markdown_text: str) -> list[tuple[str, str]]:
    """Read semantic sections without requiring one exact Markdown label."""
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(r"(?ms)^\s*##[ \t]+([^\n]+)\n(.*?)(?=^\s*##[ \t]+|\Z)", markdown_text)
    ]


def _find_background_preservation_issues(markdown_text: str, base_resume: str) -> list[str]:
    """Protect identity, education and named employers without policing role wording."""
    issues: list[str] = []
    # Uploads may start with a document title rather than the person's name.
    explicit_name = re.search(r"(?m)^[ \t#>*_-]*姓名[ \t*_]*[:：][ \t*_]*([^\n|｜,，;；]+)", base_resume)
    name = ""
    if explicit_name:
        name = re.split(r"\s{2,}|[ \t]+(?:年龄|电话|手机|邮箱|性别|籍贯)\s*[:：]", explicit_name.group(1))[0].strip().strip("*_ ")
    else:
        heading = re.search(r"(?m)^#[ \t]+([^\n]+)", base_resume)
        if heading:
            title = re.split(r"[|｜：:]|\s+[-–—]\s+", heading.group(1), maxsplit=1)[0].strip().strip("*_ ")
            if not any(label in title for label in ("简历", "履历", "信息", "姓名")):
                # Ambiguous titles are not reliable evidence of a missing identity.
                if re.fullmatch(r"[\u4e00-\u9fff·]{2,6}|[A-Za-z]+(?:[ .'-]+[A-Za-z]+)*", title):
                    name = title
    if name and name not in markdown_text:
        issues.append("基础信息保留校验失败：缺少原简历姓名")

    for label, aliases in BACKGROUND_SECTION_ALIASES.items():
        source_sections = [(title, body) for title, body in _resume_sections(base_resume) if any(a in title for a in aliases)]
        source = "\n".join(body for _, body in source_sections)
        if not source.strip():
            continue
        candidate = "\n".join(body for title, body in _resume_sections(markdown_text) if any(a in title for a in aliases))
        # An empty heading is not preservation of the underlying background.
        content = candidate if label == "教育经历" else re.sub(r"(?m)^\s*#{1,6}\s+.*$", "", candidate)
        if not content.strip():
            issues.append(f"经历保留校验失败：缺少或清空{label}内容")
            continue
        source_entries = re.findall(r"(?m)^\s*###\s+(.+?)\s*$", source)
        candidate_entries = re.findall(r"(?m)^\s*###\s+(.+?)\s*$", candidate)
        for entry in source_entries:
            identity = re.split(r"[|｜]", entry, maxsplit=1)[0].strip().strip("*_ ")
            # Allow heading changes and a move to plain text, but keep the actual employer/school.
            if identity not in candidate and not any(_project_identity_matches(entry, other) for other in candidate_entries):
                issues.append(f"经历保留校验失败：{label}缺少 {identity}")
        if label == "教育经历":
            schools = [
                re.sub(r"^(?:毕业于|就读于|在读于|毕业院校|就读院校|所在院校)", "", school)
                for school in re.findall(r"[\u4e00-\u9fffA-Za-z]+(?:大学|学院|学校)", source)
            ]
            degrees = re.findall(r"博士|硕士|本科|学士|大专|专科", source)
            dates = _extract_validation_tokens(source, [FACT_TOKEN_PATTERNS[3]])
            candidate_dates = {_normalize_validation_token(t) for t in _extract_validation_tokens(candidate, [FACT_TOKEN_PATTERNS[3]])}
            for fact in dict.fromkeys([*schools, *degrees]):
                if fact not in candidate:
                    issues.append(f"教育信息保留校验失败：缺少 {fact}")
            for fact in dict.fromkeys(dates):
                if _normalize_validation_token(fact) not in candidate_dates:
                    issues.append(f"教育信息保留校验失败：缺少时间 {fact}")
    return issues


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
    issues.extend(_find_project_preservation_issues(markdown_text, base_resume))
    issues.extend(_find_background_preservation_issues(markdown_text, base_resume))
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

    for section in _required_sections_from_base(base_resume):
        aliases = BACKGROUND_SECTION_ALIASES.get(section.removeprefix("## "), ())
        if aliases and any(any(alias in title for alias in aliases) for title, _ in _resume_sections(markdown_text)):
            continue
        if section not in markdown_text:
            issues.append(f"缺少基础简历中的常规栏目：{section.replace('## ', '')}")

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


def _required_sections_from_base(base_resume: str) -> list[str]:
    return [section for section in REQUIRED_RESUME_SECTIONS if section in base_resume]


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


def _resume_display_markdown(markdown_text: str) -> str:
    """Unify equivalent labels without moving, merging or dropping sections.

    Adapted from #227's heading normalization; keep the candidate's section
    order and custom case-study headings instead of imposing education first.
    """
    aliases = {
        "个人优势": "个人概述", "职业概述": "个人概述",
        "任职经历": "工作经历", "工作经验": "工作经历",
        "教育经历": "教育背景", "相关技能": "专业技能",
    }
    return re.sub(
        r"(?m)^##[ \t]+([^\n]+?)[ \t]*$",
        lambda match: "## " + aliases.get(match[1], match[1]),
        markdown_text,
    )


def _resume_html(markdown_text: str, *, image_mode: bool = False) -> str:
    """Build a readable, single-column resume shared by PDF and PNG."""
    import markdown2

    markdown_text = _resume_display_markdown(markdown_text)
    # markdown2 treats a CJK colon at the closing emphasis boundary as literal
    # Markdown. Keep the visible text, placing punctuation outside the emphasis.
    markdown_text = re.sub(r"\*\*([^*\n]+?)([：:])\*\*", r"**\1**\2", markdown_text)
    html_body = markdown2.markdown(markdown_text, extras=["tables", "fenced-code-blocks"])
    # Separate contact lines that Markdown otherwise folds into one paragraph.
    def masthead(match):
        contacts = re.sub(r"(?<!>)\n(?=\S)", "<br>\n", match[2].strip())
        return f'<header class="resume-header">{match[1]}{contacts}</header>\n'

    html_body = re.sub(r"\A(<h1>.*?</h1>)\s*(.*?)(?=<h[2-6]\b|\Z)", masthead, html_body, flags=re.S)

    def entry_heading(match):
        title, metadata = match[1], match[2]
        plain = unescape(re.sub(r"<[^>]+>", "", metadata)).strip()
        date_part = re.split(r"[|｜]", plain, maxsplit=1)[0].strip()
        # Only style short, explicit year/date metadata. Narrative paragraphs
        # stay untouched, even when they immediately follow an entry heading.
        if len(plain) > 140 or not re.fullmatch(r"(?:19|20)\d{2}[\d年月日、,./\s\-–—~至今现]*", date_part):
            return match[0]
        return f'<div class="resume-entry">{title}<p class="resume-meta">{metadata}</p></div>\n'

    html_body = re.sub(r"(<h3>.*?</h3>)\s*<p>(.*?)</p>", entry_heading, html_body, flags=re.S)
    page_rule = "@page { size: A4; margin: 0; }" if image_mode else """@page {
        size: A4; margin: 12mm 14mm 14mm;
        @bottom-right {
            content: counter(page) " / " counter(pages);
            font: 8pt sans-serif; color: #667085;
        }
    }"""
    sheet_style = """
    html, body { margin: 0; padding: 0; background: #fff; }
    [data-resume-sheet] { width: 210mm; min-height: 297mm; padding: 12mm 14mm; background: #fff; }
    """ if image_mode else "body { width: 182mm; }"
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
        font-size: 10.25pt; line-height: 1.45; margin: 0; color: #293340;
    }}
    .resume-header {{ border-bottom: 1.5pt solid #264d64; padding-bottom: 3mm; margin-bottom: 4mm; }}
    .resume-header p {{ color: #536170; font-size: 9pt; line-height: 1.6; margin: 0; }}
    h1 {{ font-size: 25pt; font-weight: 700; letter-spacing: .6pt; line-height: 1.15; color: #182d3b; margin: 0 0 2.5mm; }}
    h2 {{ font-size: 12pt; letter-spacing: .5pt; color: #264d64; margin: 4.5mm 0 2.2mm; padding-left: 2.5mm; border-left: 2.5pt solid #264d64; line-height: 1.15; break-after: avoid; }}
    h3 {{ font-size: 10.5pt; color: #182d3b; margin: 2.5mm 0 1mm; line-height: 1.4; break-after: avoid; }}
    .resume-entry {{ display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; column-gap: 4mm; margin: 2.5mm 0 1.2mm; break-inside: avoid; break-after: avoid; }}
    .resume-entry h3 {{ margin: 0 0 .7mm; }}
    .resume-meta {{ font-size: 9pt; color: #607080; margin: 0; }}
    .resume-meta strong {{ font-weight: 400; }}
    p {{ margin: 0 0 1.5mm; orphans: 2; widows: 2; }}
    ul, ol {{ padding-left: 4.5mm; margin: 1mm 0 2mm; }}
    li {{ padding-left: .5mm; margin: 0 0 .9mm; orphans: 2; widows: 2; }}
    li::marker {{ color: #738592; font-size: .8em; }}
    strong {{ font-weight: 700; color: #243b4b; }}
    h3, li, table, blockquote {{ break-inside: avoid; }}
    .resume-continuation {{ font-size: 8.5pt; color: #607080; border-bottom: .5pt solid #d8e0e5; padding: 0 0 2mm; margin: 0 0 3mm; list-style: none; break-after: avoid; }}
    li.resume-continuation {{ margin-left: -4.5mm; }}
    a {{ color: #264d64; text-decoration: none; overflow-wrap: anywhere; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1.2mm 0; font-size: 10pt; }}
    th, td {{ border: .5pt solid #b8c7d9; padding: 1mm 1.5mm; text-align: left; }}
    th {{ background: #edf3f8; color: #1f4e79; }}
</style>
</head>
<body>
{rendered_body}
</body>
</html>"""


def _balanced_page_starts(boundaries: list[dict], page_height: float) -> list[int]:
    """Balance measured content at safe boundaries, without shrinking the text.

    The final boundary is the bottom of the document. Prefer section starts;
    allow long lists to continue between complete bullets. Oversized indivisible
    blocks fall back to Chrome's native pagination.
    """
    if len(boundaries) < 3 or page_height <= 0:
        return []
    positions = [float(item["y"]) for item in boundaries]
    total = positions[-1] - positions[0]
    if total <= page_height:
        return []
    if any(b - a > page_height for a, b in zip(positions, positions[1:])):
        return []
    end = len(positions) - 1
    for pages in range(math.ceil(total / page_height), end + 1):
        target = total / pages
        states = {0: (0.0, [])}
        for _ in range(pages):
            next_states = {}
            for start, (cost, cuts) in states.items():
                for stop in range(start + 1, end + 1):
                    height = positions[stop] - positions[start]
                    if height > page_height:
                        break
                    penalty = 0 if stop == end or boundaries[stop].get("section") else page_height ** 2 * 0.003
                    score = cost + (height - target) ** 2 + penalty
                    if stop not in next_states or score < next_states[stop][0]:
                        next_states[stop] = (score, cuts + [stop])
            states = next_states
        if end in states:
            return states[end][1][:-1]
    return []


def _balance_pdf_pages(target_id: str) -> None:
    """Measure the actual loaded font and keep headings with their first item."""
    layout = evaluate(target_id, """(async () => {
        await document.fonts.ready;
        const children = [...document.body.children];
        const boundaries = [{y: 0, section: true}];
        for (const list of document.querySelectorAll('ol')) {
            let ordinal = list.hasAttribute('start') ? list.start : (list.reversed ? list.children.length : 1);
            for (const item of list.children) {
                if (item.hasAttribute('value')) ordinal = item.value;
                item.dataset.resumeOrdinal = String(ordinal);
                ordinal += list.reversed ? -1 : 1;
            }
        }
        let sectionTitle = '';
        let entryTitle = '';
        const add = (element, section) => {
            element.dataset.resumeBreak = String(boundaries.length);
            element.dataset.resumeContinuation = sectionTitle +
                (!section && entryTitle ? ' · ' + entryTitle : '');
            boundaries.push({y: element.getBoundingClientRect().top, section});
        };
        for (let i = 1; i < children.length; i++) {
            const element = children[i];
            const previous = children[i - 1];
            if (element.tagName === 'H2') { sectionTitle = element.textContent; entryTitle = ''; }
            const entry = element.matches('.resume-entry') ? element.querySelector('h3') :
                (element.tagName === 'H3' ? element : null);
            if (entry) entryTitle = entry.textContent;
            const afterHeading = /^H[1-6]$/.test(previous.tagName) || previous.matches('.resume-entry');
            if ((/^H[23]$/.test(element.tagName) || entry) && !afterHeading) add(element, true);
            else if (element.tagName === 'UL' || element.tagName === 'OL') {
                [...element.children].slice(1).forEach(item => add(item, false));
            } else if (!afterHeading && /^(P|TABLE|BLOCKQUOTE)$/.test(element.tagName)) {
                add(element, false);
            }
        }
        boundaries.push({y: document.body.getBoundingClientRect().bottom, section: true});
        return boundaries;
    })()""")
    if not isinstance(layout, list):
        return
    # Reserve room for the continuation label, footer and print rounding.
    starts = _balanced_page_starts(layout, (297 - 26 - 10) * 96 / 25.4)
    if starts:
        evaluate(target_id, """(() => {
            const starts = %s;
            for (const index of starts) {
                const element = document.querySelector(`[data-resume-break="${index}"]`);
                if (element.tagName === 'H2' || !element.dataset.resumeContinuation) {
                    element.style.breakBefore = 'page';
                    continue;
                }
                const label = document.createElement(element.tagName === 'LI' ? 'li' : 'div');
                label.className = 'resume-continuation';
                label.textContent = element.dataset.resumeContinuation + '（续）';
                label.style.breakBefore = 'page';
                if (element.dataset.resumeOrdinal) {
                    // Do not shift numbers in a continued ordered list.
                    element.value = Number(element.dataset.resumeOrdinal);
                    label.value = element.value - (element.parentElement.reversed ? -1 : 1);
                }
                element.before(label);
            }
            return true;
        })()""" % json.dumps(starts))


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
                    _balance_pdf_pages(target_id)
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
    tailored_md: str,
    *,
    source: str,
) -> Path:
    """Persist editable Markdown and deterministic PDF/PNG derivatives."""
    output_dir = Path(config.get("profile", {}).get("resume_output_dir", "./data/resumes"))
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = _safe_resume_basename(job)

    md_path = output_dir / f"{base_name}.md"
    md_path.write_text(tailored_md, encoding="utf-8")

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
    candidate = str(markdown_text or "").strip()
    if not candidate:
        raise ValueError("图片简历内容不能为空")
    candidate += "\n"

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
        return _save_resume_artifacts(db, job, config, candidate, source=source)
    finally:
        db.close()


def _build_resume_prompt(job: dict, resume_text: str, resume_max_pages: int) -> str:
    """Pass the full job description and factual master to the model."""
    recruiter_job = _is_recruiter_job(job)
    prompt_company = "猎头/代招岗位（客户公司未提供）" if recruiter_job else job["company"]
    return RESUME_TAILOR_PROMPT.format(
        title=job["title"],
        company=prompt_company,
        salary=job["salary"] or "面议",
        education=job.get("education", "") or "未识别",
        recruitment_type={"campus": "校招", "experienced": "社招"}.get(
            job.get("recruitment_type", ""), "未识别"
        ),
        jd=job.get("jd") or "无详细描述",
        resume=resume_text,
        resume_max_pages=resume_max_pages,
        completion_marker=RESUME_COMPLETION_MARKER,
        master_policy=MASTER_RESUME_POLICY,
    )


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

    base_prompt = _build_resume_prompt(job, resume_text, resume_max_pages)

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
        candidate_md = _remove_generated_target_header(candidate_md)
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
        if _is_nearly_unchanged(candidate_md, resume_text):
            blocking_issues.append("生成结果与原始简历几乎一致，定制化不足；请检查母版或重新生成")
        if attempt == 0 and (quality_issues or blocking_issues or artifacts):
            retry_issues = [*blocking_issues, *quality_issues]
            if artifacts:
                retry_issues.append(f"包含定制过程性措辞：{', '.join(artifacts)}")
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
        tailored_md,
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
