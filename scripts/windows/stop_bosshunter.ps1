# Stops what the desktop launcher started: the local workbench, the browser runtime
# proxy (cdp-proxy), the dedicated BossHunterChrome browser, and any launcher still
# running. The launcher starts these processes detached and windowless, so closing
# the web page or the Chrome windows leaves them running.
#
# The companion desktop shortcut ("BossHunter Stop") is installed by
# install_desktop_shortcut.ps1.

$ErrorActionPreference = "Stop"
$Ports = @(3456, 8686, 9222)

$Targets = @(Get-CimInstance Win32_Process | Where-Object {
		$name = $_.Name
		$cmd = [string]$_.CommandLine
		($name -eq "chrome.exe" -and $cmd -like "*BossHunterChrome*") -or
		($name -eq "node.exe" -and $cmd -like "*cdp-proxy*") -or
		($name -in @("powershell.exe", "pwsh.exe") -and $cmd -like "*start_bosshunter.ps1*") -or
		$name -eq "bosshunter.exe" -or
		($name -in @("python.exe", "pythonw.exe") -and $cmd -like "*bosshunter.main*")
	})

if ($Targets.Count -eq 0) {
	Write-Host "BossHunter is not running."
} else {
	foreach ($proc in $Targets) {
		Write-Host ("Stopping {0} (PID {1})..." -f $proc.Name, $proc.ProcessId)
		try {
			Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
		} catch {
			Write-Warning ("Failed to stop PID {0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
		}
	}
}

Start-Sleep -Milliseconds 500
$Busy = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
		Where-Object { $_.LocalPort -in $Ports })

if ($Busy.Count -gt 0) {
	foreach ($conn in $Busy) {
		Write-Warning ("Port {0} is still held by PID {1}." -f $conn.LocalPort, $conn.OwningProcess)
	}
} else {
	Write-Host "Ports 3456 / 8686 / 9222 are free. BossHunter is stopped."
}
