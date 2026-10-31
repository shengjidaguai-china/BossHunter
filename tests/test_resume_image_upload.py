from unittest.mock import patch

import pytest

from bosshunter.executor import resume_images
from bosshunter.executor.resume_images import (
    attach_resume_images,
    pick_file_input,
    rank_file_input,
    resume_image_settings,
)


DISCOVER = resume_images.JS_DISCOVER_FILE_INPUTS
PENDING = resume_images.JS_COUNT_PENDING_IMAGES
COUNT = resume_images.JS_COUNT_MESSAGE_IMAGES
CONFIRM = resume_images.JS_CLICK_UPLOAD_CONFIRM


def _config(paths, enabled=True):
    return {"profile": {"resume_images": paths, "send_resume_images": enabled}}


def test_settings_disabled_by_default():
    settings = resume_image_settings(_config([], enabled=False))
    assert settings["enabled"] is False
    assert settings["paths"] == []
    assert settings["ready"] is False


def test_settings_reports_missing_and_unsupported_files(tmp_path):
    missing = str(tmp_path / "nope.png")
    wrong = tmp_path / "resume.pdf"
    wrong.write_text("not an image")
    settings = resume_image_settings(_config([missing, str(wrong)]))

    assert settings["enabled"] is True
    assert settings["ready"] is False
    reasons = {entry["path"]: entry["reason"] for entry in settings["entries"]}
    assert "文件不存在" in reasons[missing]
    assert "不支持的格式" in reasons[str(wrong)]


def test_settings_accepts_png_and_records_size(tmp_path):
    image = tmp_path / "resume.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    settings = resume_image_settings(_config([str(image)]))

    assert settings["ready"] is True
    assert settings["paths"] == [str(image)]
    assert settings["entries"][0]["size"] == len(image.read_bytes())


def test_rank_prefers_image_accept_over_visible_generic_input():
    image_picker = {"accept": "image/png,image/jpeg", "multiple": True, "rendered": False}
    visible_generic = {"accept": "*/*", "multiple": False, "rendered": True}
    assert rank_file_input(image_picker) > rank_file_input(visible_generic)
    assert pick_file_input([visible_generic, image_picker]) is image_picker


def test_pick_returns_none_without_inputs():
    assert pick_file_input([]) is None


class _FakePage:
    """Drives attach_resume_images with scripted responses per exact script.

    Dispatch has to be exact-string based: several of the page scripts share
    substrings (``blob:`` appears in both the pending and message-image probes),
    so a ``in``-based router silently mislabels them.
    """

    def __init__(self, inputs, pending=0, message_images=0, confirm=None):
        self.inputs = inputs
        self.pending = pending
        self.message_images = message_images
        self.confirm = confirm or {"ok": False, "error": "no_confirm_button"}
        self.calls = []

    def evaluate(self, target_id, expression, timeout=30):
        import json

        self.calls.append(expression)
        if expression == DISCOVER:
            return json.dumps({"ok": True, "url": "https://www.zhipin.com/web/geek/chat",
                               "count": len(self.inputs), "inputs": self.inputs})
        if expression == PENDING:
            return json.dumps({"ok": True, "pending": self.pending})
        if expression == COUNT:
            return json.dumps({"ok": True, "images": self.message_images})
        if expression == CONFIRM:
            return json.dumps(self.confirm)
        # marker / set-files acknowledge
        return True


def test_attach_skipped_when_not_enabled(tmp_path):
    image = tmp_path / "resume.png"
    image.write_bytes(b"0" * 16)
    page = _FakePage([])

    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate), patch(
        "bosshunter.executor.resume_images.set_files", return_value=True
    ):
        report = attach_resume_images("t", _config([str(image)], enabled=False))

    assert report["skipped"] is True
    assert report["success"] is False


def test_attach_reports_unusable_paths_without_touching_browser(tmp_path):
    page = _FakePage([])
    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate):
        report = attach_resume_images("t", _config(["/definitely/missing.png"]), job={"id": "1"})

    assert report["success"] is False
    assert "missing.png" in report["reason"]
    assert page.calls == []


def test_attach_without_file_input_is_reported_not_raised(tmp_path):
    image = tmp_path / "resume.png"
    image.write_bytes(b"0" * 16)
    page = _FakePage([])

    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate), patch(
        "bosshunter.executor.resume_images.set_files", return_value=True
    ):
        report = attach_resume_images("t", _config([str(image)]), job={"id": "1", "company": "示例"})

    assert report["reason"] == "no_file_input"
    assert report["success"] is False


def test_attach_success_increments_message_images(tmp_path, monkeypatch):
    images = []
    for name in ("a.png", "b.png"):
        path = tmp_path / name
        path.write_bytes(b"0" * 16)
        images.append(str(path))
    # 2 inputs: a visible generic one and a hidden image picker.
    inputs = [
        {"index": 0, "accept": "*/*", "multiple": False, "rendered": True, "ancestors": "form"},
        {"index": 1, "accept": "image/*", "multiple": True, "rendered": False, "ancestors": "div.chat-input"},
    ]
    page = _FakePage(inputs, pending=1, message_images=0)

    def stage_files(target_id, selector, files):
        # Uploading the batch is what makes the new bubbles appear.
        page.message_images += 2
        return True

    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate), patch(
        "bosshunter.executor.resume_images.set_files", side_effect=stage_files
    ) as set_files:
        report = attach_resume_images("t", _config(images), job={"id": "1", "company": "示例"})

    assert report["success"] is True
    assert report["images_before"] == 0
    assert report["images_after"] == 2
    assert len(report["files"]) == 2
    # The image picker was marked and both files pushed in a single call.
    selector = "input[data-bh-resume-input]"
    assert set_files.call_count == 1
    set_files.assert_called_once_with("t", selector, images)


