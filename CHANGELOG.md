# BossHunter 更新记录

这里记录用户可以感知的功能、体验和稳定性变化。版本号与项目当前发布版本保持一致；同一版本内的持续优化按日期分别记录。

| 日期 | 版本号 | 类型 | 更新内容 |
| --- | --- | --- | --- |
| 2026-09-09 | v2.4.0 | 采集、AI、简历与工作台 | 汇总近期多平台断点续采、完整简历评分与评分依据、失败重试、定制简历预览确认、首页数据概览和紧凑布局，以及 AI 连接、macOS 面板、前端构建和文档维护改进。 |
| 2026-09-01 | v2.3.2 | 采集与简历稳定性 | 完成 51job API 只读采集的安全整合和真实环境验证；修复智联详情页被误判为需重新登录、单平台登录问题阻断后续平台以及中文 PDF 简历乱码，并调整页数上限提示位置。 |
| 2026-08-29 | v2.3.2 | 稳定性与平台适配 | 合入猎聘只读采集后端（前端入口待接入）、BOSS 搜索筛选和安全岗位链接；修复 AI 凭据、错误提示、评分恢复与监测回复，并补齐采集器和运行边界测试。 |
| 2026-08-25 | v2.3.1 | 多平台与安全整合 | 合入智联/51job 只读采集、外部平台人工投递闭环、岗位池与筛选增强、Windows 兼容、招呼语与消息判定修复，并重整 BOSS 页面访问保护设置。 |
| 2026-08-13 | v2.3.0 | 功能与可恢复性 | 增加多范围岗位导出、离线城市目录、任务安全的岗位回收站和可独立重试的 AI 评分；同步改进配置安全、岗位筛选与投递队列。 |
| 2026-08-02 | v2.2.0 | 功能与稳定性 | 单岗位失败不再中断全流程；额度未完成岗位下次优先续发；加强首次沟通、历史会话、任务停止、后台页面与最新配置生效逻辑，并简化工作台。 |
| 2026-07-30 | v2.1.1 | 稳定性修复 | 修复 AI 评分与招呼语可能因 Token 限制中断的问题：回答被截断时增大输出上限重试，上下文过长时压缩请求，额度或限流异常会保留进度并在工作台显示原因。 |
| 2026-07-30 | v2.1.0 | 体验优化 | 支持中文名 Markdown 与 Word（`.docx`）简历；新增 DeepSeek、豆包和自定义兼容 API；启动前可明确诊断 Chrome、远程调试与 AI 配置问题。 |
| 2026-07-27 | v2.0.0 | 功能改进 | 优化定制简历投递和监测恢复流程，并整理公开文档中的隐私内容。 |
| 2026-06-29 | v2.0.0 | 稳定性 | 修复工作台任务可能卡住的问题；自动跟进默认关闭，把发送决定留给用户。 |

## v2.4.0

本节汇总 2026-09-01 上次记录之后的功能、修复与维护改动，以及本次工作台更新。

### 岗位采集与任务恢复

