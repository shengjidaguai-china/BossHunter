# Stops what the desktop launcher started: the local workbench, the browser runtime
# proxy (cdp-proxy), the dedicated BossHunterChrome browser, and any launcher still
# running. The launcher starts these processes detached and windowless, so closing
# the web page or the Chrome windows leaves them running.
#
# Targets are identified by ownership instead of broad name sweeps, so unrelated
# Python / Node / PowerShell / Chrome processes are never force-stopped:
#   launcher  - powershell whose -File is exactly this repository's launcher
#   workbench - the process listening on 8686 whose command line runs `... web`
#   runtime   - the port owner of a Browser Runtime port that answers /health
#   chrome    - chrome.exe whose --user-data-dir is exactly the dedicated profile
#
# The companion desktop shortcut ("BossHunter Stop") is installed by
# install_desktop_shortcut.ps1.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "BossHunterProcessMatch.ps1")

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LauncherPath = Join-Path $PSScriptRoot "start_bosshunter.ps1"
$ChromeProfile = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "BossHunterChrome" } else { "" }
$WebPort = 8686
$ChromeDebugPort = 9222
$RuntimePortRange = 3456..3556
$StopTimeoutMs = 2000

$script:RuntimePorts = @()

function Get-ProcessCommandLine {
	param([int]$ProcessId)

	try {
		$proc = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $ProcessId) -ErrorAction Stop
	} catch {
		return $null
	}
	if (-not $proc) { return $null }
	return [pscustomobject]@{
		ProcessId   = [int]$proc.ProcessId
		Name        = [string]$proc.Name
		CommandLine = [string]$proc.CommandLine
	}
}

function New-Target {
	param([int]$ProcessId, [string]$Name, [string]$Kind)

	return [pscustomobject]@{
		ProcessId = $ProcessId
		Name      = $Name
		Kind      = $Kind
	}
}

function Get-ListeningPids {
	param([int]$Port)

	try {
		return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
				Select-Object -ExpandProperty OwningProcess -Unique)
	} catch {
		return @()
	}
}

function Get-LauncherTargets {
	$targets = @()
	try {
		$procs = @(Get-CimInstance Win32_Process -ErrorAction Stop |
				Where-Object { $_.Name -in @("powershell.exe", "pwsh.exe") })
	} catch {
		Write-Warning ("Could not enumerate processes: {0}" -f $_.Exception.Message)
		return $targets
	}
	foreach ($proc in $procs) {
		if ([int]$proc.ProcessId -eq $PID) { continue }
		if (-not (Test-LauncherCommandLine -CommandLine ([string]$proc.CommandLine) -LauncherPath $LauncherPath)) { continue }
		$targets += (New-Target -ProcessId ([int]$proc.ProcessId) -Name ([string]$proc.Name) -Kind "launcher")
	}
	return $targets
}

function Get-WorkbenchTargets {
	$targets = @()
	$seen = @{}

	# The process holding 8686 is the workbench the panel talks to. Verify it
	# really runs `... web` before stopping it; a foreign service on that port is
	# reported instead of killed.
	foreach ($procId in (Get-ListeningPids -Port $WebPort)) {
		$proc = Get-ProcessCommandLine -ProcessId $procId
		if (-not $proc) { continue }
		if (-not (Test-WorkbenchCommandLine -CommandLine $proc.CommandLine)) {
			Write-Warning ("Port {0} is held by {1} (PID {2}), which is not the BossHunter workbench. Leaving it alone." -f $WebPort, $proc.Name, $proc.ProcessId)
			continue
		}
		$seen[$proc.ProcessId] = $true
		$targets += (New-Target -ProcessId $proc.ProcessId -Name $proc.Name -Kind "workbench")
	}

	# A second workbench from this checkout can lose the port race while still
	# holding the database open, so stop it too. Other checkouts are out of scope.
	try {
		$procs = @(Get-CimInstance Win32_Process -ErrorAction Stop |
				Where-Object { $_.Name -in @("python.exe", "pythonw.exe", "bosshunter.exe") })
	} catch {
		return $targets
	}
	foreach ($proc in $procs) {
		if ($seen.ContainsKey([int]$proc.ProcessId)) { continue }
		if (-not (Test-WorkbenchCommandLine -CommandLine ([string]$proc.CommandLine))) { continue }
		if (-not (Test-CommandLineFromRepo -CommandLine ([string]$proc.CommandLine) -RepoRoot $RepoRoot)) { continue }
		$seen[[int]$proc.ProcessId] = $true
		$targets += (New-Target -ProcessId ([int]$proc.ProcessId) -Name ([string]$proc.Name) -Kind "workbench")
	}
	return $targets
}

