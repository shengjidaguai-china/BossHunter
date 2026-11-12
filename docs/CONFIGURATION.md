# BossHunter 配置指南

推荐运行 `bosshunter web`，在 `http://127.0.0.1:8686` 的本地面板完成配置。需要手动编辑时，可复制仓库根目录的 [`config.example.yaml`](../config.example.yaml) 为 `config.yaml`。

面板中填写的 AI API Key 或 Auth Token 会保存在与配置文件同目录的隐藏凭据文件（默认 `.config.credentials.yaml`），并以仅当前用户可读写的权限写入；普通 `config.yaml`、配置下载和浏览器接口都不包含原始凭据。旧版写在 `config.yaml` 中的凭据会在下次启动 BossHunter 时自动迁移。不要分享隐藏凭据文件。

## 通用模型与服务商接入

在「配置 → AI 设置」选择接入方式：

- 模型服务：支持 OpenAI、Claude、Gemini、DeepSeek、豆包、通义千问、Kimi、智谱、MiniMax、硅基流动、OpenRouter、OpenCode Go，以及本地或远程的 Ollama、LM Studio。选择预设后，填写 API Key 和模型 ID，保存后测试连接；地址始终可以修改。
- 其他服务商：选择「自定义服务」，指定 OpenAI 兼容 Chat Completions 或 Anthropic 兼容 Messages 协议，填写服务地址、API Key 与任意模型 ID。预设不构成服务商或模型白名单；私有部署、代理网关、其他设备上的推理服务同样可以接入。服务需支持所选文本接口；只有厂商专有接口、仅 Responses/嵌入/图像生成接口的服务不能直接用 Chat Completions 代替。
- 无需认证的接口：选择「无需认证」，可在没有 API Key 的情况下获取模型和执行任务，系统不会读取或发送环境变量或已保存的凭据。Ollama、LM Studio 预设默认此方式；远程服务启用认证后请改为 API Key。
- 本机 AI：选择「本机 Codex」或「本机 Claude Code」。先在终端安装并登录对应工具，保存配置，再点击「验证并授权」。Codex 模型留空时会读取 `$CODEX_HOME/config.toml`（默认 `~/.codex/config.toml`）顶层的 `model` 设置，并显式传给 CLI，以避免旧版 CLI 回退到账号不可用的内置模型。只读取该公开模型设置，不加载其中的 Hook、MCP 或凭据；Claude Code 留空时使用工具默认模型。显式填写模型时优先使用填写值。

从 Codex 桌面应用启动时，优先使用应用通过 `CODEX_CLI_PATH` 提供的 CLI，再回退到系统 PATH 中的版本，避免全局旧版本不支持当前账号模型。应用内不升级或修改全局 CLI。默认模型设置变化和 CLI 路径/版本变化都会使旧授权失效，需要重新验证。模型不支持、登录失效、版本参数不兼容等失败会显示对应的脱敏提示。

模型可从接口获取，也可手动填写，大小写与带 `/` 的模型标识会保留（DeepSeek 沿用其原有大小写规范化）。新服务商不继承旧服务的模型 ID 和凭据；请填写当前服务支持的 ID。OpenAI 预设使用 `max_completion_tokens`，其余兼容预设默认 `max_tokens`；可根据模型说明在「输出 Token 参数」切换。使用 `max_completion_tokens` 时不额外传入温度，以兼容固定温度的推理模型。不同地区和账户的服务地址可能不同，请以账户控制台为准。若网关要求额外的路由请求头，可在配置中添加 `ai.extra_headers`；`Authorization`、`x-api-key`、`Content-Type`、`Host` 等由程序负责的认证头不能通过该字段覆盖。OpenCode Go 预设已内置其必需的 `x-opencode-session`。

