@echo off
chcp 65001 >nul
title BossHunter - 手机端服务与自动化启动器

echo ============================================================
echo   🚀 BossHunter 手机端可用部署一键启动器
echo ============================================================
echo.

:: 检查 Chrome 是否已经开启远程调试端口 9222
netstat -ano | findstr "9222" >nul
if %errorlevel% equ 0 (
    echo [✓] 检测到 Chrome 远程调试端口 9222 已在运行中。
) else (
    echo [i] 正在启动独立调试版 Google Chrome...
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not exist %CHROME_PATH% set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    if not exist %CHROME_PATH% set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

    if exist %CHROME_PATH% (
        start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\BossHunterChrome" https://www.zhipin.com
        echo [✓] 调试版 Chrome 已启动！请在该 Chrome 窗口中登录 BOSS 直聘等平台账号。
    ) else (
        echo [!] 未自动找到 Chrome 路径，请手动开启 Chrome 调试端口：
        echo     chrome.exe --remote-debugging-port=9222 --user-data-dir="%%LOCALAPPDATA%%\BossHunterChrome"
    )
)

echo.
echo [i] 正在启动 BossHunter Web 服务 (监听 0.0.0.0，支持局域网手机访问)...
echo.

cd /d "%~dp0"
bosshunter web --host 0.0.0.0 --port 8686

pause
