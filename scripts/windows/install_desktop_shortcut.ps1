[CmdletBinding()]
param(
	[string]$ShortcutName = "BossHunter"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Launcher = Join-Path $PSScriptRoot "start_bosshunter.ps1"
$Stopper = Join-Path $PSScriptRoot "stop_bosshunter.ps1"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "$ShortcutName.lnk"
$PowerShell = Join-Path $PSHOME "powershell.exe"
$IconPath = Join-Path $RepoRoot "assets\bosshunter.ico"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Launcher`""
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Start the BossHunter Chrome profile and local workbench"
if (Test-Path -LiteralPath $IconPath) {
	$Shortcut.IconLocation = "$IconPath,0"
}
$Shortcut.Save()

Write-Host "Created desktop shortcut: $ShortcutPath"

# The stop shortcut opens a visible window so the shutdown summary stays readable.
$StopShortcutPath = Join-Path $Desktop "$ShortcutName Stop.lnk"
$StopShortcut = $Shell.CreateShortcut($StopShortcutPath)
$StopShortcut.TargetPath = $PowerShell
$StopShortcut.Arguments = "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$Stopper`""
$StopShortcut.WorkingDirectory = $RepoRoot
$StopShortcut.Description = "Stop the BossHunter workbench, browser runtime, and dedicated Chrome profile"
if (Test-Path -LiteralPath $IconPath) {
	$StopShortcut.IconLocation = "$IconPath,0"
}
$StopShortcut.Save()

Write-Host "Created desktop shortcut: $StopShortcutPath"