- 猎聘只读采集接入 Web 面板，可在采集窗口选择猎聘并设置关键词、城市和页数；配置页、岗位筛选、平台标签和导出同步支持猎聘，仍不开放自动投递或消息监测。([#139](https://github.com/shengjidaguai-china/BossHunter/pull/139))
- BOSS 明确区分“重新采集”和“继续采集”：重新采集从各城市、关键词组合的第一页开始发现新岗位，按岗位 ID 去重；只有继续采集才复用原任务参数和断点。整页保存成功后才推进断点，保存失败保留重试位置，支持恢复未完成的 BOSS 单平台采集任务。采集结束区分无新增、空结果、未完成和解析或保存失败，避免把部分失败显示为全部完成。([#170](https://github.com/shengjidaguai-china/BossHunter/pull/170)、[#196](https://github.com/shengjidaguai-china/BossHunter/pull/196))
- 改进 BOSS 滚动加载和搜索页保留；先还原薪资字体编码再筛选，无法解析时明确记录原因。采集后自动评分只处理本次新增岗位，实时显示 AI 阶段、完成、通过、过滤与失败数量。([#196](https://github.com/shengjidaguai-china/BossHunter/pull/196))
- 智联和猎聘只读采集后端支持带有效期的断点，续采可跳过已完成的城市、关键词组合；失败页保留重试位置。智联补齐配置校验、时间窗口、屏蔽公司、一票否决词、JD 和实习岗位过滤。([#155](https://github.com/shengjidaguai-china/BossHunter/pull/155)、[#158](https://github.com/shengjidaguai-china/BossHunter/pull/158)、[#159](https://github.com/shengjidaguai-china/BossHunter/pull/159))
- 恢复并更新 51job、猎聘、智联的离线城市快照。智联增加默认关闭的实验性只读 API 采集框架，可通过 `platforms.zhilian.search.api_fetch` 开启；接口不可用时回退页面采集，真实响应字段仍需登录环境校准，验证码或风控信号仍停止任务。([#156](https://github.com/shengjidaguai-china/BossHunter/pull/156)、[#162](https://github.com/shengjidaguai-china/BossHunter/pull/162))

### AI 评分、筛选与连接诊断

- 评分使用完整简历和清理后的完整 JD，结合城市、薪资区间以及直接经验、相近经验、待确认信息和必备条件判断匹配度，减少重复扣分；上下文不足时不再静默截断简历，无法完成时明确报错。全量、自动和恢复评分不再被内部 1000 条上限截断，手动勾选仍保留 1000 条限制。([#203](https://github.com/shengjidaguai-china/BossHunter/pull/203))
- 保存成功评分的依据快照，并提供只读查询接口；历史岗位没有快照、预筛失败或评分错误时分别返回明确状态。本次提供后端查询能力，不追溯重算旧岗位，也不新增评分分析页面。([#77](https://github.com/shengjidaguai-china/BossHunter/pull/77))
- 薪资过滤改进区间重叠判断，支持薪资上界比例和无法解析薪资的过滤配置；AI 评分纳入期望薪资。招呼语优先使用有依据的正向经历，增加检查和重试，毕业届别根据教育日期判断。([#172](https://github.com/shengjidaguai-china/BossHunter/pull/172))
- AI 请求与启动检查避免继承系统代理；无效 Base URL 给出明确提示，DeepSeek 模型别名可解析为实际模型，也可关闭自动解析。区分客户端初始化失败与服务请求失败，诊断信息只包含安全的运行环境版本信息。([#172](https://github.com/shengjidaguai-china/BossHunter/pull/172)、[#179](https://github.com/shengjidaguai-china/BossHunter/pull/179))
- 将启动校验、配置保存和任务创建纳入同一受保护流程：已有任务或截止时间导致启动被拒绝时，不覆盖配置；配置保存失败时，不创建后台任务。([#203](https://github.com/shengjidaguai-china/BossHunter/pull/203))

### 投递、HR 回复与简历

- 发送失败保留具体原因，包括岗位关闭、已经投递、缺少招呼语、尚未评分或未确认；成功后清除旧失败信息。失败招呼语可重试，点击后立即显示处理中并防止重复操作；改进 HR 沟通意向和简历请求识别。([#145](https://github.com/shengjidaguai-china/BossHunter/pull/145)、[#152](https://github.com/shengjidaguai-china/BossHunter/pull/152)、[#161](https://github.com/shengjidaguai-china/BossHunter/pull/161))
- 简历生成失败的待办支持重新生成或忽略，同步待办和简历请求状态，并保留失败历史，避免错误覆盖已推进的状态。([#92](https://github.com/shengjidaguai-china/BossHunter/pull/92))
- 定制简历后端增加预览、编辑和显式确认流程：保留母版中的全部项目、教育、联系方式和事实数据，不编造、合并或删减经历；同一份 Markdown 生成 PDF 和完整 PNG 预览，并检查截图是否完整。预览与确认通过接口完成，本次不新增前端编辑器；生成后不会自动发送。([#143](https://github.com/shengjidaguai-china/BossHunter/pull/143))
- 配置页支持在指定区域拖入简历，原始 PDF 与转换后的 Markdown 可折叠对照预览；上传路径统一为绝对路径，修复后续读取失败和异常 PDF 难以清除的问题。([#176](https://github.com/shengjidaguai-china/BossHunter/pull/176))

### 工作台首页与操作体验

- 增加最近 7 日发送和回复趋势、高分公司 TOP5，最近活动显示 3 条；各统计独立加载，单个接口失败不阻塞其他区域，空数据提供操作引导。([#202](https://github.com/shengjidaguai-china/BossHunter/pull/202))
- 保持原有配色，突出“运行全流程”、采集和监测入口；启动检查、运行状态、失败原因和普通通知默认只占一行，详情按需展开，合并重复提示。今日待确认的筛选默认收起，展开后使用紧凑控件；保留生效条件数、结果数、重置和薪资校验。无 HR 简历待办时缩为一行，兼容窄窗口导航。([#202](https://github.com/shengjidaguai-china/BossHunter/pull/202))
- 增加独立启动检查入口，在创建任务前展示需处理的问题；补充 BOSS 关键词输入的回车和逗号提示。([#171](https://github.com/shengjidaguai-china/BossHunter/pull/171))

### 安装、文档与维护

- 修复 macOS 隐私权限环境下静态资源被误报为 403、导致面板无法加载的问题。([#175](https://github.com/shengjidaguai-china/BossHunter/pull/175))
- 前端构建产物改为按需生成，打包时纳入安装包；CI 增加前端构建，缺少产物时提供明确提示。完整上手指南及本次首页快速开始均补齐“先构建前端、再安装 Python 包”的步骤。([#147](https://github.com/shengjidaguai-china/BossHunter/pull/147)、[#197](https://github.com/shengjidaguai-china/BossHunter/pull/197))
- 增加可缩放、搜索、追踪关系和导出图片的交互结构图，支持深浅主题；补充跨平台编排、51job 和 BOSS 边界条件的回归测试。([#151](https://github.com/shengjidaguai-china/BossHunter/pull/151)、[#153](https://github.com/shengjidaguai-china/BossHunter/pull/153)、[#157](https://github.com/shengjidaguai-china/BossHunter/pull/157)、[#183](https://github.com/shengjidaguai-china/BossHunter/pull/183))
- 更新贡献记录、维护者候选记录与共同维护规则，明确参与编写者不计入自己的技术批准，高风险改动需两名独立维护者批准；恢复非商业许可证文件。([#149](https://github.com/shengjidaguai-china/BossHunter/pull/149)、[#150](https://github.com/shengjidaguai-china/BossHunter/pull/150)、[#165](https://github.com/shengjidaguai-china/BossHunter/pull/165)、[#182](https://github.com/shengjidaguai-china/BossHunter/pull/182)、[#184](https://github.com/shengjidaguai-china/BossHunter/pull/184)、[#194](https://github.com/shengjidaguai-china/BossHunter/pull/194))

### 升级说明

- 从源码安装或更新时，先按[完整上手指南](docs/QUICKSTART.md#2-安装)重新构建前端，再安装 Python 包；前端、程序版本、健康检查和首页统一为 **v2.4.0**。
- BOSS 旧任务若没有可靠断点，需要重新采集；希望查找新岗位时选择“重新采集”，仅恢复中断任务时选择“继续采集”。
- 猎聘已提供 Web 面板只读采集入口，不支持自动投递或消息监测；智联实验性 API 默认关闭。所有发送仍须人工确认，原有时间窗口、额度和异常停止保护继续生效。

## v2.3.2

### 新增与改进

- 51job 升级为页面上下文中的只读搜索 API 采集，加入保守采样、速率控制、真实末页判定、断点续采与 fail-closed 异常保护。
- 合入猎聘只读采集后端，支持已核验城市、详情采集和安全翻页；前端采集窗口入口待后续接入，且不开放自动投递与消息监控。验证码、限流和异常页面继续 fail-closed。
- BOSS 采集支持职位类型、经验、学历、公司规模、薪资和行业筛选，岗位池可安全打开原职位链接。
- 监测执行页保留多轮 HR 回复记录，支持安全读取单条待处理消息、生成建议和精确打开对应会话；本地 AI 凭据迁移至独立受限文件。

### 问题修复

- 兼容部分模型的评分字段别名，并把空响应、JSON 解析、缺失字段和非法字段值显示为可定位的错误。
- AI 空响应按原流程重试；仍失败时只标记当前岗位并继续其他岗位，额度、鉴权和服务级故障仍会安全暂停。
- 修复暂停评分任务无法恢复、失败原因未保存，以及字符串 `"false"` 被误当成强制重启的问题。
- AI 凭据改为本地配置优先、环境变量仅在配置留空时补位，避免其他工具的残留环境变量静默覆盖面板设置。
- 修复未知外部平台标签触发 `KeyError`，并收紧 51job 城市校验，外部编码不能绕过内置已核验城市。
- 修复智联已加载职位详情时被误判为需重新登录的问题；确实需登录时只停止智联当前任务，后续平台继续执行。
- 修复中文定制简历在降级渲染和独立运行目录下可能乱码或找不到输出文件的问题，统一等待 Chrome 并使用绝对 PDF 路径。
- 采集页的理论页数提示移到“最大页数”下方，计算与实际上限更易对照。

### 验证

- 完成 608 项测试与 21 个子测试；BOSS、51job、智联、猎聘、跨平台编排、中文 PDF 简历和运行存储边界均有专项回归覆盖。
- 51job 完成真实登录环境的只读采集验收；智联跨平台继续执行和中文 PDF 简历由用户完成本地验收。
- GitHub CI 的 Python 3.11 / 3.12 通过，前端 TypeScript 检查和生产构建通过。

### 贡献者致谢

- [@yukinoshi](https://github.com/yukinoshi)：评分兼容、错误传播、暂停恢复和 AI 凭据优先级修复（[#114](https://github.com/shengjidaguai-china/BossHunter/pull/114)、[#115](https://github.com/shengjidaguai-china/BossHunter/pull/115)、[#117](https://github.com/shengjidaguai-china/BossHunter/pull/117)、[#118](https://github.com/shengjidaguai-china/BossHunter/pull/118)）。
- [@yuppiez99999](https://github.com/yuppiez99999)：采集器测试、运行边界、平台能力与注册模型测试、51job 安全回归与猎聘适配验证（[#122](https://github.com/shengjidaguai-china/BossHunter/pull/122)、[#126](https://github.com/shengjidaguai-china/BossHunter/pull/126)、[#127](https://github.com/shengjidaguai-china/BossHunter/pull/127)、[#130](https://github.com/shengjidaguai-china/BossHunter/pull/130)–[#132](https://github.com/shengjidaguai-china/BossHunter/pull/132)、[#142](https://github.com/shengjidaguai-china/BossHunter/pull/142)）。
- [@yuj-029](https://github.com/yuj-029)：51job API 只读采集核心实现，最终基于最新主线安全整合（[#81](https://github.com/shengjidaguai-china/BossHunter/pull/81) → [#142](https://github.com/shengjidaguai-china/BossHunter/pull/142)）。
- [@likris588-ux](https://github.com/likris588-ux)：猎聘只读采集器原始实现（[#89](https://github.com/shengjidaguai-china/BossHunter/pull/89) → [#127](https://github.com/shengjidaguai-china/BossHunter/pull/127)）。
- [@gaogao34](https://github.com/gaogao34)：BOSS 搜索筛选与人工招呼语保护（[#104](https://github.com/shengjidaguai-china/BossHunter/pull/104) → [#125](https://github.com/shengjidaguai-china/BossHunter/pull/125)）。
- [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk)：监测回复轮次、安全读取待处理消息、会话精确跳转、面板交互和本地凭据迁移修复（[#119](https://github.com/shengjidaguai-china/BossHunter/pull/119) → [#124](https://github.com/shengjidaguai-china/BossHunter/pull/124)、[#134](https://github.com/shengjidaguai-china/BossHunter/pull/134)）。
- [@zeroTwo0617](https://github.com/zeroTwo0617)：岗位池安全打开 BOSS 原职位链接（[#112](https://github.com/shengjidaguai-china/BossHunter/pull/112) → [#123](https://github.com/shengjidaguai-china/BossHunter/pull/123)）。

## v2.3.1

### 新增与改进

- 支持智联招聘与 51job 只读采集，外部平台岗位可在本地评分、生成招呼语，并由用户通过原始链接人工投递和标记已发送。
- 增强岗位池分页、排序、筛选、评分与投递队列，补充学历、招聘类型、招呼语风格和来源信息。
- 重整 BOSS 页面访问保护设置，降低风险词误报，支持可配置随机冷却，并为超出页面上限的采集计划提供提前提醒。
- 改进 Windows 启动兼容性、发送结果确认、HR 消息判定、简历编码校验和任务恢复能力。

### 验证

- 完成 401 项测试与 16 个子测试，GitHub CI 的 Python 3.11 / 3.12 均通过，并完成本地真实环境验收。

## v2.3.0

### 新增与改进

- 支持导出当前筛选结果或全量岗位，自定义城市优先使用离线目录查询。
- 新增岗位回收站，删除后可恢复，并避免与正在运行的任务冲突。
- 将 AI 评分拆分为可独立运行、可恢复的步骤，单条失败不阻断其他岗位。
- 改进岗位筛选、分页、统计、评分重试、投递队列与重复任务保护。
- 配置采用原子写入，导出配置不包含凭据，新增公司屏蔽与自定义城市支持。

### 验证

- 完成从岗位采集、AI 评分、人工确认、招呼语发送到 HR 监测的本地全流程测试。
- 50 个新岗位完成评分：9 个通过、40 个过滤、1 个失败被正确隔离；9 个已确认岗位全部发送成功。

### 贡献者致谢

- [@haohao-fly](https://github.com/haohao-fly)：岗位筛选、分页与统计，结构化评分与投递队列。
- [@meixiaoxie](https://github.com/meixiaoxie)：配置安全、公司屏蔽、自定义城市与 Windows WSGI 回归测试。
- [@zhenian-666](https://github.com/zhenian-666)：岗位导出、离线城市目录、回收站与可恢复的独立 AI 评分。

## v2.2.0

### 新增与改进

- 单个岗位发送失败后继续其他岗位和后续监测，不再将部分成功判定为整体失败。
- 区分成功、失败和待下次发送数量，额度未执行岗位保留已生成招呼语。
- 下次运行全流程时，先处理上次已确认但未发送的岗位，再采集新岗位。
- 真正发送前重新读取配置，人工确认期间修改的每日上限和发送节奏可立即生效。
- 增强平台预设招呼语、首次沟通编辑器和历史会话的状态识别、发送验证与安全重试。
- 采集、AI、发送与监测环节统一支持及时停止和已完成结果保留。
- 工作台移除全量重新评分入口，主操作改为三栏布局。

### 问题修复

- 修复单岗位失败或每日额度截止导致全流程提前结束的问题。
- 修复任务启动后修改发送设置不生效的问题。
- 修复部分发送结果无法正确验证、失败任务页面残留和停止响应不及时的问题。

### 安全与兼容性

- 验证码、限流、账号拦截或连续系统错误仍会安全暂停。
- 不需要迁移原有配置、简历、岗位或投递记录。

### 贡献者致谢

- [@yukinoshi](https://github.com/yukinoshi)：提交 [#25](https://github.com/powerycy/BossHunter/pull/25)，贡献多 AI 服务兼容与 Thinking 参数等改进思路。
- [@elowenzhouyb-source](https://github.com/elowenzhouyb-source)：提交 [#27](https://github.com/powerycy/BossHunter/pull/27)，贡献 AI 评分、招呼语与发送可靠性等改进思路。

## 更新说明写作规则

- 优先描述用户获得的收益，不堆叠内部实现细节。
- 明确区分新功能、体验优化、问题修复和需要用户操作的变更。
- 每次发布或重要更新都补充日期、版本号、类型与更新内容。
- 如果存在不兼容变更，单独标注“需要操作”，并写清升级步骤。
