# BossHunter 完整上手指南

本指南适合第一次安装和运行 BossHunter。首页只保留最短启动路径，平台登录、浏览器连接和排错细节统一放在这里。

## 1. 准备环境

| 依赖 | 版本 | 用途 |
|---|---|---|
| Python | 3.10+ | 核心运行时 |
| Node.js | 22+ | 本地 Browser Runtime / CDP 代理 |
| Google Chrome | 最新稳定版 | 连接已登录的招聘平台 |
| Git | — | 下载和更新源码（源码安装时需要） |
| AI API Key | — | Anthropic 或 OpenAI 兼容接口 |

自动化操作招聘平台存在账号限制或封禁风险。请仅用于个人求职，保持低频，并遵守平台规则。

## 2. 安装

Windows 用户请直接按下面的「Windows 首次安装与桌面快捷方式」完成安装；一键启动器负责安装后的日常启动，不会代替依赖安装。

首次使用请先在 frontend 目录构建前端产物（`dist` 不随 git 仓库跟踪，需本地按需构建），再安装 Python 包；否则 `pip install -e .` 会报 `frontend/dist` 缺失。

```bash
git clone https://github.com/shengjidaguai-china/BossHunter.git
cd BossHunter
npm --prefix src/bosshunter/web/frontend ci
npm --prefix src/bosshunter/web/frontend run build
pip install -e .
```

仅在需要 `xhtml2pdf` 备用渲染时安装 PDF 可选依赖：

```bash
pip install -e ".[pdf]"
```

### Windows 首次安装与桌面快捷方式

1. 安装 Git、Python 3.10+、Node.js 22+ 和 Google Chrome。Python 安装时勾选 **Add python.exe to PATH**，安装完成后重新打开 PowerShell。
2. 在准备存放项目的位置打开 PowerShell，确认 `git --version`、`py --version`、`node --version` 和 `npm.cmd --version` 均能运行。下面使用 `npm.cmd`，避免 PowerShell 将 `npm` 解析为受执行策略限制的 `npm.ps1`。
3. 下载源码，在仓库自己的虚拟环境中安装。所有命令均在同一个 PowerShell 窗口依次执行：

```powershell
git clone https://github.com/shengjidaguai-china/BossHunter.git
cd BossHunter
py -m venv .venv
npm.cmd --prefix src/bosshunter/web/frontend ci
npm.cmd --prefix src/bosshunter/web/frontend run build
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m bosshunter.main --help
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\install_desktop_shortcut.ps1
```

如果没有 `py`，但 `python --version` 显示 3.10+，可将创建虚拟环境的命令改为 `python -m venv .venv`。这里直接调用虚拟环境的 Python，不需要执行 `Activate.ps1`，也不需要修改系统执行策略。`Bypass` 仅用于当前脚本进程。

4. 双击桌面的 **BossHunter** 快捷方式。现有启动器会打开 `%LOCALAPPDATA%\BossHunterChrome` 专用 Chrome 配置目录，启用 `9222` 远程调试，运行 Browser Runtime 连接检查，再打开 `http://127.0.0.1:8686` 工作台。请在这个专用 Chrome 窗口中手动登录招聘平台。

启动器优先使用 PATH 中的 `bosshunter`，其次使用仓库 `.venv\Scripts\python.exe`，最后才尝试系统 Python。若电脑上已有其他 BossHunter 安装，首次排错可明确指定本次安装的 Python：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\start_bosshunter.ps1 -PythonPath .\.venv\Scripts\python.exe
```

快捷方式以后台方式启动，不要求保留终端。请保持专用 Chrome 窗口开启；快捷方式仅打开 Chrome 和工作台，不会自动登录或开始投递。移动仓库后请重新运行快捷方式安装脚本。启动器的详细说明见 [Windows 一键启动器](windows-launcher.md)。

### macOS 安装

从 Homebrew Python（3.12 起）或系统 Python 安装时，pip 会报
 `error: externally-managed-environment`（PEP 668）——macOS 禁止直接向系统环境装包，需要先创建虚拟环境：

```bash
# 依赖（已安装可跳过）
brew install python node@22

# 克隆并创建虚拟环境
git clone https://github.com/shengjidaguai-china/BossHunter.git
cd BossHunter
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
bosshunter web
```

注意：

- 新开的终端需要先执行 `source .venv/bin/activate`，否则找不到 `bosshunter` 命令；可把这一行追加到 `~/.zshrc` 简化日常使用。
- 如果 `brew install node@22` 后 `node` 仍不可用，按 brew 提示把 keg-only 路径加入 PATH（`export PATH="$(brew --prefix node@22)/bin:$PATH"`）。
- 希望双击启动（专用 Chrome 调试实例 + 本地工作台），见 [macOS 一键启动器](macos-launcher.md)。

## 3. 开启 Chrome 远程调试

Windows 桌面快捷方式已经完成远程调试启动，不需要再次运行下面的命令。如果采用手动启动，可在 Chrome 地址栏打开 `chrome://inspect/#remote-debugging`，启用 **Allow remote debugging**。

也可以使用独立用户目录启动 Chrome：

```bash
# macOS
open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$HOME/.bosshunter-chrome"

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.bosshunter-chrome"
```

Windows 手动启动（PowerShell；Chrome 安装位置不同时调整可执行文件路径）：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 "--user-data-dir=$env:LOCALAPPDATA\BossHunterChrome"
```

使用启动参数时会打开一个独立 Chrome 窗口。请在这个窗口中登录要使用的招聘平台，并在任务期间保持窗口开启；其他 Chrome 窗口的登录状态不会自动复用。

Chrome 136+ 在使用默认用户目录时会忽略 `--remote-debugging-port`，必须像上面这样搭配独立的 `--user-data-dir` 启动；macOS 上如果已有普通 Chrome 窗口在运行，请先完全退出（`Cmd+Q`）再执行启动命令。

## 4. 完成本地配置

```bash
bosshunter web
```

浏览器会打开 `http://127.0.0.1:8686`。Windows 用户通过快捷方式已经打开工作台，无需再启动一个 Web 进程。请在本地面板完成：

