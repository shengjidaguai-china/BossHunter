"""Best-effort resume-image attachment after a greeting is delivered.

This module is deliberately isolated from the greeting delivery semantics.
BossHunter only marks a job ``sent`` once the greeting text is *verified* in the
conversation — that guarantee is what prevents duplicate greetings. Resume
images are an additive extra, so every failure path here is reported and
swallowed: an image that will not upload must never convert an already
delivered greeting into a failed send.

The BOSS chat upload control is a hidden ``<input type="file">`` behind a
toolbar button. We do not hard-code a single selector, because BOSS renames
those classes without notice. Instead we enumerate every file input on the
conversation page, rank them by how likely they are the image picker, tag the
winner with a data attribute, and push the files into that node through CDP
``DOM.setFileInputFiles``. Everything we discover is logged, so the selector can
be pinned after the first live run (see ``bosshunter resume-images --probe``).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from bosshunter.browser import evaluate, set_files


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# Marked onto the chosen file input so CDP can target it without a brittle path.
_INPUT_TAG = "data-bh-resume-input"

# Collected before upload so we can report what the page actually offered.
JS_DISCOVER_FILE_INPUTS = """
(() => {
    const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify({
        ok: true,
        url: location.href,
        count: inputs.length,
        inputs: inputs.map((input, index) => {
            const rect = input.getBoundingClientRect();
            const chain = [];
            let node = input;
            for (let depth = 0; depth < 3 && node && node.parentElement; depth += 1) {
                node = node.parentElement;
                const cls = typeof node.className === 'string' && node.className.trim()
                    ? '.' + node.className.trim().split(/\\s+/).join('.')
                    : '';
                chain.unshift(node.tagName.toLowerCase() + cls);
            }
            return {
                index,
                accept: (input.getAttribute('accept') || '').slice(0, 80),
                multiple: !!input.multiple,
                rendered: rect.width > 0 && rect.height > 0,
                ancestors: chain.slice(-2).join(' > '),
            };
        }),
    });
})()
"""

JS_COUNT_PENDING_IMAGES = """
(() => {
    return JSON.stringify({
        ok: true,
        pending: document.querySelectorAll('img[src^="blob:"]').length,
    });
})()
"""

# A locally picked image only shows up as a blob: URL until it finishes
# uploading, so a non-zero count proves the file input accepted our files.
JS_COUNT_MESSAGE_IMAGES = """
(() => {
    // 'img.message-image' is BOSS's real chat-image class: the element itself
    // carries it, so a descendant selector like '.message-img img' never matches.
    const selectors = [
        'img.message-image',
        '.message-img img', '.msg-img img', '.img-msg img',
        '[class*="message"][class*="img"] img',
        '.chat-item img', '.item-img img', 'img[src^="blob:"]'
    ];
    const urls = new Set();
    selectors.forEach((selector) => {
        document.querySelectorAll(selector).forEach((img) => {
            const src = img.getAttribute('src') || '';
            if (src) urls.add(src);
        });
    });
    return JSON.stringify({ ok: true, images: urls.size, urls: Array.from(urls).slice(0, 12) });
})()
"""

# BOSS sometimes opens a preview pane instead of sending the file immediately.
JS_CLICK_UPLOAD_CONFIRM = """
(() => {
    const wanted = ['发送', '确定', '确认', '发送图片'];
    const buttons = Array.from(
        document.querySelectorAll('button, a, span, div[role="button"]')
    );
    for (const button of buttons) {
        const text = (button.innerText || '').trim();
        if (!wanted.includes(text)) continue;
        const rect = button.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            button.click();
            return JSON.stringify({ ok: true, clicked: text });
        }
    }
    return JSON.stringify({ ok: false, error: 'no_confirm_button' });
})()
"""


def _parse_js_result(result: Any) -> dict:
    """Best-effort JSON decode of a CDP ``evaluate`` response."""
    if not result:
        return {"success": False, "error": "no_response"}
    if isinstance(result, dict):
        return result
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "error": "parse_error"}


def _log(logger: Callable[[str], None] | None, message: str) -> None:
    if callable(logger):
        try:
            logger(message)
        except Exception:
            pass


def _stopping(stop_event: Any) -> bool:
    return bool(stop_event and stop_event.is_set())


def resume_image_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Resolve and validate the configured resume images without touching disk.

    Returns a report dict and never raises: callers decide whether a warning
    should block sending.
    """
    profile = config.get("profile") if isinstance(config.get("profile"), dict) else {}
    raw_paths = profile.get("resume_images", [])
    raw_paths = raw_paths if isinstance(raw_paths, list) else []

    entries: list[dict[str, Any]] = []
    for raw in raw_paths:
        text = str(raw).strip()
        entry: dict[str, Any] = {"path": text, "exists": False, "size": None, "reason": ""}
        if not text:
            entry["reason"] = "路径为空"
            entries.append(entry)
            continue
        try:
            candidate = Path(text).expanduser()
            candidate = candidate.resolve() if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
            if not candidate.exists():
                entry["reason"] = "文件不存在"
            elif candidate.suffix.lower() not in IMAGE_EXTENSIONS:
                entry["reason"] = f"不支持的格式（仅支持 {', '.join(sorted(IMAGE_EXTENSIONS))}）"
            elif candidate.stat().st_size <= 0:
                entry["reason"] = "文件为空"
            else:
                entry["exists"] = True
                entry["size"] = candidate.stat().st_size
                entry["path"] = str(candidate)
        except OSError as exc:
            entry["reason"] = f"无法读取文件: {exc}"
        entries.append(entry)

    return {
        "enabled": bool(profile.get("send_resume_images", False)),
        "entries": entries,
        "paths": [entry["path"] for entry in entries if entry["exists"]],
        "ready": any(entry["exists"] for entry in entries),
    }


