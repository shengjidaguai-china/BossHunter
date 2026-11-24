"""Scoring against several resumes: the best match drives the job score."""

import json
from unittest.mock import MagicMock, patch

import pytest

from bosshunter.ai import scorer

JOB = {
    "id": "job-1",
    "title": "AI Agent 开发实习生",
    "company": "测试公司",
    "salary": "200-300元/天",
    "city": "广州",
    "experience": "3天/周",
    "education": "本科",
    "recruitment_type": "campus",
    "jd": "负责 Agent 工作流开发，熟悉 Python。",
}

LIBRARY = [
    {"id": "primary", "label": "AI 应用开发", "focus": "Agent", "text": "主简历：Python + LangGraph Agent 项目", "primary": "1"},
    {"id": "ops", "label": "内容运营", "focus": "内容", "text": "运营简历：公众号与社群运营", "primary": ""},
]

SCORE_JSON = """{
  "role_summary": "Agent 开发",
  "core_duties": {"score": 34, "evidence": "LangGraph Agent 项目直接对应"},
  "transferable_evidence": {"score": 21, "evidence": "工程化落地经验"},
  "hard_requirements": {"score": 13, "evidence": "本科在读，Python 熟练"},
  "tools_industry": {"score": 8, "evidence": "用过 LangGraph"},
  "practical_fit": {"score": 9, "evidence": "广州，薪资匹配"},
  "caps": [], "hard_gaps": [], "reason": "高度匹配", "missing": "",
  "best_resume_id": "primary",
  "resume_fit": [
    {"resume_id": "primary", "score": 92, "reason": "Agent 项目直接匹配"},
    {"resume_id": "ops", "score": 28, "reason": "缺少开发证据"}
  ]
}"""


def test_single_resume_prompt_is_unchanged():
    prompt = scorer._build_scoring_prompt(JOB, "只有这一份简历", {})
    assert "只有这一份简历" in prompt
    assert "多份简历" not in prompt
    assert "best_resume_id" not in prompt


def test_multi_resume_prompt_lists_every_resume_and_asks_for_fit():
    prompt = scorer._build_scoring_prompt(JOB, LIBRARY, {})
    assert "共 2 份简历" in prompt
    assert "简历 id: primary" in prompt and "简历 id: ops" in prompt
    assert "请先判断哪一份与本岗位最匹配" in prompt
    assert "best_resume_id" in prompt and "resume_fit" in prompt


def test_score_payload_carries_best_resume_and_fit():
    result = scorer.validate_structured_score_payload(json.loads(SCORE_JSON))
    assert result is not None
    assert result.score == 85
    assert result.best_resume_id == "primary"
    assert [item["resume_id"] for item in result.resume_fit] == ["primary", "ops"]
    assert result.resume_fit[0]["score"] == 92


@pytest.mark.parametrize("fit,expected", [
    ([{"resume_id": "", "score": 80}], []),
    ([{"resume_id": "primary", "score": 101}], []),
    ([{"resume_id": "primary", "score": "x"}], []),
    ([{"resume_id": "primary", "score": True}], []),
    ("not-a-list", []),
])
def test_invalid_resume_fit_entries_are_dropped(fit, expected):
    assert list(scorer._normalize_resume_fit(fit)) == expected


def test_scoring_persists_best_resume_for_each_job():
    db = MagicMock()
    with (
        patch("bosshunter.ai.scorer.get_db", return_value=db),
        patch("bosshunter.ai.scorer._load_resume", return_value="主简历：Python + LangGraph Agent 项目"),
        patch("bosshunter.ai.scorer._load_resume_library", return_value=LIBRARY),
        patch("bosshunter.ai.scorer.get_jobs_by_status", return_value=[JOB]),
        patch("bosshunter.ai.scorer.quick_score", return_value=(80, "通过")),
        patch("bosshunter.ai.scorer._call_claude", return_value=SCORE_JSON),
        patch("bosshunter.ai.scorer.update_job_quick_score"),
        patch("bosshunter.ai.scorer.update_job_score"),
        patch("bosshunter.ai.scorer.update_job_status"),
        patch("bosshunter.ai.scorer.persist_job_score_and_trace"),
        patch("bosshunter.ai.scorer.update_job_resume_fit") as fit,
    ):
        scored, filtered = scorer.score_jobs({"ai": {"scoring_concurrency": 1}, "scoring": {"threshold": 70}})

    assert (scored, filtered) == (1, 0)
    fit.assert_called_once()
    _db, job_id, best_id, resume_fit = fit.call_args.args
    assert job_id == "job-1"
    assert best_id == "primary"
    assert [item["resume_id"] for item in resume_fit] == ["primary", "ops"]


def test_unknown_best_resume_falls_back_to_first_library_entry():
    db = MagicMock()
    payload = json.loads(SCORE_JSON)
    payload["best_resume_id"] = "deleted-resume"
    with (
        patch("bosshunter.ai.scorer.get_db", return_value=db),
        patch("bosshunter.ai.scorer._load_resume", return_value="主简历"),
        patch("bosshunter.ai.scorer._load_resume_library", return_value=LIBRARY),
        patch("bosshunter.ai.scorer.get_jobs_by_status", return_value=[JOB]),
        patch("bosshunter.ai.scorer.quick_score", return_value=(80, "通过")),
        patch("bosshunter.ai.scorer._call_claude", return_value=json.dumps(payload, ensure_ascii=False)),
        patch("bosshunter.ai.scorer.update_job_quick_score"),
        patch("bosshunter.ai.scorer.update_job_score"),
        patch("bosshunter.ai.scorer.update_job_status"),
        patch("bosshunter.ai.scorer.persist_job_score_and_trace"),
        patch("bosshunter.ai.scorer.update_job_resume_fit") as fit,
    ):
        scorer.score_jobs({"ai": {"scoring_concurrency": 1}, "scoring": {"threshold": 70}})

    assert fit.call_args.args[2] == "primary"


def test_single_resume_scoring_skips_fit_persistence():
    db = MagicMock()
    with (
        patch("bosshunter.ai.scorer.get_db", return_value=db),
        patch("bosshunter.ai.scorer._load_resume", return_value="主简历"),
        patch("bosshunter.ai.scorer._load_resume_library", return_value=LIBRARY[:1]),
        patch("bosshunter.ai.scorer.get_jobs_by_status", return_value=[JOB]),
        patch("bosshunter.ai.scorer.quick_score", return_value=(80, "通过")),
        patch("bosshunter.ai.scorer._call_claude", return_value=SCORE_JSON),
        patch("bosshunter.ai.scorer.update_job_quick_score"),
        patch("bosshunter.ai.scorer.update_job_score"),
        patch("bosshunter.ai.scorer.update_job_status"),
        patch("bosshunter.ai.scorer.persist_job_score_and_trace"),
        patch("bosshunter.ai.scorer.update_job_resume_fit") as fit,
    ):
        scorer.score_jobs({"ai": {"scoring_concurrency": 1}, "scoring": {"threshold": 70}})

    fit.assert_not_called()
