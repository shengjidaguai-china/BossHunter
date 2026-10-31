from pathlib import Path
import os
import subprocess
import tempfile
import time
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "scripts" / "macos" / "start_bosshunter.sh"
INSTALLER = REPO_ROOT / "scripts" / "macos" / "install_launcher.command"
# The launcher rejects a machine without Chrome before reaching the code under
# test, so the end-to-end cases only run where Chrome is actually installed.
_CHROME_INSTALLED = Path("/Applications/Google Chrome.app").is_dir() or (
	Path.home() / "Applications" / "Google Chrome.app"
).is_dir()


class MacOSLauncherTests(unittest.TestCase):
	def test_launcher_is_portable_and_opens_both_services(self):
		text = LAUNCHER.read_text(encoding="utf-8")
		self.assertIn("#!/bin/bash", text)
		self.assertIn("BASH_SOURCE", text)
		self.assertIn("bosshunter.main", text)
		self.assertIn("--python-path", text)
		self.assertIn("command -v bosshunter", text)
		self.assertIn("remote-debugging-port=9222", text)
		self.assertIn("--user-data-dir", text)
		self.assertIn("http://127.0.0.1:8686", text)
		self.assertIn("web --no-open", text)
		# Interpreter and prefix must expand as quoted arrays so that paths with
		# spaces survive word splitting (review fix on PR for #236). The prefix
		# uses the ${name[@]+...} form because `bosshunter` on PATH leaves it as
		# an empty array, and `set -u` on macOS bash 3.2 aborts on that (#293).
		self.assertIn('"${RUNNER[@]}" ${RUNNER_PREFIX[@]+"${RUNNER_PREFIX[@]}"}', text)
		self.assertNotIn('"${RUNNER[@]}" "${RUNNER_PREFIX[@]}"', text)
		self.assertNotIn("$RUNNER $RUNNER_PREFIX", text)
		self.assertNotIn("shellcheck disable=SC2086", text)
		# Dedicated profile is mandatory: Chrome 136+ blocks debug ports on it.
		self.assertIn(".bosshunter-chrome", text)
		self.assertNotIn("/Users/pikachu", text)

	def test_installer_creates_a_double_click_entry(self):
		text = INSTALLER.read_text(encoding="utf-8")
		self.assertIn("#!/bin/bash", text)
		self.assertIn("BASH_SOURCE", text)
		self.assertIn("start_bosshunter.sh", text)
		self.assertIn("$HOME/Desktop", text)
		self.assertIn("BossHunter.command", text)
		self.assertIn("chmod +x", text)
		self.assertNotIn("/Users/pikachu", text)

	def test_launcher_scripts_are_executable(self):
		for script in (LAUNCHER, INSTALLER):
			mode = script.stat().st_mode
			self.assertTrue(mode & 0o100, f"{script.name} is not executable")

	def test_runner_handles_spaces_in_interpreter_path(self):
		"""Fake interpreter under a space-containing directory must receive intact argv."""
		with tempfile.TemporaryDirectory(prefix="Job Search ") as tmp:
			fake_python = Path(tmp) / "My Env" / "python"
			fake_python.parent.mkdir()
			log_path = Path(tmp) / "argv.log"
			fake_python.write_text(
				"#!/bin/bash\n"
				f"printf '%s\\n' \"$0\" \"$@\" >> '{log_path}'\n",
				encoding="utf-8",
			)
			os.chmod(fake_python, 0o755)
			# macOS tempdirs live behind the /var -> /private/var symlink; hand the
			# launcher the canonical path so argv equality checks are meaningful.
			resolved_python = str(fake_python.resolve())

			proc = subprocess.Popen(
				[
					"/bin/bash",
					str(LAUNCHER),
					"--skip-chrome",
					"--python-path",
					resolved_python,
				],
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
			)
			try:
				calls = self._wait_for_calls(log_path)
			finally:
				proc.terminate()
				proc.wait(timeout=15)

			# Each call logs one argv per line; the interpreter path must never
			# be word-split and both invocations must be present.
			self.assertIn("connect", calls)
			self.assertIn("--no-open", calls)
			self.assertEqual(calls.count("web"), 1)
			self.assertEqual(calls.count("-m"), 2)
			self.assertEqual(calls.count("bosshunter.main"), 2)
			self.assertEqual(calls.count(resolved_python), 2)

	@unittest.skipUnless(
		_CHROME_INSTALLED,
		"launcher verifies Chrome before the code under test; no macOS Chrome app here",
	)
	def test_runner_on_path_leaves_no_prefix_and_still_runs(self):
		"""`bosshunter` on PATH needs no `-m` prefix, so the prefix array is empty.

		macOS ships bash 3.2 where `set -u` aborts on an empty array expansion, so
		this branch used to exit 1 with `RUNNER_PREFIX[@]: unbound variable` after
		`source .venv/bin/activate` — the path the docs recommend. Cover it by
		putting a `bosshunter` shim on PATH and passing no `--python-path`.
		"""
		with tempfile.TemporaryDirectory(prefix="bh path ") as tmp:
			shim_dir = Path(tmp) / "bin"
			shim_dir.mkdir()
			log_path = Path(tmp) / "argv.log"
			shim = shim_dir / "bosshunter"
			shim.write_text(
				"#!/bin/bash\n"
				f"printf '%s\\n' \"$0\" \"$@\" >> '{log_path}'\n",
				encoding="utf-8",
			)
			os.chmod(shim, 0o755)

			env = dict(os.environ)
			env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
			# A repo-relative .venv would win over python3 but not over the PATH
			# shim, so the empty-prefix branch is the one actually exercised.
			proc = subprocess.Popen(
				["/bin/bash", str(LAUNCHER), "--skip-chrome"],
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
				env=env,
			)
			try:
				calls = self._wait_for_calls(log_path)
			finally:
				proc.terminate()
				proc.wait(timeout=15)
			_, stderr = proc.communicate(timeout=15)

			self.assertNotIn("unbound variable", stderr)
			self.assertIn("connect", calls)
			self.assertIn("--no-open", calls)
			# No `-m bosshunter.main` prefix: the shim is invoked directly.
			self.assertNotIn("-m", calls)
			self.assertEqual(calls.count(str(shim)), 2)

	@staticmethod
	def _wait_for_calls(log_path, timeout=30):
		deadline = time.monotonic() + timeout
		while time.monotonic() < deadline:
			if log_path.exists():
				lines = log_path.read_text(encoding="utf-8").splitlines()
				if "--no-open" in lines:
					return lines
			time.sleep(0.2)
		return []


if __name__ == "__main__":
	unittest.main()
