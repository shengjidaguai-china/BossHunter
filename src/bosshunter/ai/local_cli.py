"""Explicitly authorized text-only adapters for locally installed AI CLIs.

Authentication stays inside each CLI. BossHunter never opens its credential files.
"""

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from bosshunter.cancellation import OperationCancelled, stop_requested

LOCAL_SERVICES = {"codex_cli": "codex", "claude_cli": "claude"}
PROBE_REPLY = "BOSSHUNTER_AI_OK"


def _resolved_model(config: dict) -> str:
    """Honor an explicit model, or the public top-level Codex model setting.

    Read only the model line, never auth.json, OAuth tokens, caches, or keychains.
    Keep ignoring the rest of the CLI configuration (hooks and tool servers).
    """
    ai = config.get("ai", {})
    model = str(ai.get("model") or "").strip()
    if model or ai.get("service") != "codex_cli":
        return model
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    try:
        with (codex_home / "config.toml").open(encoding="utf-8-sig") as source:
            for line in source:
                if line.lstrip().startswith("["):
                    break
                match = re.fullmatch(r'''\s*model\s*=\s*(?:"([^"\\\r\n]+)"|'([^'\r\n]+)')\s*(?:#.*)?''', line.rstrip("\r\n"))
                if match:
                    return (match.group(1) or match.group(2)).strip()
    except FileNotFoundError:
        pass
    except (OSError, UnicodeError):
        from bosshunter.ai.credentials import AIRequestError
        raise AIRequestError("local_config", "无法读取 Codex 的模型设置，请在 AI 设置中手动填写可用模型 ID") from None
    return ""


def _process_error(stdout: str, stderr: str):
    """Classify terminal failures, ignoring unrelated startup warnings."""
    from bosshunter.ai.credentials import AIRequestError

    terminal = [line for line in stderr.splitlines() if re.match(r"^error:", line, re.IGNORECASE)]
    detail = "\n".join(terminal) if terminal else stderr[-2000:]
    try:
        payload = json.loads(stdout)
        if isinstance(payload, dict) and payload.get("is_error"):
            detail = str(payload.get("result") or detail)
    except ValueError:
        pass
    detail = detail.lower()
    if re.search(r"unexpected argument|unknown option|unrecognized (argument|option)", detail):
        return AIRequestError("local_version", "当前 AI 工具版本不支持所需参数，请升级 CLI 后重新验证")
    if re.search(r"model.*(not supported|not found|does not exist|not available)|unsupported model", detail):
        return AIRequestError("local_model", "当前模型不受本机 AI 账号支持，请填写可用模型 ID，或清空以使用工具已配置的模型")
    if re.search(r"not logged in|please (log|sign) in|login required|401|unauthorized|invalid.api.key", detail):
        return AIRequestError("local_auth", "本机 AI 登录已失效或凭据无效，请在终端重新登录对应工具后验证")
    if re.search(r"insufficient.quota|quota.exceeded|balance|billing|429|rate.limit", detail):
        return AIRequestError("local_quota", "本机 AI 账号额度不足或被限流，请检查额度后重试")
    if re.search(r"connection.*(failed|refused|closed)|timed out|dns|error sending request", detail):
        return AIRequestError("network", "本机 AI 无法连接模型服务，请检查网络、代理或服务地址")
    return AIRequestError("local_tool", "本机 AI 调用失败，请在终端检查登录、模型权限和额度后重新验证")


def is_local_ai(config: dict) -> bool:
    return config.get("ai", {}).get("service") in LOCAL_SERVICES


def _command(config: dict) -> list[str]:
    from bosshunter.ai.credentials import AIRequestError

    tool = LOCAL_SERVICES.get(config.get("ai", {}).get("service"))
    if not tool:
        raise AIRequestError("local_tool", "请选择支持的本机 AI 工具")
    executable = None
    if tool == "codex":
        # The desktop app may ship a newer CLI than the global npm shim.
        # Use its supplied executable path, without opening any login files.
        bundled = os.environ.get("CODEX_CLI_PATH", "")
        if bundled and Path(bundled).is_absolute() and Path(bundled).is_file():
            executable = bundled
    executable = executable or shutil.which(tool)
    if not executable:
        raise AIRequestError("local_tool", f"未找到 {tool}，请安装并在终端登录后重启 BossHunter")
    path = Path(executable).resolve()
    if path.parent == Path.cwd().resolve():
        raise AIRequestError("local_tool", "请使用安装在系统 PATH 中的 AI 工具，不从当前项目目录启动")
    # Never execute npm .cmd/.bat wrappers through a shell on Windows.
    if path.suffix.lower() in {".cmd", ".bat", ".ps1"}:
        script = path.parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        node = shutil.which("node")
        if tool != "codex" or not node or not script.is_file():
            raise AIRequestError("local_tool", "当前安装方式无法安全调用，请安装原生 CLI 或标准 Codex npm 包")
        if Path(node).resolve().parent == Path.cwd().resolve():
            raise AIRequestError("local_tool", "请使用系统安装的 Node.js")
        return [str(Path(node).resolve()), str(script.resolve())]
    return [str(path)]


