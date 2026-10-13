from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "scripts" / "windows" / "start_bosshunter.ps1"
INSTALLER = REPO_ROOT / "scripts" / "windows" / "install_desktop_shortcut.ps1"


class WindowsLauncherTests(unittest.TestCase):
	@unittest.skipUnless(os.name == "nt", "requires Windows Start-Process argument parsing")
	def test_chrome_profile_with_spaces_is_one_argument(self):
		powershell = shutil.which("powershell") or shutil.which("pwsh")
		if not powershell:
			self.skipTest("PowerShell is not installed")
		# Exercise both launch sites through Start-Process, using Python instead of Chrome.
		profile_arguments = [
			line.strip().rstrip(",")
			for line in LAUNCHER.read_text(encoding="utf-8").splitlines()
			if "--user-data-dir=" in line
		]
		self.assertEqual(len(profile_arguments), 2)
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			probe = root / "argv_probe.py"
			output = root / "argv.json"
			probe.write_text(
				"import json, os, sys\n"
				"with open(os.environ['BOSSHUNTER_ARGV_OUTPUT'], 'w') as f:\n"
				"    json.dump(sys.argv[1:], f)\n",
				encoding="utf-8",
			)
			env = dict(
				os.environ,
				BOSSHUNTER_ARGV_OUTPUT=str(output),
				BOSSHUNTER_ARGV_PYTHON=sys.executable,
				BOSSHUNTER_ARGV_PROBE=str(probe),
			)
			profile = str(root / "user with spaces" / "BossHunterChrome")
			env["BOSSHUNTER_ARGV_PROFILE"] = profile
			for argument in profile_arguments:
				with self.subTest(argument=argument):
					output.unlink(missing_ok=True)
					command = (
						'$ChromeProfile = $env:BOSSHUNTER_ARGV_PROFILE; '
						'$probeArg = \'"\' + $env:BOSSHUNTER_ARGV_PROBE + \'"\'; '
						'$argsForProbe = @($probeArg, ' + argument + ', "https://www.zhipin.com"); '
						'Start-Process -FilePath $env:BOSSHUNTER_ARGV_PYTHON '
						'-ArgumentList $argsForProbe -WindowStyle Hidden -Wait'
					)
					subprocess.run(
						[powershell, "-NoProfile", "-NonInteractive", "-Command", command],
						check=True, env=env, capture_output=True, text=True, timeout=30,
					)
					self.assertEqual(
						json.loads(output.read_text(encoding="utf-8")),
						[f"--user-data-dir={profile}", "https://www.zhipin.com"],
					)

	def test_launcher_is_portable_and_opens_both_services(self):
		text = LAUNCHER.read_text(encoding="utf-8")
		self.assertIn("$PSScriptRoot", text)
		self.assertIn("bosshunter.main", text)
		self.assertIn("$PythonPath", text)
		self.assertIn("Get-Command", text)
		self.assertIn("remote-debugging-port=9222", text)
		self.assertIn("http://127.0.0.1:8686", text)
		self.assertIn("-WindowStyle Hidden", text)
		self.assertNotIn("C:\\Users\\123", text)

	def test_launcher_tries_the_repository_venv_before_path_python(self):
		text = LAUNCHER.read_text(encoding="utf-8")
		# Mirrors scripts/macos/start_bosshunter.sh: the CLI command on PATH first,
		# then the repository venv, then Python on PATH. A project installed inside
		# the venv is only importable there, so it must be tried before `py`/`python`.
		self.assertIn('Join-Path $RepoRoot ".venv\\Scripts\\python.exe"', text)
		bosshunter_branch = text.index("if ($Bosshunter)")
		venv_branch = text.index("elseif (Test-Path -LiteralPath $VenvPython)")
		path_python = text.index('Get-Command "python"')
		self.assertLess(bosshunter_branch, venv_branch)
		self.assertLess(venv_branch, path_python)

	def test_installer_creates_a_shortcut_to_the_launcher(self):
		text = INSTALLER.read_text(encoding="utf-8")
		self.assertIn("CreateShortcut", text)
		self.assertIn("start_bosshunter.ps1", text)
		self.assertIn('GetFolderPath("Desktop")', text)
		self.assertIn("-WindowStyle Hidden", text)
		self.assertNotIn("C:\\Users\\123", text)


if __name__ == "__main__":
	unittest.main()
