# Offline checks for the Windows process-matching rules. The rules are pure
# functions, so every case below is a fabricated command line: no process is
# inspected and nothing is stopped. This covers what the Linux CI cannot.
#
# Run with Windows PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tests\windows\test_stop_matching.ps1

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\scripts\windows\BossHunterProcessMatch.ps1")

$RepoRoot = "D:\repo\BossHunter"
$OtherRepo = "D:\other\BossHunter"
$LauncherPath = Join-Path $RepoRoot "scripts\windows\start_bosshunter.ps1"
$ChromeProfile = "C:\Users\Ada Lovelace\AppData\Local\BossHunterChrome"

$script:Checks = 0
$script:Failures = @()

function Assert-Equal {
	param([string]$Name, $Expected, $Actual)

	$script:Checks++
	if ($Expected -eq $Actual) { return }
	$script:Failures += ("{0}  (expected {1}, got {2})" -f $Name, $Expected, $Actual)
}

function Assert-True {
	param([string]$Name, $Actual)
	Assert-Equal -Name $Name -Expected $true -Actual ([bool]$Actual)
}

function Assert-False {
	param([string]$Name, $Actual)
	Assert-Equal -Name $Name -Expected $false -Actual ([bool]$Actual)
}

# ── Workbench: `... web` only, never CLI subcommands ─────────────────────

Assert-True "workbench: python -m bosshunter.main web" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main web --no-open'))

Assert-True "workbench: bosshunter.exe web" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\bosshunter.exe" web --no-open'))

Assert-True "workbench: pythonw.exe web" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\pythonw.exe" -m bosshunter.main web'))

Assert-False "workbench: CLI scrape from another checkout" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\other\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main scrape'))

Assert-False "workbench: CLI run" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main run'))

Assert-False "workbench: monitor" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main monitor --interval 60'))

Assert-False "workbench: module without subcommand" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main'))

Assert-False "workbench: subcommand prefix (webhook)" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main webhook'))

Assert-False "workbench: pytest run" (Test-WorkbenchCommandLine -CommandLine (
		'"D:\repo\BossHunter\.venv\Scripts\python.exe" -m pytest tests/test_web.py'))

Assert-False "workbench: unrelated node cdp-proxy" (Test-WorkbenchCommandLine -CommandLine (
		'node.exe "D:\other-project\cdp-proxy.js"'))

Assert-False "workbench: empty command line" (Test-WorkbenchCommandLine -CommandLine "")

# ── Chrome: exact --user-data-dir, not a URL that mentions the profile ────

Assert-True "chrome: quoted profile path with spaces" (Test-ChromeProfileCommandLine `
		-CommandLine ('"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="{0}" http://127.0.0.1:8686' -f $ChromeProfile) `
		-ExpectedProfile $ChromeProfile)

Assert-True "chrome: unquoted profile path" (Test-ChromeProfileCommandLine `
		-CommandLine ("chrome.exe --user-data-dir={0}" -f $ChromeProfile) `
		-ExpectedProfile $ChromeProfile)

Assert-True "chrome: lowercase command line" (Test-ChromeProfileCommandLine `
		-CommandLine ('chrome.exe --user-data-dir=C:\Users\Ada Lovelace\AppData\Local\Bosshunterchrome') `
		-ExpectedProfile $ChromeProfile)

Assert-False "chrome: page URL contains the profile name" (Test-ChromeProfileCommandLine `
		-CommandLine ('"C:\Program Files\Google\Chrome\Application\chrome.exe" https://github.com/search?q=BossHunterChrome') `
		-ExpectedProfile $ChromeProfile)

Assert-False "chrome: default profile" (Test-ChromeProfileCommandLine `
		-CommandLine ('chrome.exe --user-data-dir="C:\Users\Ada Lovelace\AppData\Local\Google\Chrome\User Data"') `
		-ExpectedProfile $ChromeProfile)

Assert-False "chrome: no user-data-dir" (Test-ChromeProfileCommandLine `
		-CommandLine ('chrome.exe --remote-debugging-port=9222 https://www.zhipin.com') `
		-ExpectedProfile $ChromeProfile)

Assert-False "chrome: sibling profile sharing the prefix" (Test-ChromeProfileCommandLine `
		-CommandLine ('chrome.exe --user-data-dir=C:\Users\Ada Lovelace\AppData\Local\BossHunterChrome2') `
		-ExpectedProfile $ChromeProfile)

Assert-True "chrome: value ends the command line" (Test-ChromeProfileCommandLine `
		-CommandLine ('chrome.exe --user-data-dir={0}' -f $ChromeProfile) `
		-ExpectedProfile $ChromeProfile)

# ── Launcher: exact -File target, not any command line mentioning it ─────

Assert-True "launcher: shortcut command line" (Test-LauncherCommandLine `
		-CommandLine ('powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $LauncherPath) `
		-LauncherPath $LauncherPath)

Assert-True "launcher: unquoted -File" (Test-LauncherCommandLine `
		-CommandLine ("powershell.exe -File {0}" -f $LauncherPath) `
		-LauncherPath $LauncherPath)

Assert-False "launcher: command line that mentions the script" (Test-LauncherCommandLine `
		-CommandLine 'pwsh.exe -NoProfile -Command "Get-Content .\scripts\windows\start_bosshunter.ps1"' `
		-LauncherPath $LauncherPath)

Assert-False "launcher: same file name, other checkout" (Test-LauncherCommandLine `
		-CommandLine ('powershell.exe -File "{0}"' -f (Join-Path $OtherRepo "scripts\windows\start_bosshunter.ps1")) `
		-LauncherPath $LauncherPath)

Assert-False "launcher: the stop script itself" (Test-LauncherCommandLine `
		-CommandLine ('powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File "{0}"' -f (Join-Path $RepoRoot "scripts\windows\stop_bosshunter.ps1")) `
		-LauncherPath $LauncherPath)

# ── Repository containment (secondary anchor for a second workbench) ─────

Assert-True "repo: interpreter inside this checkout" (Test-CommandLineFromRepo `
		-CommandLine ('"D:\repo\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main web --no-open') `
		-RepoRoot $RepoRoot)

Assert-True "repo: forward slashes" (Test-CommandLineFromRepo `
		-CommandLine ('D:/repo/BossHunter/.venv/Scripts/python.exe -m bosshunter.main web') `
		-RepoRoot $RepoRoot)

Assert-False "repo: sibling directory sharing the prefix" (Test-CommandLineFromRepo `
		-CommandLine ('"D:\repo\BossHunter2\.venv\Scripts\python.exe" -m bosshunter.main web') `
		-RepoRoot $RepoRoot)

Assert-False "repo: another checkout" (Test-CommandLineFromRepo `
		-CommandLine ('"D:\other\BossHunter\.venv\Scripts\python.exe" -m bosshunter.main web') `
		-RepoRoot $RepoRoot)

if ($script:Failures.Count -gt 0) {
	foreach ($failure in $script:Failures) {
		Write-Host ("FAIL  {0}" -f $failure)
	}
	Write-Host ("{0}/{1} checks passed." -f ($script:Checks - $script:Failures.Count), $script:Checks)
	exit 1
}

Write-Host ("{0}/{0} checks passed. No process was inspected or stopped." -f $script:Checks)
