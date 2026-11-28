"""Browser operations scoped to an existing Ego Lite task space."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


_BRIDGE = Path(__file__).with_name("runtime") / "ego-task-space.mjs"
_RESPONSE = "BOSSHUNTER_EGO "


class EgoTaskSpaceError(RuntimeError):
    """The configured task space could not be used."""


class EgoTaskSpace:
    def __init__(self, space_id: int) -> None:
        self.space_id = space_id
        self.executable = shutil.which("ego-browser") or Path.home() / ".local/bin/ego-browser"

    @classmethod
    def from_config(cls, config: dict[str, Any], *, section: str = "collection") -> EgoTaskSpace | None:
        space_id = (config.get(section) or {}).get("ego_task_space_id")
        if space_id is None:
            return None
        if type(space_id) is not int or space_id <= 0:
            raise ValueError(f"{section}.ego_task_space_id 必须是已有 Ego Lite 任务空间的正整数 ID")
        return cls(space_id)

    def _call(self, action: str, *, timeout: float = 30, **args: Any) -> Any:
        request = json.dumps({"id": self.space_id, "action": action, "args": args})
        script = f"const request = {request};\n" + _BRIDGE.read_text(encoding="utf-8")
        try:
            result = subprocess.run(
                [self.executable, "nodejs"],
                input=script,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout + 5,
            )
        except subprocess.TimeoutExpired as exc:
            raise EgoTaskSpaceError(f"Ego Lite 任务空间 {self.space_id} 操作超时（{action}）") from exc
        except OSError as exc:
            raise EgoTaskSpaceError("无法运行 ego-browser，请确认已安装在 PATH 或 ~/.local/bin 中") from exc
        if result.returncode == 0:
            for line in reversed((result.stdout + "\n" + result.stderr).split("\n")):
                if line.startswith(_RESPONSE):
                    try:
                        reply = json.loads(line[len(_RESPONSE):])
                    except ValueError:
                        break
                    if reply.get("unavailable"):
                        break
                    return reply.get("value")
        raise EgoTaskSpaceError(f"无法使用 Ego Lite 任务空间 {self.space_id}，请确认它仍由 Agent 控制")

    def check(self) -> None:
        if self._call("check") is not True:
            raise EgoTaskSpaceError(f"Ego Lite 任务空间 {self.space_id} 不可用")

    def get_page_targets(self) -> list[dict]:
        return self._call("targets") or []

    def new_tab(self, url: str, background: bool = False) -> str | None:
        # The SDK manages foreground behavior within the task space.
        return self._call("new", url=url)

    def close_tab(self, target_id: str) -> bool:
        # Do not mask a collector's original error while giving up browser control.
        try:
            return self._call("close", label=target_id) is True
        except EgoTaskSpaceError:
            return False

    def navigate(self, target_id: str, url: str) -> bool:
        return self._call("navigate", label=target_id, url=url) is True

    def evaluate(self, target_id: str, expression: str, timeout: float = 30) -> Any:
        return self._call("evaluate", timeout=timeout, label=target_id, expression=expression)

    def scroll(self, target_id: str, y: int = 0, direction: str = "") -> bool:
        return self._call("scroll", label=target_id, y=y, direction=direction) is True

    def wait_for_load(self, target_id: str, timeout: float = 10) -> bool:
        return self._call("wait", timeout=timeout, label=target_id, ms=int(timeout * 1000)) is True

    navigate_action = navigate

    def click_action(self, target_id: str, selector: str) -> bool:
        return self._call("click", timeout=15, label=target_id, selector=selector) is True

    def type_text_action(self, target_id: str, text: str, human: bool = False) -> bool:
        return self._call("type", label=target_id, text=text) is True

    def press_key_action(self, target_id: str, key: str) -> bool:
        chord = "ControlOrMeta+A" if key == "SelectAll" else key
        return self._call("key", label=target_id, chord=chord) is True

    # RuntimeClient names used by the shared browser facade.
    targets = get_page_targets
    click = click_action
    type_text = type_text_action
    press_key = press_key_action

    def health(self) -> dict:
        self.check()
        return {"ego_task_space_id": self.space_id}

    def click_at(self, target_id: str, selector: str) -> bool:
        return self._call("click_at", label=target_id, selector=selector) is True

    def info(self, target_id: str) -> dict | None:
        return self._call("info", label=target_id)

    def set_files(self, target_id: str, selector: str, files: list[str]) -> bool:
        return self._call("files", label=target_id, selector=selector, files=files) is True

    def screenshot(self, target_id: str, file_path: str | Path, *, selector: str = "") -> bool:
        return self._call("screenshot", label=target_id, path=str(file_path), selector=selector) is True

    def print_pdf(self, target_id: str, file_path: str | Path) -> bool:
        return self._call("pdf", label=target_id, path=str(file_path)) is True
