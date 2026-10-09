# Windows one-click launcher

BossHunter includes optional PowerShell helpers for Windows users who want a desktop shortcut that opens the dedicated Chrome profile and the local workbench together.

## Install

Install BossHunter first:

```powershell
pip install -e .
```

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install_desktop_shortcut.ps1
```

This creates a `BossHunter.lnk` shortcut on the current user's desktop. The shortcut uses repository-relative paths and does not store API keys, passwords, or recruitment-platform credentials.

During normal use, the shortcut keeps the PowerShell launcher and local web process hidden in the background, so no terminal window needs to remain open. Running the launcher script directly still shows diagnostics.

## Use

Double-click the shortcut. It will:

1. Open a dedicated Chrome profile with remote debugging enabled and navigate to BOSS直聘.
2. Start the local BossHunter Browser Runtime and run the connection check.
3. Start the local workbench at `http://127.0.0.1:8686`.

Log in manually in the dedicated Chrome profile when required. The launcher does not submit applications or bypass the project's manual confirmation safeguards.

## Options

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_bosshunter.ps1 -SkipChrome
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_bosshunter.ps1 -PythonPath C:\path\to\python.exe
```

`-SkipChrome` reuses an already-running debug Chrome instance. `-PythonPath` forces a specific interpreter, for example a virtual environment Python.

Without `-PythonPath`, the launcher resolves the interpreter the same way the macOS launcher does: the `bosshunter` command on `PATH` first, then the repository virtual environment (`.venv\Scripts\python.exe`), then `py`/`python` on `PATH`. The repository venv is the one that matters for a checkout installed with `pip install -e .`, because such a project is only importable there.