function Test-RuntimeHealth {
	param([int]$Port)

	try {
		$health = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $Port) -TimeoutSec 1 -ErrorAction Stop
	} catch {
		return $false
	}
	return ($health.status -eq "ok" -and $health.runtime -eq "bosshunter")
}

function Get-RuntimeTargets {
	$targets = @()

	# The runtime port comes from config.yaml and shifts to a free port when the
	# configured one is taken, so discover it from the health endpoint instead of
	# assuming 3456.
	try {
		$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
				Where-Object { $_.LocalPort -in $RuntimePortRange })
	} catch {
		Write-Warning ("Could not inspect listening ports: {0}" -f $_.Exception.Message)
		return $targets
	}
	foreach ($conn in $listeners) {
		$proc = Get-ProcessCommandLine -ProcessId $conn.OwningProcess
		if (-not $proc -or $proc.Name -ne "node.exe") { continue }
		if (-not (Test-RuntimeHealth -Port $conn.LocalPort)) { continue }
		if ($script:RuntimePorts -contains $conn.LocalPort) { continue }
		$script:RuntimePorts += $conn.LocalPort
		$targets += (New-Target -ProcessId $proc.ProcessId -Name "node.exe" -Kind ("runtime on port {0}" -f $conn.LocalPort))
	}
	return $targets
}

function Get-ChromeTargets {
	$targets = @()
	if (-not $ChromeProfile) { return $targets }
	try {
		$procs = @(Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" -ErrorAction Stop)
	} catch {
		return $targets
	}
	foreach ($proc in $procs) {
		if (-not (Test-ChromeProfileCommandLine -CommandLine ([string]$proc.CommandLine) -ExpectedProfile $ChromeProfile)) { continue }
		$targets += (New-Target -ProcessId ([int]$proc.ProcessId) -Name "chrome.exe" -Kind "dedicated Chrome")
	}
	return $targets
}

function Stop-BossHunterTargets {
	param([object[]]$Targets)

	foreach ($target in $Targets) {
		if (-not (Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue)) { continue }
		Write-Host ("Stopping {0} ({1}, PID {2})..." -f $target.Kind, $target.Name, $target.ProcessId)
		try {
			Stop-Process -Id $target.ProcessId -Force -ErrorAction Stop
		} catch {
			# A parent workbench can take its child down with it, so a vanished
			# process is a success rather than a failed stop.
			if (Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue) {
				Write-Warning ("Failed to stop PID {0}: {1}" -f $target.ProcessId, $_.Exception.Message)
			}
		}
	}
}

# Stop the launcher first: a launcher still in its startup window would otherwise
# spawn a fresh workbench right after the rest is gone. Re-enumerating afterwards
# covers whatever it managed to start in the meantime.
$LauncherTargets = @(Get-LauncherTargets)
$AllTargets = @($LauncherTargets)
Stop-BossHunterTargets -Targets $LauncherTargets
if ($LauncherTargets.Count -gt 0) {
	Start-Sleep -Milliseconds 200
}

$RemainingTargets = @()
$RemainingTargets += @(Get-WorkbenchTargets)
$RemainingTargets += @(Get-RuntimeTargets)
$RemainingTargets += @(Get-ChromeTargets)
$AllTargets += @($RemainingTargets)
Stop-BossHunterTargets -Targets $RemainingTargets

$Survivors = @()

if ($AllTargets.Count -eq 0) {
	Write-Host "BossHunter is not running."
} else {
	# Chrome and the workbench take a moment to release their sockets, so allow a
	# bounded grace period instead of a single fixed sleep.
	$deadline = (Get-Date).AddMilliseconds($StopTimeoutMs)
	do {
		$Survivors = @($AllTargets | Where-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue })
		if ($Survivors.Count -eq 0) { break }
		Start-Sleep -Milliseconds 250
	} while ((Get-Date) -lt $deadline)

	foreach ($proc in $Survivors) {
		Write-Warning ("PID {0} ({1}) is still running." -f $proc.ProcessId, $proc.Name)
	}
}

$PortsToCheck = @($WebPort, $ChromeDebugPort) + $script:RuntimePorts
$Busy = @()
foreach ($port in ($PortsToCheck | Select-Object -Unique)) {
	foreach ($procId in (Get-ListeningPids -Port $port)) {
		$Busy += [pscustomobject]@{ Port = $port; ProcessId = $procId }
	}
}

if ($Busy.Count -gt 0) {
	foreach ($conn in $Busy) {
		$owner = Get-ProcessCommandLine -ProcessId $conn.ProcessId
		$name = if ($owner) { $owner.Name } else { "unknown" }
		Write-Warning ("Port {0} is still held by {1} (PID {2})." -f $conn.Port, $name, $conn.ProcessId)
	}
} else {
	Write-Host ("Ports {0} are free. BossHunter is stopped." -f (($PortsToCheck | Select-Object -Unique) -join " / "))
}
