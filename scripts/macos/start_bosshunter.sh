#!/bin/bash
# BossHunter macOS one-click launcher.
# Mirrors scripts/windows/start_bosshunter.ps1:
#   dedicated Chrome debug profile -> Browser Runtime connect check -> local workbench.
#
# Usage: ./start_bosshunter.sh [--skip-chrome] [--python-path /path/to/python]

set -u

SKIP_CHROME=0
CUSTOM_PYTHON=""

while [ "$#" -gt 0 ]; do
	case "$1" in
		--skip-chrome)
			SKIP_CHROME=1
			;;
		--python-path)
			if [ "$#" -lt 2 ]; then
				echo "[BossHunter] --python-path requires a value." >&2
				exit 1
			fi
			CUSTOM_PYTHON="$2"
			shift
			;;
		*)
			echo "[BossHunter] Unknown argument: $1" >&2
			exit 1
			;;
	esac
	shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Resolve how to invoke bosshunter: CLI command first, then explicit venv Python,
# then python3 on PATH (run as `python3 -m bosshunter.main`). Arrays keep
# interpreters and repository paths that contain spaces intact across calls.
RUNNER=()
RUNNER_PREFIX=()
if [ -n "$CUSTOM_PYTHON" ]; then
	if [ ! -x "$CUSTOM_PYTHON" ]; then
		echo "[BossHunter] Configured Python was not found: $CUSTOM_PYTHON" >&2
		exit 1
	fi
	RUNNER=("$CUSTOM_PYTHON")
	RUNNER_PREFIX=(-m bosshunter.main)
elif command -v bosshunter >/dev/null 2>&1; then
	RUNNER=("$(command -v bosshunter)")
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
	# Projects installed inside the repository venv are only importable there.
	RUNNER=("$REPO_ROOT/.venv/bin/python")
	RUNNER_PREFIX=(-m bosshunter.main)
elif command -v python3 >/dev/null 2>&1; then
	RUNNER=("$(command -v python3)")
	RUNNER_PREFIX=(-m bosshunter.main)
else
	echo "[BossHunter] Could not find BossHunter or Python. Install the project first: see docs/QUICKSTART.md (macOS install section)." >&2
	exit 1
fi

# Locate Google Chrome. `open -na` is the documented launch path; BOSS_HUNTER_CHROME
# can point to an alternative .app bundle or Chrome binary for non-standard setups.
CHROME_APP="Google Chrome"
if [ -n "${BOSS_HUNTER_CHROME:-}" ]; then
	CHROME_APP="$BOSS_HUNTER_CHROME"
	if [ ! -e "$CHROME_APP" ]; then
		echo "[BossHunter] BOSS_HUNTER_CHROME does not exist: $CHROME_APP" >&2
		exit 1
	fi
elif [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "$HOME/Applications/Google Chrome.app" ]; then
	echo "[BossHunter] Could not find Google Chrome. Install Chrome or set BOSS_HUNTER_CHROME to the app path." >&2
	exit 1
fi

launch_chrome() {
	# `open -na` accepts an app name or a .app path and detaches the instance
	# from this terminal, so closing the shell will not kill the debug Chrome.
	open -na "$CHROME_APP" --args "$@"
}

# Chrome 136+ ignores --remote-debugging-port on the DEFAULT profile, so a
# dedicated --user-data-dir is mandatory. Reuse it for the workbench tab too.
CHROME_PROFILE="$HOME/.bosshunter-chrome"
DEBUG_URL="http://127.0.0.1:9222/json/version"
WORKBENCH_URL="http://127.0.0.1:8686/"

if [ "$SKIP_CHROME" -eq 0 ]; then
	echo "[BossHunter] Starting the BossHunter Chrome profile..."
	launch_chrome \
		--remote-debugging-port=9222 \
		--user-data-dir="$CHROME_PROFILE" \
		"https://www.zhipin.com"

	CHROME_READY=0
	for _ in $(seq 1 20); do
		sleep 0.5
		if curl -s --max-time 2 "$DEBUG_URL" >/dev/null 2>&1; then
			CHROME_READY=1
			break
		fi
	done
	if [ "$CHROME_READY" -eq 0 ]; then
		echo "[BossHunter] Warning: Chrome remote debugging did not become ready within 10 seconds." >&2
		echo "[BossHunter] If Chrome was already running with your normal profile, quit it fully and re-run this script." >&2
	fi
fi

echo "[BossHunter] Starting the Browser Runtime..."
if ! "${RUNNER[@]}" "${RUNNER_PREFIX[@]}" connect; then
	echo "[BossHunter] Warning: browser connection check failed with ${RUNNER[0]}; the workbench will still be opened." >&2
fi

echo "[BossHunter] Starting the local workbench..."
cd "$REPO_ROOT" && nohup "${RUNNER[@]}" "${RUNNER_PREFIX[@]}" web --no-open >/dev/null 2>&1 &

WEB_READY=0
for _ in $(seq 1 20); do
	sleep 0.5
	if curl -s --max-time 2 "$WORKBENCH_URL" >/dev/null 2>&1; then
		WEB_READY=1
		break
	fi
done
if [ "$WEB_READY" -eq 0 ]; then
	echo "[BossHunter] Warning: the workbench did not answer on $WORKBENCH_URL within 10 seconds (runner: ${RUNNER[0]})." >&2
fi

if [ "$SKIP_CHROME" -eq 0 ]; then
	# Same --user-data-dir reuses the running debug instance, so the workbench
	# opens inside the BossHunter Chrome profile window.
	launch_chrome \
		--remote-debugging-port=9222 \
		--user-data-dir="$CHROME_PROFILE" \
		"$WORKBENCH_URL"
fi

echo "[BossHunter] BossHunter is ready. Log in manually in the dedicated Chrome window if needed."
