from unittest.mock import patch

import pytest

from bosshunter.ai import greeter
from bosshunter.db import get_db, insert_job

URL = "https://portfolio.example"
GREETING = "你好，我做过主图和详情页设计，作品集：" + URL
JOB = {"id": "new", "title": "电商设计", "company": "测试公司", "salary": "10K"}


@pytest.mark.parametrize(
	"profile",
	[
		{"greeting_preference": "高分且高度匹配岗位可附作品集：" + URL + "，普通岗位以文字邀请为主。"},
		{"extra_highlights": ["作品集：" + URL]},
		{"portfolio_url": URL},
	],
)
def test_user_provided_urls_pass_without_unnecessary_ai_retry(tmp_path, profile):
	config = {"profile": {"resume_path": str(tmp_path / "missing.md"), **profile}, "ai": {"greeting_max_attempts": 2}}
	with patch.object(greeter, "_call_claude", return_value=GREETING) as call:
		assert greeter._generate_with_token_retry(JOB, "真实经历，不含链接", config) == GREETING
	call.assert_called_once()


@pytest.mark.parametrize(
	"untrusted",
	[
		"https://invented.example/work",
		"https://portfolio.example.evil.example",
		"https://portfolio.example/invented-page",
	],
)
def test_pref_url_does_not_allow_model_invented_domains_or_paths(tmp_path, untrusted):
	config = {"profile": {"resume_path": str(tmp_path / "missing.md"), "greeting_preference": "作品集：" + URL}}
	assert greeter._has_untrusted_greeting_url("作品：" + untrusted, "真实经历", config)


def test_job_description_urls_are_not_candidate_facts(tmp_path):
	config = {"profile": {"resume_path": str(tmp_path / "missing.md")}}
	job = {**JOB, "jd": "参考网站：https://employer.example"}
	with patch.object(greeter, "_call_claude", return_value="我的作品：https://employer.example"):
		assert greeter._generate_greeting_once(job, "真实简历", config) is None


def test_batch_recovers_missing_greeting_without_overwriting_manual_text(tmp_path):
	path = tmp_path / "jobs.db"
	resume = tmp_path / "resume.md"
	resume.write_text("有主图与详情页设计经历", encoding="utf-8")
	db = get_db(path)
	for id in ("new", "manual"):
		insert_job(db, {**JOB, "id": id})
	db.execute("UPDATE jobs SET status='ready'")
	db.execute(
		"UPDATE jobs SET greeting='人工确认内容',greeting_selection='edited',greeting_reviewed_at=CURRENT_TIMESTAMP WHERE id='manual'"
	)
	db.commit()
	db.close()
	config = {
		"profile": {"resume_path": str(resume), "greeting_preference": "可附作品集：" + URL},
		"ai": {"greeting_style_suggestions": False},
	}
	with patch.object(greeter, "_call_claude", return_value=GREETING) as call:
		assert greeter.generate_greetings(config, job_ids=["new", "manual"], db_path=path) == 1
	call.assert_called_once()
	assert config["_workbench_greeting_report"]["failed_count"] == 0
	assert config["_workbench_greeting_report"]["skipped_existing"] == 1
	db = get_db(path)
	try:
		assert db.execute("SELECT greeting FROM jobs WHERE id='new'").fetchone()[0] == GREETING
		row = db.execute(
			"SELECT greeting,greeting_selection,greeting_reviewed_at FROM jobs WHERE id='manual'"
		).fetchone()
		assert row[0] == "人工确认内容" and row[1] == "edited" and row[2]
	finally:
		db.close()


@pytest.mark.parametrize("suffix", ["”", "（相关案例）", "、欢迎查看", "】", "`"])
def test_chinese_prose_and_markdown_delimiters_are_not_part_of_url(tmp_path, suffix):
	config = {"profile": {"resume_path": str(tmp_path / "missing.md"), "greeting_preference": "作品集：" + URL}}
	greeting = "作品集：" + URL + suffix
	assert greeter._extract_urls(greeting) == {"portfolio.example"}
	assert not greeter._has_untrusted_greeting_url(greeting, "真实简历", config)
	with patch.object(greeter, "_call_claude", return_value=greeting):
		result = greeter._generate_greeting_once(JOB, "真实简历", config)
		assert result and URL in result
		assert not greeter._has_untrusted_greeting_url(result, "真实简历", config)


def test_allowed_url_is_explicit_even_when_preference_would_be_truncated(tmp_path):
	config = {
		"profile": {
			"resume_path": str(tmp_path / "missing.md"),
			"greeting_preference": "保持真实经历。" * 100 + "作品集：" + URL,
		}
	}
	with patch.object(greeter, "_call_claude", return_value=GREETING) as call:
		assert greeter._generate_greeting_once(JOB, "真实简历", config) == GREETING
	prompt = call.call_args.args[0]
	assert "- portfolio.example" in prompt
	assert "不增加 www、子域名或路径" in prompt
