"""Resume library: several resumes per profile, best match per job."""

from pathlib import Path

from bosshunter.resumes import (
    PRIMARY_RESUME_ID,
    entry_for_job,
    entry_by_id,
    path_for_job,
    prompt_library,
    read_resume_text,
    resume_entries,
    text_for_job,
)


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def library_config(tmp_path: Path) -> dict:
    primary = write(tmp_path / "ai.md", "主简历：AI Agent 开发")
    ops = write(tmp_path / "ops.md", "运营简历：内容运营与社群")
    data = write(tmp_path / "data.md", "数据简历：数据分析与标注")
    return {
        "profile": {
            "resume_path": str(primary),
            "resumes": [
                {"id": "ops", "label": "内容运营", "focus": "内容/社群", "path": str(ops)},
                {"id": "data", "label": "数据分析", "path": str(data)},
            ],
        }
    }


def test_primary_resume_leads_the_library(tmp_path):
    entries = resume_entries(library_config(tmp_path))
    assert [entry.id for entry in entries] == [PRIMARY_RESUME_ID, "ops", "data"]
    assert entries[0].primary is True
    assert entries[1].display_label() == "内容运营（内容/社群）"
    assert all(entry.exists for entry in entries)


def test_single_resume_config_still_works(tmp_path):
    primary = write(tmp_path / "only.md", "只有一份")
    entries = resume_entries({"profile": {"resume_path": str(primary)}})
    assert len(entries) == 1
    assert entries[0].id == PRIMARY_RESUME_ID and entries[0].primary is True
    assert read_resume_text(entries[0]) == "只有一份"


def test_duplicate_paths_are_dropped(tmp_path):
    primary = write(tmp_path / "ai.md", "主简历")
    config = {"profile": {"resume_path": str(primary), "resumes": [{"id": "dup", "path": str(primary)}]}}
    entries = resume_entries(config)
    assert len(entries) == 1
    assert entries[0].primary is True


def test_best_resume_from_scoring_is_used_per_job(tmp_path):
    config = library_config(tmp_path)
    entries = resume_entries(config)
    job = {"best_resume_id": "ops"}
    assert entry_for_job(config, job).id == "ops"
    assert text_for_job(config, job).startswith("运营简历")
    assert path_for_job(config, job) == Path(entries[1].path)
    # Unknown or missing best_resume_id falls back to the primary resume.
    assert entry_for_job(config, {"best_resume_id": "nope"}).id == PRIMARY_RESUME_ID
    assert entry_for_job(config, {}).id == PRIMARY_RESUME_ID


def test_entry_by_id_and_prompt_library(tmp_path):
    config = library_config(tmp_path)
    entries = resume_entries(config)
    assert entry_by_id(entries, "data").label == "数据分析"
    assert entry_by_id(entries, "") is None
    library = prompt_library(config, max_chars=6)
    assert [item["id"] for item in library] == [PRIMARY_RESUME_ID, "ops", "data"]
    assert all(len(item["text"]) <= 6 for item in library)
    assert library[0]["primary"] == "1"


def test_missing_files_are_skipped_in_prompt_library(tmp_path):
    config = library_config(tmp_path)
    Path(config["profile"]["resumes"][0]["path"]).unlink()
    ids = [item["id"] for item in prompt_library(config)]
    assert ids == [PRIMARY_RESUME_ID, "data"]


def test_empty_config_has_no_library():
    assert resume_entries({}) == []
    assert resume_entries(None) == []
    assert entry_for_job({}, {"best_resume_id": "x"}) is None
