[CmdletBinding()]
param(
	[switch]$SkipChrome,
	[string]$PythonPath
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

. (Join-Path $PSScriptRoot "BossHunterProcessMatch.ps1")

# One workbench only: it owns port 8686 and the database. A second copy cannot
# serve a second panel (both would bind the same port) and would share the same
# config.yaml and jobs.db without coordination, so it is refused up front.
$WebPort = 8686
$WorkbenchUrl = "http://127.0.0.1:$WebPort"

function Get-WorkbenchOwner {
	try {
		$listeners = @(Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction Stop)
	} catch {
		return $null
	}
	foreach ($conn in $listeners) {
		try {
			$proc = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $conn.OwningProcess) -ErrorAction Stop
		} catch {
			continue
		}
		if ($proc -and (Test-WorkbenchCommandLine -CommandLine ([string]$proc.CommandLine))) {
			return $proc
		}
	}
	return $null
}

function Test-WorkbenchHttp {
	try {
		$health = Invoke-RestMethod -Uri ("{0}/api/health" -f $WorkbenchUrl) -TimeoutSec 2 -ErrorAction Stop
	} catch {
		return $false
	}
	return ($health.status -eq "ok")
}

if ($PythonPath) {
	if (-not (Test-Path -LiteralPath $PythonPath)) {
		throw "Configured Python was not found: $PythonPath"
	}
	$Runner = (Resolve-Path -LiteralPath $PythonPath).Path
	$RunnerPrefix = @("-m", "bosshunter.main")
} else {
	# Resolve how to invoke bosshunter, mirroring scripts/macos/start_bosshunter.sh:
	# the CLI command on PATH first, then the repository virtual environment, then
	# Python on PATH (run as `python -m bosshunter.main`).
	$Bosshunter = Get-Command "bosshunter" -ErrorAction SilentlyContinue
	$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
	if ($Bosshunter) {
		$Runner = $Bosshunter.Source
		$RunnerPrefix = @()
	} elseif (Test-Path -LiteralPath $VenvPython) {
		# A project installed inside the repository venv is only importable there.
		$Runner = $VenvPython
		$RunnerPrefix = @("-m", "bosshunter.main")
	} else {
		$Python = Get-Command "py" -ErrorAction SilentlyContinue
		if (-not $Python) {
			$Python = Get-Command "python" -ErrorAction SilentlyContinue
		}
		if (-not $Python) {
			throw "Could not find BossHunter or Python. Install the project first with: pip install -e ."
		}
		$Runner = $Python.Source
		$RunnerPrefix = @("-m", "bosshunter.main")
	}
}

$Workbench = Get-WorkbenchOwner
if (-not $Workbench) {
	$Busy = @(Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue)
	if ($Busy.Count -gt 0) {
		throw ("Port {0} is already used by another program (PID {1}). Close it before starting BossHunter." -f $WebPort, $Busy[0].OwningProcess)
	}
}

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
	throw "Could not find Google Chrome. Install Chrome or set up a compatible browser manually."
}

$Chrome = $ChromeCandidates | Select-Object -First 1
$ChromeProfile = Join-Path $env:LOCALAPPDATA "BossHunterChrome"
$ChromeArguments = @(
	"--remote-debugging-port=9222",
	"--user-data-dir=$ChromeProfile",
	"https://www.zhipin.com"
)

if (-not $SkipChrome) {
	$ChromeRunning = $false
	try {
		$null = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 2
		$ChromeRunning = $true
	} catch {
		# Chrome is not running yet.
	}
	if ($ChromeRunning) {
		Write-Host "Reusing the running BossHunter Chrome profile..."
	} else {
		Write-Host "Starting the BossHunter Chrome profile..."
		Start-Process -FilePath $Chrome -ArgumentList $ChromeArguments
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

if ($Workbench) {
	Write-Host ("The local workbench is already running at {0} (PID {1}). Reusing it." -f $WorkbenchUrl, $Workbench.ProcessId)
} else {
	Write-Host "Starting the Browser Runtime..."
	& $Runner @RunnerPrefix "connect"
	if ($LASTEXITCODE -ne 0) {
		Write-Warning "Browser connection check returned exit code $LASTEXITCODE. The workbench will still be opened."
	}

	Write-Host "Starting the local workbench..."
	$WebArguments = @($RunnerPrefix) + @("web", "--no-open")
	$WebProcess = Start-Process -FilePath $Runner -ArgumentList $WebArguments -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru

	# Wait on the process this launcher started. Probing the port alone would be
	# satisfied by a workbench that won the race, hiding a child that just died.
	$WebReady = $false
	for ($i = 0; $i -lt 20; $i++) {
		Start-Sleep -Milliseconds 500
		if ($WebProcess.HasExited) {
			# The venv trampoline does not report the child's exit code, so point at
			# the likely cause instead of printing a number that may be wrong.
			throw ("The local workbench exited during startup. Check that port {0} is free and that 'bosshunter web' starts on its own." -f $WebPort)
		}
		if (Test-WorkbenchHttp) {
			$WebReady = $true
			break
		}
	}
	if (-not $WebReady) {
		throw ("The local workbench did not answer {0}/api/health within 10 seconds." -f $WorkbenchUrl)
	}
}

if (-not $SkipChrome) {
	Start-Process -FilePath $Chrome -ArgumentList @(
		"--remote-debugging-port=9222",
		"--user-data-dir=$ChromeProfile",
		"http://127.0.0.1:8686"
	)
}

Write-Host "BossHunter is ready. Log in manually in the dedicated Chrome window if needed."
