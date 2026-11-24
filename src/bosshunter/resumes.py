"""Resume library: several resumes, one best-fit choice per job.

BossHunter used to score every job against a single resume. Users who apply to
different tracks (AI application engineering, data annotation, product ops…)
need each job judged against the resume that fits it best, so the library keeps
every configured resume and the scorer picks the best match per job.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

PRIMARY_RESUME_ID = "primary"
MAX_RESUMES = 8
MAX_FOCUS_CHARS = 60
_SLUG_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


@dataclass(frozen=True)
class ResumeEntry:
    """One resume in the library."""

    id: str
    label: str
    path: str
    focus: str = ""
    primary: bool = False

    @property
    def exists(self) -> bool:
        return bool(self.path) and Path(self.path).is_file()

    def display_label(self) -> str:
        return f"{self.label}（{self.focus}）" if self.focus else self.label


def _clean_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit].strip()


def _path_key(path: str) -> str:
    try:
        return os.path.normcase(os.path.abspath(os.path.expanduser(str(path))))
    except (OSError, ValueError):
        return str(path)


def make_resume_id(value: str, fallback: str) -> str:
    """Build a stable, human-readable resume id from a label or filename."""
    slug = _SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-")
    slug = slug[:40]
    return slug or fallback


def resume_entries(config: dict[str, Any] | None) -> list[ResumeEntry]:
    """Return the configured resume library, primary first.

    ``profile.resumes`` is the library; ``profile.resume_path`` stays the
    primary resume so older configurations and the single-resume workflow keep
    working unchanged.
    """
    profile = config.get("profile") if isinstance(config, dict) else None
    profile = profile if isinstance(profile, dict) else {}

    entries: list[ResumeEntry] = []
    seen: set[str] = set()
    used_ids: set[str] = set()
    raw_entries = profile.get("resumes")
    for index, raw in enumerate(raw_entries if isinstance(raw_entries, list) else []):
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path") or "").strip()
        if not path:
            continue
        key = _path_key(path)
        if key in seen:
            continue
        seen.add(key)
        label = _clean_text(raw.get("label"), 40) or Path(path).stem
        resume_id = make_resume_id(str(raw.get("id") or label), f"resume-{index + 1}")
        if resume_id in used_ids:
            resume_id = f"{resume_id}-{index + 1}"
        used_ids.add(resume_id)
        entries.append(ResumeEntry(
            id=resume_id,
            label=label,
            path=str(Path(path).expanduser()),
            focus=_clean_text(raw.get("focus"), MAX_FOCUS_CHARS),
        ))

    primary_path = str(profile.get("resume_path") or "").strip()
    if primary_path:
        key = _path_key(primary_path)
        if key in seen:
            entries = [replace(entry, primary=True) if _path_key(entry.path) == key else entry
                       for entry in entries]
        else:
            entries.insert(0, ResumeEntry(
                id=PRIMARY_RESUME_ID,
                label=_clean_text(profile.get("resume_label"), 40) or Path(primary_path).stem,
                path=str(Path(primary_path).expanduser()),
                focus=_clean_text(profile.get("resume_focus"), MAX_FOCUS_CHARS),
                primary=True,
            ))

    if entries and not any(entry.primary for entry in entries):
        entries[0] = replace(entries[0], primary=True)
    return entries[:MAX_RESUMES]


def primary_entry(entries: list[ResumeEntry]) -> ResumeEntry | None:
    for entry in entries:
        if entry.primary:
            return entry
    return entries[0] if entries else None


def entry_by_id(entries: list[ResumeEntry], resume_id: str) -> ResumeEntry | None:
    wanted = str(resume_id or "").strip()
    if not wanted:
        return None
    for entry in entries:
        if entry.id == wanted:
            return entry
    return None


def read_resume_text(entry: ResumeEntry | None) -> str:
    if entry is None or not entry.path:
        return ""
    try:
        return Path(entry.path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def entry_for_job(config: dict[str, Any] | None, job: dict[str, Any] | None) -> ResumeEntry | None:
    """The resume that scored this job best, falling back to the primary one."""
    entries = resume_entries(config)
    if not entries:
        return None
    chosen = entry_by_id(entries, str((job or {}).get("best_resume_id") or ""))
    return chosen or primary_entry(entries)


def path_for_job(config: dict[str, Any] | None, job: dict[str, Any] | None) -> Path | None:
    entry = entry_for_job(config, job)
    return Path(entry.path) if entry else None


def text_for_job(config: dict[str, Any] | None, job: dict[str, Any] | None) -> str:
    return read_resume_text(entry_for_job(config, job))


def prompt_library(config: dict[str, Any] | None, *, max_chars: int | None = None) -> list[dict[str, str]]:
    """Resume texts prepared for the scoring prompt (empty entries dropped)."""
    library: list[dict[str, str]] = []
    for entry in resume_entries(config):
        text = read_resume_text(entry)
        if not text.strip():
            continue
        if max_chars is not None and len(text) > max_chars:
            text = text[:max_chars]
        library.append({
            "id": entry.id,
            "label": entry.display_label(),
            "focus": entry.focus,
            "text": text,
            "primary": "1" if entry.primary else "",
        })
    return library


def normalize_resume_record(*, label: Any, focus: Any, path: str, existing_ids: set[str]) -> dict[str, str]:
    """Build one ``profile.resumes`` record for the web upload API."""
    cleaned_label = _clean_text(label, 40) or Path(path).stem
    resume_id = make_resume_id(cleaned_label, "resume")
    suffix = 2
    base_id = resume_id
    while resume_id in existing_ids:
        resume_id = f"{base_id}-{suffix}"
        suffix += 1
    return {
        "id": resume_id,
        "label": cleaned_label,
        "path": str(Path(path).expanduser()),
        "focus": _clean_text(focus, MAX_FOCUS_CHARS),
    }
