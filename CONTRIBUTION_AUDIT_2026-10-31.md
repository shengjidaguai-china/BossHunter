# 两类贡献逐项复核 · 2026-10-31

> 快照：**2026-10-31 14:05:12（Asia/Shanghai）**；主线 [`77f3572`](https://github.com/shengjidaguai-china/BossHunter/commit/77f3572fa98aa1a2e0c73a79f0dace1c0619da70)。

本轮将旧的个人封顶评分和 PR 覆盖占比替换为 [v2 逐项累计标准](CONTRIBUTION_CRITERIA.md)。以下每项列出原始分档、加权分、采用链/本人证据和理由；完整公开评审正文、时间与作者保存在 [评分账本](contributions/2026-10-31.json)。[复算结果](contributions/2026-10-31-results.json) 同时记录账本校验值，防止结果与分项不同步。

## 来源与核对范围

- 项目：GitHub 已关闭 PR 列表按更新时间倒序，100 条一页，读取第 1–3 页共 207 条；来源及采用 PR 共 127 个文件列表，结合采用说明和关键主线提交核对。PR 未合并但代码被另一 PR 实际采用，按采用链记；不能只看原 PR 是否合并。
- 维护：149 个 PR、55 个 Issue 的候选集合，读取 PR 元数据、评审、逐行评论和普通评论；Issue 时间由原始 REST 评论补齐。按作者、任期起点、快照、自审及实际内容筛选。候选集不等于完整历史活动全集。
- 分页：207 条列表读取全部 3 页；127 个 PR 文件列表按返回结果核对分页；维护候选的分页及评论集合已核对，采集记录未报错。删除的记录、私下工作和候选集合之外未命中活动未知。
- 身份：solplum 与旧 2021291696 账号 ID 相同，本次当前榜合并；8 月旧署名不回写。#90 当前账号显示与原提交名的关系未证实，采用 #211 明确保留的 @bactdt 署名，不擅自认定账号变更。
- 本次为贡献证据核对和算术复算，没有重新执行历史产品测试。下文“运行/复现”均指来源中本人当时留下的记录。

## 项目贡献明细

分档顺序 **E / U / R / Q**，得分 `2E+3U+2R+Q`。124 项已评分、1 项暂缓；共 52 位署名，其中 51 位进入分数分母。分数相同只作稳定字母排序，不表示额外高低。

<a id="project-yuppiez99999"></a>
### [@yuppiez99999](https://github.com/yuppiez99999)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p044 · 猎聘采集器适配测试 | 2/0/2/2 | 10 | [#121](https://github.com/shengjidaguai-china/BossHunter/pull/121) · [#127](https://github.com/shengjidaguai-china/BossHunter/pull/127) → [#127](https://github.com/shengjidaguai-china/BossHunter/pull/127) 08-29 20:18（10 分） | 只计可分离的适配测试；不再取得原采集器完整功能分。 |
| p045 · BOSS 采集器专用及异常边界回归 | 3/0/2/3 | 13 | [#122](https://github.com/shengjidaguai-china/BossHunter/pull/122) · [#157](https://github.com/shengjidaguai-china/BossHunter/pull/157) → [#122](https://github.com/shengjidaguai-china/BossHunter/pull/122) 08-29 18:27（10 分）；[#157](https://github.com/shengjidaguai-china/BossHunter/pull/157) 09-06 14:54（3 分） | 两次覆盖补充合为一个测试目标，测试数量不线性换分。 |
| p046 · 外部投递未知平台标签容错 | 1/1/1/2 | 9 | [#95](https://github.com/shengjidaguai-china/BossHunter/pull/95) · [#126](https://github.com/shengjidaguai-china/BossHunter/pull/126) → [#126](https://github.com/shengjidaguai-china/BossHunter/pull/126) 08-29 20:08（9 分） | 仅采用的局部修复。 |
| p047 · 运行存储与恢复边界回归 | 2/0/3/2 | 12 | [#97](https://github.com/shengjidaguai-china/BossHunter/pull/97) · [#126](https://github.com/shengjidaguai-china/BossHunter/pull/126) → [#126](https://github.com/shengjidaguai-china/BossHunter/pull/126) 08-29 20:08（12 分） | 独立存储目标，排除旧分支矛盾假设及历史重复。 |
| p048 · 51job 城市、分页、采样及异常回归 | 4/0/3/3 | 17 | [#98](https://github.com/shengjidaguai-china/BossHunter/pull/98) · [#99](https://github.com/shengjidaguai-china/BossHunter/pull/99) · [#126](https://github.com/shengjidaguai-china/BossHunter/pull/126) · [#81](https://github.com/shengjidaguai-china/BossHunter/pull/81) · [#142](https://github.com/shengjidaguai-china/BossHunter/pull/142) · [#153](https://github.com/shengjidaguai-china/BossHunter/pull/153) → [#126](https://github.com/shengjidaguai-china/BossHunter/pull/126) 08-29 20:08（10 分）；[#142](https://github.com/shengjidaguai-china/BossHunter/pull/142) 09-01 19:21（5 分）；[#153](https://github.com/shengjidaguai-china/BossHunter/pull/153) 09-06 14:52（2 分） | 同一采集器测试目标合并；#81 的 29 项补充已由 #142 采用，不漏计也不重计。 |
| p049 · 职位硬过滤工具回归 | 2/0/2/2 | 10 | [#130](https://github.com/shengjidaguai-china/BossHunter/pull/130) → [#130](https://github.com/shengjidaguai-china/BossHunter/pull/130) 08-31 10:06（10 分） | 针对关键词、公司屏蔽及薪资工具边界。 |
| p050 · 采集模型、注册与平台能力契约回归 | 2/0/2/2 | 10 | [#131](https://github.com/shengjidaguai-china/BossHunter/pull/131) · [#132](https://github.com/shengjidaguai-china/BossHunter/pull/132) → [#131](https://github.com/shengjidaguai-china/BossHunter/pull/131) 08-31 10:16（8 分）；[#132](https://github.com/shengjidaguai-china/BossHunter/pull/132) 08-31 19:28（2 分） | 基础模型和能力注册作为同一契约目标；3 行能力表不按覆盖率满分推高。 |
| p051 · 前端产物按需构建与打包交付 | 4/3/3/2 | 25 | [#147](https://github.com/shengjidaguai-china/BossHunter/pull/147) → [#147](https://github.com/shengjidaguai-china/BossHunter/pull/147) 09-06 14:58（25 分） | 交付链路实际实现进入项目榜；曾发现的安装/打包缺口未当成已解决。 |
| p052 · 采集编排参数、分支及失败回归 | 3/0/3/3 | 15 | [#151](https://github.com/shengjidaguai-china/BossHunter/pull/151) → [#151](https://github.com/shengjidaguai-china/BossHunter/pull/151) 09-06 14:50（15 分） | 以实际新增测试范围评价，不采用夸大的 41% 基线。 |
| p053 · 智联配置、时间窗及硬过滤接入 | 3/3/3/2 | 23 | [#155](https://github.com/shengjidaguai-china/BossHunter/pull/155) → [#155](https://github.com/shengjidaguai-china/BossHunter/pull/155) 09-01 22:22（23 分） | 不同于后续断点和 API 模式的采集边界能力。 |
| p054 · 三平台城市快照与加载回退 | 3/3/2/2 | 21 | [#156](https://github.com/shengjidaguai-china/BossHunter/pull/156) → [#156](https://github.com/shengjidaguai-china/BossHunter/pull/156) 09-06 15:44（21 分） | 只评三平台数据快照和加载边界，不重复后续元数据校正。 |
| p055 · 城市快照采集日期元数据校正 | 1/1/0/1 | 6 | [#262](https://github.com/shengjidaguai-china/BossHunter/pull/262) → [#262](https://github.com/shengjidaguai-china/BossHunter/pull/262) 09-30 14:09（6 分） | 独立的小范围可追溯性目标，不再取得城市覆盖功能分。 |
| p056 · 猎聘词级和页级断点接入 | 3/3/2/2 | 21 | [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) → [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) 09-06 18:56（21 分） | 只计原作者接入；feng 的详情/保存失败补丁及负责人修复分开。 |
| p057 · 智联词级和页级断点接入 | 3/3/2/2 | 21 | [#159](https://github.com/shengjidaguai-china/BossHunter/pull/159) → [#159](https://github.com/shengjidaguai-china/BossHunter/pull/159) 09-02 15:24（21 分） | 独立平台接入，不把同样的通用存储代码再次计入。 |
| p058 · 智联可选 API-fetch 框架 | 4/4/3/3 | 29 | [#162](https://github.com/shengjidaguai-china/BossHunter/pull/162) → [#162](https://github.com/shengjidaguai-china/BossHunter/pull/162) 09-06 15:24（29 分） | 默认关闭、分级风控及 DOM 降级的实际采用范围。 |
| p059 · BOSS 断点续采接入（历史采用） | 3/3/2/2 | 21 | [#170](https://github.com/shengjidaguai-china/BossHunter/pull/170) → [#170](https://github.com/shengjidaguai-china/BossHunter/pull/170) 09-06 08:15（21 分） | 按历史采用计；后来主线改变策略不抹除当时贡献，不把旧问题算成果。 |
| p060 · 维护成员状态文档同步 | 1/1/0/1 | 6 | [#200](https://github.com/shengjidaguai-china/BossHunter/pull/200) → [#200](https://github.com/shengjidaguai-china/BossHunter/pull/200) 09-19 11:30（6 分） | 采用的文档改动算项目成果，成员核验过程不再另记本人维护分。 |
| p061 · 薪资字体不可解析时可选跳过 | 2/3/2/2 | 19 | [#205](https://github.com/shengjidaguai-china/BossHunter/pull/205) → [#205](https://github.com/shengjidaguai-china/BossHunter/pull/205) 09-13 22:28（19 分） | 只计可选失败策略，不冒充 #225 的动态字形解码。 |
| p062 · 全流程/采集启动防抖及失败反馈 | 2/2/2/2 | 16 | [#206](https://github.com/shengjidaguai-china/BossHunter/pull/206) → [#206](https://github.com/shengjidaguai-china/BossHunter/pull/206) 09-15 18:29（16 分） | 自己的交付及自测不再进入维护分；Rain 后续评分弹窗等增量另列。 |
| p063 · 招呼语任务面板兼容适配 | 2/2/1/2 | 14 | [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) → [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) 09-12 20:26（14 分） | 仅 a622b81 的任务面板范围，非原预览功能全额。 |
| p064 · SQLite 上下文管理器 Mock 修正 | 1/0/2/2 | 8 | [#219](https://github.com/shengjidaguai-china/BossHunter/pull/219) → [#219](https://github.com/shengjidaguai-china/BossHunter/pull/219) 09-19 11:22（8 分） | 两个文件的一项测试环境修复，非产品功能。 |
| p065 · 忽略本地提案和评审草稿 | 1/1/0/1 | 6 | [#265](https://github.com/shengjidaguai-china/BossHunter/pull/265) → [#265](https://github.com/shengjidaguai-china/BossHunter/pull/265) 10-04 12:07（6 分） | 两条忽略规则的局部交付。 |
| p118 · 任务面板最新招呼进度渲染回归 | 1/0/1/2 | 6 | [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) → [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) 09-15 18:24（6 分） | 069cb0a 的独立新增测试，联合署名与提交说明相互支持；不重计 #211 面板实现。 |

<a id="project-fengziliang43-cmyk"></a>
### [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p066 · 监测回复轮次与操作状态 | 3/3/3/2 | 23 | [#119](https://github.com/shengjidaguai-china/BossHunter/pull/119) · [#124](https://github.com/shengjidaguai-china/BossHunter/pull/124) → [#124](https://github.com/shengjidaguai-china/BossHunter/pull/124) 08-29 19:42（23 分） | 只计 #119 被采用的原始范围；负责人追加锁、陈旧轮次和外链加固不计入本人实现。 |
| p067 · 真实对话轮次同步与安全操作 | 4/4/3/3 | 29 | [#134](https://github.com/shengjidaguai-china/BossHunter/pull/134) → [#134](https://github.com/shengjidaguai-china/BossHunter/pull/134) 08-31 19:33（29 分） | 跨存储、监测、API 和页面的实际完整流程。 |
| p068 · 本地凭据独立存储与迁移 | 3/2/4/3 | 23 | [#134](https://github.com/shengjidaguai-china/BossHunter/pull/134) → [#134](https://github.com/shengjidaguai-china/BossHunter/pull/134) 08-31 19:33（23 分） | 与对话同步目标分开，实际凭据隔离实现。 |
| p069 · 重试与正常发送的常驻反馈修复 | 2/2/2/2 | 16 | [#145](https://github.com/shengjidaguai-china/BossHunter/pull/145) → [#145](https://github.com/shengjidaguai-china/BossHunter/pull/145) 09-08 13:14（16 分） | 只评本人追加通知补丁及交互回归，原 direct_send 修复属原作者。 |
| p070 · 详情/保存失败不错误完成断点 | 3/2/3/3 | 21 | [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) → [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) 09-06 18:56（21 分） | 只评本人追加的两条遗漏路径及回归，不重复原作者 TTL 等修复。 |
| p071 · 外包精确匹配、一致性重算及回归 | 4/3/3/3 | 26 | [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164) → [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164) 10-03 09:02（26 分） | 只计精确匹配、等级/时间戳、配置重算、数据与测试改动；既有关键词引擎和库不算从零原创。 |
| p072 · Agent API 本机访问及确认/任务保护 | 4/2/5/3 | 27 | [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) → [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) 09-15 18:24（27 分） | 只计 c5c7452 / 4ba0a16 的保护与测试；原 Agent API 能力属 kai。 |
| p073 · 智联普通登录提示与真实登录墙区分 | 3/3/3/3 | 24 | [#254](https://github.com/shengjidaguai-china/BossHunter/pull/254) → [#254](https://github.com/shengjidaguai-china/BossHunter/pull/254) 09-29 16:41（24 分） | JS 与离线解析共同修复，有定向反例回归。 |

<a id="project-yukinoshi"></a>
### [@yukinoshi](https://github.com/yukinoshi)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p006 · 多 AI 与 Thinking 参数兼容 | 2/3/2/1 | 18 | [#25](https://github.com/shengjidaguai-china/BossHunter/pull/25) · [#28](https://github.com/shengjidaguai-china/BossHunter/pull/28) → [#28](https://github.com/shengjidaguai-china/BossHunter/pull/28) 08-02 23:34（18 分） | 只评 #25 被采用的兼容范围，不将 #28 整体发送重构归给此人。 |
| p007 · Windows 保留端口自动回退 | 2/3/2/2 | 19 | [#48](https://github.com/shengjidaguai-china/BossHunter/pull/48) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（19 分） | 原始修复被整合采用；不重复评分原 PR 和整合 PR。 |
| p008 · 评分字段别名及校验诊断 | 2/3/2/2 | 19 | [#114](https://github.com/shengjidaguai-china/BossHunter/pull/114) → [#114](https://github.com/shengjidaguai-china/BossHunter/pull/114) 08-29 18:51（19 分） | 单组件边界与针对性回归。 |
| p009 · AI 错误分类传播与空响应重试 | 3/3/3/2 | 23 | [#115](https://github.com/shengjidaguai-china/BossHunter/pull/115) → [#115](https://github.com/shengjidaguai-china/BossHunter/pull/115) 08-29 19:09（23 分） | 评分、招呼语及异常分类联动，保留重试与暂停语义。 |
| p010 · 暂停评分自愈与失败落库 | 3/3/3/2 | 23 | [#117](https://github.com/shengjidaguai-china/BossHunter/pull/117) → [#117](https://github.com/shengjidaguai-china/BossHunter/pull/117) 08-29 19:04（23 分） | 服务端恢复与前端启动链路联动，活跃任务保护。 |
| p011 · 配置凭据优先级一致 | 3/3/3/2 | 23 | [#118](https://github.com/shengjidaguai-china/BossHunter/pull/118) → [#118](https://github.com/shengjidaguai-china/BossHunter/pull/118) 08-29 19:24（23 分） | 配置、读取、预检与展示一致性，不宣称新增凭据隔离系统。 |
| p012 · 删除岗位不打断整批评分 | 2/2/3/2 | 18 | [#77](https://github.com/shengjidaguai-china/BossHunter/pull/77) → [#77](https://github.com/shengjidaguai-china/BossHunter/pull/77) 09-06 15:11（18 分） | 只评 db8db19 实际修复；冲突处理和自测不另算维护分。 |
| p013 · 招呼语工作流既有回归适配 | 2/0/2/2 | 10 | [#82](https://github.com/shengjidaguai-china/BossHunter/pull/82) · [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) → [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) 09-12 20:26（10 分） | 只评 85b7cf7 测试改写，不重复取得原功能分。 |
| p014 · 城市快照测试夹具与注释适配 | 1/0/1/2 | 6 | [#156](https://github.com/shengjidaguai-china/BossHunter/pull/156) → [#156](https://github.com/shengjidaguai-china/BossHunter/pull/156) 09-06 15:44（6 分） | 073459a 的四个未知城市用例修正；不计入快照数据主体。 |

<a id="project-shuaigechz-cloud"></a>
### [@shuaigechz-cloud](https://github.com/shuaigechz-cloud)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p027 · 对应会话的发送送达验证 | 2/3/4/2 | 23 | [#49](https://github.com/shengjidaguai-china/BossHunter/pull/49) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（23 分） | 仅已采用的会话证据，不把输入框清空当送达。 |
| p028 · HR、自身与系统消息方向 | 2/3/3/2 | 21 | [#50](https://github.com/shengjidaguai-china/BossHunter/pull/50) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（21 分） | 实际消息分类与回归，减少误触发。 |
| p029 · 确定性招呼语风格规则 | 3/3/2/2 | 21 | [#51](https://github.com/shengjidaguai-china/BossHunter/pull/51) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（21 分） | 不重复计算后续预览/确认流程。 |
| p030 · 原文和优化预览、显式选择 | 4/4/4/3 | 31 | [#82](https://github.com/shengjidaguai-china/BossHunter/pull/82) · [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) → [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) 09-12 20:26（31 分） | 只评 #82 的选择流程；#211 负责人并发加固、其他人任务面板和测试各自分开。 |
| p031 · 可编辑、预览并人工确认的定制简历 | 5/5/4/3 | 36 | [#143](https://github.com/shengjidaguai-china/BossHunter/pull/143) → [#143](https://github.com/shengjidaguai-china/BossHunter/pull/143) 09-06 18:15（36 分） | 生成、PDF/PNG 渲染、数据库与审核接口的已采用完整链路。 |
| p032 · 建议提示、栏目名与运行时探测边界 | 2/2/2/2 | 16 | [#227](https://github.com/shengjidaguai-china/BossHunter/pull/227) · [#237](https://github.com/shengjidaguai-china/BossHunter/pull/237) → [#237](https://github.com/shengjidaguai-china/BossHunter/pull/237) 09-23 00:28（16 分） | 只计 #237 明确采用的三项小范围内容；不计未采用的整套发送/监测改动。 |

<a id="project-d1822787566"></a>
### [@D1822787566](https://github.com/D1822787566)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p103 · 手动岗位状态和历史入口 | 4/3/2/2 | 23 | [#259](https://github.com/shengjidaguai-china/BossHunter/pull/259) → [#259](https://github.com/shengjidaguai-china/BossHunter/pull/259) 10-01 15:29（23 分） | 只评实际合并版本；feng 未采用并发补丁不冒充本次已修复。 |
| p104 · 岗位池多选筛选与导出一致性 | 4/3/2/2 | 23 | [#261](https://github.com/shengjidaguai-china/BossHunter/pull/261) → [#261](https://github.com/shengjidaguai-china/BossHunter/pull/261) 10-01 15:32（23 分） | 完整功能只计一次；后续两个独立的小范围体验和边界目标只评其增量。 |
| p105 · 筛选菜单键盘及外部点击可访问性 | 1/2/1/2 | 12 | [#272](https://github.com/shengjidaguai-china/BossHunter/pull/272) → [#272](https://github.com/shengjidaguai-china/BossHunter/pull/272) 10-08 21:36（12 分） | 只评 Escape、焦点与外部点击退出目标，不再获得完整多选功能分。 |
| p106 · 空白学历在前后端一致归为未知 | 1/1/1/2 | 9 | [#273](https://github.com/shengjidaguai-china/BossHunter/pull/273) → [#273](https://github.com/shengjidaguai-china/BossHunter/pull/273) 10-09 07:40（9 分） | 只评一处边界一致性与回归，不再次取得查询功能分。 |
| p107 · 首次使用跨页交互引导 | 4/3/1/3 | 22 | [#276](https://github.com/shengjidaguai-china/BossHunter/pull/276) → [#276](https://github.com/shengjidaguai-china/BossHunter/pull/276) 10-08 21:57（22 分） | 实际控件、高亮、保存及预检步骤，不把教程当自动配置系统。 |
| p108 · 采集统计及有界错误明细持久化 | 4/3/3/3 | 26 | [#278](https://github.com/shengjidaguai-china/BossHunter/pull/278) → [#278](https://github.com/shengjidaguai-china/BossHunter/pull/278) 10-12 10:44（26 分） | 采集到存储和前端展示联动；有异常脱敏与续采回归。 |

<a id="project-zhenian-666"></a>
### [@zhenian-666](https://github.com/zhenian-666)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p021 · 多范围 CSV/XLSX 导出与城市目录 | 3/3/2/2 | 21 | [#40](https://github.com/shengjidaguai-china/BossHunter/pull/40) · [#41](https://github.com/shengjidaguai-china/BossHunter/pull/41) → [#41](https://github.com/shengjidaguai-china/BossHunter/pull/41) 08-13 20:18（21 分） | 源方案一次采用；不使用原 PR 全部意图评分。 |
| p022 · 岗位回收站和恢复边界 | 4/3/3/3 | 26 | [#40](https://github.com/shengjidaguai-china/BossHunter/pull/40) · [#42](https://github.com/shengjidaguai-china/BossHunter/pull/42) → [#42](https://github.com/shengjidaguai-china/BossHunter/pull/42) 08-13 20:19（26 分） | API、存储、页面与恢复兼容形成完整链路。 |
| p023 · 独立 AI 评分与恢复流程 | 4/4/3/3 | 29 | [#40](https://github.com/shengjidaguai-china/BossHunter/pull/40) · [#43](https://github.com/shengjidaguai-china/BossHunter/pull/43) → [#43](https://github.com/shengjidaguai-china/BossHunter/pull/43) 08-13 20:19（29 分） | 单独任务、状态与前端流程，和回收站分开。 |
| p024 · 统一采集架构与智联只读采集 | 5/5/3/2 | 33 | [#45](https://github.com/shengjidaguai-china/BossHunter/pull/45) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（33 分） | 只读采集已采用；原分支发送和监测未采用，不计。 |

<a id="project-yuj-029"></a>
### [@yuj-029](https://github.com/yuj-029)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p039 · 51job 只读采集核心与页面研究 | 4/5/2/2 | 29 | [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（29 分） | 以 #62 对 #58 的采用说明为证；未采用独立数据库和额外节奏器不计。 |
| p040 · 51job API 采样、分页及断点核心 | 4/4/3/2 | 28 | [#81](https://github.com/shengjidaguai-china/BossHunter/pull/81) · [#142](https://github.com/shengjidaguai-china/BossHunter/pull/142) → [#142](https://github.com/shengjidaguai-china/BossHunter/pull/142) 09-01 19:21（28 分） | 不把负责人的 fail-closed 加固或 yuppie 的专项测试归给原作者。 |
| p041 · 51job 共享薪资预筛及标题空白兼容 | 2/3/2/2 | 19 | [#270](https://github.com/shengjidaguai-china/BossHunter/pull/270) → [#270](https://github.com/shengjidaguai-china/BossHunter/pull/270) 10-08 22:00（19 分） | 与新 API 采集能力不同的现有逻辑修复。 |

<a id="project-gioiazheng"></a>
### [@GioiaZheng](https://github.com/GioiaZheng)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p001 · PDF 依赖可选降级 | 1/1/1/2 | 9 | [#6](https://github.com/shengjidaguai-china/BossHunter/pull/6) → [#6](https://github.com/shengjidaguai-china/BossHunter/pull/6) 06-07 15:35（9 分） | 局部依赖修复及回归，不按新增功能评价。 |
| p002 · 凭据脱敏、统一安全读取 | 3/2/4/3 | 23 | [#7](https://github.com/shengjidaguai-china/BossHunter/pull/7) · [#8](https://github.com/shengjidaguai-china/BossHunter/pull/8) → [#8](https://github.com/shengjidaguai-china/BossHunter/pull/8) 06-07 15:24（21 分）；[#7](https://github.com/shengjidaguai-china/BossHunter/pull/7) 06-07 15:24（2 分） | 两次同目标交付合为一项；配置与凭据读取边界联动，含回归。 |
| p003 · 人工确认与招呼语使用说明 | 1/1/1/1 | 8 | [#9](https://github.com/shengjidaguai-china/BossHunter/pull/9) → [#9](https://github.com/shengjidaguai-china/BossHunter/pull/9) 06-07 15:24（8 分） | 仅采用的帮助和规则说明，不把文档当成新确认机制。 |
| p004 · 移除不支持的 AI 选项 | 1/1/1/1 | 8 | [#10](https://github.com/shengjidaguai-china/BossHunter/pull/10) → [#10](https://github.com/shengjidaguai-china/BossHunter/pull/10) 06-07 15:41（8 分） | 局部配置兼容，未增加新服务商能力。 |
| p005 · 限定可发送的 ready 岗位 | 2/3/4/2 | 23 | [#12](https://github.com/shengjidaguai-china/BossHunter/pull/12) → [#12](https://github.com/shengjidaguai-china/BossHunter/pull/12) 06-07 15:24（23 分） | 发送选择安全及回归，属于独立已采用修复。 |

<a id="project-pikachuprogrammer01"></a>
### [@pikachuprogrammer01](https://github.com/pikachuprogrammer01)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p082 · 简历拖放、原件保留与双预览 | 4/4/4/3 | 31 | [#176](https://github.com/shengjidaguai-china/BossHunter/pull/176) → [#176](https://github.com/shengjidaguai-china/BossHunter/pull/176) 09-08 21:57（31 分） | 上传、读取、生命周期和前后端兼容链路。 |
| p083 · macOS 启动器及安装指南 | 3/3/2/3 | 22 | [#238](https://github.com/shengjidaguai-china/BossHunter/pull/238) → [#238](https://github.com/shengjidaguai-china/BossHunter/pull/238) 09-27 16:48（22 分） | 含空格路径等回归；不声称真实 macOS 全链路已测。 |

<a id="project-zepengfan145-netizen"></a>
### [@zepengfan145-netizen](https://github.com/zepengfan145-netizen)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p119 · 招呼语队列进度与真实任务状态 | 3/2/1/2 | 16 | [#86](https://github.com/shengjidaguai-china/BossHunter/pull/86) → [#86](https://github.com/shengjidaguai-china/BossHunter/pull/86) 08-30 17:33（16 分） | 发送日志、前端回显和针对性回归；不把此可见性改进当发送安全系统。 |
| p120 · 拒绝招呼语编造的未提供网址 | 2/3/3/2 | 21 | [#88](https://github.com/shengjidaguai-china/BossHunter/pull/88) → [#88](https://github.com/shengjidaguai-china/BossHunter/pull/88) 08-30 17:36（21 分） | Prompt 与保存前确定性白名单校验、失败重试和回归；不涉及新增外发权限。 |
| p121 · 失败招呼语复用直接发送通道 | 2/3/1/1 | 16 | [#145](https://github.com/shengjidaguai-china/BossHunter/pull/145) → [#145](https://github.com/shengjidaguai-china/BossHunter/pull/145) 09-08 13:14（16 分） | 原作者 direct_send 接线、按钮防重复与等待反馈；feng 后补常驻提示和回归另列。 |

<a id="project-haohao-fly"></a>
### [@haohao-fly](https://github.com/haohao-fly)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p017 · 岗位查询、筛选、分页与运行统计 | 4/4/3/2 | 28 | [#38](https://github.com/shengjidaguai-china/BossHunter/pull/38) · [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) → [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) 08-13 20:18（28 分） | 只计最终采用的服务端查询与任务展示范围；未采用的活跃度预筛、并行采集不计。 |
| p018 · 投递队列与任务冲突保护 | 3/3/3/2 | 23 | [#38](https://github.com/shengjidaguai-china/BossHunter/pull/38) · [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) → [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) 08-13 20:18（23 分） | 与查询展示目标独立；不把负责人整合加固再次归属原作者。 |

<a id="project-hdfhssg"></a>
### [@hdfhssg](https://github.com/hdfhssg)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p033 · 学历与招聘类型配置、筛选和评分上下文 | 4/4/2/2 | 26 | [#54](https://github.com/shengjidaguai-china/BossHunter/pull/54) · [#55](https://github.com/shengjidaguai-china/BossHunter/pull/55) · [#64](https://github.com/shengjidaguai-china/BossHunter/pull/64) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（26 分） | 多个源 PR 的同一成果合并计一次，不按 PR 数重复。 |
| p034 · 岗位池排序分页、队列与额度提示 | 4/3/2/2 | 23 | [#55](https://github.com/shengjidaguai-china/BossHunter/pull/55) · [#65](https://github.com/shengjidaguai-china/BossHunter/pull/65) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（23 分） | 已采用的另一组岗位整理及任务展示成果；负责人新增发送校验不归此人。 |

<a id="project-hr18798895295"></a>
### [@Hr18798895295](https://github.com/Hr18798895295)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p112 · Windows 新手安装引导 | 2/2/1/1 | 13 | [#280](https://github.com/shengjidaguai-china/BossHunter/pull/280) → [#280](https://github.com/shengjidaguai-china/BossHunter/pull/280) 10-12 11:41（13 分） | 完整的安装说明及常见路径边界；只计文档可用性，未真机安装，不取得启动器代码或发送保护分。 |
| p113 · 发送时间窗口严格校验与最终边界检查 | 5/4/5/3 | 35 | [#280](https://github.com/shengjidaguai-china/BossHunter/pull/280) → [#280](https://github.com/shengjidaguai-china/BossHunter/pull/280) 10-12 11:41（35 分） | 配置、API、任务及等待/提交多入口不变量，和安装说明分开。 |

<a id="project-rainmemery"></a>
### [@Rainmemery](https://github.com/Rainmemery)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p090 · 测试恢复 Python 3.10 兼容 | 1/0/1/1 | 5 | [#220](https://github.com/shengjidaguai-china/BossHunter/pull/220) → [#220](https://github.com/shengjidaguai-china/BossHunter/pull/220) 09-13 22:44（5 分） | 局部测试导入兼容修复，无新增用户功能或专项行为回归，不套产品升级档。 |
| p091 · 按实际字体轮廓重建薪资映射 | 4/4/3/3 | 29 | [#225](https://github.com/shengjidaguai-china/BossHunter/pull/225) → [#225](https://github.com/shengjidaguai-china/BossHunter/pull/225) 09-19 11:25（29 分） | 字体来源、轮廓匹配、缓存刷新与失败回退形成完整解码目标。 |
| p092 · 评分弹窗与启动回调错误传播增量 | 2/2/1/2 | 14 | [#226](https://github.com/shengjidaguai-china/BossHunter/pull/226) → [#226](https://github.com/shengjidaguai-china/BossHunter/pull/226) 09-19 11:32（14 分） | #206 已采用的采集防抖不重新计；只计后续评分弹窗和回调/预检增量。 |

<a id="project-meixiaoxie"></a>
### [@meixiaoxie](https://github.com/meixiaoxie)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p019 · 结构化评分及可靠请求处理 | 3/4/3/2 | 26 | [#37](https://github.com/shengjidaguai-china/BossHunter/pull/37) · [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) → [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) 08-13 20:18（26 分） | 只计实际采用的评分结构、错误重试与安全暂停；不重复归给 #38。 |
| p020 · 配置原子保存及下载脱敏 | 2/2/4/2 | 20 | [#37](https://github.com/shengjidaguai-china/BossHunter/pull/37) · [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) → [#39](https://github.com/shengjidaguai-china/BossHunter/pull/39) 08-13 20:18（20 分） | 独立的配置可靠性与敏感信息保护目标。 |

<a id="project-erickingwhy"></a>
### [@EricKingWhy](https://github.com/EricKingWhy)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p109 · Windows 启动器复用仓库虚拟环境 | 2/3/2/2 | 19 | [#263](https://github.com/shengjidaguai-china/BossHunter/pull/263) → [#263](https://github.com/shengjidaguai-china/BossHunter/pull/263) 10-01 15:25（19 分） | 独立安装可用性修复。 |
| p110 · 城市多选及中文查询参数解码 | 4/3/3/3 | 26 | [#269](https://github.com/shengjidaguai-china/BossHunter/pull/269) → [#269](https://github.com/shengjidaguai-china/BossHunter/pull/269) 10-08 21:08（26 分） | 服务端/导出/工作台一致性，中文修复为该查询交付的组成部分。 |

<a id="project-nourishman"></a>
### [@Nourishman](https://github.com/Nourishman)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p025 · 文字层 PDF 与模型 ID 规范化 | 2/3/2/2 | 19 | [#29](https://github.com/shengjidaguai-china/BossHunter/pull/29) · [#44](https://github.com/shengjidaguai-china/BossHunter/pull/44) → [#44](https://github.com/shengjidaguai-china/BossHunter/pull/44) 08-13 20:52（19 分） | 原 #29 选择性采用部分，不计 OCR 等未交付范围。 |
| p026 · 岗位恢复和确认交接竞态 | 2/3/3/2 | 21 | [#29](https://github.com/shengjidaguai-china/BossHunter/pull/29) · [#44](https://github.com/shengjidaguai-china/BossHunter/pull/44) → [#44](https://github.com/shengjidaguai-china/BossHunter/pull/44) 08-13 20:52（21 分） | 只评实际采用的状态修复，与 PDF 兼容目标独立。 |

<a id="project-spades6"></a>
### [@Spades6](https://github.com/Spades6)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p074 · 猎聘面板配置、筛选和导出入口 | 4/4/2/2 | 26 | [#139](https://github.com/shengjidaguai-china/BossHunter/pull/139) → [#139](https://github.com/shengjidaguai-china/BossHunter/pull/139) 09-09 17:33（26 分） | 完整接通已存在的后端能力，不重新取得猎聘采集器分。 |
| p075 · 简历相对路径按配置目录解析 | 1/2/2/2 | 14 | [#215](https://github.com/shengjidaguai-china/BossHunter/pull/215) → [#215](https://github.com/shengjidaguai-china/BossHunter/pull/215) 09-12 21:04（14 分） | 局部路径一致性修复，有 decoy cwd 回归。 |

<a id="project-hebuyu688"></a>
### [@Hebuyu688](https://github.com/Hebuyu688)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p079 · AI 请求诊断与模型别名兼容 | 2/2/2/2 | 16 | [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172) → [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172) 09-06 16:00（16 分） | 只计新增代理隔离、错误归类和别名解析。 |
| p080 · 薪资区间与招呼语事实边界 | 2/3/2/2 | 19 | [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172) → [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172) 09-06 16:00（19 分） | 采用的预筛区间、正向依据与毕业届别校验，非整套生成重写。 |

<a id="project-pototoooo"></a>
### [@Pototoooo](https://github.com/Pototoooo)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p101 · 仅实习模式及配置/详情/发送保护 | 5/4/5/3 | 35 | [#256](https://github.com/shengjidaguai-china/BossHunter/pull/256) → [#256](https://github.com/shengjidaguai-china/BossHunter/pull/256) 10-08 21:16（35 分） | #264 已单独采用的 jobType 编码不再计入本项；计其独立三层保护和回归。 |

<a id="project-kai04072911-sudo"></a>
### [@kai04072911-sudo](https://github.com/kai04072911-sudo)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p089 · 本机 Agent 受控工作流 API | 4/5/3/3 | 32 | [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) → [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) 09-15 18:24（32 分） | 以实际主线 069cb0a 采用为准；不重复给 feng 的访问与确认加固实现。 |

<a id="project-zerotwo0617"></a>
### [@zeroTwo0617](https://github.com/zeroTwo0617)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p122 · 岗位池打开 BOSS 原职位入口 | 1/2/0/0 | 8 | [#112](https://github.com/shengjidaguai-china/BossHunter/pull/112) · [#123](https://github.com/shengjidaguai-china/BossHunter/pull/123) → [#123](https://github.com/shengjidaguai-china/BossHunter/pull/123) 08-29 19:33（8 分） | 只评原始入口；负责人补充的域名校验、相对链接兼容和构建不算原作者成果。 |
| p123 · 简历生成失败重试、放弃与历史处理 | 4/3/3/1 | 24 | [#92](https://github.com/shengjidaguai-china/BossHunter/pull/92) → [#92](https://github.com/shengjidaguai-china/BossHunter/pull/92) 09-08 13:13（24 分） | 前后端和历史状态联动；保护后续状态，不将负责人后补强化测试当原作者交付。 |

<a id="project-zh-hanlabs"></a>
### [@zh-hanlabs](https://github.com/zh-hanlabs)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p099 · 开发安装指引与平台说明校正 | 1/1/1/1 | 8 | [#250](https://github.com/shengjidaguai-china/BossHunter/pull/250) · [#251](https://github.com/shengjidaguai-china/BossHunter/pull/251) → [#251](https://github.com/shengjidaguai-china/BossHunter/pull/251) 09-27 17:05（3 分）；[#250](https://github.com/shengjidaguai-china/BossHunter/pull/250) 09-28 14:42（5 分） | 两项小文档校正合并为同类维护文档交付。 |
| p100 · 智联和猎聘共享薪资预筛 | 3/3/3/3 | 24 | [#252](https://github.com/shengjidaguai-china/BossHunter/pull/252) → [#252](https://github.com/shengjidaguai-china/BossHunter/pull/252) 09-28 14:39（24 分） | 抽取共用规则并接入多个采集路径，含定向回归。 |

<a id="project-atticus-zhou"></a>
### [@atticus-zhou](https://github.com/atticus-zhou)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p015 · 评分、招呼语及发送可靠性的代码实现 | 4/4/4/2 | 30 | [#27](https://github.com/shengjidaguai-china/BossHunter/pull/27) · [#28](https://github.com/shengjidaguai-china/BossHunter/pull/28) → [#28](https://github.com/shengjidaguai-china/BossHunter/pull/28) 08-02 23:34（30 分） | #28 明确确认 #27 分支代码作者；仅评其已有来源证实的实现方向，负责人新增整合与全版本功能不全归属此人。 |

<a id="project-chnerui"></a>
### [@CHNERUI](https://github.com/CHNERUI)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p115 · 浏览器测试隔离真实标签页 | 1/1/2/2 | 11 | [#292](https://github.com/shengjidaguai-china/BossHunter/pull/292) → [#292](https://github.com/shengjidaguai-china/BossHunter/pull/292) 10-25 09:58（11 分） | 针对测试副作用的独立修复。 |
| p116 · HR 名称和中文活跃标签解析 | 2/3/2/2 | 19 | [#295](https://github.com/shengjidaguai-china/BossHunter/pull/295) → [#295](https://github.com/shengjidaguai-china/BossHunter/pull/295) 10-27 13:14（19 分） | 字段选择器和统一正则回归为同一提取修复。 |

<a id="project-gaogao34"></a>
### [@gaogao34](https://github.com/gaogao34)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p124 · BOSS 搜索筛选与配置传递 | 3/3/1/0 | 17 | [#104](https://github.com/shengjidaguai-china/BossHunter/pull/104) · [#125](https://github.com/shengjidaguai-china/BossHunter/pull/125) → [#125](https://github.com/shengjidaguai-china/BossHunter/pull/125) 08-29 19:58（17 分） | 只计原始筛选与接线；负责人重整的严格值校验、正常队列加固和回归不转记。原自动投递循环未采用。 |
| p125 · 保留人工或已有招呼语 | 1/2/2/0 | 12 | [#104](https://github.com/shengjidaguai-china/BossHunter/pull/104) · [#125](https://github.com/shengjidaguai-china/BossHunter/pull/125) → [#125](https://github.com/shengjidaguai-china/BossHunter/pull/125) 08-29 19:58（12 分） | 只计原始跳过覆盖的保护目标；负责人补全 ready 状态及报告不重复归给原作者。 |

<a id="project-1028huli"></a>
### [@1028huli](https://github.com/1028huli)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p087 · AI 模型列表草稿查询与选择 | 4/3/4/3 | 28 | [#212](https://github.com/shengjidaguai-china/BossHunter/pull/212) → [#212](https://github.com/shengjidaguai-china/BossHunter/pull/212) 09-12 21:25（28 分） | 前后端、两协议、分页及 URL/凭据边界，查询不落盘。 |

<a id="project-bactdt"></a>
### [@bactdt](https://github.com/bactdt)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p042 · 招呼语后台生成、编辑和重生成 | 4/4/3/2 | 28 | [#90](https://github.com/shengjidaguai-china/BossHunter/pull/90) · [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) → [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) 09-12 20:26（28 分） | 以 #211 保留的原实现署名为准；不将未知账号变化当新贡献者。 |

<a id="project-likris588-ux"></a>
### [@likris588-ux](https://github.com/likris588-ux)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p043 · 猎聘只读采集器原始实现 | 4/5/2/1 | 28 | [#89](https://github.com/shengjidaguai-china/BossHunter/pull/89) · [#121](https://github.com/shengjidaguai-china/BossHunter/pull/121) · [#127](https://github.com/shengjidaguai-china/BossHunter/pull/127) → [#127](https://github.com/shengjidaguai-china/BossHunter/pull/127) 08-29 20:18（28 分） | 仅原始列表、详情、分页及城市能力；yuppie 的独立测试和负责人加固不重复归属。 |

<a id="project-bianshilong0604"></a>
### [@bianshilong0604](https://github.com/bianshilong0604)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p038 · 持久化评分解释及只读 API | 4/3/3/3 | 26 | [#77](https://github.com/shengjidaguai-china/BossHunter/pull/77) → [#77](https://github.com/shengjidaguai-china/BossHunter/pull/77) 09-06 15:11（26 分） | 白名单快照、数据库、API 与降级语义；yuki 的批次修复单列。 |

<a id="project-miaomiao636"></a>
### [@miaomiao636](https://github.com/miaomiao636)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p088 · 本地面试准备交接与 Markdown 降级 | 3/3/4/3 | 26 | [#217](https://github.com/shengjidaguai-china/BossHunter/pull/217) → [#217](https://github.com/shengjidaguai-china/BossHunter/pull/217) 10-09 22:10（26 分） | 最小字段、显式同意和来源/窗口/版本绑定；未把外部接收端能力算本项目已完成。 |

<a id="project-petalecho"></a>
### [@PetalEcho](https://github.com/PetalEcho)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p111 · 公司屏蔽预览确认及历史隐藏 | 4/3/3/3 | 26 | [#271](https://github.com/shengjidaguai-china/BossHunter/pull/271) → [#271](https://github.com/shengjidaguai-china/BossHunter/pull/271) 10-12 10:41（26 分） | 前后端并发与分页一致性，保留岗位原始状态。 |

<a id="project-xingeeks"></a>
### [@xinGeeks](https://github.com/xinGeeks)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p077 · 外包判定接入、持久化和初版徽标 | 4/4/2/2 | 26 | [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164) → [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164) 10-03 09:02（26 分） | 只计已有检测模块的激活、数据库和展示；不把既有 621 行引擎及关键词全归原创。 |

<a id="project-c4002159"></a>
### [@c4002159](https://github.com/c4002159)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p114 · 51job 空响应有界重试与降速 | 3/3/3/3 | 24 | [#288](https://github.com/shengjidaguai-china/BossHunter/pull/288) → [#288](https://github.com/shengjidaguai-china/BossHunter/pull/288) 10-24 11:49（24 分） | 真实风控继续停止，只恢复瞬时无响应。 |

<a id="project-fenghuangyuan1412"></a>
### [@fenghuangyuan1412](https://github.com/fenghuangyuan1412)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p096 · 元/千/万及年薪的预筛解析 | 2/4/3/2 | 24 | [#241](https://github.com/shengjidaguai-china/BossHunter/pull/241) → [#241](https://github.com/shengjidaguai-china/BossHunter/pull/241) 09-23 00:18（24 分） | 恢复多平台主要筛选场景；保留无单位不猜测的边界。 |

<a id="project-qingmuy"></a>
### [@qingmuy](https://github.com/qingmuy)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p098 · 仅 WebSocket 的 Chrome 调试发现 | 3/3/3/3 | 24 | [#249](https://github.com/shengjidaguai-china/BossHunter/pull/249) → [#249](https://github.com/shengjidaguai-china/BossHunter/pull/249) 09-27 17:01（24 分） | 真实握手、路径卫生及陈旧端点防护，跨发现/Runtime 兼容。 |

<a id="project-solplum"></a>
### [@solplum](https://github.com/solplum)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p095 · 浏览器导航、连接及卡片重试 | 3/3/3/2 | 23 | [#233](https://github.com/shengjidaguai-china/BossHunter/pull/233) → [#233](https://github.com/shengjidaguai-china/BossHunter/pull/233) 09-19 11:42（23 分） | 三处稳定性目标合并为同一浏览器恢复事项；旧账号同一 ID 已核实。 |

<a id="project-txz990"></a>
### [@txz990](https://github.com/txz990)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p076 · 真实发送失败原因与关闭岗位诊断 | 3/3/3/2 | 23 | [#161](https://github.com/shengjidaguai-china/BossHunter/pull/161) → [#161](https://github.com/shengjidaguai-china/BossHunter/pull/161) 09-05 19:43（23 分） | 存储迁移、多个失败写入点和前端读取一致，复用现有标签页。 |

<a id="project-1115yt"></a>
### [@1115yt](https://github.com/1115yt)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p097 · salary=403 不再误触安全暂停 | 2/3/3/2 | 21 | [#247](https://github.com/shengjidaguai-china/BossHunter/pull/247) → [#247](https://github.com/shengjidaguai-china/BossHunter/pull/247) 09-27 16:36（21 分） | 修正错误路径识别，不削弱真实风控信号。 |

<a id="project-henry369-0"></a>
### [@Henry369-0](https://github.com/Henry369-0)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p035 · Windows 一键启动器和桌面快捷方式 | 3/3/2/2 | 21 | [#57](https://github.com/shengjidaguai-china/BossHunter/pull/57) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（21 分） | 脚本、路径覆盖及说明形成已采用启动体验。 |

<a id="project-lau0708"></a>
### [@lau0708](https://github.com/lau0708)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p093 · 浅色、深色及系统主题 | 4/3/1/2 | 21 | [#221](https://github.com/shengjidaguai-china/BossHunter/pull/221) → [#221](https://github.com/shengjidaguai-china/BossHunter/pull/221) 09-19 21:01（21 分） | 全局 token、持久化、防闪烁与页面迁移，一项完整主题成果。 |

<a id="project-lujie-cmd"></a>
### [@lujie-cmd](https://github.com/lujie-cmd)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p117 · XLSX 外部字符串防公式解释 | 2/2/4/2 | 20 | [#300](https://github.com/shengjidaguai-china/BossHunter/pull/300) → [#300](https://github.com/shengjidaguai-china/BossHunter/pull/300) 10-30 16:16（20 分） | 与已有 CSV 规则共用判定，保留数值字段及回归。 |

<a id="project-caojun1015"></a>
### [@CaoJun1015](https://github.com/CaoJun1015)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p084 · AI 运行环境异常独立诊断 | 2/3/2/2 | 19 | [#179](https://github.com/shengjidaguai-china/BossHunter/pull/179) → [#179](https://github.com/shengjidaguai-china/BossHunter/pull/179) 09-06 00:29（19 分） | 请求前错误分类、版本提示和敏感错误防泄漏。 |

<a id="project-cangyuyi"></a>
### [@cangyuyi](https://github.com/cangyuyi)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p086 · 趋势、高分公司及最近活动工作台 | 3/3/1/1 | 18 | [#202](https://github.com/shengjidaguai-china/BossHunter/pull/202) → [#202](https://github.com/shengjidaguai-china/BossHunter/pull/202) 09-09 19:30（18 分） | 只计 fc0acbb 的原始界面实现；负责人后续首页重排与版本发布不全归原作者。 |

<a id="project-heroims"></a>
### [@heroims](https://github.com/heroims)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p081 · macOS TCC 静态资源 403 修复 | 2/3/2/1 | 18 | [#175](https://github.com/shengjidaguai-china/BossHunter/pull/175) → [#175](https://github.com/shengjidaguai-china/BossHunter/pull/175) 09-06 19:52（18 分） | 服务端路径约束与直接读取，恢复工作台可用。 |

<a id="project-changxin-yr"></a>
### [@Changxin-YR](https://github.com/Changxin-YR)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p094 · 失效 CDP 端口校验 | 1/3/2/2 | 17 | [#229](https://github.com/shengjidaguai-china/BossHunter/pull/229) → [#229](https://github.com/shengjidaguai-china/BossHunter/pull/229) 09-19 11:39（17 分） | 用真实服务身份验证避免诱饵端口，有回归。 |

<a id="project-jinxuans"></a>
### [@Jinxuans](https://github.com/Jinxuans)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p102 · BOSS 全职/兼职/实习编码修正 | 1/3/2/2 | 17 | [#264](https://github.com/shengjidaguai-china/BossHunter/pull/264) → [#264](https://github.com/shengjidaguai-china/BossHunter/pull/264) 10-01 16:14（17 分） | 实际先采用的映射和参数化回归；#256 继承后不重复计。 |

<a id="project-acnhong"></a>
### [@AcNHong](https://github.com/AcNHong)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p037 · 标签失焦提交与输入法兼容 | 1/2/1/1 | 11 | [#69](https://github.com/shengjidaguai-china/BossHunter/pull/69) → [#69](https://github.com/shengjidaguai-china/BossHunter/pull/69) 09-09 17:29（11 分） | 最终仅单文件输入修复，移除的薪资功能不计。 |

<a id="project-hanmmjade"></a>
### [@HanmmJade](https://github.com/HanmmJade)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p078 · 前置全流程预检与关键词提示 | 1/2/1/1 | 11 | [#171](https://github.com/shengjidaguai-china/BossHunter/pull/171) → [#171](https://github.com/shengjidaguai-china/BossHunter/pull/171) 09-06 11:38（11 分） | 复用已有预检能力的页面入口，不当成新预检系统。 |

<a id="project-kgleonc"></a>
### [@kgleonc](https://github.com/kgleonc)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p085 · 安装指南补前端构建步骤 | 1/2/1/1 | 11 | [#197](https://github.com/shengjidaguai-china/BossHunter/pull/197) → [#197](https://github.com/shengjidaguai-china/BossHunter/pull/197) 09-07 20:34（11 分） | 修复可复现的安装说明缺失，不按完整构建系统评分。 |

<a id="project-colin-cai0318"></a>
### [@Colin-Cai0318](https://github.com/Colin-Cai0318)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p036 · Markdown 上传 UTF-8 校验 | 1/1/2/1 | 10 | [#61](https://github.com/shengjidaguai-china/BossHunter/pull/61) · [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) → [#62](https://github.com/shengjidaguai-china/BossHunter/pull/62) 08-25 17:49（10 分） | 简历工作室主体未采用，仅局部上传校验评分。 |

<a id="project-elowenzhouyb-source"></a>
### [@elowenzhouyb-source](https://github.com/elowenzhouyb-source)

| 事项 | E/U/R/Q | 分数 | 原始来源 → 实际采用（北京时间） | 评分与归属理由 |
|---|---|---:|---|---|
| p016 · 可靠性方案与联合署名（待分项） | 0/0/0/0 | 待分项 | [#27](https://github.com/shengjidaguai-china/BossHunter/pull/27) · [#28](https://github.com/shengjidaguai-china/BossHunter/pull/28) → [#28](https://github.com/shengjidaguai-china/BossHunter/pull/28) 08-02 23:34（0 分） | 已确认方案被采用，但无法从当前材料分离出独立实现份额；保留署名，暂不与代码作者重复量化。 |

### 采用归属的补充证据

- [#218 实际采用提交，含 yuppie 任务进度专项测试；PR 当前文件接口不能代替采用提交。](https://github.com/shengjidaguai-china/BossHunter/commit/069cb0a30c5d7205a32ba4b152075ff031b1f587)
- [yukinoshi 在 #77 的批次删除修复](https://github.com/shengjidaguai-china/BossHunter/commit/db8db192e8356615b1674ad2fb3ad23f261294f1)
- [yukinoshi 在 #82→#211 的既有回归适配](https://github.com/shengjidaguai-china/BossHunter/commit/85b7cf780c31394f5c17399c5cb16704e8367108)
- [yuppie 在 #211 的任务面板兼容](https://github.com/shengjidaguai-china/BossHunter/commit/a622b81b12257ad3569cb58c773f555e370b51e4)
- [feng 在 #218 的访问/确认边界补丁](https://github.com/shengjidaguai-china/BossHunter/commit/c5c7452ad00db54df2fa056b3a2c0e1fe2f2fa3b)
- [feng 在 #218 的补丁与测试整合](https://github.com/shengjidaguai-china/BossHunter/commit/4ba0a161bb2053cbe00841454cd537c000b8a0ca)

- #27→#28：atticus 的代码范围与 elow 的方案联合署名分开记录，方案份额待确认，不默认均分。
- #37/#38→#39：评分、配置与岗位/队列分开归属；未采用的低分自动删除、HR 活跃度预筛和并行采集不计。
- #62：各来源按采用说明分开，智联及 51job 原分支未采用的发送/监测能力不计。
- #89→#121→#127：猎聘原采集器归 likris，yuppie 只计可分离测试，负责人后补加固不转记。
- #164：xin 的既有检测接入、存储和初版展示，与 feng 的精确匹配/一致性/回归分别计；既有引擎与关键词库不宣称由两人从零原创。
- #218：采用提交 069cb0a 早于 PR 合并字段，以实际主线提交为日期；kai 的 API、feng 的保护、yuppie 的专项测试分开。接口当前显示空差异不能推翻已经采用的提交。
- #264 先采用的招聘类型编码不再算 #256 的新增实现；#259 未被采用的并发候选补丁不进入项目榜。

## v2.1 审查修正

本次保持权重，纠正证据归属。项目总分仍为 2454；维护总分由 1825 改为 1814（yuppie -6、feng -5），共 172 个已评分个人事项。撤回项不代表当事人没有工作，只表示现有材料不足以独立计分。

| 事项 | 修正 | 依据 |
|---|---:|---|
| m-yuppiez99999-280-b 安装指南 | 撤回 5 | 本人评审仅具体分析发送窗口，未核对安装指南。 |
| m-fengziliang43-cmyk-280-b 安装指南 | 暂缓 5 | 只明确提及指引和启动器测试；测试已计主事项，无独立步骤核验记录。 |
| m-yuppiez99999-202-b 版本一致性 | 6 → 5 | 版本文件及断言静态核对成立；共用构建和交接不重复计，P=0。 |
| m-yuppiez99999-204 与 -204-b | 保留 16+10 | 两种故障各有具体分析和独立修正路线，按不同原文段落分配证据。 |

`scoring_evidence` 保存计分原文的链接、位置和摘录；原始完整评论仍用于审计和覆盖统计。共享证据仅在已经登记范围、原文段落不重叠时通过；不能把这项检查解释成自动识别语义重复或自动评估真实价值。撤回项原文保留在账本 `maintenance_revisions`。

## 维护贡献明细

分档顺序 **E / I / V / P**，得分 `2E+2I+V+P`。下文 172 行均为个人独立事项，不是 172 个不同 PR。某条记录若服务于两个独立目标，分别限定范围并注明；原始正文保留在账本，不能只按下表摘要判定工时。

### [@yuppiez99999](https://github.com/yuppiez99999) · 890 分

| 事项与范围 | E/I/V/P | 分数 | 来源与本人证据 | 评分理由与限制 |
|---|---|---:|---|---|
| feat: 新增可追溯的简历工作室 | 3/2/1/1 | 12 | [#61](https://github.com/shengjidaguai-china/BossHunter/pull/61)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/61#issuecomment-5492464780) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/61#issuecomment-5493600277) | 抽查隐私告知缺口并区分既采用局部与暂缓整体功能，提供里程碑及 CI 交接；不冒认既有发现。 |
| feat: add local OCR fallback for image-only PDF resumes | 1/0/1/1 | 4 | [#67](https://github.com/shengjidaguai-china/BossHunter/pull/67)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/67#issuecomment-5492310019) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/67#issuecomment-5493599908) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/67#pullrequestreview-5124694629) | 具体识别 dist 产物及依赖审批要求，给出可执行清理要求。 |
| fix(web): 保存未回车的标签并兼容中文输入法 | 3/2/1/2 | 13 | [#69](https://github.com/shengjidaguai-china/BossHunter/pull/69) · [Issue #160](https://github.com/shengjidaguai-china/BossHunter/issues/160)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/69#issuecomment-5492221899) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/69#issuecomment-5493599571) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/69#pullrequestreview-5123556659) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/69#pullrequestreview-5149701470) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/69#issuecomment-5596948283) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/issues/160#issuecomment-5519668077) · [本人记录 7](https://github.com/shengjidaguai-china/BossHunter/issues/160#issuecomment-5600342100) · [本人记录 8](https://github.com/shengjidaguai-china/BossHunter/issues/160#issuecomment-5854412281) | 先核对跨域薪资冲突、后确认薪资范围移除及输入法修订收敛；作者构建报告非亲跑。 |
| fix(executor): 修复监控风险检测的掩码误判 | 2/2/1/1 | 10 | [#73](https://github.com/shengjidaguai-china/BossHunter/pull/73)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/73#issuecomment-5492265735) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/73#issuecomment-5493597058) | 既有风险停止保留、缺测试和旧分支分诊；无复现或已修复证据。 |
| feat(score-trace): 新增持久化评分解释 API | 2/2/1/0 | 9 | [#77](https://github.com/shengjidaguai-china/BossHunter/pull/77) · [Issue #70](https://github.com/shengjidaguai-china/BossHunter/issues/70)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/77#issuecomment-5492356447) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/77#issuecomment-5493601219) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/77#pullrequestreview-5124525090) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/issues/70#issuecomment-5493284159) | 评分解释持久化、白名单和断点并存静态核验。 |
| feat: add greeting preview and explicit selection | 3/2/1/1 | 12 | [#82](https://github.com/shengjidaguai-china/BossHunter/pull/82)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/82#issuecomment-5492658909) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/82#issuecomment-5493598278) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/82#pullrequestreview-5142679138) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/82#pullrequestreview-5142706658) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/82#issuecomment-5586357221) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/82#issuecomment-5594949998) | 显式选择、状态保护、前后端和迁移核对，重复批准不升级；同步为机械整合。 |
| feat: 打招呼语生成/编辑/重生成工作流 | 3/3/1/2 | 15 | [#90](https://github.com/shengjidaguai-china/BossHunter/pull/90)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/90#issuecomment-5492104465) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/90#issuecomment-5493599173) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/90#issuecomment-5595748563) | 复查他人提出的 sent 状态保护修订并核对后台任务，另协调 #82 与依赖顺序；不将他人发现记本人。 |
| fix: allow retry and dismiss resume_failed pending items | 3/2/1/2 | 13 | [#92](https://github.com/shengjidaguai-china/BossHunter/pull/92) · [Issue #91](https://github.com/shengjidaguai-china/BossHunter/issues/91)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/92#issuecomment-5492133661) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/92#issuecomment-5493598751) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5124559936) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/92#issuecomment-5558327490) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5137547016) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/issues/91#issuecomment-5493283717) · [本人记录 7](https://github.com/shengjidaguai-china/BossHunter/issues/91#issuecomment-5579650272) | 重试仅生成不发送、状态和失败落库多路径核验；Issue #91 同项归并。；Issue 中本人又逐项核对采用结果并跟进关闭。 |
| feat: BOSS 搜索页筛选条件与投递循环增强 | 2/2/1/1 | 10 | [#104](https://github.com/shengjidaguai-china/BossHunter/pull/104)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/104#issuecomment-5459833276) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/104#pullrequestreview-5056844621) | 采集参数跨域契约核对，明确未覆盖部分和拆分审核交接。 |
| feat: 接入猎聘 Web 面板前端入口 | 3/2/1/2 | 13 | [#139](https://github.com/shengjidaguai-china/BossHunter/pull/139)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/139#issuecomment-5492418549) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/139#issuecomment-5493597853) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/139#pullrequestreview-5084448426) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/139#issuecomment-5556903576) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/139#pullrequestreview-5124681328) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/139#issuecomment-5562418124) · [本人记录 7](https://github.com/shengjidaguai-china/BossHunter/pull/139#pullrequestreview-5137415466) · [本人记录 8](https://github.com/shengjidaguai-china/BossHunter/pull/139#issuecomment-5579676930) · [本人记录 9](https://github.com/shengjidaguai-china/BossHunter/pull/139#pullrequestreview-5137603545) · [本人记录 10](https://github.com/shengjidaguai-china/BossHunter/pull/139#issuecomment-5594950348) | 多平台面板、导出和配置审核，确认产物及 README 冲突修订；重复重批不加。 |
| feat(resume): add reviewable PNG tailoring workflow | 1/1/1/0 | 5 | [#143](https://github.com/shengjidaguai-china/BossHunter/pull/143)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/143#issuecomment-5492172348) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/143#issuecomment-5493600823) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/143#pullrequestreview-5124571223) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/143#issuecomment-5558327607) | 简历母版及预览功能简短核对、引用 CI；未记录系统性独立运行。 |
| fix: 修复发送失败岗位无法重新发送 | 3/2/1/2 | 13 | [#145](https://github.com/shengjidaguai-china/BossHunter/pull/145) · [Issue #144](https://github.com/shengjidaguai-china/BossHunter/issues/144) · [Issue #188](https://github.com/shengjidaguai-china/BossHunter/issues/188)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/145#issuecomment-5492026070) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/145#issuecomment-5493597440) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/145#pullrequestreview-5137546922) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/issues/144#issuecomment-5493283410) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/issues/144#issuecomment-5579650743) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/issues/188#issuecomment-5558380916) · [本人记录 7](https://github.com/shengjidaguai-china/BossHunter/issues/188#issuecomment-5579652810) · [本人记录 8](https://github.com/shengjidaguai-china/BossHunter/issues/188#issuecomment-5595055661) | 重试实际入口、防重和结果反馈核对，Issue #144/#188 同项合并。；Issue 中本人又逐项核对采用结果并跟进关闭。 |
| feat(outsourcing): 公司名后展示 外包 / 疑似外包 徽标 | 4/2/3/2 | 17 | [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/164#pullrequestreview-5123552636) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/164#discussion_r3974700745) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/164#pullrequestreview-5161768710) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/164#issuecomment-5646215560) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/164#issuecomment-5646231323) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/164#issuecomment-5682017377) · [本人记录 7](https://github.com/shengjidaguai-china/BossHunter/pull/164#issuecomment-5807253542) · [本人记录 8](https://github.com/shengjidaguai-china/BossHunter/pull/164#pullrequestreview-5398244306) | 复查精确匹配等他人阻塞修订，独立主线对照及同步后回归；不重复取得实现和原始发现。 |
| 优化 AI 诊断、薪资过滤和招呼语生成 | 2/2/1/1 | 10 | [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/172#pullrequestreview-5121183079) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/172#pullrequestreview-5124689286) | 采集依赖、函数契约和预筛语义跨域审核及冲突协调。 |
| fix(web): 绕过 bottle.static_file 的 os.access 误判，修复 macOS TCC 导致的静态资源 403 | 2/2/1/0 | 9 | [#175](https://github.com/shengjidaguai-china/BossHunter/pull/175)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/175#pullrequestreview-5124545793) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/175#issuecomment-5558327364) | 静态资源读取与路径约束核查，引用 CI 无本机 TCC 复现。 |
| feat(web): 配置页简历拖放上传与 PDF/MD 双预览 | 3/2/1/1 | 12 | [#176](https://github.com/shengjidaguai-china/BossHunter/pull/176)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/176#pullrequestreview-5142494869) | 上传、净化、生命周期与本地预览边界的多组件静态审核。 |
| feat（集合）：补全51job已核验城市编码（31个主要城市） | 3/3/1/1 | 14 | [#181](https://github.com/shengjidaguai-china/BossHunter/pull/181)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/181#pullrequestreview-5123550127) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/181#issuecomment-5558762985) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/181#issuecomment-5559372331) | 与已核验城市来源交叉对照发现 11 处编码不一致，阻止错误数据采用；不按差异数线性加分。 |
| docs: 首页替换为可点击的交互结构图 | 1/0/1/0 | 3 | [#183](https://github.com/shengjidaguai-china/BossHunter/pull/183)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/183#pullrequestreview-5124548213) | 交互图文档与 CI 简单核对，未记录额外验证。 |
| fix: 区分 BOSS 临时风险暂停与采集上限提示 | 3/1/3/0 | 11 | [#189](https://github.com/shengjidaguai-china/BossHunter/pull/189)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/189#pullrequestreview-5125124370) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/189#issuecomment-5596948960) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/189#pullrequestreview-5161673105) | 文案无行为变更核查并独立相关回归、主线失败对照；文案风险低不抬影响档。 |
| fix(web): 添加缺失的favicon，修复浏览器tab图标404 | 2/1/1/2 | 9 | [#193](https://github.com/shengjidaguai-china/BossHunter/pull/193)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/193#issuecomment-5570220242) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/193#issuecomment-5594946884) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/193#issuecomment-5594947106) | 核对 favicon 已被 #202 包含并关闭重复 PR，先前产物提醒合为同项。 |
| feat(web): 工作台首页数据可视化增强 | 1/0/1/1 | 4 | [#195](https://github.com/shengjidaguai-china/BossHunter/pull/195)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/195#issuecomment-5570219921) | 具体要求移除不再跟踪的 dist，未证明关闭或产品修复。 |
| fix(boss): 修复采集跳过、重复翻页和薪资误判，恢复续采及评分进度 | 3/2/1/1 | 12 | [#196](https://github.com/shengjidaguai-china/BossHunter/pull/196)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/196#pullrequestreview-5131629623) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/196#pullrequestreview-5149162331) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/196#issuecomment-5594950667) | BOSS 新搜索与显式续采增量审核，多次批准只计实际增量检查。 |
| feat(web): 精简首页并更新至 v2.4.0 | 3/2/1/1 | 12 | [#202](https://github.com/shengjidaguai-china/BossHunter/pull/202)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5149170728) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5594950956) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5149696877) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5596947759) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5153537016) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5600974302) | 首页原始及精简版多轮审核，机械冲突整合；版本核验另列独立目标。 |
| feat(mobile): 支持手机端移动工作台、触控卡片流与局域网快捷连接 | 3/4/1/1 | 16 | [#204](https://github.com/shengjidaguai-china/BossHunter/pull/204)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/204#pullrequestreview-5149691088) | 发现默认无鉴权全网监听暴露本地简历与密钥的跨入口隐私风险；未修复不算闭环。 |
| 解决大量无法投递，一键投递失败的问题 | 3/3/1/1 | 14 | [#208](https://github.com/shengjidaguai-china/BossHunter/pull/208) · [Issue #187](https://github.com/shengjidaguai-china/BossHunter/issues/187)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/208#discussion_r3967189976) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/208#discussion_r3967189985) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/208#discussion_r3967189995) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/208#discussion_r3967190004) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/208#pullrequestreview-5152864505) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/208#pullrequestreview-5187030700) · [本人记录 7](https://github.com/shengjidaguai-china/BossHunter/pull/208#pullrequestreview-5208789154) · [本人记录 8](https://github.com/shengjidaguai-china/BossHunter/pull/208#pullrequestreview-5208801577) · [本人记录 9](https://github.com/shengjidaguai-china/BossHunter/pull/208#issuecomment-5711976700) · [本人记录 10](https://github.com/shengjidaguai-china/BossHunter/pull/208#pullrequestreview-5243847968) · [本人记录 11](https://github.com/shengjidaguai-china/BossHunter/pull/208#issuecomment-5854337925) · [本人记录 12](https://github.com/shengjidaguai-china/BossHunter/issues/187#issuecomment-5558381158) | 定位偏好指令被直接发送的语义错误并给出拆分修复路线；多次复述未解决不升级 V。 |
| feat: 支持 51job 人工确认后投递在线简历 | 3/3/2/1 | 15 | [#209](https://github.com/shengjidaguai-china/BossHunter/pull/209)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/209#discussion_r3974594352) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/209#discussion_r3974594355) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/209#discussion_r3974594361) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/209#discussion_r3974594368) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/209#pullrequestreview-5161654241) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/209#issuecomment-5682013485) | 复现日志断言回归并分析未明失败的外发边界，阻塞建议有效；不声称已修。 |
| docs: 引导维护者及 AI 在条件齐备后主动合并 | 2/0/1/1 | 6 | [#210](https://github.com/shengjidaguai-china/BossHunter/pull/210)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/210#pullrequestreview-5152900038) | 核对治理锚点、审批人数和主动交接不改变保护条件，规则实现不归审核者。 |
| feat: AI 配置支持获取模型列表并选择模型 | 3/2/2/1 | 13 | [#212](https://github.com/shengjidaguai-china/BossHunter/pull/212)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/212#pullrequestreview-5161688265) | 模型查询路径和数据不落盘核查，记录 Python 定向回归与前端构建。 |
| feat(web): 可选的本地面试准备入口与岗位草稿交接 | 3/2/1/1 | 12 | [#217](https://github.com/shengjidaguai-china/BossHunter/pull/217) · [Issue #216](https://github.com/shengjidaguai-china/BossHunter/issues/216)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/217#issuecomment-5633627889) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/217#pullrequestreview-5471130420) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/216#issuecomment-5641949442) | 本机六字段、显式同意、窗口和版本绑定静态核验；外部接收端未合不算端到端闭环。 |
| fix(tests): 修复 Python 3.10 下 datetime.UTC 导致测试套件无法运行 | 1/1/1/0 | 5 | [#220](https://github.com/shengjidaguai-china/BossHunter/pull/220)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/220#pullrequestreview-5191035777) | Python 3.10 UTC 导入兼容核对，只有测试改动。 |
| feat(web): 支持深色模式与浅色/深色/跟随系统主题切换 | 2/1/1/1 | 8 | [#221](https://github.com/shengjidaguai-china/BossHunter/pull/221)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/221#issuecomment-5681957074) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/221#issuecomment-5693648202) | 冲突、失效批准及新 head 重新审核的具体协调，未替作者实现主题。 |
| fix: 默认详情页上限调整为 900、总页面上限调整为 1100 | 2/2/1/1 | 10 | [#222](https://github.com/shengjidaguai-china/BossHunter/pull/222)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/222#pullrequestreview-5260287342) | 默认额度、运行回退和边界测试设计核对；未将提高预算当安全成果。 |
| feat(boss): 从页面实际加载的字体重建薪资数字映射 | 3/2/1/2 | 13 | [#225](https://github.com/shengjidaguai-china/BossHunter/pull/225) · [Issue #198](https://github.com/shengjidaguai-china/BossHunter/issues/198)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/225#pullrequestreview-5211356365) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/198#issuecomment-5576924904) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/198#issuecomment-5854407599) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/issues/198#issuecomment-5888542487) | 动态字体映射、回退和幂等性核对，Issue #198 相关分诊合并且排除本人 #205 进度。；Issue 中本人又逐项核对采用结果并跟进关闭。 |
| fix(web): 采集/评分弹窗确认后按结果自动关闭并补充加载与失败提示 | 2/1/1/1 | 8 | [#226](https://github.com/shengjidaguai-china/BossHunter/pull/226)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/226#pullrequestreview-5208848006) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/226#issuecomment-5678878386) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/226#pullrequestreview-5219709520) | 弹窗增量、回调返回和重基后变化核对；本人 #206 自测不计入。 |
| feat: 优化招呼语审核、定制简历与回复监测安全 | 3/2/1/0 | 11 | [#227](https://github.com/shengjidaguai-china/BossHunter/pull/227)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/227#pullrequestreview-5219729981) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/227#issuecomment-5739126926) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/227#issuecomment-5742149128) | 招呼语、母版及监测多路径审核；错误的旧批准仍有效说法不计推进。 |
| fix: 跳过已失效的 DevToolsActivePort，避免误连非 CDP 端口 | 2/2/1/1 | 10 | [#229](https://github.com/shengjidaguai-china/BossHunter/pull/229)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/229#pullrequestreview-5233605335) | 陈旧端口根因、诱饵用例及 CI 放行检查，无独立运行声明。 |
| fix(browser): 浏览器链路稳定性三处修复——navigate 超时竞态、CDP attach 重试、智联卡片点击重试 | 3/2/1/1 | 12 | [#233](https://github.com/shengjidaguai-china/BossHunter/pull/233)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/233#pullrequestreview-5233602220) | 浏览器三条恢复路径和 CI 核对，无新增实现。 |
| feat(scripts): macOS 一键启动器与安装指南 | 3/2/1/1 | 12 | [#238](https://github.com/shengjidaguai-china/BossHunter/pull/238) · [Issue #236](https://github.com/shengjidaguai-china/BossHunter/issues/236)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/238#pullrequestreview-5260286687) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/238#pullrequestreview-5329548756) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/236#issuecomment-5742143356) | macOS 脚本及说明核对、基于修订后 CI 的复审；629 passed 未明确本人执行按引用处理。 |
| feat: 支持按 HR 活跃时间筛选与采集过滤 | 2/2/1/1 | 10 | [#239](https://github.com/shengjidaguai-china/BossHunter/pull/239) · [Issue #230](https://github.com/shengjidaguai-china/BossHunter/issues/230)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/239#pullrequestreview-5267186426) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/239#issuecomment-5780166677) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/239#issuecomment-5854337734) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/issues/230#issuecomment-5724560592) | 活跃度采集快照、分页和导出一致性核验，Issue #230 同项。 |
| fix(prefilter): 支持元/千/万年薪格式，修复智联与前程无忧岗位被薪资预筛全量误杀 | 1/2/1/0 | 7 | [#241](https://github.com/shengjidaguai-china/BossHunter/pull/241) · [Issue #240](https://github.com/shengjidaguai-china/BossHunter/issues/240)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/241#pullrequestreview-5267185872) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/240#issuecomment-5761321840) | 薪资单位解析和定向测试设计简短审核，Issue #240 同项。 |
| fix(boss): 避免搜索参数误触发 403 风控 | 2/2/1/1 | 10 | [#247](https://github.com/shengjidaguai-china/BossHunter/pull/247) · [Issue #243](https://github.com/shengjidaguai-china/BossHunter/issues/243)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/247#pullrequestreview-5289727809) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/243#issuecomment-5780057373) | URL 精确风控判定及负例核对，Issue #243 同项，不声称解决所有验证码。 |
| fix(browser): 支持仅暴露 WebSocket 的 Chrome 调试端点 (#244) | 2/2/1/1 | 10 | [#249](https://github.com/shengjidaguai-china/BossHunter/pull/249) · [Issue #244](https://github.com/shengjidaguai-china/BossHunter/issues/244)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/249#pullrequestreview-5329537522) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/244#issuecomment-5780058699) | 握手与路径卫生静态复核，引用另一维护者批准不算本人运行，Issue #244 同项。 |
| docs(contributing): 修正本地开发安装命令 | 1/1/1/1 | 6 | [#250](https://github.com/shengjidaguai-china/BossHunter/pull/250)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/250#pullrequestreview-5329562128) | 安装 extra 与现有指南/CI 对照，具体审批交接。 |
| docs(faq): 平台支持列表补充猎聘 | 1/0/1/0 | 3 | [#251](https://github.com/shengjidaguai-china/BossHunter/pull/251)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/251#pullrequestreview-5329561329) | FAQ 平台标签一致性简单核对。 |
| fix(collection): 智联与猎聘采集阶段应用薪资预筛 | 2/2/1/1 | 10 | [#252](https://github.com/shengjidaguai-china/BossHunter/pull/252) · [Issue #232](https://github.com/shengjidaguai-china/BossHunter/issues/232)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/252#pullrequestreview-5329561229) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/232#issuecomment-5724544990) | 薪资规则抽取与双平台接入审核，Issue #232 同项，测试报告不作为亲跑。 |
| Recruiting agent | 2/2/1/1 | 10 | [#253](https://github.com/shengjidaguai-china/BossHunter/pull/253)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/253#issuecomment-5854337376) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/253#issuecomment-5976494847) | 识别招聘方向反转、fork 徽章和缺失说明，交项目负责人决策，不按大改行数加分。 |
| fix(zhilian): 避免普通登录提示误拦可读岗位列表 | 3/3/1/1 | 14 | [#254](https://github.com/shengjidaguai-china/BossHunter/pull/254) · [Issue #245](https://github.com/shengjidaguai-china/BossHunter/issues/245)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/254#pullrequestreview-5334811596) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/245#issuecomment-5780059773) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/245#issuecomment-5854446206) | 可读列表与登录墙两套解析边界复核，Issue #245 同项，未计 feng 实现为本人。；Issue #245 的本人具体根因定位计入本项，不只按批准计。 |
| fix(monitor): 核对附件简历系统通知并同步真实发送回执 | 3/2/1/1 | 12 | [#255](https://github.com/shengjidaguai-china/BossHunter/pull/255) · [Issue #248](https://github.com/shengjidaguai-china/BossHunter/issues/248)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/255#pullrequestreview-5346583934) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/255#pullrequestreview-5464333345) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/248#issuecomment-5854406184) | 附件请求/回执顺序与状态白名单审核；未独立定位 yuki 提出的循环缺陷。 |
| fix(boss): 修正实习筛选参数并在采集、评分和发送前校验职位类型 | 3/2/2/2 | 14 | [#256](https://github.com/shengjidaguai-china/BossHunter/pull/256)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/256#issuecomment-5864851459) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/256#issuecomment-5864865957) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/256#issuecomment-5976454393) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/256#pullrequestreview-5410397897) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/256#issuecomment-6031910718) | 基于 bi 阻塞修订复查三层实习保护，独立 116 项相关回归；不算原始缺陷发现。 |
| docs: 结束 shuaigechz-cloud 的候选维护观察期 | 1/0/1/0 | 3 | [#258](https://github.com/shengjidaguai-china/BossHunter/pull/258)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/258#pullrequestreview-5346581973) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/258#pullrequestreview-5346600643) | 观察期档案和贡献保留核对；重复重批不升级。 |
| feat: 支持手动调整岗位状态 (#242) | 2/2/1/1 | 10 | [#259](https://github.com/shengjidaguai-china/BossHunter/pull/259) · [Issue #242](https://github.com/shengjidaguai-china/BossHunter/issues/242)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/259#pullrequestreview-5349819322) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/242#issuecomment-5761323045) | 手动状态白名单及人工确认核查、Issue #242 分诊归并；漏检并发不获安全发现分。 |
| feat: 支持岗位池多选筛选 | 2/2/1/0 | 9 | [#261](https://github.com/shengjidaguai-china/BossHunter/pull/261)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/261#pullrequestreview-5349821406) | 多选 OR/AND、SQL 和导出一致性审核，测试数字未明确本地运行。 |
| fix(scripts): Windows 启动器回退到仓库 .venv 解释器，与 macOS 一致 | 1/1/1/0 | 5 | [#263](https://github.com/shengjidaguai-china/BossHunter/pull/263)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/263#pullrequestreview-5361857011) | Windows 回退脚本、文档与测试设计核对，无真机执行声明。 |
| fix: correct BOSS job type search codes | 1/1/1/1 | 6 | [#264](https://github.com/shengjidaguai-china/BossHunter/pull/264)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/264#pullrequestreview-5376258331) | 招聘类型映射与 #256 继承关系核对，避免重复合并。 |
| feat(outsourcing): close evidence feedback loop | 3/3/2/1 | 15 | [#267](https://github.com/shengjidaguai-china/BossHunter/pull/267)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/267#pullrequestreview-5410429259) | 外包证据并发写入缺少任务互斥的有效阻塞发现，定向回归；未修复不算闭环。 |
| fix(windows): 保留含空格的 Chrome 配置目录参数 | 2/1/2/0 | 8 | [#268](https://github.com/shengjidaguai-china/BossHunter/pull/268)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/268#pullrequestreview-5410385335) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/268#issuecomment-6538571762) | Windows 含空格 argv 探针独立运行，限定脚本范围。 |
| feat: 岗位池与工作台支持按城市筛选，并修复中文筛选参数乱码 | 3/2/2/0 | 12 | [#269](https://github.com/shengjidaguai-china/BossHunter/pull/269)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/269#pullrequestreview-5438080553) | 中文参数解码、城市列表与导出跨层核验，独立本地相关测试。 |
| fix(51job): 统一薪资筛选规则并兼容标题空格 | 2/2/1/0 | 9 | [#270](https://github.com/shengjidaguai-china/BossHunter/pull/270)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/270#pullrequestreview-5457361196) | 51job 薪资复用与英文词界审核；121 passed 未明确本机运行，保守按报告。 |
| feat: 岗位池支持屏蔽公司并隐藏黑名单岗位 | 3/2/1/0 | 11 | [#271](https://github.com/shengjidaguai-china/BossHunter/pull/271)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/271#issuecomment-6061373422) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/271#pullrequestreview-5471394434) | 屏蔽确认、并发、分页和无删除语义静态核验。 |
| fix(web): 让岗位池多选筛选支持 Escape 和外部点击关闭 | 1/1/1/0 | 5 | [#272](https://github.com/shengjidaguai-china/BossHunter/pull/272)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/272#pullrequestreview-5457435213) | 键盘与外部点击清理逻辑及三个用例核对。 |
| fix(web): 统一纯空格学历的“未识别”筛选结果 | 1/1/1/0 | 5 | [#273](https://github.com/shengjidaguai-china/BossHunter/pull/273)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/273#issuecomment-6061103996) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/273#pullrequestreview-5464122682) | 空白学历与后端一致性单点核对。 |
| 工作台新增首次使用交互引导 | 2/1/1/1 | 8 | [#276](https://github.com/shengjidaguai-china/BossHunter/pull/276)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/276#pullrequestreview-5457692260) | 跨路由首次引导及测试设计核对，交接第二审核。 |
| 修复浏览器连接状态误报及预检重试成功提示 | 3/2/1/1 | 12 | [#277](https://github.com/shengjidaguai-china/BossHunter/pull/277)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/277#pullrequestreview-5457580042) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/277#issuecomment-6061564935) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/277#pullrequestreview-5464099952) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/277#pullrequestreview-5511439553) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/277#issuecomment-6538570757) | Runtime 健康、Chrome 状态及预检提示跨层审核；重复重批不额外得分。 |
| 优化采集进度展示，补充过滤与异常记录 | 3/2/1/1 | 12 | [#278](https://github.com/shengjidaguai-china/BossHunter/pull/278)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/278#pullrequestreview-5457581325) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/278#issuecomment-6061565684) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/278#pullrequestreview-5464100195) | 采集记录有界、脱敏、断点和前端边界审核，测试报告未明确亲跑。 |
| feat: 整合 Windows 新手引导与自动投递时间窗口优化 | 3/2/1/1 | 12 | [#280](https://github.com/shengjidaguai-china/BossHunter/pull/280)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/280#pullrequestreview-5464273937) | 发送时段各入口和最终提交边界静态核验；没有安装指南具体核对记录，不另计该分项。 |
| fix(db): 手动岗位状态更新原子化，保护并发投递与回收站记录 | 3/2/1/0 | 11 | [#283](https://github.com/shengjidaguai-china/BossHunter/pull/283)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/283#pullrequestreview-5511299424) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/283#issuecomment-6538570461) | 双连接事务、软删除与批量回滚静态复核，原问题属 feng 发现；尚未合入。 |
| feat: 为智联、51job、猎聘增加人工确认投递与采集保护 | 4/2/1/1 | 14 | [#285](https://github.com/shengjidaguai-china/BossHunter/pull/285)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/285#pullrequestreview-5511351477) | 多平台交付、永久提交围栏、额度与页面身份多子系统审核；测试数字按报告未冒认为本地运行。 |
| feat(windows): add stop script and desktop shortcut | 2/2/1/0 | 9 | [#286](https://github.com/shengjidaguai-china/BossHunter/pull/286) · [Issue #284](https://github.com/shengjidaguai-china/BossHunter/issues/284)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/286#pullrequestreview-5543322413) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/286#issuecomment-6538572058) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/284#issuecomment-6157519769) | Windows 定向停止进程与端口反馈核验，Issue #284 同项。 |
| feat: 整合本地开发改动（评分重试、城市优先、简历图片投递） | 3/3/1/1 | 14 | [#287](https://github.com/shengjidaguai-china/BossHunter/pull/287)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/287#issuecomment-6316056543) | 复核 bi 两项未修发送阻塞并明确维持意见；无新独立发现与验证闭环。 |
| fix(51job): 接口无响应时先重试并降频，再按 L3 停止 | 2/2/1/0 | 9 | [#288](https://github.com/shengjidaguai-china/BossHunter/pull/288)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/288#pullrequestreview-5613183900) | 有界空响应恢复与真实风险停止路径静态审核。 |
| feat(采集): 跳过近期已投递或岗位池已有的公司（可选，默认关闭） | 2/1/1/0 | 7 | [#290](https://github.com/shengjidaguai-china/BossHunter/pull/290) · [Issue #289](https://github.com/shengjidaguai-china/BossHunter/issues/289)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/290#pullrequestreview-5613216761) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/290#issuecomment-6379522811) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/289#issuecomment-6339451797) | 仅默认关闭、SQL 绑定与期限校验的已证实工作；前缀误并漏检不获安全发现分。 |
| feat(筛选): 按 HR 活跃度、岗位更新时间、工作地点过滤（默认关闭） | 2/1/1/0 | 7 | [#291](https://github.com/shengjidaguai-china/BossHunter/pull/291)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/291#pullrequestreview-5613246870) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/291#issuecomment-6379534675) | 仅开关、未知策略与函数边界审核；未发现真实字段接入缺失不获功能完整性分。 |
| test: stop resume runtime tests from opening real browser tabs | 1/1/1/0 | 5 | [#292](https://github.com/shengjidaguai-china/BossHunter/pull/292)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/292#pullrequestreview-5636759357) | 测试隔离替换点和两个运行器的机制核对。 |
| macOS 启动器无 Chrome / bash 3.2 空数组的启动失败复核 | 2/2/1/1 | 10 | [#294](https://github.com/shengjidaguai-china/BossHunter/pull/294) · [#299](https://github.com/shengjidaguai-china/BossHunter/pull/299) · [Issue #293](https://github.com/shengjidaguai-china/BossHunter/issues/293)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/294#pullrequestreview-5636765515) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/294#issuecomment-6538570998) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/293#issuecomment-6392028780) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/299#pullrequestreview-5662572243) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/299#issuecomment-6538571379) | 两条不同触发路径围绕同一 macOS 启动目标合并审核；仅静态核验和引用报告，无真机运行声明。 |
| fix(boss): read HR name and online tag from .job-boss-info | 2/2/1/1 | 10 | [#295](https://github.com/shengjidaguai-china/BossHunter/pull/295)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/295#issuecomment-6392023008) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/295#pullrequestreview-5662483812) | 共用活跃标签正则及选择器修订核对，原始缺口由 bi 发现。 |
| feat: add safe unreplied recontact workflow | 3/2/1/0 | 11 | [#296](https://github.com/shengjidaguai-china/BossHunter/pull/296)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/296#pullrequestreview-5662797798) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/296#issuecomment-6518362911) | 已核查的冷却、身份和额度边界；最终发送检查未调用被漏检，不获该项闭环分。 |
| feat(collection): BOSS 低产切城与有期限持续采集 | 3/2/1/1 | 12 | [#298](https://github.com/shengjidaguai-china/BossHunter/pull/298) · [Issue #297](https://github.com/shengjidaguai-china/BossHunter/issues/297)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/298#pullrequestreview-5694594751) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/297#issuecomment-6435187860) | 持续采集时限、恢复所有权和停止边界跨组件审核，Issue #297 同项。 |
| fix(export): 避免 XLSX 导出把岗位数据写成 Excel 公式 | 1/2/1/0 | 7 | [#300](https://github.com/shengjidaguai-china/BossHunter/pull/300)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/300#pullrequestreview-5692412841) | XLSX 与 CSV 共用判定及字符串类型核对。 |
| fix(ai): 兼容 reasoning effort 参数拒绝，修复连接成功但评分失败 | 2/2/1/1 | 10 | [#303](https://github.com/shengjidaguai-china/BossHunter/pull/303) · [Issue #302](https://github.com/shengjidaguai-china/BossHunter/issues/302)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/303#pullrequestreview-5709730650) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/303#issuecomment-6538569828) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/302#issuecomment-6538573968) | reasoning 参数拒绝重试与连接预检范围核对，Issue #302 同项。 |
| feat(web): AI 评分进度条与岗位列表自动刷新 | 2/2/1/1 | 10 | [#305](https://github.com/shengjidaguai-china/BossHunter/pull/305) · [Issue #304](https://github.com/shengjidaguai-china/BossHunter/issues/304)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/305#pullrequestreview-5709760124) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/305#issuecomment-6538570141) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/issues/304#issuecomment-6538574253) | 评分进度、单请求轮询和陈旧响应核对，Issue #304 同项。 |
| Issue #78 独立处理 | 2/2/1/1 | 10 | [Issue #78](https://github.com/shengjidaguai-china/BossHunter/issues/78)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/78#issuecomment-5459841957) | 风险锁/账号切换的具体分域与边界核对；不声称已实现修改。 |
| Issue #93 独立处理 | 1/1/0/1 | 5 | [Issue #93](https://github.com/shengjidaguai-china/BossHunter/issues/93)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/93#issuecomment-5493284541) | 区分冷却、回显和队列中断并要求具体日志；尚不能定位。 |
| Issue #168 独立处理 | 1/0/1/1 | 4 | [Issue #168](https://github.com/shengjidaguai-china/BossHunter/issues/168)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/168#issuecomment-5549882175) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/168#issuecomment-5551623715) | 只读采集、限速及安全停止的具体使用咨询答复，未计新修复。 |
| Issue #174 独立处理 | 1/1/0/1 | 5 | [Issue #174](https://github.com/shengjidaguai-china/BossHunter/issues/174)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/174#issuecomment-5549882092) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/174#issuecomment-5854380700) | 针对 51job 风控报告索要可定位的命令、日志和环境；未修复。 |
| Issue #178 独立处理 | 1/1/1/1 | 6 | [Issue #178](https://github.com/shengjidaguai-china/BossHunter/issues/178)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/178#issuecomment-5596945363) | 将安装失败关联 #197 的已采用说明；无本人重装或复现，不给闭环档。 |
| Issue #186 独立处理 | 1/0/1/1 | 4 | [Issue #186](https://github.com/shengjidaguai-china/BossHunter/issues/186)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/186#issuecomment-5558381027) | 逐项核对任职申请缺失的证据及安全承诺并给出补充要求。 |
| Issue #192 独立处理 | 1/1/1/2 | 7 | [Issue #192](https://github.com/shengjidaguai-china/BossHunter/issues/192)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/192#issuecomment-5570210592) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/192#issuecomment-5682012909) | 结合报告者补充明确白屏来自演示视频并关闭误报，不当成产品修复。 |
| Issue #213 独立处理 | 1/1/1/1 | 6 | [Issue #213](https://github.com/shengjidaguai-china/BossHunter/issues/213)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/213#issuecomment-5620028142) | 提供对应版本从主线更新及重装的具体操作指引。 |
| Issue #228 独立处理 | 1/1/0/1 | 5 | [Issue #228](https://github.com/shengjidaguai-china/BossHunter/issues/228)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/228#issuecomment-5724546063) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/228#issuecomment-5854379140) | 针对凭证拒绝请求脱敏配置与模型权限核查；未证实服务商兼容或修复。 |
| Issue #231 独立处理 | 1/1/0/1 | 5 | [Issue #231](https://github.com/shengjidaguai-china/BossHunter/issues/231)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/231#issuecomment-5724560008) | Docker 浏览器、显示与持久化的可执行可行性分诊，未实现不计项目分。 |
| Issue #234 独立处理 | 2/1/0/1 | 7 | [Issue #234](https://github.com/shengjidaguai-china/BossHunter/issues/234)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/234#issuecomment-5724559232) | 对四项意向给出范围与边界条件，只计方案分诊，未采用设想无项目分。 |
| Issue #235 独立处理 | 1/1/0/1 | 5 | [Issue #235](https://github.com/shengjidaguai-china/BossHunter/issues/235)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/235#issuecomment-5724543873) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/235#issuecomment-5854378440) | 区分真实验证码和 URL 误报并给出降速/复测建议，#247 不等于验证码已解决。 |
| Issue #301 独立处理 | 1/1/0/1 | 5 | [Issue #301](https://github.com/shengjidaguai-china/BossHunter/issues/301)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/301#issuecomment-6538574642) | 针对无法找到沟通按钮提出分场景排查和脱敏日志请求；尚未闭环。 |
| v2.4.0 版本元数据与发布断言核验 | 1/1/1/0 | 5 | [#202](https://github.com/shengjidaguai-china/BossHunter/pull/202)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5149170728) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5594950956) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5149696877) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5596947759) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5153537016) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5600974302) | 只计版本文件及新增一致性断言的具体静态核对；构建、分支同步和合并交接仅计首页主事项，本分项 P=0。 |
| 移动工作台二维码缺少依赖声明的安装故障发现 | 2/2/1/1 | 10 | [#204](https://github.com/shengjidaguai-china/BossHunter/pull/204)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/204#pullrequestreview-5149691088) | 缺少 qrcode 依赖使干净安装的接口报错，与默认监听的隐私暴露是独立目标；未修复不计闭环。 |

### [@bianshilong0604](https://github.com/bianshilong0604) · 388 分

| 事项与范围 | E/I/V/P | 分数 | 来源与本人证据 | 评分理由与限制 |
|---|---|---:|---|---|
| fix: reject invented greeting URLs | 4/3/3/2 | 19 | [#88](https://github.com/shengjidaguai-china/BossHunter/pull/88)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5463732307) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5466342761) | 发现简历尾部隐私外发与裸 URL 问题，修订后独立 55 项运行并确认恢复边界。 |
| feat: 打招呼语生成/编辑/重生成工作流 | 3/3/1/1 | 14 | [#90](https://github.com/shengjidaguai-china/BossHunter/pull/90)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/90#issuecomment-5463882496) | 明确复现步骤定位陈旧 tab 将 sent 改回 ready 及后台任务问题；未记录本人修订复测。 |
| feat(web): 配置页简历拖放上传与 PDF/MD 双预览 | 3/2/3/1 | 14 | [#176](https://github.com/shengjidaguai-china/BossHunter/pull/176)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/176#pullrequestreview-5128808466) | 简历生命周期与上传产品复审，前后端本地及基线对照验证。 |
| fix(web): 运行/采集启动弹窗防抖+loading，成功即关、失败在弹窗内提示 (#177) | 2/1/2/0 | 8 | [#206](https://github.com/shengjidaguai-china/BossHunter/pull/206)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/206#pullrequestreview-5193263572) | 弹窗交互和定向前端验证，无发送边界或额外闭环。 |
| 增加本机 Agent Tool API，支持无 AI Key 的受控求职工作流 | 3/2/2/1 | 13 | [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/218#pullrequestreview-5193265373) | 本机 Agent、无 Key 路径和偏好字段独立定向回归，明确远程使用边界。 |
| feat(web): 支持深色模式与浅色/深色/跟随系统主题切换 | 3/1/2/1 | 11 | [#221](https://github.com/shengjidaguai-china/BossHunter/pull/221)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/221#pullrequestreview-5193474964) | 全局主题验收及前端运行，首次 CI 待放行的明确交接。 |
| fix: 默认详情页上限调整为 900、总页面上限调整为 1100 | 3/2/3/0 | 13 | [#222](https://github.com/shengjidaguai-china/BossHunter/pull/222)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/222#pullrequestreview-5274620959) | 页面预算及保留额度检查，安全测试失败独立基线复现、前端验证。 |
| feat: 优化招呼语控制、岗位定制简历与工作台展示 | 4/2/3/0 | 15 | [#237](https://github.com/shengjidaguai-china/BossHunter/pull/237)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/237#pullrequestreview-5274629430) | 确认对象隔离、简历事实保护与队列跨层验证；未冒认原始安全设计。 |
| feat(scripts): macOS 一键启动器与安装指南 | 4/3/3/2 | 19 | [#238](https://github.com/shengjidaguai-china/BossHunter/pull/238)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/238#pullrequestreview-5300604146) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/238#pullrequestreview-5324891025) | 定位空格解释器路径导致两条启动链失败，修订复查并运行静态用例；未声称 macOS 真机验证。 |
| feat: 支持按 HR 活跃时间筛选与采集过滤 | 3/2/2/0 | 12 | [#239](https://github.com/shengjidaguai-china/BossHunter/pull/239)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/239#pullrequestreview-5274620664) | 采集快照、分页与导出统一判定及定向运行。 |
| fix(prefilter): 支持元/千/万年薪格式，修复智联与前程无忧岗位被薪资预筛全量误杀 | 2/2/2/0 | 10 | [#241](https://github.com/shengjidaguai-china/BossHunter/pull/241)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/241#pullrequestreview-5274630828) | 薪资单位误杀的独立边界回归，无原始缺陷发现声明。 |
| fix(boss): 避免搜索参数误触发 403 风控 | 2/2/2/0 | 10 | [#247](https://github.com/shengjidaguai-china/BossHunter/pull/247)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/247#pullrequestreview-5300576955) | URL 误报负例与真实阻断的定向本地运行。 |
| fix(zhilian): 避免普通登录提示误拦可读岗位列表 | 3/2/2/1 | 13 | [#254](https://github.com/shengjidaguai-china/BossHunter/pull/254)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/254#pullrequestreview-5334691834) | 登录墙和普通 CTA 边界独立测试，指出同步后须重新审核。 |
| fix(boss): 修正实习筛选参数并在采集、评分和发送前校验职位类型 | 4/4/3/2 | 21 | [#256](https://github.com/shengjidaguai-china/BossHunter/pull/256)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/256#pullrequestreview-5334712929) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/256#pullrequestreview-5450457484) | 复现 allow_internship=false 经详情/历史发送绕过，复查三层修订并跑 62 项保护回归。 |
| fix(prefilter): 日薪/周薪/时薪按无法解析处理，修复实习岗位被薪资预筛误过滤 | 2/2/2/0 | 10 | [#266](https://github.com/shengjidaguai-china/BossHunter/pull/266)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/266#pullrequestreview-5450555289) | 日/周薪语义与默认未知策略的独立定向运行。 |
| feat: 岗位池与工作台支持按城市筛选，并修复中文筛选参数乱码 | 3/2/3/0 | 13 | [#269](https://github.com/shengjidaguai-china/BossHunter/pull/269)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/269#pullrequestreview-5450534737) | 中文重复参数、城市/区县与导出多层独立验证。 |
| fix(51job): 统一薪资筛选规则并兼容标题空格 | 3/2/2/0 | 12 | [#270](https://github.com/shengjidaguai-china/BossHunter/pull/270)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/270#pullrequestreview-5450546620) | 51job 薪资区间和中英文词界独立相关回归。 |
| feat: 岗位池支持屏蔽公司并隐藏黑名单岗位 | 4/2/3/0 | 15 | [#271](https://github.com/shengjidaguai-china/BossHunter/pull/271)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/271#issuecomment-6050601964) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/271#pullrequestreview-5476902517) | 屏蔽预览、并发和分页合并组合后的前后端验证。 |
| fix(web): 让岗位池多选筛选支持 Escape 和外部点击关闭 | 2/1/2/0 | 8 | [#272](https://github.com/shengjidaguai-china/BossHunter/pull/272)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/272#pullrequestreview-5450505602) | 可访问性、焦点及外部点击定向前端运行。 |
| fix(web): 统一纯空格学历的“未识别”筛选结果 | 1/1/2/0 | 6 | [#273](https://github.com/shengjidaguai-china/BossHunter/pull/273)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/273#pullrequestreview-5450504413) | 空白学历边界及前端回归运行。 |
| 工作台新增首次使用交互引导 | 3/1/2/0 | 10 | [#276](https://github.com/shengjidaguai-china/BossHunter/pull/276)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/276#pullrequestreview-5450485616) | 真实控件、保存状态及退出语义的前端运行。 |
| 优化采集进度展示，补充过滤与异常记录 | 4/2/3/0 | 15 | [#278](https://github.com/shengjidaguai-china/BossHunter/pull/278)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/278#pullrequestreview-5476912142) | 四平台采集、断点恢复和前端明细的系统性独立验证，保留异常脱敏界限。 |
| feat: 整合本地开发改动（评分重试、城市优先、简历图片投递） | 3/3/1/1 | 14 | [#287](https://github.com/shengjidaguai-china/BossHunter/pull/287)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/287#pullrequestreview-5542029257) | 发现图片总数误当送达及全页发送按钮匹配两个具体阻塞；无已修复证据。 |
| fix(51job): 接口无响应时先重试并降频，再按 L3 停止 | 2/2/1/0 | 9 | [#288](https://github.com/shengjidaguai-china/BossHunter/pull/288)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/288#pullrequestreview-5636328771) | 空响应恢复与真实风险停止审核；109 项来自作者报告，不能当本人运行。 |
| feat(采集): 跳过近期已投递或岗位池已有的公司（可选，默认关闭） | 3/3/1/1 | 14 | [#290](https://github.com/shengjidaguai-china/BossHunter/pull/290)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/290#pullrequestreview-5636339785) | 定位两字根前缀把不同雇主误合并的触发场景；未修不算闭环。 |
| feat(筛选): 按 HR 活跃度、岗位更新时间、工作地点过滤（默认关闭） | 3/3/1/1 | 14 | [#291](https://github.com/shengjidaguai-china/BossHunter/pull/291)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/291#pullrequestreview-5636330380) | 发现更新时间字段未接真实采集数据，且三个筛选配置未接 Web schema；默认关闭不能代替功能接入。 |
| fix(boss): read HR name and online tag from .job-boss-info | 4/3/3/2 | 19 | [#295](https://github.com/shengjidaguai-china/BossHunter/pull/295)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/295#pullrequestreview-5636323400) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/295#pullrequestreview-5646820352) | 定位中文数字/天标签缺口，复查共用正则修订并运行 42 项回归。 |
| feat: add safe unreplied recontact workflow | 3/4/2/1 | 17 | [#296](https://github.com/shengjidaguai-china/BossHunter/pull/296)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/296#pullrequestreview-5680199992) | 独立运行相关测试后仍发现未调用最终发送检查及另一发送边界；截至快照未闭环。 |
| fix(export): 避免 XLSX 导出把岗位数据写成 Excel 公式 | 2/2/2/0 | 10 | [#300](https://github.com/shengjidaguai-china/BossHunter/pull/300)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/300#pullrequestreview-5707430826) | XLSX 公式解释风险修订独立导出回归，未声称真实 Excel 实测。 |
| Issue #216 独立处理 | 2/2/1/1 | 10 | [Issue #216](https://github.com/shengjidaguai-china/BossHunter/issues/216)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/issues/216#issuecomment-5658272516) | 明确本机可选入口、Markdown 独立降级和接收端未发布条件，具体产品/协议交接。 |

### [@yukinoshi](https://github.com/yukinoshi) · 337 分

| 事项与范围 | E/I/V/P | 分数 | 来源与本人证据 | 评分理由与限制 |
|---|---|---:|---|---|
| feat: show detailed greeting queue progress | 3/2/3/1 | 14 | [#86](https://github.com/shengjidaguai-china/BossHunter/pull/86) · [Issue #84](https://github.com/shengjidaguai-china/BossHunter/issues/84)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/86#issuecomment-5466756964) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/84#issuecomment-5466785774) | 无源码改动的冲突整合、基线复跑及核心域交接；原 Issue #84 合并为同一事项。 |
| fix: allow retry and dismiss resume_failed pending items | 4/3/3/2 | 19 | [#92](https://github.com/shengjidaguai-china/BossHunter/pull/92)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/92#issuecomment-5469650769) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5077287271) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5089153466) · [本人记录 4](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5125252995) · [本人记录 5](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5125263034) · [本人记录 6](https://github.com/shengjidaguai-china/BossHunter/pull/92#issuecomment-5559146222) | 状态覆盖、失败历史和测试意见修订复查，多轮合并树及主线对照验证；重复正文不另加。 |
| fix: surface real send-failure reason on error jobs; detect closed po… | 3/2/3/1 | 14 | [#161](https://github.com/shengjidaguai-china/BossHunter/pull/161)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/161#issuecomment-5509043019) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/161#pullrequestreview-5121085202) | 失败原因写入和关闭探测复核，独立全量与主线环境失败对照。 |
| feat(collection): 智联 API-fetch 框架 — 同源 fetch + L0-L3 风控分级 + 断点续采复用 | 4/2/3/1 | 16 | [#162](https://github.com/shengjidaguai-china/BossHunter/pull/162)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/162#pullrequestreview-5124275522) | 跨采集编排、安全分级和断点系统验证，新增用例及主线失败对照；未声称发现新安全漏洞。 |
| feat(outsourcing): 公司名后展示 外包 / 疑似外包 徽标 | 4/2/3/1 | 16 | [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/164#pullrequestreview-5362102646) | 数据库、检测结果与前端多层验证并提出检测质量跟进；实现补丁属其他作者。 |
| feat(web): 工作台全流程预检前置；BOSS关键词输入提示 | 2/1/2/1 | 9 | [#171](https://github.com/shengjidaguai-china/BossHunter/pull/171)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/171#pullrequestreview-5124003966) | 复用预检、并发按钮和输入提示核对及本地构建；补 Issue 建议不算成果。 |
| 优化 AI 诊断、薪资过滤和招呼语生成 | 4/2/3/1 | 16 | [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/172#issuecomment-5551597258) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/172#pullrequestreview-5124357527) · [本人记录 3](https://github.com/shengjidaguai-china/BossHunter/pull/172#pullrequestreview-5124670902) | 诊断、预筛及环境兼容验证，机械解决 dist 冲突并复跑合并树。 |
| feat(web): 配置页简历拖放上传与 PDF/MD 双预览 | 4/2/3/2 | 17 | [#176](https://github.com/shengjidaguai-china/BossHunter/pull/176)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/176#issuecomment-5551981943) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/176#pullrequestreview-5123873074) | 上传路径、伴随文件及删除语义多轮确认，基线对照和前后端验证闭环。 |
| fix(ai): 区分运行环境异常与 API 配置错误 | 3/2/3/1 | 14 | [#179](https://github.com/shengjidaguai-china/BossHunter/pull/179) · [Issue #163](https://github.com/shengjidaguai-china/BossHunter/issues/163)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/179#pullrequestreview-5122026768) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/issues/163#issuecomment-5552063755) | 环境异常分类和脱敏核验、主线基线对照，关联 Issue #163 不另计。 |
| feat（集合）：补全51job已核验城市编码（31个主要城市） | 1/1/1/1 | 6 | [#181](https://github.com/shengjidaguai-china/BossHunter/pull/181)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/181#issuecomment-5557112052) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/181#issuecomment-5559034431) | 识别城市数据重叠并给出合并顺序；自身 #156 测试补丁不再记维护。 |
| fix: 区分 BOSS 临时风险暂停与采集上限提示 | 1/0/1/0 | 3 | [#189](https://github.com/shengjidaguai-china/BossHunter/pull/189)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/189#pullrequestreview-5186413608) | 仅提示文案和无控制流变化核对，未把他人回归算亲跑。 |
| docs(maintainers): 同步 bianshilong0604 团队邀请已接受状态 | 1/0/1/0 | 3 | [#200](https://github.com/shengjidaguai-china/BossHunter/pull/200)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/200#pullrequestreview-5254301247) | 成员状态一行文档复核，未记录本人查询 membership。 |
| feat(web): 精简首页并更新至 v2.4.0 | 4/2/3/1 | 16 | [#202](https://github.com/shengjidaguai-china/BossHunter/pull/202)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/202#issuecomment-5599377030) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/202#pullrequestreview-5153635734) | 首页与接口边界、版本元数据的合并树验证和基线回归；本人未实现产品逻辑。 |
| fix(boss): 薪资字体不可解析时可保留岗位（默认策略不变） | 2/1/1/0 | 7 | [#205](https://github.com/shengjidaguai-china/BossHunter/pull/205)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/205#pullrequestreview-5185810227) | 可选跳过策略、默认值与测试设计静态核对，未记录独立执行。 |
| fix(web): 运行/采集启动弹窗防抖+loading，成功即关、失败在弹窗内提示 (#177) | 2/1/1/0 | 7 | [#206](https://github.com/shengjidaguai-china/BossHunter/pull/206)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/206#pullrequestreview-5185810159) | 弹窗防抖、错误反馈及关闭状态静态核验。 |
| feat: AI 配置支持获取模型列表并选择模型 | 2/2/1/0 | 9 | [#212](https://github.com/shengjidaguai-china/BossHunter/pull/212)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/212#pullrequestreview-5185810048) | 只读模型查询、URL 和凭据边界静态核验，不给漏洞发现档。 |
| fix(web): 简历上传按 base_dir 解析相对 resume_path，不再受进程 cwd 影响 | 1/1/1/0 | 5 | [#215](https://github.com/shengjidaguai-china/BossHunter/pull/215)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/215#pullrequestreview-5185810105) | 相对路径修复及 decoy 回归设计核对，无独立运行声明。 |
| feat(web): 可选的本地面试准备入口与岗位草稿交接 | 2/2/1/1 | 10 | [#217](https://github.com/shengjidaguai-china/BossHunter/pull/217)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/217#pullrequestreview-5185806366) | 本机字段交接和来源校验核对，明确接收端未就绪、端到端待验。 |
| fix(test): Mock() 替换为 MagicMock() 防止 sqlite magic method TypeError (#191) | 1/1/1/0 | 5 | [#219](https://github.com/shengjidaguai-china/BossHunter/pull/219)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/219#pullrequestreview-5254299759) · [本人记录 2](https://github.com/shengjidaguai-china/BossHunter/pull/219#pullrequestreview-5254300111) | 两个测试文件 context manager mock 修正核对；重复批准不增加分。 |
| feat(web): 支持深色模式与浅色/深色/跟随系统主题切换 | 3/1/1/0 | 9 | [#221](https://github.com/shengjidaguai-china/BossHunter/pull/221)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/221#pullrequestreview-5254317304) | 全局主题、持久化及防闪烁多组件静态审核。 |
| feat(boss): 从页面实际加载的字体重建薪资数字映射 | 3/2/1/1 | 12 | [#225](https://github.com/shengjidaguai-china/BossHunter/pull/225)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/225#pullrequestreview-5254311967) | 字体轮廓匹配、缓存回退及合成字体测试设计核查，指出同步读取边界。 |
| fix(web): 采集/评分弹窗确认后按结果自动关闭并补充加载与失败提示 | 2/1/1/0 | 7 | [#226](https://github.com/shengjidaguai-china/BossHunter/pull/226)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/226#pullrequestreview-5254307086) | 弹窗成功失败和递归返回语义核对，无亲跑声明。 |
| feat: 优化招呼语审核、定制简历与回复监测安全 | 3/2/1/0 | 11 | [#227](https://github.com/shengjidaguai-china/BossHunter/pull/227)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/227#pullrequestreview-5254322903) | 发送状态、简历事实和监测多路径静态审核；不声称验证整套无缺陷。 |
| fix: 跳过已失效的 DevToolsActivePort，避免误连非 CDP 端口 | 2/2/1/0 | 9 | [#229](https://github.com/shengjidaguai-china/BossHunter/pull/229)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/229#pullrequestreview-5254309790) | 诱饵端口和真实 CDP 发现逻辑及测试设计核对。 |
| fix(browser): 浏览器链路稳定性三处修复——navigate 超时竞态、CDP attach 重试、智联卡片点击重试 | 3/2/1/0 | 11 | [#233](https://github.com/shengjidaguai-china/BossHunter/pull/233)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/233#pullrequestreview-5254308567) | 导航、attach 和卡片恢复多个路径审核，非新实现。 |
| fix(browser): 支持仅暴露 WebSocket 的 Chrome 调试端点 (#244) | 4/2/3/1 | 16 | [#249](https://github.com/shengjidaguai-china/BossHunter/pull/249)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/249#pullrequestreview-5313324854) | 真实 WebSocket 握手及主线对照，指出 URL 选择和超时等非阻塞偏差。 |
| fix(monitor): 核对附件简历系统通知并同步真实发送回执 | 3/3/2/1 | 15 | [#255](https://github.com/shengjidaguai-china/BossHunter/pull/255)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/255#pullrequestreview-5362103022) | 识别监测循环预算消耗和重复读取缺陷，记录本地测试环境限制；未证明修订闭环。 |
| feat: 支持手动调整岗位状态 (#242) | 2/2/1/0 | 9 | [#259](https://github.com/shengjidaguai-china/BossHunter/pull/259)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/259#pullrequestreview-5362102833) | 仅已证实的目标状态、人工确认和历史核对；漏检并发覆盖不获发现或闭环分。 |
| feat: 支持岗位池多选筛选 | 4/2/3/1 | 16 | [#261](https://github.com/shengjidaguai-china/BossHunter/pull/261)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/261#pullrequestreview-5362102200) | 多选查询与导出、多层独立验证及主线对照，明确空白学历/键盘跟进。 |
| chore(data): 补齐 51job/猎聘城市快照 fetched_at 元数据 | 1/1/1/0 | 5 | [#262](https://github.com/shengjidaguai-china/BossHunter/pull/262)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/262#pullrequestreview-5362101965) | 城市数组逐字节及快照日期核对；9/9 报告无明确本人运行，不升 V2。 |
| fix(scripts): Windows 启动器回退到仓库 .venv 解释器，与 macOS 一致 | 2/1/1/1 | 8 | [#263](https://github.com/shengjidaguai-china/BossHunter/pull/263)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/263#pullrequestreview-5362102426) | Windows 回退顺序、路径及首次 CI 放行条件核对；AST 报告不当真机验证。 |
| chore: ignore local maintainer working docs | 1/0/1/0 | 3 | [#265](https://github.com/shengjidaguai-china/BossHunter/pull/265)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/265#pullrequestreview-5404083020) | 两条忽略模式的范围和已跟踪文件影响核对。 |

### [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) · 199 分

| 事项与范围 | E/I/V/P | 分数 | 来源与本人证据 | 评分理由与限制 |
|---|---|---:|---|---|
| fix(executor): 修复监控风险检测的掩码误判 | 3/4/2/1 | 17 | [#73](https://github.com/shengjidaguai-china/BossHunter/pull/73)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/73#pullrequestreview-5124305409) | 对比主线复现可见风险文案、分割文本和 URL 检测漏停；关键保护问题未修。 |
| build(frontend): 停止跟踪 dist，改为按需构建以消除产物合并冲突 | 4/3/3/1 | 18 | [#147](https://github.com/shengjidaguai-china/BossHunter/pull/147)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/147#pullrequestreview-5124304248) | 构建、wheel 与全新安装/sdist 多路径验证并复现未解决交付缺口；批准不代表缺口闭环。 |
| test(collection): orchestrator 覆盖率 41%->95% 补齐 28 个测试 | 3/2/3/1 | 14 | [#151](https://github.com/shengjidaguai-china/BossHunter/pull/151)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/151#pullrequestreview-5124304668) | 独立父提交及主线对照运行，纠正覆盖率基线与断言无效用法。 |
| docs(maintainers): 同步 bianshilong0604 团队邀请已接受状态 | 1/0/2/0 | 4 | [#200](https://github.com/shengjidaguai-china/BossHunter/pull/200)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/200#pullrequestreview-5189637985) | 本人查询 membership 证实文档状态；只是身份记录核验不改权限。 |
| fix(boss): 薪资字体不可解析时可保留岗位（默认策略不变） | 4/2/3/0 | 15 | [#205](https://github.com/shengjidaguai-china/BossHunter/pull/205)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/205#pullrequestreview-5189782344) | 采集及前后端系统回归、独立纯主线复现失败并保留限制。 |
| feat: 支持 51job 人工确认后投递在线简历 | 1/2/1/0 | 7 | [#209](https://github.com/shengjidaguai-china/BossHunter/pull/209)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/209#pullrequestreview-5189782386) | 当前记录仅确认未修的 fail-open 等问题；未见独立复现细节，且仍批准，不给闭环或高验证档。 |
| docs(contributing): 修正本地开发安装命令 | 2/1/2/1 | 9 | [#250](https://github.com/shengjidaguai-china/BossHunter/pull/250)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/250#pullrequestreview-5330009377) | 安装元数据和本地整合构建核对，未声称干净环境完整安装；明确新 head 接续条件。 |
| fix(collection): 智联与猎聘采集阶段应用薪资预筛 | 4/2/3/1 | 16 | [#252](https://github.com/shengjidaguai-china/BossHunter/pull/252)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/252#pullrequestreview-5330009474) | 双平台薪资及断点独立验证、整合版失败纯主线对照，交接作者同步。 |
| fix(boss): 修正实习筛选参数并在采集、评分和发送前校验职位类型 | 4/2/3/2 | 17 | [#256](https://github.com/shengjidaguai-china/BossHunter/pull/256)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/256#pullrequestreview-5364227384) | 对原阻塞修订完成 Python/前端/合成浏览器多层验证；原始发现属 bi，未真采集。 |
| feat: 支持手动调整岗位状态 (#242) | 3/3/2/1 | 15 | [#259](https://github.com/shengjidaguai-china/BossHunter/pull/259)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/259#issuecomment-5908198865) | 真实双 SQLite 连接复现并发覆盖和软删除假成功；未采用候选补丁不计项目或闭环，补丁自测不叠加。 |
| fix: correct BOSS job type search codes | 3/1/2/1 | 11 | [#264](https://github.com/shengjidaguai-china/BossHunter/pull/264)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/264#pullrequestreview-5364224743) | 类型映射回归及与 #256 合并树兼容验证，明确 CI 未运行及缺真实站点验证。 |
| feat(outsourcing): close evidence feedback loop | 2/2/1/1 | 10 | [#267](https://github.com/shengjidaguai-china/BossHunter/pull/267)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/267#issuecomment-6117272530) | 复查他人并发阻塞仍在，给出锁及 409 回归交接；未实现闭环。 |
| 修复浏览器连接状态误报及预检重试成功提示 | 4/2/3/1 | 16 | [#277](https://github.com/shengjidaguai-china/BossHunter/pull/277)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/277#pullrequestreview-5486335440) | Runtime/CLI/前端独立验证并定位合并冲突，明确保留双方回归及重新批准条件。 |
| feat: 整合 Windows 新手引导与自动投递时间窗口优化 | 4/2/3/1 | 16 | [#280](https://github.com/shengjidaguai-china/BossHunter/pull/280)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/280#pullrequestreview-5486337471) | 窗口多入口与发送最终边界跨层独立验证；Windows 启动器相关运行合入本事项，不再为安装指引另计分，未在 Windows 真机安装。 |
| feat(dist): portable distribution packages for Windows and macOS | 3/3/1/1 | 14 | [#282](https://github.com/shengjidaguai-china/BossHunter/pull/282)；[本人记录 1](https://github.com/shengjidaguai-china/BossHunter/pull/282#pullrequestreview-5486315850) | 发现陌生服务误判健康和空格目录传参问题，给出离线回归要求；后续空白批准不算修订闭环。 |

## 未计分的维护记录

仅列本次候选中被排除的个人 PR / Issue 组合。空白批准、自身实现、自测以及无实质工作的记录不进入已评分覆盖；不表示当事人没有做过任何工作。#299 的 yuppie 工作已合并进 #294，属于合并计分，不列为遗漏。

| 维护者 | 来源 | 排除原因 |
|---|---|---|
| [@bianshilong0604](https://github.com/bianshilong0604) | [Issue #79](https://github.com/shengjidaguai-china/BossHunter/issues/79) | 泛泛欢迎未来提交 PR，无具体检查/可执行分诊，不评分。 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#133](https://github.com/shengjidaguai-china/BossHunter/pull/133) | 本人 PR，排除自述/自审 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#139](https://github.com/shengjidaguai-china/BossHunter/pull/139) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#143](https://github.com/shengjidaguai-china/BossHunter/pull/143) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#145](https://github.com/shengjidaguai-china/BossHunter/pull/145) | 共同实现，整条 PR 保守排除维护计分 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#156](https://github.com/shengjidaguai-china/BossHunter/pull/156) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) | 共同实现，整条 PR 保守排除维护计分 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#162](https://github.com/shengjidaguai-china/BossHunter/pull/162) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#164](https://github.com/shengjidaguai-china/BossHunter/pull/164) | 共同实现，整条 PR 保守排除维护计分 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#172](https://github.com/shengjidaguai-china/BossHunter/pull/172) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#175](https://github.com/shengjidaguai-china/BossHunter/pull/175) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#183](https://github.com/shengjidaguai-china/BossHunter/pull/183) | 只有空白批准/一般提醒，无独立检查说明 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) | 共同实现，整条 PR 保守排除维护计分 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#255](https://github.com/shengjidaguai-china/BossHunter/pull/255) | 本人 PR，排除自述/自审 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | [#287](https://github.com/shengjidaguai-china/BossHunter/pull/287) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#77](https://github.com/shengjidaguai-china/BossHunter/pull/77) | 共同实现，整条 PR 保守排除维护计分 |
| [@yukinoshi](https://github.com/yukinoshi) | [#82](https://github.com/shengjidaguai-china/BossHunter/pull/82) | 共同实现，整条 PR 保守排除维护计分 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #91](https://github.com/shengjidaguai-china/BossHunter/issues/91) | 仅指向已计 PR 审核 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #100](https://github.com/shengjidaguai-china/BossHunter/issues/100) | 本人 #117 实现 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #101](https://github.com/shengjidaguai-china/BossHunter/issues/101) | 本人 #115 实现 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #102](https://github.com/shengjidaguai-china/BossHunter/issues/102) | 本人 #115 实现 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #103](https://github.com/shengjidaguai-china/BossHunter/issues/103) | 本人 #118 实现 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #107](https://github.com/shengjidaguai-china/BossHunter/issues/107) | 本人 #114 实现 |
| [@yukinoshi](https://github.com/yukinoshi) | [#115](https://github.com/shengjidaguai-china/BossHunter/pull/115) | 本人 PR，排除自述/自审 |
| [@yukinoshi](https://github.com/yukinoshi) | [#117](https://github.com/shengjidaguai-china/BossHunter/pull/117) | 本人 PR，排除自述/自审 |
| [@yukinoshi](https://github.com/yukinoshi) | [#143](https://github.com/shengjidaguai-china/BossHunter/pull/143) | 共同实现，整条 PR 保守排除维护计分 |
| [@yukinoshi](https://github.com/yukinoshi) | [#147](https://github.com/shengjidaguai-china/BossHunter/pull/147) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#151](https://github.com/shengjidaguai-china/BossHunter/pull/151) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#153](https://github.com/shengjidaguai-china/BossHunter/pull/153) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#156](https://github.com/shengjidaguai-china/BossHunter/pull/156) | 共同实现，整条 PR 保守排除维护计分 |
| [@yukinoshi](https://github.com/yukinoshi) | [#157](https://github.com/shengjidaguai-china/BossHunter/pull/157) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #166](https://github.com/shengjidaguai-china/BossHunter/issues/166) | 仅关闭提示，无独立验证说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#175](https://github.com/shengjidaguai-china/BossHunter/pull/175) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [Issue #178](https://github.com/shengjidaguai-china/BossHunter/issues/178) | 礼貌邀请，无具体维护检查 |
| [@yukinoshi](https://github.com/yukinoshi) | [#180](https://github.com/shengjidaguai-china/BossHunter/pull/180) | 本人 PR，排除自述/自审 |
| [@yukinoshi](https://github.com/yukinoshi) | [#183](https://github.com/shengjidaguai-china/BossHunter/pull/183) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#197](https://github.com/shengjidaguai-china/BossHunter/pull/197) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yukinoshi](https://github.com/yukinoshi) | [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#81](https://github.com/shengjidaguai-china/BossHunter/pull/81) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#89](https://github.com/shengjidaguai-china/BossHunter/pull/89) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#95](https://github.com/shengjidaguai-china/BossHunter/pull/95) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #96](https://github.com/shengjidaguai-china/BossHunter/issues/96) | 本人任职申请 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#97](https://github.com/shengjidaguai-china/BossHunter/pull/97) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#98](https://github.com/shengjidaguai-china/BossHunter/pull/98) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#99](https://github.com/shengjidaguai-china/BossHunter/pull/99) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#111](https://github.com/shengjidaguai-china/BossHunter/pull/111) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #113](https://github.com/shengjidaguai-china/BossHunter/issues/113) | 本人任职申请 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#121](https://github.com/shengjidaguai-china/BossHunter/pull/121) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#122](https://github.com/shengjidaguai-china/BossHunter/pull/122) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#127](https://github.com/shengjidaguai-china/BossHunter/pull/127) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#142](https://github.com/shengjidaguai-china/BossHunter/pull/142) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #146](https://github.com/shengjidaguai-china/BossHunter/issues/146) | 本人 #147 实现与进度 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#147](https://github.com/shengjidaguai-china/BossHunter/pull/147) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#154](https://github.com/shengjidaguai-china/BossHunter/pull/154) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#158](https://github.com/shengjidaguai-china/BossHunter/pull/158) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #167](https://github.com/shengjidaguai-china/BossHunter/issues/167) | 本人 #156 实现与进度 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#169](https://github.com/shengjidaguai-china/BossHunter/pull/169) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #185](https://github.com/shengjidaguai-china/BossHunter/issues/185) | 本人 Issue/实现跟进 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #191](https://github.com/shengjidaguai-china/BossHunter/issues/191) | 本人 #219 测试修复及相关进度 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#200](https://github.com/shengjidaguai-china/BossHunter/pull/200) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#205](https://github.com/shengjidaguai-china/BossHunter/pull/205) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #207](https://github.com/shengjidaguai-china/BossHunter/issues/207) | 本人 #266 实现及相关进度 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#211](https://github.com/shengjidaguai-china/BossHunter/pull/211) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #214](https://github.com/shengjidaguai-china/BossHunter/issues/214) | 与共同实现 PR #218 同一事项，保守排除自述和自审。 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#215](https://github.com/shengjidaguai-china/BossHunter/pull/215) | 只有空白批准/一般提醒，无独立检查说明 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) | 主线采用提交含本人新增任务面板回归，整条 PR 保守排除维护；实现已进入项目榜。 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#237](https://github.com/shengjidaguai-china/BossHunter/pull/237) | 共同实现，整条 PR 保守排除维护计分 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#266](https://github.com/shengjidaguai-china/BossHunter/pull/266) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #274](https://github.com/shengjidaguai-china/BossHunter/issues/274) | 本人未合入的 #282 实现与进度 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [Issue #275](https://github.com/shengjidaguai-china/BossHunter/issues/275) | 本人未合入的 #281 实现与进度 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#281](https://github.com/shengjidaguai-china/BossHunter/pull/281) | 本人 PR，排除自述/自审 |
| [@yuppiez99999](https://github.com/yuppiez99999) | [#282](https://github.com/shengjidaguai-china/BossHunter/pull/282) | 本人 PR，排除自述/自审 |

## 权重敏感性

将每个基础权重分别乘 0.8 或 1.2，检查全部 16 个端点组合；所有人同一组权重，保持原分档不变。这是权重敏感性检查，不是统计置信区间，也没有模拟分档错误和漏采。维护四人的顺序在所有组合中不变，项目累计前六名顺序不变。靠近的名次应结合事项证据解释。

| 榜单 | 贡献者 | 当前名次 | 16 组中的最低—最高名次 |
|---|---|---:|---|
| 维护 | [@yuppiez99999](https://github.com/yuppiez99999) | 1 | 1—1 |
| 维护 | [@bianshilong0604](https://github.com/bianshilong0604) | 2 | 2—2 |
| 维护 | [@yukinoshi](https://github.com/yukinoshi) | 3 | 3—3 |
| 维护 | [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | 4 | 4—4 |
| 项目 | [@yuppiez99999](https://github.com/yuppiez99999) | 1 | 1—1 |
| 项目 | [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | 2 | 2—2 |
| 项目 | [@yukinoshi](https://github.com/yukinoshi) | 3 | 3—3 |
| 项目 | [@shuaigechz-cloud](https://github.com/shuaigechz-cloud) | 4 | 4—4 |
| 项目 | [@D1822787566](https://github.com/D1822787566) | 5 | 5—5 |
| 项目 | [@zhenian-666](https://github.com/zhenian-666) | 6 | 6—6 |
| 项目 | [@yuj-029](https://github.com/yuj-029) | 7 | 7—8 |
| 项目 | [@GioiaZheng](https://github.com/GioiaZheng) | 8 | 7—8 |
| 项目 | [@pikachuprogrammer01](https://github.com/pikachuprogrammer01) | 9 | 9—10 |
| 项目 | [@zepengfan145-netizen](https://github.com/zepengfan145-netizen) | 9 | 9—10 |
| 项目 | [@haohao-fly](https://github.com/haohao-fly) | 11 | 11—11 |
| 项目 | [@hdfhssg](https://github.com/hdfhssg) | 12 | 12—14 |
| 项目 | [@Hr18798895295](https://github.com/Hr18798895295) | 13 | 12—14 |
| 项目 | [@Rainmemery](https://github.com/Rainmemery) | 13 | 12—14 |
| 项目 | [@meixiaoxie](https://github.com/meixiaoxie) | 15 | 13—16 |
| 项目 | [@EricKingWhy](https://github.com/EricKingWhy) | 16 | 15—16 |
| 项目 | [@Nourishman](https://github.com/Nourishman) | 17 | 17—18 |
| 项目 | [@Spades6](https://github.com/Spades6) | 17 | 17—18 |
| 项目 | [@Hebuyu688](https://github.com/Hebuyu688) | 19 | 19—20 |
| 项目 | [@Pototoooo](https://github.com/Pototoooo) | 19 | 19—20 |
| 项目 | [@kai04072911-sudo](https://github.com/kai04072911-sudo) | 21 | 21—23 |
| 项目 | [@zeroTwo0617](https://github.com/zeroTwo0617) | 21 | 21—24 |
| 项目 | [@zh-hanlabs](https://github.com/zh-hanlabs) | 21 | 21—23 |
| 项目 | [@atticus-zhou](https://github.com/atticus-zhou) | 24 | 24—25 |
| 项目 | [@CHNERUI](https://github.com/CHNERUI) | 24 | 23—27 |
| 项目 | [@gaogao34](https://github.com/gaogao34) | 26 | 24—27 |
| 项目 | [@1028huli](https://github.com/1028huli) | 27 | 26—29 |
| 项目 | [@bactdt](https://github.com/bactdt) | 27 | 27—28 |
| 项目 | [@likris588-ux](https://github.com/likris588-ux) | 27 | 26—30 |
| 项目 | [@bianshilong0604](https://github.com/bianshilong0604) | 30 | 29—32 |
| 项目 | [@miaomiao636](https://github.com/miaomiao636) | 30 | 29—33 |
| 项目 | [@PetalEcho](https://github.com/PetalEcho) | 30 | 29—32 |
| 项目 | [@xinGeeks](https://github.com/xinGeeks) | 30 | 30—33 |
| 项目 | [@c4002159](https://github.com/c4002159) | 34 | 34—35 |
| 项目 | [@fenghuangyuan1412](https://github.com/fenghuangyuan1412) | 34 | 34—36 |
| 项目 | [@qingmuy](https://github.com/qingmuy) | 34 | 34—35 |
| 项目 | [@solplum](https://github.com/solplum) | 37 | 36—37 |
| 项目 | [@txz990](https://github.com/txz990) | 37 | 36—37 |
| 项目 | [@1115yt](https://github.com/1115yt) | 39 | 39—41 |
| 项目 | [@Henry369-0](https://github.com/Henry369-0) | 39 | 39—41 |
| 项目 | [@lau0708](https://github.com/lau0708) | 39 | 39—42 |
| 项目 | [@lujie-cmd](https://github.com/lujie-cmd) | 42 | 39—44 |
| 项目 | [@CaoJun1015](https://github.com/CaoJun1015) | 43 | 42—43 |
| 项目 | [@cangyuyi](https://github.com/cangyuyi) | 44 | 42—47 |
| 项目 | [@heroims](https://github.com/heroims) | 44 | 44—45 |
| 项目 | [@Changxin-YR](https://github.com/Changxin-YR) | 46 | 45—46 |
| 项目 | [@Jinxuans](https://github.com/Jinxuans) | 46 | 45—46 |
| 项目 | [@AcNHong](https://github.com/AcNHong) | 48 | 48—48 |
| 项目 | [@HanmmJade](https://github.com/HanmmJade) | 48 | 48—48 |
| 项目 | [@kgleonc](https://github.com/kgleonc) | 48 | 48—48 |
| 项目 | [@Colin-Cai0318](https://github.com/Colin-Cai0318) | 51 | 48—51 |

## 复算方法与已知限制

```sh
python3 contributions/recalculate.py --check
```

脚本不访问网络、不自动给人打分、不提交文件；它验证四维范围、公式、采用日期、任期、证据作者、自审排除、事项标识、覆盖集合和记录数量，并复算最大余数百分比、并列名次及权重敏感性。分档或证据有修订时，用 `--write` 更新计算结果后再核对榜单文案。

对同一目标分期采用的成果保留各次增量日期；项目近期分数按增量分计算，敏感性只检验两类累计榜。旧月归档仍是旧方法，不能直接比较。所有比例一位小数合计 100.0%，不把四舍五入的占比用作排序。

- 人工分档判断；可核实事实不等于客观价值精确测量。
- 维护范围是本次 149 PR / 55 Issue 候选集合，不声称覆盖删除记录、私下工作或所有未被候选集合命中的活动。
- 历史项目按源 PR、实际采用说明、主线提交和文件差异核对；不是所有历史代码逐行或产品行为重测。
- 时间投入未知，不从评论、PR、代码行或测试数量推算工时。
- elowenzhouyb-source 的方案被采用但独立份额无法分离，保留署名并暂缓量化。
- 共同实现整条 PR 保守排除维护分，可能低估其可分离的独立审核。
- 历史测试结果来自当时记录；本次没有重新运行这些产品测试。
- 自动校验能拦截同一证据片段的重复使用，不能自动理解改写后的语义相同、跨 Issue/PR 的相同目标或贡献价值；仍需人工核对与补证。