1. 上传自己的 Markdown（`.md`）或 Word（`.docx`）简历，不要继续使用示例简历。
2. 设置搜索关键词、目标城市、评分阈值、发送频率和时间窗口。在「反监测设置」中分别选择开始、结束时间；用「添加时间段」设置多个时段，直接修改时间或删除对应行。
3. 在“AI 设置”中选择服务商，填写服务商提供的 API Key 和模型名称。
4. 保存配置。

API Key 只应在本地面板输入，不要粘贴到 Issue、聊天记录或提交文件中。更多字段说明见 [配置指南](CONFIGURATION.md)。

时间窗口按电脑本地时间执行，包含开始时间、不包含结束时间。例如 `09:00-12:00`、`14:00-16:00` 会在 12:00 至 14:00 之间暂停发送，16:00 停止当天后台任务；不会自动等到次日继续发送。结束时间必须晚于开始时间，不能跨午夜，重复、重叠或不完整的时间段不能保存。保留默认 `09:00-16:00` 或缩短时段即可，无需提高发送频率。保存后重新打开配置页，确认所有时间段与预期一致。

YAML 仍使用 `throttle.send_windows: ["09:00-12:00", "14:00-16:00"]` 字符串列表。旧配置的空列表 `[]` 表示不限制发送时间，也不设置每日窗口截止；界面会明确提示，首次使用建议保留有限时间段。

## 5. 检查连接

```bash
bosshunter ai-status
bosshunter connect
```

- `ai-status` 安全检查 AI 服务，不显示完整 Key。
- `connect` 只检查 Browser Runtime 和 Chrome 连接，不会替你启动或登录 Chrome。

如果浏览器连接失败，请确认远程调试已开启，并且招聘平台是在同一个可控制的 Chrome 窗口中登录。

Windows 未激活虚拟环境时，对应检查命令为：

```powershell
.\.venv\Scripts\python.exe -m bosshunter.main ai-status
.\.venv\Scripts\python.exe -m bosshunter.main connect
```

## 6. 开始运行

确认简历、AI 和 Chrome 均已就绪后运行：

```bash
bosshunter run
```

完整流程为：采集岗位 → AI 评分 → 人工确认投递清单 → 生成招呼语 → 低频发送 → 监听回复。

只有 BOSS 直聘支持确认后的低频发送和监听。智联招聘、前程无忧 51job 仅支持只读采集和 AI 处理；请打开原平台链接手动投递，再回到岗位池标记“已发送”。

可在工作台停止任务；命令行模式按 `Ctrl+C` 停止。全部命令见 [CLI 命令](CLI.md)。

### Windows 日常启动与排错

日常双击桌面快捷方式，确认专用 Chrome 的登录状态，在工作台检查配置后再启动任务。当天窗口结束后任务已经停止，下一天需要重新启动任务并按流程完成人工确认。

| 现象 | 处理方式 |
|---|---|
| `py`、`node` 或 `git` 无法识别 | 安装相应依赖，重新打开 PowerShell，确认版本命令能运行。 |
| `npm.ps1` 或 `Activate.ps1` 被执行策略阻止 | 使用上述 `npm.cmd` 和 `.venv\Scripts\python.exe` 命令；无需全局放开执行策略。 |
| 安装时报 `frontend/dist` 缺失 | 在仓库根目录先完成 `npm.cmd ... ci` 和 `npm.cmd ... run build`，成功后再安装 Python 包。 |
| `No module named bosshunter` 或找不到 BossHunter | 用 `.\.venv\Scripts\python.exe -m pip install -e .` 安装，并通过启动器的 `-PythonPath` 参数确认使用同一个环境。 |
| 快捷方式无反应、工作台打不开 | 在仓库根目录直接运行上述 `start_bosshunter.ps1` 命令查看报错。确认 `http://127.0.0.1:8686` 是否已有工作台；避免反复启动多个进程。 |
| Chrome 连接失败或 `9222` 未就绪 | 关闭 BossHunter 专用 Chrome 后重新启动快捷方式；仅在专用窗口登录。可访问 `http://127.0.0.1:9222/json/version` 查看端点是否就绪，再运行 `connect`。连接检查失败时启动器仍会打开工作台，不代表连接已成功。 |
| Chrome 用户目录含空格时启动失败 | 用第 3 节的 PowerShell 手动命令启动专用 Chrome，再运行 `.\.venv\Scripts\python.exe -m bosshunter.main web`；命令保留了完整的用户目录参数。 |
| 时间段无法保存或配置无法加载 | 按提示修改 YAML 或界面的时段，使用两位小时和分钟，确保起止有效且不重复、不重叠。不要通过清空列表规避错误。 |
| 窗口外没有发送或任务已停止 | 检查电脑的日期、时区和配置的时段；到开始时间后启动任务，不要使用强制发送绕过窗口。 |

启动器不会清理浏览器登录或结束所有后台进程。关闭页面前先在工作台停止任务；重新登录时继续使用同一个专用 Chrome 配置目录。更多问题见 [常见问题](FAQ.md)。

## 安全边界

- 所有投递必须经过人工确认。
- 仅在配置的时间窗口内发送，并受随机间隔和每日上限约束。
- 检测到验证码、频率限制、登录墙或未知页面时停止，不尝试绕过。
- 即使采用保守策略，也无法保证账号绝对安全，请自行评估风险。
