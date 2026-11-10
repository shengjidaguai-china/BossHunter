import io
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from threading import Event
from unittest.mock import patch

from bosshunter.ai import local_cli
from bosshunter.ai.credentials import AIRequestError, call_anthropic_text, get_ai_api_key
from bosshunter.cancellation import OperationCancelled
from bosshunter.config import credentials_path_for, load_config, save_config
from bosshunter.web import server
from bosshunter.web.preflight import _check_ai_connection

FAKE_CLI = '''import json, sys, time
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.buffer.read().decode("utf-8")
if prompt == "fail":
    print("sensitive-provider-error", file=sys.stderr)
    sys.exit(1)
if prompt == "wait":
    time.sleep(30)
reply = "BOSSHUNTER_AI_OK" if "Reply with exactly" in prompt else prompt
if "--output-last-message" in args:
    Path(args[args.index("--output-last-message") + 1]).write_text(reply, encoding="utf-8")
else:
    print(json.dumps({"result": reply}))
'''


class LocalAiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        environment_patch = patch.dict("os.environ", {"CODEX_CLI_PATH": ""})
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        script = self.root / "fake_cli.py"
        script.write_text(FAKE_CLI, encoding="utf-8")
        self.command = [sys.executable, str(script)]
        self.command_patch = patch.object(local_cli, "_command", return_value=self.command)
        self.command_patch.start()
        self.addCleanup(self.command_patch.stop)
        self.config = {"ai": {"service": "codex_cli", "provider": "local_cli", "model": ""}}
        old_base = server.BASE_DIR
        server.set_base_dir(self.root)
        self.addCleanup(server.set_base_dir, old_base)

    def request(self, path, body=None, overrides=None):
        payload = json.dumps(body).encode() if body is not None else b""
        environ = {
            "REMOTE_ADDR": "127.0.0.1", "HTTP_HOST": "127.0.0.1:8686",
            "REQUEST_METHOD": "POST" if body is not None else "GET",
            "PATH_INFO": path, "QUERY_STRING": "", "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "8686", "wsgi.version": (1, 0), "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(payload), "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": False,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(payload)),
        }
        environ.update(overrides or {})
        status = []
        def start_response(value, headers, exc_info=None):
            status.append(value)
        response = server.app(environ, start_response)
        try:
            text = b"".join(response).decode()
        finally:
            if hasattr(response, "close"):
                response.close()
        return int(status[0].split()[0]), text

    def test_probe_authorization_and_unicode_text_dispatch_for_both_tools(self):
        for service in local_cli.LOCAL_SERVICES:
            with self.subTest(service=service):
                self.config["ai"] = {"service": service, "provider": "local_cli", "model": ""}
                self.assertFalse(local_cli.local_ai_authorized(self.config))
                with self.assertRaises(AIRequestError):
                    call_anthropic_text("简历正文", self.config, 100)
                self.config["ai"]["local_cli_grant"] = local_cli.verify_local_ai(self.config)
                self.assertTrue(local_cli.local_ai_authorized(self.config))
                self.assertEqual(call_anthropic_text("简历正文", self.config, 100), "简历正文")
                self.assertIsNone(get_ai_api_key(self.config))

    def test_unexpected_probe_response_does_not_authorize(self):
        with (
            patch.object(local_cli, "_invoke", return_value="some unrelated text"),
            self.assertRaises(AIRequestError),
        ):
            local_cli.verify_local_ai(self.config)
        self.assertFalse(local_cli.local_ai_authorized(self.config))

    def test_changed_model_or_installation_invalidates_grant(self):
        self.config["ai"]["local_cli_grant"] = local_cli.verify_local_ai(self.config)
        self.config["ai"]["model"] = "other-model"
        self.assertFalse(local_cli.local_ai_authorized(self.config))
        self.config["ai"]["model"] = ""
        Path(self.command[-1]).write_text(FAKE_CLI + "\n# new version", encoding="utf-8")
        self.assertFalse(local_cli.local_ai_authorized(self.config))

    def test_failed_process_output_is_not_exposed(self):
        self.config["ai"]["local_cli_grant"] = local_cli.verify_local_ai(self.config)
        with self.assertRaises(AIRequestError) as raised:
            local_cli.call_local_text("fail", self.config)
        self.assertNotIn("sensitive-provider-error", str(raised.exception))

    def test_timeout_and_cancellation_kill_started_process(self):
        original_popen = subprocess.Popen
        processes = []
        def launch(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            if args[0][:2] == self.command:
                processes.append(process)
            return process
        with patch.object(local_cli.subprocess, "Popen", side_effect=launch):
            with self.assertRaises(AIRequestError):
                local_cli._invoke("wait", self.config, self.command, 0.1)
            self.assertIsNotNone(processes[-1].poll())
            event = Event()
            self.config["_workbench_stop_event"] = event
            def cancel_after_start(*args, **kwargs):
                process = launch(*args, **kwargs)
                event.set()
                return process
            with (
                patch.object(local_cli.subprocess, "Popen", side_effect=cancel_after_start),
                self.assertRaises(OperationCancelled),
            ):
                local_cli._invoke("wait", self.config, self.command, 5)
            self.assertIsNotNone(processes[-1].poll())

    def test_prompt_uses_stdin_and_cli_restrictions_are_enabled(self):
        original_popen = subprocess.Popen
        for service in local_cli.LOCAL_SERVICES:
            self.config["ai"]["service"] = service
            with patch.object(local_cli.subprocess, "Popen", wraps=original_popen) as launch:
                result = local_cli._invoke("private-resume $(echo secret)", self.config, self.command, 5)
            self.assertEqual(result, "private-resume $(echo secret)")
            args = launch.call_args.args[0]
            self.assertFalse(launch.call_args.kwargs["shell"])
            self.assertNotIn("private-resume $(echo secret)", args)
            self.assertNotEqual(Path(launch.call_args.kwargs["cwd"]), Path.cwd())
            if service == "codex_cli":
                self.assertIn("read-only", args)
                self.assertIn("features.shell_tool=false", args)
                self.assertIn("--ignore-user-config", args)
            else:
                self.assertEqual(args[args.index("--tools") + 1], "")
                self.assertIn("--strict-mcp-config", args)
                self.assertIn("--no-session-persistence", args)

    def test_route_verifies_then_persists_private_grant_and_revocation_blocks_old_snapshot(self):
        save_config(self.config, server.CONFIG_PATH)
        status, body = self.request("/api/config/local-ai/authorize", {"confirm": True})
        self.assertEqual(status, 200, body)
        loaded = deepcopy(load_config(server.CONFIG_PATH))
        self.assertTrue(local_cli.local_ai_authorized(loaded))
        self.assertEqual(loaded["_local_ai_config_path"], str(server.CONFIG_PATH.resolve()))
        save_config(loaded, server.CONFIG_PATH)
        self.assertNotIn("_local_ai_config_path", server.CONFIG_PATH.read_text(encoding="utf-8"))
        grant = loaded["ai"]["local_cli_grant"]
        self.assertNotIn(grant, server.CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertIn(grant, credentials_path_for(server.CONFIG_PATH).read_text(encoding="utf-8"))
        self.assertNotIn(grant, self.request("/api/config")[1])
        self.assertNotIn(grant, server._config_download_payload(loaded))
        self.assertNotIn("_local_ai_config_path", self.request("/api/config")[1])
        self.assertEqual(_check_ai_connection(loaded, True)[0]["status"], "pass")
        self.assertEqual(self.request("/api/config/local-ai/revoke", {})[0], 200)
        self.assertFalse(local_cli.local_ai_authorized(loaded))
        server._write_config(loaded)
        self.assertNotIn("local_cli_grant", load_config(server.CONFIG_PATH)["ai"])
        with self.assertRaises(AIRequestError):
            local_cli.call_local_text("old task snapshot", loaded)

    def test_unrelated_save_preserves_grant_but_model_change_removes_it(self):
        save_config(self.config, server.CONFIG_PATH)
        self.assertEqual(self.request("/api/config/local-ai/authorize", {"confirm": True})[0], 200)
        displayed = json.loads(self.request("/api/config")[1])
        displayed["ai"]["timeout_seconds"] = 100
        self.assertEqual(self.request("/api/config", displayed)[0], 200)
        self.assertTrue(local_cli.local_ai_authorized(load_config(server.CONFIG_PATH)))
        displayed["ai"]["model"] = "another-model"
        self.assertEqual(self.request("/api/config", displayed)[0], 200)
        self.assertNotIn("local_cli_grant", load_config(server.CONFIG_PATH)["ai"])

    def test_forged_grant_is_discarded_and_failed_probe_does_not_persist(self):
        save_config(self.config, server.CONFIG_PATH)
        forged = {"ai": {**self.config["ai"], "local_cli_grant": "forged", "local_cli_authorized": True}}
        self.assertNotIn("local_cli_grant", server._sanitize_config_for_write(forged)["ai"])
        with patch.object(server, "verify_local_ai", side_effect=AIRequestError("local_tool", "not logged in")):
            self.assertEqual(self.request("/api/config/local-ai/authorize", {"confirm": True})[0], 400)
        self.assertNotIn("local_cli_grant", load_config(server.CONFIG_PATH)["ai"])
        self.assertEqual(self.request("/api/config/local-ai/authorize", {})[0], 400)

    def test_config_change_during_probe_prevents_authorization(self):
        save_config(self.config, server.CONFIG_PATH)
        def changed(config):
            updated = {**config, "ai": {**config["ai"], "model": "changed"}}
            save_config(updated, server.CONFIG_PATH)
            return "outdated-grant"
        with patch.object(server, "verify_local_ai", side_effect=changed):
            self.assertEqual(self.request("/api/config/local-ai/authorize", {"confirm": True})[0], 409)
        self.assertNotIn("local_cli_grant", load_config(server.CONFIG_PATH)["ai"])

    def test_authorization_routes_require_loopback_and_same_origin(self):
        for override in ({"REMOTE_ADDR": "192.168.1.5"}, {"HTTP_HOST": "attacker.example"},
                         {"HTTP_ORIGIN": "https://attacker.example"}):
            for action in ("authorize", "revoke"):
                with self.subTest(override=override, action=action):
                    self.assertEqual(self.request(f"/api/config/local-ai/{action}", {"confirm": True}, override)[0], 403)

    def test_windows_npm_wrapper_is_replaced_with_node_argv(self):
        wrapper = self.root / "codex.cmd"
        wrapper.write_text("do not run this shell wrapper", encoding="utf-8")
        script = self.root / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        script.parent.mkdir(parents=True)
        script.write_text("// fake npm entry", encoding="utf-8")
        self.command_patch.stop()
        with patch.object(local_cli.shutil, "which", side_effect=[str(wrapper), sys.executable]):
            command = local_cli._command(self.config)
        self.assertEqual(command, [str(Path(sys.executable).resolve()), str(script.resolve())])

    def test_missing_tool_does_not_fall_back_to_api_credentials(self):
        self.command_patch.stop()
        self.config["ai"]["api_key"] = "unused-api-key"
        with patch.object(local_cli.shutil, "which", return_value=None), self.assertRaises(AIRequestError):
            call_anthropic_text("prompt", self.config, 100)
        self.assertIsNone(get_ai_api_key(self.config))

    def test_empty_codex_model_uses_configured_model_instead_of_cli_builtin_default(self):
        codex_home = self.root / "codex-home"
        codex_home.mkdir()
        settings = codex_home / "config.toml"
        settings.write_text('model = "account-supported-model" # current choice\n[hooks]\ncommand = "must-not-run"\n', encoding="utf-8")
        original_popen = subprocess.Popen
        with patch.dict("os.environ", {"CODEX_HOME": str(codex_home)}):
            with patch.object(local_cli.subprocess, "Popen", wraps=original_popen) as launch:
                self.assertEqual(local_cli._invoke("hello", self.config, self.command, 5), "hello")
            args = launch.call_args.args[0]
            self.assertEqual(args[args.index("--model") + 1], "account-supported-model")
            self.assertIn("--ignore-user-config", args)
            self.assertIn("features.apps=false", args)
            self.assertIn("features.remote_plugin=false", args)
            self.config["ai"]["local_cli_grant"] = local_cli.verify_local_ai(self.config)
            settings.write_text('model = "another-account-model"\n', encoding="utf-8")
            self.assertFalse(local_cli.local_ai_authorized(self.config))

    def test_explicit_model_wins_and_table_models_are_not_used_as_defaults(self):
        codex_home = self.root / "codex-home"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text("# no root model\n[profiles.other]\nmodel = 'unselected-model'\n", encoding="utf-8")
        with patch.dict("os.environ", {"CODEX_HOME": str(codex_home)}):
            self.assertEqual(local_cli._resolved_model(self.config), "")
            self.config["ai"]["model"] = "explicit-model"
            with patch.object(Path, "open", side_effect=AssertionError("must not read settings")):
                self.assertEqual(local_cli._resolved_model(self.config), "explicit-model")

    def test_desktop_cli_is_preferred_to_an_older_global_npm_install(self):
        bundled = self.root / "codex.exe"
        bundled.write_bytes(b"test executable identity; do not execute")
        self.command_patch.stop()
        with (
            patch.dict("os.environ", {"CODEX_CLI_PATH": str(bundled)}),
            patch.object(local_cli.shutil, "which", side_effect=AssertionError("must not use global CLI")),
        ):
            self.assertEqual(local_cli._command(self.config), [str(bundled.resolve())])

    def test_terminal_model_failure_is_not_confused_with_startup_auth_warnings(self):
        error = local_cli._process_error("", 'WARN model cache 401\nERROR: {"message": "The model is not supported when using Codex with a ChatGPT account."}')
        self.assertEqual(error.kind, "local_model")
        self.assertNotIn("401", error.user_message)
        for output, kind in (("ERROR: not logged in; secret-value", "local_auth"),
                             ("error: unexpected argument '--new-flag'", "local_version"),
                             ("ERROR: insufficient_quota secret-value", "local_quota")):
            with self.subTest(kind=kind):
                error = local_cli._process_error("", output)
                self.assertEqual(error.kind, kind)
                self.assertNotIn("secret-value", error.user_message)

    def test_claude_error_result_does_not_become_final_text(self):
        error = local_cli._process_error('{"is_error":true,"result":"not logged in secret-value"}', "unrelated warning")
        self.assertEqual(error.kind, "local_auth")
        self.assertNotIn("secret-value", error.user_message)

    def test_local_service_without_model_uses_cli_default(self):
        save_config({"ai": {"service": "codex_cli"}}, server.CONFIG_PATH)
        loaded = load_config(server.CONFIG_PATH)
        self.assertEqual(loaded["ai"]["provider"], "local_cli")
        self.assertEqual(loaded["ai"]["model"], "")


if __name__ == "__main__":
    unittest.main()