def test_attach_skips_when_conversation_already_holds_the_resume_images(tmp_path):
    """Several postings can share one HR chat; images must not be re-uploaded.

    Verified live on 2026-10-14: five 多益网络 游戏客户端开发工程师 postings all
    opened 曾先生's conversation. The greeting was correctly deduplicated (one
    copy in the chat) but the resume images were uploaded on every pass, so the
    HR saw the same two pages four times. A chat that already carries the full
    set is treated as done.
    """
    images = []
    for name in ("a.png", "b.png"):
        path = tmp_path / name
        path.write_bytes(b"0" * 16)
        images.append(str(path))
    inputs = [{"index": 0, "accept": "image/*", "multiple": True, "rendered": False, "ancestors": "div.chat"}]
    # The conversation already holds both resume pages.
    page = _FakePage(inputs, pending=0, message_images=2)

    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate), patch(
        "bosshunter.executor.resume_images.set_files", return_value=True
    ) as set_files:
        report = attach_resume_images("t", _config(images), job={"id": "2", "company": "多益网络"})

    assert report["success"] is True
    assert report["skipped"] is True
    assert report["reason"] == "conversation_already_has_images"
    assert set_files.call_count == 0, "已有简历图片时不得再次上传"
    # It must bail out before even probing for the upload control.
    assert DISCOVER not in page.calls



def test_attach_reports_when_marking_the_input_fails(tmp_path):
    image = tmp_path / "only.png"
    image.write_bytes(b"0" * 16)
    inputs = [{"index": 0, "accept": "image/*", "multiple": True, "rendered": False, "ancestors": "div.chat"}]
    page = _FakePage(inputs, pending=1, message_images=0)

    def refuse_marker(target_id, expression, timeout=30):
        if "removeAttribute" in expression:
            return False
        return page.evaluate(target_id, expression, timeout)
    with patch("bosshunter.executor.resume_images.evaluate", side_effect=refuse_marker), patch(
        "bosshunter.executor.resume_images.set_files", return_value=True
    ) as set_files:
        report = attach_resume_images("t", _config([str(image)]))

    assert report["reason"] == "mark_file_input_failed"
    assert set_files.call_count == 0


def test_attach_reports_when_image_never_appears(tmp_path):
    image = tmp_path / "only.png"
    image.write_bytes(b"0" * 16)
    inputs = [{"index": 0, "accept": "image/*", "multiple": True, "rendered": False, "ancestors": "div.chat"}]
    page = _FakePage(inputs, pending=0, message_images=0)

    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate), patch(
        "bosshunter.executor.resume_images.set_files", return_value=True
    ), patch("bosshunter.executor.resume_images.time.sleep"):
        report = attach_resume_images("t", _config([str(image)]), max_wait_seconds=1.0)

    assert report["success"] is False
    assert report["reason"] == "image_not_confirmed_in_conversation"


def test_attach_stops_early_when_stop_event_is_set(tmp_path):
    image = tmp_path / "stop.png"
    image.write_bytes(b"0" * 16)
    inputs = [{"index": 0, "accept": "image/*", "multiple": True, "rendered": False, "ancestors": "div.chat"}]

    class StopEvent:
        def is_set(self):
            return True

    page = _FakePage(inputs)
    with patch("bosshunter.executor.resume_images.evaluate", page.evaluate), patch(
        "bosshunter.executor.resume_images.set_files", return_value=True
    ):
        report = attach_resume_images("t", _config([str(image)]), stop_event=StopEvent())

    assert report["success"] is False
    assert report["reason"] == "task_stopped"


def test_settings_tolerates_non_list_and_missing_section():
    assert resume_image_settings({})["paths"] == []
    assert resume_image_settings({"profile": {"resume_images": "nope"}})["paths"] == []
    assert resume_image_settings({"profile": {"resume_images": ["", "  "]}})["paths"] == []


def test_count_selector_matches_boss_real_chat_image_dom():
    """Regression: the verification probe must see BOSS's real image bubbles.

    Confirmed against a live conversation on 2026-10-13 after a real delivery:
    BOSS renders each uploaded chat picture as ``<img class="message-image"
    src="https://imgaz.bosszhipin.com/beijin/zp/chat/file/...">`` — the class
    sits on the ``<img>`` itself, so every descendant selector used previously
    ('.message-img img', '[class*="message"][class*="img"] img', ...) missed it
    and the probe reported 0 images for a pair that had genuinely been sent.
    """
    selectors = [
        line.strip().strip(",").strip("'\"")
        for line in resume_images.JS_COUNT_MESSAGE_IMAGES.splitlines()
        if line.strip().startswith("'")
    ]

    assert "img.message-image" in selectors, "必须包含 BOSS 真实聊天图片的选择器"
    assert selectors[0] == "img.message-image", "真实选择器应排在最前，优先命中"

    # 至少保留 blob 预览探测，用于上传过程中（落库前）的判断
    assert any("blob:" in selector for selector in selectors), "需保留上传预览阶段的探测"
