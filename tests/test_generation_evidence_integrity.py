from unittest.mock import MagicMock, patch

from bosshunter.ai import greeter, resume
from bosshunter.ai.credentials import AIRequestError


def test_context_retry_keeps_middle_and_tail_evidence():
    source = "开头经历。" * 400 + "中部：医学直播案例。\n" + "其他经历。" * 400 + "尾部：社媒增长案例。"
    job = {"id": "one", "title": "内容运营", "company": "示例", "salary": "", "jd": "内容运营。" * 150}
    with patch.object(greeter, "_call_claude", side_effect=[
        AIRequestError("context_limit", "上下文过长"), "您好，我做过社媒内容运营。",
    ]) as call:
        assert greeter._generate_with_token_retry(job, source, {})
    assert call.call_count == 2
    assert all(source in item.args[0] for item in call.call_args_list)


def test_long_greeting_is_not_silently_cut_mid_fact():
    greeting = "真实经历。" * 35 + "成果周期为三个月。"
    assert greeter._normalize_greeting_response(greeting) == greeting


def test_excessive_output_is_kept_without_quality_retry():
    with patch.object(greeter, "_call_claude", side_effect=["经历。" * 110, "您好，我做过内容运营。"]) as call:
        result = greeter._generate_with_token_retry(
            {"title": "运营", "company": "示例", "salary": ""}, "真实经历。",
            {"ai": {"greeting_style_suggestions": False}},
        )
    assert result == "经历。" * 110
    assert call.call_count == 1
    assert "全文不得超过300字符" in call.call_args.args[0]


def test_style_length_hint_does_not_trigger_rewrite_when_disabled():
    greeting = "内容策划与复盘。" * 12
    db = MagicMock()
    job = {"id": "one", "title": "运营", "company": "示例", "salary": "", "status": "approved"}
    with (
        patch.object(greeter, "get_db", return_value=db),
        patch.object(greeter, "get_jobs_by_status", return_value=[job]),
        patch.object(greeter, "_get_resume_summary", return_value="真实简历"),
        patch.object(greeter, "_call_claude", return_value=greeting) as call,
        patch.object(greeter, "save_generated_greeting_preview", return_value=True) as save,
    ):
        assert greeter.generate_greetings({"ai": {"greeting_style_suggestions": False}}) == 1
    assert call.call_count == 1
    assert save.call_args.kwargs["selected_greeting"] == greeting
    assert any("40-90字" in issue for issue in save.call_args.kwargs["style_issues"])


def test_low_quality_long_draft_is_saved_without_rewrite_or_version_selection(tmp_path):
    from bosshunter.db import get_db, insert_job, update_job_status

    db_path = tmp_path / "jobs.db"
    db = get_db(db_path)
    insert_job(db, {"id": "advice-only", "title": "运营", "company": "示例", "salary": ""})
    update_job_status(db, "advice-only", "approved")
    db.close()
    greeting = "我做过内容策划。" * 40 + "方便聊聊吗？"
    config = {
        "profile": {"greeting_preference": "不提问"},
        "ai": {"greeting_style_suggestions": True, "greeting_max_iterations": 100, "greeting_auto_apply_style": True},
    }
    with (
        patch.object(greeter, "_get_resume_summary", return_value="真实简历"),
        patch.object(greeter, "_call_claude", side_effect=[greeting, '{"avg": 1, "critique": "建议精简"}']) as call,
    ):
        assert greeter.generate_greetings(config, db_path=db_path) == 1
    assert call.call_count == 2  # One generation and one advisory review, no rewrite.
    db = get_db(db_path)
    row = dict(db.execute("SELECT * FROM jobs WHERE id = 'advice-only'").fetchone())
    assert row["greeting"] == greeting
    assert not row["greeting_optimized"]
    assert row["greeting_selection"] == "generated"
    assert "300" in row["greeting_style_issues"]
    assert "不提问" in row["greeting_style_issues"]
    assert "建议精简" in row["greeting_style_issues"]
    assert not row["greeting_reviewed_at"]
    assert db.execute("SELECT count(*) FROM history WHERE action IN ('greeting_failed', 'sent')").fetchone()[0] == 0
    db.close()
    assert config["_workbench_greeting_report"]["failed_count"] == 0


BASE = """# 李晓｜内容运营
联系：13912345678｜li@example.com
作品：https://example.com/work
## 职业经历
### 甲科技有限公司｜运营
- 内容策划。
### 乙公司｜传播
- 直播执行。
## 教育背景
### 示例大学｜本科
2018.09-2022.06
"""


def test_contacts_outside_basic_info_section_cannot_disappear():
    candidate = BASE.replace("联系：13912345678｜li@example.com\n", "").replace("作品：https://example.com/work\n", "")
    missing = resume._find_missing_core_facts(candidate, BASE)
    assert set(missing) == {"13912345678", "li@example.com", "https://example.com/work"}


def test_name_cannot_disappear():
    issues = resume._find_blocking_integrity_issues(BASE.replace("李晓", "其他人"), BASE)
    assert any("姓名" in issue for issue in issues)


def test_section_aliases_and_reordering_preserve_background():
    candidate = BASE.replace("职业经历", "工作经验").replace("教育背景", "教育经历")
    assert resume._find_blocking_integrity_issues(candidate, BASE) == []


def test_combined_education_skills_section_and_inline_school_are_valid():
    candidate = BASE.replace("教育背景", "教育与技能").replace("### 示例大学｜本科\n2018.09-2022.06", "示例大学｜本科｜2018.09-2022.06")
    assert resume._find_blocking_integrity_issues(candidate, BASE) == []


def test_school_details_can_be_in_heading():
    candidate = BASE.replace("### 示例大学｜本科\n2018.09-2022.06", "### 示例大学｜本科｜2018.09-2022.06")
    assert resume._find_blocking_integrity_issues(candidate, BASE) == []


def test_project_link_is_not_mistaken_for_required_contact():
    source = BASE + "\n## 项目经历\n### 示例项目\n- 内容策划 https://example.com/project\n"
    candidate = source.replace(" https://example.com/project", "")
    assert resume._find_missing_core_facts(candidate, source) == []


def test_missing_employer_is_blocked_without_restricting_role_wording():
    candidate = BASE.replace("### 乙公司｜传播\n- 直播执行。\n", "")
    assert any("乙公司" in issue for issue in resume._find_blocking_integrity_issues(candidate, BASE))
    assert resume._find_blocking_integrity_issues(BASE.replace("直播执行", "主导直播执行"), BASE) == []


def test_education_content_and_dates_cannot_disappear():
    for candidate in (BASE.split("## 教育背景")[0], BASE.replace("2018.09-2022.06", ""), BASE.replace("本科", "")):
        assert any("教育" in issue for issue in resume._find_blocking_integrity_issues(candidate, BASE))


def test_empty_education_heading_is_not_complete():
    candidate = BASE.split("## 教育背景")[0] + "## 教育经历\n"
    assert any("缺少或清空教育经历" in issue for issue in resume._find_blocking_integrity_issues(candidate, BASE))