def rank_file_input(input_meta: dict[str, Any]) -> int:
    """Score a discovered file input; a higher score means a likelier image picker."""
    accept = str(input_meta.get("accept") or "").lower()
    score = 0
    if "image" in accept:
        score += 100
    elif not accept or accept in {"*/*", "*"}:
        score += 5
    if input_meta.get("multiple"):
        score += 3
    # A visible input is normally the styled upload label, not the real picker.
    if input_meta.get("rendered"):
        score -= 10
    ancestors = str(input_meta.get("ancestors") or "").lower()
    if any(word in ancestors for word in ("chat", "dialog", "send", "input")):
        score += 2
    return score


def pick_file_input(inputs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the file input most likely to be the chat image picker."""
    if not inputs:
        return None
    return sorted(inputs, key=rank_file_input, reverse=True)[0]


def probe_file_inputs(target_id: str) -> dict[str, Any]:
    """Report every file input found on ``target_id`` (used by ``--probe``)."""
    parsed = _parse_js_result(evaluate(target_id, JS_DISCOVER_FILE_INPUTS))
    inputs = parsed.get("inputs") if isinstance(parsed.get("inputs"), list) else []
    for meta in inputs:
        meta["score"] = rank_file_input(meta)
    parsed["inputs"] = inputs
    return parsed


def attach_resume_images(
    target_id: str,
    config: dict[str, Any],
    *,
    job: dict[str, Any] | None = None,
    stop_event: Any = None,
    logger: Callable[[str], None] | None = None,
    max_wait_seconds: float = 12.0,
) -> dict[str, Any]:
    """Upload the configured resume images into an already-open conversation.

    Never raises. The returned report always carries ``success``; callers should
    log it rather than let it influence the greeting outcome.
    """
    settings = resume_image_settings(config)
    report: dict[str, Any] = {"success": False, "files": [], "reason": ""}

    if not settings["enabled"]:
        report.update(skipped=True, reason="未开启简历图片发送")
        return report
    if not settings["paths"]:
        details = "; ".join(
            f"{entry['path']}: {entry['reason']}" for entry in settings["entries"] if entry["reason"]
        )
        _log(logger, f"    ! 简历图片已开启但不可用 → {details or '未配置简历图片'}")
        report["reason"] = details or "no_resume_images"
        return report
    if _stopping(stop_event):
        report["reason"] = "task_stopped"
        return report

    # Conversation-level guard. Several postings can funnel into ONE HR chat
    # (verified 2026-10-14: five 多益网络 游戏客户端开发工程师 postings all opened
    # 曾先生's conversation). On the 2nd..nth posting the greeting is correctly
    # skipped as "already delivered", but this step used to upload the resume
    # images again -- BOSS renders every picture as its own bubble, so the HR saw
    # the same two pages four times. If the chat already carries at least one
    # resume image, this job's delivery is already complete.
    before_message_images = _count_images(target_id)
    if before_message_images >= len(settings["paths"]):
        _log(logger, f"    · 会话中已有 {before_message_images} 张图片，跳过重复上传简历图片")
        report.update(success=True, skipped=True, reason="conversation_already_has_images")
        return report

    inputs = probe_file_inputs(target_id)["inputs"]
    if inputs:
        summary = "、".join(
            f"#{meta.get('index')}[{meta.get('accept') or '无 accept'}{'|multiple' if meta.get('multiple') else ''}]"
            for meta in inputs[:4]
        )
        _log(logger, f"    · 会话页发现 {len(inputs)} 个上传控件: {summary}")
    else:
        _log(logger, "    ! 会话页未发现上传控件，跳过简历图片发送")
        report["reason"] = "no_file_input"
        return report

    chosen = pick_file_input(inputs)
    index = chosen.get("index", 0)
    # Mark the winning input so CDP can target it without a brittle selector path.
    marker = (
        f"(function(){{const inputs=Array.from(document.querySelectorAll('input[type=\"file\"]'));"
        f"if(!inputs.length||{index}>=inputs.length)return false;"
        f"inputs.forEach(function(node,position){{node.removeAttribute('{_INPUT_TAG}');"
        f"if(position==={index})node.setAttribute('{_INPUT_TAG}','1');}});return true;}})()"
    )
    marked = evaluate(target_id, marker)
    if marked is False or marked is None:
        _log(logger, "    ! 上传控件标记失败，跳过简历图片发送")
        report["reason"] = "mark_file_input_failed"
        return report
    multiple = bool(chosen.get("multiple"))

    _log(
        logger,
        f"    · 选择上传控件 #{index}（{chosen.get('accept') or '无 accept'}"
        f"{'，支持多选' if multiple else ''}），上传前会话图片 {before_message_images} 张",
    )

    staged: list[str] = []
    for start in range(0, len(settings["paths"]), len(settings["paths"]) if multiple else 1):
        if multiple:
            batch = settings["paths"]
        else:
            batch = settings["paths"][start : start + 1]
        if _stopping(stop_event):
            report.update(reason="task_stopped", files=staged)
            return report
        if not set_files(target_id, f"input[{_INPUT_TAG}]", batch):
            names = ", ".join(Path(path).name for path in batch)
            _log(logger, f"    ! 简历图片写入上传控件失败: {names}")
            continue
        staged.extend(batch)
        _log(logger, "    · 已载入简历图片: " + ", ".join(Path(path).name for path in batch))

        if _wait_until(lambda: _pending_images(target_id) > 0, 6.0, stop_event):
            confirm = _parse_js_result(evaluate(target_id, JS_CLICK_UPLOAD_CONFIRM))
            if confirm.get("ok"):
                _log(logger, f"    · 已点击「{confirm.get('clicked')}」确认上传")
        else:
            # Either the picker auto-sent, or it needs an explicit confirm click.
            confirm = _parse_js_result(evaluate(target_id, JS_CLICK_UPLOAD_CONFIRM))
            if confirm.get("ok"):
                _log(logger, f"    · 已点击「{confirm.get('clicked')}」确认上传")
            else:
                _log(logger, "    · 上传预览未出现，稍后按会话图片数量判断结果")
        if multiple:
            break

    if not staged:
        report["reason"] = "no_file_staged"
        return report

    success = False
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        if _stopping(stop_event):
            break
        if _count_images(target_id) > before_message_images:
            success = True
            break
        time.sleep(0.8)

    after_message_images = _count_images(target_id)
    report.update(
        success=success,
        files=staged,
        images_before=before_message_images,
        images_after=after_message_images,
    )
    if success:
        _log(logger, f"    ✓ 简历图片已发送（会话图片 {before_message_images} → {after_message_images}）")
    else:
        report["reason"] = "image_not_confirmed_in_conversation"
        _log(
            logger,
            "    ! 简历图片未在会话中确认，可能未发送成功（招呼语已送达状态不受影响）",
        )
    return report


def _count_images(target_id: str) -> int:
    parsed = _parse_js_result(evaluate(target_id, JS_COUNT_MESSAGE_IMAGES))
    try:
        return int(parsed.get("images", 0))
    except (TypeError, ValueError):
        return 0


def _pending_images(target_id: str) -> int:
    parsed = _parse_js_result(evaluate(target_id, JS_COUNT_PENDING_IMAGES))
    try:
        return int(parsed.get("pending", 0))
    except (TypeError, ValueError):
        return 0


def _wait_until(predicate: Callable[[], bool], timeout: float, stop_event: Any) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return True
        except Exception:
            return False
        if _stopping(stop_event):
            return False
        time.sleep(0.4)
    return False
