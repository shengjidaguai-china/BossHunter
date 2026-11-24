"""Filter analytics: why jobs were dropped, and what kind of roles they were.

Only reads persisted job rows; no AI calls. Category rules are ordered and
mutually exclusive so the percentages add up.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

# (category, keywords) — first match wins, so the most specific rules come first.
CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("算法 / AI 研究", ("算法", "机器学习", "深度学习", "大模型", "llm", "nlp", "cv", "推荐",
                        "强化学习", "人工智能", "量化", "ai模型")),
    ("内容制作 / 影视", ("视频", "剪辑", "短剧", "编剧", "漫剧", "动画", "音乐", "音频", "制作",
                         "拍摄", "影视", "达人", "营销", "策划", "aigc", "配音", "字幕", "生图", "图像")),
    ("数据", ("数据", "数仓", "etl", "bi", "爬虫", "采集", "标注", "分析")),
    ("测试 / 运维 / 安全", ("测试", "运维", "sre", "devops", "安全", "渗透")),
    ("研发 / 开发", ("研发", "开发", "后端", "前端", "全栈", "java", "python", "golang", "go开发",
                     "c++", "嵌入式", "架构", "engineer", "工程师", "agent", "自动化", "ai应用", "ai技术",
                     "infra", "ios", "android", "移动端")),
    ("交付 / 实施 / IT", ("fde", "实施", "交付", "部署", "it实习", "it 实习", "it支持", "技术支持", "驻场")),
    ("产品", ("产品", "pm", "product")),
    ("运营 / 内容", ("运营", "内容", "新媒体", "社群", "编辑", "文案", "直播", "短视频")),
    ("销售 / 市场 / 商务", ("销售", "市场", "商务", "bd", "客户", "渠道", "拓展", "招商")),
    ("设计", ("设计", "ui", "ux", "视觉", "平面", "交互")),
    ("职能 / 其他", ("人事", "hr", "行政", "财务", "法务", "会计", "助理", "招聘", "猎头")),
)

UNKNOWN_CATEGORY = "未分类"

REASON_PRE_FILTER = "预筛淘汰（规则）"
REASON_SCORE = "AI 评分未达标"
REASON_MANUAL = "手动/其他"
REASON_HISTORY = "历史数据（无理由）"


def classify_job_title(title: str | None) -> str:
    """Bucket a job title into a coarse role category."""
    text = str(title or "").lower()
    if not text.strip():
        return UNKNOWN_CATEGORY
    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return UNKNOWN_CATEGORY


def classify_filter_reason(job: dict[str, Any]) -> str:
    """Bucket the persisted reason a job was filtered out."""
    reason = str(job.get("filter_reason") or "").strip()
    score_reason = str(job.get("score_reason") or "")
    if reason:
        if reason.startswith("预筛") or reason.startswith("【否决词"):
            return REASON_PRE_FILTER
        if reason.startswith("AI 评分") or "低于阈值" in reason:
            return REASON_SCORE
        return REASON_MANUAL
    # 旧数据没有 filter_reason：按 score_reason 与分数回推。
    if score_reason.startswith("预筛不通过") or score_reason.startswith("【否决词"):
        return REASON_PRE_FILTER
    if "低于阈值" in score_reason:
        return REASON_SCORE
    try:
        score = int(job.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    if score > 0 and score_reason:
        return REASON_SCORE
    return REASON_HISTORY


def _score_band(score: Any) -> str:
    try:
        value = int(score)
    except (TypeError, ValueError):
        return "未评分"
    if value <= 0:
        return "0 分（预筛）"
    if value < 30:
        return "1-29 分"
    if value < 50:
        return "30-49 分"
    if value < 70:
        return "50-69 分"
    return "70 分以上"


def _job_payload(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(job.get("id") or ""),
        "title": job.get("title") or "",
        "company": job.get("company") or "",
        "city": job.get("city") or "",
        "salary": job.get("salary") or "",
        "score": int(job.get("score") or 0),
        "category": classify_job_title(job.get("title")),
        "filter_reason": (job.get("filter_reason") or "").strip(),
        "reason_category": classify_filter_reason(job),
        "url": job.get("url") or "",
        "created_at": job.get("created_at") or "",
    }


def build_filter_stats(jobs: Iterable[dict[str, Any]], *, sample_limit: int = 5) -> dict[str, Any]:
    """Aggregate filtered jobs by role type, reason, score band and company."""
    rows = [_job_payload(job) for job in jobs]
    total = len(rows)
    category_counter = Counter(row["category"] for row in rows)
    reason_counter = Counter(row["reason_category"] for row in rows)
    band_counter = Counter(_score_band(row["score"]) for row in rows)
    company_counter = Counter(row["company"] for row in rows if row["company"])

    categories: list[dict[str, Any]] = []
    for category, count in category_counter.most_common():
        sample_rows = sorted(
            (row for row in rows if row["category"] == category),
            key=lambda row: row["score"],
            reverse=True,
        )
        scores = [row["score"] for row in sample_rows]
        categories.append({
            "category": category,
            "count": count,
            "share": round(count / total * 100, 1) if total else 0.0,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "samples": sample_rows[:sample_limit],
        })

    reasons = [
        {"reason": reason, "count": count, "share": round(count / total * 100, 1) if total else 0.0}
        for reason, count in reason_counter.most_common()
    ]
    bands = [{"band": band, "count": count} for band, count in band_counter.most_common()]
    companies = [
        {"company": company, "count": count} for company, count in company_counter.most_common(10)
    ]
    return {
        "total": total,
        "categories": categories,
        "reasons": reasons,
        "score_bands": bands,
        "top_companies": companies,
    }
