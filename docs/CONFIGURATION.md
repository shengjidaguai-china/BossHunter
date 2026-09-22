# BossHunter 配置指南

推荐运行 `bosshunter web`，在 `http://127.0.0.1:8686` 的本地面板完成配置。需要手动编辑时，可复制仓库根目录的 [`config.example.yaml`](../config.example.yaml) 为 `config.yaml`。

面板中填写的 AI API Key 或 Auth Token 会保存在与配置文件同目录的隐藏凭据文件（默认 `.config.credentials.yaml`），并以仅当前用户可读写的权限写入；普通 `config.yaml`、配置下载和浏览器接口都不包含原始凭据。旧版写在 `config.yaml` 中的凭据会在下次启动 BossHunter 时自动迁移。不要分享隐藏凭据文件。

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

## HR 活跃时间筛选

在「配置 → 个人信息」设置 **BOSS HR 活跃时间（天）**，例如 `7`：

```yaml
profile:
  hr_active_within_days: 7       # 0-365；默认 0，不限制
  hr_active_keep_unknown: true  # 默认保留未知；设为 false 可只采集已识别的活跃岗位
```

该规则在 BOSS 详情读取后、入库前生效，覆盖单独采集和全流程中的采集。被过滤岗位计入采集的「过滤」数量，不占新增数量。其他平台目前未采集此信号，不受该配置影响；已有岗位也不会被删除或自动改状态。

岗位池和首页待确认列表的「招聘者活跃」筛选支持近 1 / 3 / 7 / 30 天以及「活跃度未知」，默认显示全部。近 N 天筛选只包含已识别且满足条件的岗位；岗位池的「导出筛选结果」使用相同条件。

解析支持「在线」「刚刚活跃」「今日活跃」「昨天活跃」「3天内活跃」「近7天活跃」「本周活跃」「本月活跃」及数字分钟/小时/天标签。区间按上界判断，例如「近7天活跃」不算近 3 天；「今日」按 1 天、「昨天」按 2 天保守归类。空值、「近期活跃」等无法确定范围的文案属于未知，不等同于不活跃。

活跃度是**采集时页面显示的状态**，不是实时在线状态，也不是职位发布时间；本次筛选不重新访问平台刷新，也不按已存天数推算最近登录时间。

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
