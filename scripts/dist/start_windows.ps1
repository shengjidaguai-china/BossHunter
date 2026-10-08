# BossHunter portable launcher (Windows).
# Bundled Python, dependencies, frontend assets, and a Node.js runtime
# (via patchright's bundled driver) live inside this directory. No Git,
# pip, npm, or system Python is required.
[CmdletBinding()]
param(
	[switch]$SkipChrome
)

$ErrorActionPreference = "Stop"
$DistRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$PythonExe = Join-Path $DistRoot "python\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
	throw "Bundled Python was not found: $PythonExe. The distribution package may be incomplete."
}

# patchright ships a private Node.js runtime; point BossHunter at it so the
# Browser Runtime (.mjs) works without a system Node.js installation.
$BundledNode = Join-Path $DistRoot "python\Lib\site-packages\patchright\driver\node.exe"
if (Test-Path -LiteralPath $BundledNode) {
	$env:BOSSHUNTER_NODE_PATH = $BundledNode
}

# Data (config.yaml, data/) is stored in the distribution directory and
# survives restarts and version upgrades.
Set-Location -LiteralPath $DistRoot

$ChromeCandidates = @()
if ($env:ProgramFiles) {
	$ChromeCandidates += Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"
}
if (${env:ProgramFiles(x86)}) {
	$ChromeCandidates += Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"
}
if ($env:LOCALAPPDATA) {
	$ChromeCandidates += Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe"
}
$ChromeCandidates = $ChromeCandidates | Where-Object { Test-Path -LiteralPath $_ }

if (-not $ChromeCandidates) {
	Write-Warning "Google Chrome was not found. BossHunter needs Chrome with remote debugging to collect jobs. Install Chrome from https://www.google.com/chrome/ and start this launcher again."
	Write-Host "Opening the workbench without Chrome setup. You can retry after installing Chrome."
	$SkipChrome = $true
} else {
	$Chrome = $ChromeCandidates | Select-Object -First 1
	$ChromeProfile = Join-Path $env:LOCALAPPDATA "BossHunterChrome"
}

if (-not $SkipChrome) {
	# Reuse an already-running BossHunter Chrome profile instead of spawning a duplicate.
	$ChromeRunning = $false
	try {
		$null = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 2
		$ChromeRunning = $true
	} catch {
		# Chrome is not running yet.
	}
	if (-not $ChromeRunning) {
		Write-Host "Starting the BossHunter Chrome profile..."
		Start-Process -FilePath $Chrome -ArgumentList @(
			"--remote-debugging-port=9222",
			"--user-data-dir=$ChromeProfile",
			"https://www.zhipin.com"
		)
		$ChromeReady = $false
		for ($i = 0; $i -lt 20; $i++) {
			Start-Sleep -Milliseconds 500
			try {
				$null = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 2
				$ChromeReady = $true
				break
			} catch {
				# Chrome is still starting.
			}
		}
		if (-not $ChromeReady) {
			Write-Warning "Chrome remote debugging did not become ready within 10 seconds."
		}
	}
}

if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 8686 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
	Write-Host "Starting the local workbench..."
	$WebArguments = @("-m", "bosshunter.main", "web", "--no-open")
	Start-Process -FilePath $PythonExe -ArgumentList $WebArguments -WorkingDirectory $DistRoot -WindowStyle Hidden

	$WebReady = $false
	for ($i = 0; $i -lt 30; $i++) {
		Start-Sleep -Milliseconds 500
		try {
			$null = Invoke-WebRequest -Uri "http://127.0.0.1:8686/" -UseBasicParsing -TimeoutSec 2
			$WebReady = $true
			break
		} catch {
			# The local server is still starting.
		}
	}
	if (-not $WebReady) {
		Write-Warning "The workbench did not become ready within 15 seconds. Check whether port 8686 is occupied by another program."
	}
} else {
	Write-Host "The workbench is already running at http://127.0.0.1:8686 — reusing it."
}

if (-not $SkipChrome) {
	Start-Process -FilePath $Chrome -ArgumentList @(
		"--remote-debugging-port=9222",
		"--user-data-dir=$ChromeProfile",
		"http://127.0.0.1:8686"
	)
}

Write-Host "BossHunter is ready. Log in manually in the dedicated Chrome window if needed."