服务商列表由后端注册表统一提供给配置页和配置 schema，新增预设无需在前端再次维护名单。预设地址参考官方接入文档：[Gemini](https://ai.google.dev/gemini-api/docs/openai)、[通义千问](https://www.alibabacloud.com/help/en/model-studio/regions)、[Kimi](https://platform.kimi.ai/docs/overview)、[智谱](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction)、[MiniMax](https://platform.minimax.io/docs/api-reference/text-openai-api)、[硅基流动](https://docs.siliconflow.cn/docs/userguide/quickstart)、[OpenRouter](https://openrouter.ai/docs/quickstart)、[Ollama](https://docs.ollama.com/api/openai-compatibility)、[LM Studio](https://lmstudio.ai/docs/developer/openai-compat)。

验证会发送一条简短请求并消耗少量额度，收到正确回复后才保存授权。授权涵盖岗位评分、招呼语、简历生成和回复建议所需的文本调用：相关简历和岗位文本会交给所选工具，并可能发送至工具使用的模型服务。「本机」指通过本机 CLI 接入，不代表离线推理。BossHunter 不读取或复制这些工具的 OAuth、Cookie、会话 Token 或 Keychain 登录凭据。

授权记录保存在 `.config.credentials.yaml`，不包含在普通配置、浏览器响应或配置下载中。切换工具或模型、安装文件变化后需要重新授权。点击「撤销授权」会阻止后续调用（已启动的请求可用任务停止按钮取消）。工具登录失效或额度不足时会提示调用失败，不会自动切换到其他服务。本机模式下「测试连接」只检查本地授权和安装标识，实时模型可用性由「验证并授权」请求及实际任务检查。

调用从临时工作目录启动，任务文本经标准输入传入，不作为命令行参数。Codex 使用非交互、只读沙箱和临时会话，关闭命令执行与联网搜索；Claude Code 禁用内置工具、MCP、用户/项目设置、Hook 和会话持久化。需要支持这些参数的 CLI 版本；旧版本不兼容时应升级后重新验证。

参考：[Codex 非交互模式](https://developers.openai.com/codex/noninteractive)、[Codex 配置参数](https://developers.openai.com/codex/config-reference)、[Claude Code CLI 参数](https://code.claude.com/docs/en/cli-reference)。

## 核心配置

| 配置段 | 关键字段 | 说明 |
|---|---|---|
| `profile` | `resume_path`, `salary_min/max`, `deal_breakers` | 简历、期望薪资与排除条件 |
| `search` | `keywords`, `cities`, `max_pages` | 默认搜索策略 |
| `platforms` | `boss`, `zhilian`, `51job`, `liepin` | 各平台开关与独立搜索条件 |
| `collection` | `daily_search_page_limit`, `risk_pause_*` | 采集额度与风险暂停策略 |
| `scoring` | `threshold`, `max_candidates` | 评分阈值与候选数量 |
| `throttle` | `daily_limit`, `interval_min/max`, `send_windows` | 低频发送策略 |
| `ai` | `service`, `provider`, `model`, `base_url` | AI 服务与接口；凭据由本地面板单独保存 |
| `monitor` | `interval`, `max_resume_sends_per_cycle` | 回复监听设置 |
| `follow_up` | `enabled`, `interval_hours`, `skip_weekends` | 跟进策略 |
| `browser` | `chrome_ports`, `proxy_port` | Chrome 与本地代理连接 |

完整字段、默认值和注释以 [`config.example.yaml`](../config.example.yaml) 为准。

## 平台配置边界

- BOSS 直聘：支持采集、AI 处理，以及人工确认后的低频发送和回复监听。
- 智联招聘：支持只读采集和 AI 处理，不进入自动发送、简历发送或监听。
- 前程无忧 51job：支持只读采集和 AI 处理，不进入自动发送、简历发送或监听。
- 猎聘：支持只读采集和 AI 处理，不进入自动发送、简历发送或监听。

外部只读平台应通过岗位池打开经域名校验的原平台链接，人工投递后再标记“已发送”。

## AI 服务

配置页可选择 Claude、DeepSeek、豆包或其他 OpenAI 兼容接口：

- Claude / Anthropic：Anthropic Messages，可通过 `ANTHROPIC_API_KEY` 提供 Key。
- DeepSeek：OpenAI Chat Completions，可通过 `DEEPSEEK_API_KEY` 提供 Key。
- 豆包 / 火山方舟：OpenAI Chat Completions，可通过 `ARK_API_KEY` 提供 Key。
- 其他 OpenAI 兼容接口：填写服务商提供的 Base URL 和模型 ID，可通过 `OPENAI_API_KEY` 提供 Key。

不要把真实 Key 写入示例、Issue、聊天或 Git 提交。BossHunter 不读取 Codex、Claude Code、ChatGPT 等工具自身的 OAuth、Cookie 或登录凭证。

保存后运行：

```bash
bosshunter ai-status
```

只有检测通过后再运行完整流程。

## 简历

配置项 `profile.resume_path` 必须指向本人的真实简历。支持 Markdown（`.md`）、Word（`.docx`）和带文字层的 PDF（`.pdf`）；加密、损坏、扫描版或无文字层 PDF 无法直接解析，扫描件应先进行 OCR。旧版二进制 `.doc` 暂不支持。

## 推荐的保守设置

- 保持合理的 `daily_limit` 和随机发送间隔。
- 限定 `send_windows`，避免长时间连续运行。
- 不关闭人工确认。
- 不提高默认访问频率，也不要尝试绕过验证码、登录墙或平台限制。

## BOSS 仅实习筛选

- 在 BOSS 搜索条件中将职位类型单独设为「实习」，并启用 `profile.allow_internship`。
  同时选择全职/兼职时，不会启用「仅实习」拦截；其他平台不受此规则影响。
  若未开启接受实习却选择仅实习，启动时会明确报配置冲突，不打开浏览器或入库。
  即使没有仅实习筛选，BOSS 详情明确为实习且未开启接受实习时，详情后和发送前仍会拦截。
- 采集器同时核对搜索 URL 与页面选中项。若无法确认筛选已生效，会停止该平台本轮采集，
  提示人工核对，不悄悄退回不带筛选的搜索。
- 列表缺少类型时继续读详情；依据标题与 JD 中明确的职位类型判断。
  「校招」「日薪」「有实习经历优先」不单独构成实习证据。冲突或无法判断的岗位会被过滤。
- AI 预筛和发送前再次核对，因此旧岗位记录也不能绕过仅实习限制。
  原有人工确认、薪资/排除词规则、发送额度、节流、验证码及风险暂停机制保持不变。
- 页面展示独立的职位类型和待核实原因；不修改已有记录中的校招/社招字段，也不做数据库迁移。
