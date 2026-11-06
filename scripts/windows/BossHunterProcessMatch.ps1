# Pure process-matching helpers shared by the Windows launcher, the stop script
# and the offline tests. Every function takes the values it needs as parameters,
# so the matching rules can be exercised without touching the real process table.
#
# Matching is deliberately narrow: a process only counts as a BossHunter target
# when the command line proves what it is. Broad name or substring sweeps are
# avoided so that unrelated Python, Node or PowerShell processes are never
# force-stopped.

function Get-NormalizedPath {
	param([string]$Path)

	if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
	$value = $Path.Trim().Trim('"').TrimEnd('\', '/')
	if ($value -eq "") { return "" }
	try {
		return [IO.Path]::GetFullPath($value).TrimEnd('\', '/')
	} catch {
		return $value
	}
}

function Test-WorkbenchCommandLine {
	<#
	.synopsis
	True when the command line runs the local workbench (`... web`), not a CLI
	subcommand such as scrape / run / monitor.
	#>
	param([string]$CommandLine)

	if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
	$value = $CommandLine.Replace('"', '')
	# python -m bosshunter.main web --no-open
	if ($value -match '-m\s+bosshunter\.main\s+web(?:\s|$)') { return $true }
	# <repo>\.venv\Scripts\bosshunter.exe web --no-open
	return ($value -match 'bosshunter(?:\.exe)?\s+web(?:\s|$)')
}

function Test-ChromeProfileCommandLine {
	<#
	.synopsis
	True only when --user-data-dir is exactly the dedicated profile. Chrome quotes
	the value when the path contains spaces, and some launchers pass it unquoted,
	so the expected path is matched as a value boundary instead of a substring of
	the whole command line.
	#>
	param([string]$CommandLine, [string]$ExpectedProfile)

	if ([string]::IsNullOrWhiteSpace($ExpectedProfile)) { return $false }
	if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }

	$expected = Get-NormalizedPath $ExpectedProfile
	$index = $CommandLine.IndexOf('--user-data-dir=', [StringComparison]::OrdinalIgnoreCase)
	if ($index -lt 0) { return $false }

	$value = $CommandLine.Substring($index + '--user-data-dir='.Length).TrimStart('"')
	if ($value.Length -lt $expected.Length) { return $false }
	if (-not $value.StartsWith($expected, [StringComparison]::OrdinalIgnoreCase)) { return $false }
	if ($value.Length -eq $expected.Length) { return $true }

	# The value must end there: `BossHunterChrome2` is a different profile.
	$boundary = $value[$expected.Length]
	return ($boundary -eq '"' -or [char]::IsWhiteSpace($boundary))
}

function Get-LauncherScriptPath {
	<#
	.synopsis
	Extract the -File argument of a PowerShell invocation.
	#>
	param([string]$CommandLine)

	if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $null }
	$match = [regex]::Match($CommandLine, '(?:^|\s)-file\s+(?:"([^"]+)"|(\S+))', 'IgnoreCase')
	if (-not $match.Success) { return $null }
	if ($match.Groups[1].Success) { return $match.Groups[1].Value }
	return $match.Groups[2].Value
}

function Test-LauncherCommandLine {
	param([string]$CommandLine, [string]$LauncherPath)

	if ([string]::IsNullOrWhiteSpace($LauncherPath)) { return $false }
	$actual = Get-LauncherScriptPath -CommandLine $CommandLine
	if (-not $actual) { return $false }
	return ((Get-NormalizedPath $actual) -eq (Get-NormalizedPath $LauncherPath))
}

function Test-CommandLineFromRepo {
	<#
	.synopsis
	True when the command line points inside this checkout (interpreter path is
	the usual carrier). Used as a secondary anchor so a second workbench from the
	same checkout is still found, while another checkout is left alone.
	#>
	param([string]$CommandLine, [string]$RepoRoot)

	$root = Get-NormalizedPath $RepoRoot
	if (-not $root) { return $false }
	if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
	# Require a path separator after the root so a sibling such as
	# ...\BossHunter2 is not treated as this checkout.
	$haystack = $CommandLine.Replace('"', '').Replace('/', '\')
	return ($haystack.IndexOf($root + '\', [StringComparison]::OrdinalIgnoreCase) -ge 0)
}