def _identity(config: dict, command: list[str]) -> str:
    ai = config.get("ai", {})
    files = []
    for arg in command:
        path = Path(arg)
        stat = path.stat()
        files.append([str(path), stat.st_size, stat.st_mtime_ns])
    value = ["v2", ai.get("service"), _resolved_model(config), files]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode("utf-8")).hexdigest()


def local_ai_authorized(config: dict) -> bool:
    if not is_local_ai(config):
        return False
    grant = config.get("ai", {}).get("local_cli_grant")
    if not isinstance(grant, str) or not grant:
        return False
    try:
        if path := config.get("_local_ai_config_path"):
            from bosshunter.config import load_config
            current = load_config(Path(path))
            if (current["ai"].get("local_cli_grant") != grant
                    or current["ai"].get("service") != config["ai"].get("service")
                    or str(current["ai"].get("model") or "").strip() != str(config["ai"].get("model") or "").strip()):
                return False
        return grant == _identity(config, _command(config))
    except (OSError, RuntimeError, ValueError):
        return False


def _invoke(prompt: str, config: dict, command: list[str], timeout: float) -> str:
    from bosshunter.ai.credentials import AIRequestError

    service = config["ai"]["service"]
    model = _resolved_model(config)
    env = os.environ.copy()
    # Parent app session markers must not turn this one-shot call into a nested
    # interactive session. Credentials themselves are left to the CLI.
    env.pop("CLAUDECODE", None)
    for name in ("CODEX_APP_TOOLS_PIPE_PATH", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "CODEX_THREAD_ID", "CODEX_SESSION_ID"):
        env.pop(name, None)
    with tempfile.TemporaryDirectory(prefix="bosshunter-ai-") as workspace:
        output = Path(workspace) / "answer.txt"
        if service == "codex_cli":
            args = [*command, "exec", "--ignore-user-config", "--ignore-rules",
                    "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
                    "-c", 'approval_policy="never"', "-c", "features.shell_tool=false",
                    "-c", "features.apps=false", "-c", "features.remote_plugin=false",
                    "-c", 'web_search="disabled"',
                    "--output-last-message", str(output)]
        else:
            args = [*command, "--print", "--output-format", "json", "--tools", "",
                    "--disallowedTools", "mcp__*", "--strict-mcp-config",
                    "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "",
                    "--settings", '{"disableAllHooks":true}',
                    "--disable-slash-commands", "--no-session-persistence"]
        if model:
            args.extend(["--model", model])
        if service == "codex_cli":
            args.append("-")
        if stop_requested(config):
            raise OperationCancelled("用户已请求停止")
        try:
            process = subprocess.Popen(
                args, cwd=workspace, env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                start_new_session=os.name != "nt",
            )
        except OSError:
            raise AIRequestError("local_tool", "无法启动本机 AI 工具，请检查安装") from None
        deadline = time.monotonic() + timeout
        try:
            first = True
            while True:
                if stop_requested(config):
                    raise OperationCancelled("用户已请求停止")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AIRequestError("network", "本机 AI 调用超时，请检查工具登录状态和网络")
                try:
                    stdout, stderr = process.communicate(input=prompt if first else None, timeout=min(0.2, remaining))
                    break
                except subprocess.TimeoutExpired:
                    first = False
        finally:
            if process.poll() is None:
                _kill_process_tree(process)
        if process.returncode:
            raise _process_error(stdout, stderr)
        if service == "codex_cli":
            text = output.read_text(encoding="utf-8").strip() if output.is_file() else ""
        else:
            try:
                payload = json.loads(stdout)
            except ValueError:
                payload = {}
            if isinstance(payload, dict) and payload.get("is_error"):
                raise _process_error(stdout, stderr)
            text = payload.get("result", "") if isinstance(payload, dict) else ""
        if not isinstance(text, str) or not text.strip():
            raise AIRequestError("empty_response", "本机 AI 没有返回有效文本")
        return text.strip()


def _kill_process_tree(process: subprocess.Popen) -> None:
    """Include the native Codex child spawned by its npm Node launcher."""
    if os.name == "nt":
        taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
        try:
            subprocess.run([str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        # Do not let a detached grandchild holding a pipe block task shutdown.
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()


def verify_local_ai(config: dict) -> str:
    """Issue a tiny real request; return a grant only after a correct response."""
    from bosshunter.ai.credentials import AIRequestError

    command = _command(config)
    identity = _identity(config, command)
    reply = _invoke(f"Reply with exactly {PROBE_REPLY}. Do not use tools.", config, command, 60)
    if reply != PROBE_REPLY or identity != _identity(config, _command(config)):
        raise AIRequestError("local_verification", "本机 AI 验证未通过，请检查工具和模型后重试")
    return identity


def call_local_text(prompt: str, config: dict, timeout: float | None = None) -> str:
    from bosshunter.ai.credentials import AIRequestError, _coerce_timeout

    command = _command(config)
    if not local_ai_authorized(config) or config.get("ai", {}).get("local_cli_grant") != _identity(config, command):
        raise AIRequestError("local_authorization", "本机 AI 尚未验证授权，或工具/模型已变更，请到 AI 设置重新授权")
    return _invoke(prompt, config, command, _coerce_timeout(timeout or config["ai"].get("timeout_seconds")))
