# macOS one-click launcher

BossHunter includes optional shell helpers for macOS users who want a double-click entry that opens the dedicated Chrome profile and the local workbench together. It mirrors the Windows launcher in `scripts/windows/`.

## Install

Install BossHunter first (see the macOS install section of [QUICKSTART.md](QUICKSTART.md) — a virtual environment is required due to PEP 668):

```bash
cd BossHunter
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

From the repository root, either run:

```bash
./scripts/macos/install_launcher.command
```

or double-click `scripts/macos/install_launcher.command` in Finder. This creates a `BossHunter.command` file on the current user's Desktop. The launcher uses repository-relative paths and does not store API keys, passwords, or recruitment-platform credentials.

If the repository was downloaded from the internet rather than cloned with git, macOS quarantine may block the scripts on first run. The installer clears the quarantine flag for its own launcher pair; if Gatekeeper still refuses, run `xattr -d com.apple.quarantine scripts/macos/start_bosshunter.sh` once from the repository root.

## Use

Double-click `BossHunter.command` on the Desktop. A Terminal window will open and the launcher will:

1. Open a dedicated Chrome profile (`~/.bosshunter-chrome`) with `--remote-debugging-port=9222` and navigate to BOSS直聘. Chrome 136+ ignores the debugging port on the default profile, which is why the dedicated `--user-data-dir` is mandatory.
2. Start the local BossHunter Browser Runtime and run the connection check.
3. Start the local workbench at `http://127.0.0.1:8686` and open it in the same dedicated Chrome profile.

Log in manually in the dedicated Chrome profile when required. The launcher does not submit applications or bypass the project's manual confirmation safeguards.

## Options

```bash
./scripts/macos/start_bosshunter.sh --skip-chrome        # reuse an already-running debug Chrome
./scripts/macos/start_bosshunter.sh --python-path <path> # force a specific interpreter (e.g. a venv python)
```

Set `BOSS_HUNTER_CHROME` to point at a non-standard Chrome app path. Closing the Terminal window does not stop the workbench or the Chrome instance; quit them manually when you are done.
