#!/bin/bash
# BossHunter portable launcher (macOS).
# Bundled Python, dependencies, frontend assets, and a Node.js runtime
# (via patchright's bundled driver) live inside this directory. No Git,
# pip, npm, or system Python is required.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_ROOT="$(dirname "$SCRIPT_DIR")"

PYTHON_EXE="$DIST_ROOT/python/bin/python3"
if [ ! -x "$PYTHON_EXE" ]; then
    echo "Bundled Python was not found: $PYTHON_EXE" >&2
    echo "The distribution package may be incomplete." >&2
    exit 1
fi

# patchright ships a private Node.js runtime; point BossHunter at it so the
# Browser Runtime (.mjs) works without a system Node.js installation.
BUNDLED_NODE="$DIST_ROOT/python/lib/python3.12/site-packages/patchright/driver/node"
if [ -x "$BUNDLED_NODE" ]; then
    export BOSSHUNTER_NODE_PATH="$BUNDLED_NODE"
fi

# Data (config.yaml, data/) is stored in the distribution directory and
# survives restarts and version upgrades.
cd "$DIST_ROOT"

CHROME_CANDIDATES=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
CHROME=""
for candidate in "${CHROME_CANDIDATES[@]}"; do
    if [ -x "$candidate" ]; then
        CHROME="$candidate"
        break
    fi
done

SKIP_CHROME=0
if [ -z "$CHROME" ]; then
    echo "Warning: Google Chrome was not found. BossHunter needs Chrome with remote debugging to collect jobs." >&2
    echo "Install Chrome from https://www.google.com/chrome/ and start this launcher again." >&2
    SKIP_CHROME=1
fi
CHROME_PROFILE="$HOME/Library/Application Support/BossHunterChrome"

if [ "$SKIP_CHROME" -eq 0 ]; then
    CHROME_RUNNING=0
    if curl -s --max-time 2 "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
        CHROME_RUNNING=1
    fi
    if [ "$CHROME_RUNNING" -eq 0 ]; then
        echo "Starting the BossHunter Chrome profile..."
        "$CHROME" --remote-debugging-port=9222 --user-data-dir="$CHROME_PROFILE" "https://www.zhipin.com" >/dev/null 2>&1 &
        CHROME_READY=0
        for _ in $(seq 1 20); do
            sleep 0.5
            if curl -s --max-time 2 "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
                CHROME_READY=1
                break
            fi
        done
        if [ "$CHROME_READY" -eq 0 ]; then
            echo "Warning: Chrome remote debugging did not become ready within 10 seconds." >&2
        fi
    fi
fi

if ! curl -s --max-time 2 "http://127.0.0.1:8686/" >/dev/null 2>&1; then
    echo "Starting the local workbench..."
    nohup "$PYTHON_EXE" -m bosshunter.main web --no-open >/dev/null 2>&1 &
    WEB_READY=0
    for _ in $(seq 1 30); do
        sleep 0.5
        if curl -s --max-time 2 "http://127.0.0.1:8686/" >/dev/null 2>&1; then
            WEB_READY=1
            break
        fi
    done
    if [ "$WEB_READY" -eq 0 ]; then
        echo "Warning: The workbench did not become ready within 15 seconds. Check whether port 8686 is occupied by another program." >&2
    fi
else
    echo "The workbench is already running at http://127.0.0.1:8686 — reusing it."
fi

if [ "$SKIP_CHROME" -eq 0 ]; then
    "$CHROME" --remote-debugging-port=9222 --user-data-dir="$CHROME_PROFILE" "http://127.0.0.1:8686" >/dev/null 2>&1 &
fi

echo "BossHunter is ready. Log in manually in the dedicated Chrome window if needed."