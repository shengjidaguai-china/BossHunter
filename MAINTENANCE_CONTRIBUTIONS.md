# BossHunter 正式维护者贡献榜

> 快照：**2026-10-31 14:05:12（Asia/Shanghai）**。按正式维护者各自任期累计，项目负责人不参评。

维护贡献包括独立审核、问题定位、复现、验证、具体分诊和协调。功能、修复、测试及文档的实现另见 [项目贡献榜](CONTRIBUTORS.md)。同一个人可同时上榜；自己的实现、自测和自审不重复拿维护分。

本次使用 [v2.1 评判标准](CONTRIBUTION_CRITERIA.md)：每个独立事项按有效维护工作 E、已证实影响 I、验证证据 V、推进闭环 P 评分，`2E + 2I + V + P`，**逐项相加、个人不封顶**。一个 PR 可以有两个独立目标，同一问题跨 Issue / PR 合并计；多轮复查提升证据等级，重复批准不加分。

## 累计维护贡献

共 **172 个个人维护事项、1814 分**。同一事项若有不同维护者的独立工作可分别计入，各人的 PR 覆盖有交集。占比为个人分数除以本榜总分，不是工时、PR 数量占比或全部真实维护价值占比。

| 排名 | 维护者 | 维护分 | 榜内占比 | 事项 | PR 覆盖 | Issue 覆盖 | 活跃日期数 |
|:---:|---|---:|---:|---:|---:|---:|---:|
| 1 | [@yuppiez99999](https://github.com/yuppiez99999) | **890** | **49.0%** | 95 | 81 | 36 | 43 |
| 2 | [@bianshilong0604](https://github.com/bianshilong0604) | **388** | **21.4%** | 30 | 29 | 1 | 14 |
| 3 | [@yukinoshi](https://github.com/yukinoshi) | **337** | **18.6%** | 32 | 32 | 2 | 11 |
| 4 | [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | **199** | **11.0%** | 15 | 15 | 0 | 5 |

任期起点：@yukinoshi、@yuppiez99999 为 2026-08-29；@bianshilong0604、@fengziliang43-cmyk 为 2026-08-30，均从北京时间当日 00:00 起算。身份与任期依据另见 [MAINTAINERS.md](MAINTAINERS.md)。

## 工作量和深度分别看

| 维护者 | 有效工作 2E | 已证实影响 2I | 验证 V | 推进 P | 每事项平均分 |
|---|---:|---:|---:|---:|---:|
| [@yuppiez99999](https://github.com/yuppiez99999) | 402 | 312 | 98 | 78 | 9.37 |
| [@bianshilong0604](https://github.com/bianshilong0604) | 174 | 132 | 64 | 18 | 12.93 |
| [@yukinoshi](https://github.com/yukinoshi) | 162 | 100 | 56 | 19 | 10.53 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | 90 | 62 | 34 | 13 | 13.27 |

yuppie 覆盖和持续处理量最大，因此累计贡献领先。0604 与 feng 的平均事项分更高，说明本次材料中其独立验证、有效缺陷发现等占比更高。平均分受接手任务类型影响，不能单独当作个人能力或质量排名；维护咨询与常规检查也有项目价值。

下面按本人留下的验证证据分组。一个事项只进入一个 V 档；P2 可与任一 V 档重叠，不能再相加成工作量。多轮复查、主线对照和跨层验证已进入事项分，无论评论几次都不机械翻倍。

| 维护者 | V0 分析/分诊 | V1 静态/引用报告 | V2 本人定向运行 | V3 复现复查/对照/多层验证 | P2 修订复核或确认闭环 |
|---|---:|---:|---:|---:|---:|
| [@yuppiez99999](https://github.com/yuppiez99999) | 7 | 80 | 6 | 2 | 10 |
| [@bianshilong0604](https://github.com/bianshilong0604) | 0 | 6 | 14 | 10 | 4 |
| [@yukinoshi](https://github.com/yukinoshi) | 0 | 19 | 2 | 11 | 2 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | 0 | 3 | 5 | 7 | 1 |

**工时仍未知。** 81 个 PR、97 条带正文评审或 43 个活跃日期都不能换算成小时；活跃日期只表示当日有可核实记录。事项数体现处理范围，E/V 与逐项说明体现复杂度和深度，本榜不虚构实际耗时。

## 同一个 PR 不再一律只算一份贡献

- 常规局部核对：yuppie 在 [#273](https://github.com/shengjidaguai-china/BossHunter/pull/273) 的空白学历一致性检查为 E1/I1/V1/P0，**5 分**。
- 多轮验证：yuki 在 [#92](https://github.com/shengjidaguai-china/BossHunter/pull/92) 的状态覆盖、失败历史、修订复查及主线对照为 E4/I3/V3/P2，**19 分**。
- 关键缺口及修订复核：0604 在 [#256](https://github.com/shengjidaguai-china/BossHunter/pull/256) 定位实习开关可经详情/历史发送绕过，复查三层修订并运行保护回归，为 E4/I4/V3/P2，**21 分**。
- 有效发现但尚未闭环：feng 在 [#259](https://github.com/shengjidaguai-china/BossHunter/pull/259) 的双 SQLite 连接复现与并发覆盖诊断为 E3/I3/V2/P1，**15 分**；未采用候选补丁不冒充项目成果，补丁自测不叠加维护分。
- 一个 PR 两个独立目标：yuppie 在 [#204](https://github.com/shengjidaguai-china/BossHunter/pull/204) 分别发现默认无鉴权全网监听的隐私风险（16 分）和二维码缺少依赖的安装故障（10 分）。各计本身范围，不给整个 PR 重复打满分。

## 工作记录与本轮修正

| 维护者 | 带正文 Review 记录 | 同 PR/状态/正文去重后 | Issue 回复 | 覆盖 PR：已合并 / 未合 / 关闭未合 |
|---|---:|---:|---:|---|
| [@yuppiez99999](https://github.com/yuppiez99999) | 97 | 97 | 50 | 49 / 19 / 13 |
| [@bianshilong0604](https://github.com/bianshilong0604) | 30 | 30 | 1 | 22 / 6 / 1 |
| [@yukinoshi](https://github.com/yukinoshi) | 35 | 34 | 2 | 29 / 1 / 2 |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | 13 | 13 | 0 | 10 / 3 / 2 |

- 本轮从 [#218](https://github.com/shengjidaguai-china/BossHunter/pull/218) 的实际采用提交确认 yuppie 也提供了任务面板专项回归。该实现补入项目榜，同时将整条 PR 的本人审核从维护榜保守排除；因此其有效 PR 覆盖由此前 82 改为 **81**，Review 由 100 改为 **97**。
- 0604 在 [Issue #79](https://github.com/shengjidaguai-china/BossHunter/issues/79) 的泛泛欢迎没有具体审核或可执行分诊，本轮不评分，也不列入已计分 Issue 覆盖。
- yuppie 的 [#294](https://github.com/shengjidaguai-china/BossHunter/pull/294) / [#299](https://github.com/shengjidaguai-china/BossHunter/pull/299) / [Issue #293](https://github.com/shengjidaguai-china/BossHunter/issues/293) 合为同一启动失败事项；Issue 中同一问题的提出、跟进和关闭不再次记整份贡献。
- [#287](https://github.com/shengjidaguai-china/BossHunter/pull/287)、[#290](https://github.com/shengjidaguai-china/BossHunter/pull/290)、[#291](https://github.com/shengjidaguai-china/BossHunter/pull/291)、[#296](https://github.com/shengjidaguai-china/BossHunter/pull/296) 等未闭环的有效问题发现仍计诊断贡献；后续空白批准不能证明修好了。测试数字若只是引用作者/CI，只评 V1。
- 已知漏检或错误建议不获得对应发现/闭环分，也不抹掉该人已证明的其他独立工作。所有排除记录见明细。

## 本次审查后的计分修正

权重保持 `2E+2I+V+P`。维护总分由 1825 改为 **1814 分**，排名不变。

- **yuppie：896 → 890。** #280 的评审仅涉及发送时间窗口，安装指南分项缺少证据，撤回 5 分；#202 的版本核对保留 5 分，共用构建和交接仅归首页主事项，撤回重复推进 1 分。
- **feng：204 → 199。** #280 虽提及 Windows 安装指引和启动器运行，但没有独立指引步骤核验记录；运行已计入窗口主事项，不再另计 5 分。待有具体证据再补录。
- **#204 的 16+10 分保留。** 默认监听的隐私风险与 qrcode 缺失依赖，各有独立的缺陷分析、静态核对和修正路线；分项分别绑定原文段落，未重复计算构建或合并动作。
- **共同实现 PR 的排除仍属暂缓。** 原则已改为按实际动作分开；本轮没有凭原则放宽就给已排除记录补分。必须先证明维护动作独立于本人实现、自测和自审。

账本记录撤回项的原始评分、证据和改分理由；复算会检查计分摘录与来源位置，阻止同一来源片段被换名重复计分。跨来源、改写后的同义动作仍靠人工核对。

## 精度与复算

本次覆盖 149 个 PR、55 个 Issue 的候选证据集，按本人、任期、快照和工作内容筛选；不声称覆盖删除的评论、私下沟通及所有未命中的活动。共同实现整条 PR 保守排除维护分，可能低估可分离的审核，后续可凭证据补录。历史测试只引用当时记录，本次没有重新运行产品测试。

对四项权重分别上下浮动 20% 的 16 组组合检查，四人的名次均不变。这说明当前排序在这组权重变化下稳定，不能消除人工分档和证据缺失的不确定性。

[评判标准](CONTRIBUTION_CRITERIA.md) · [每事项原分、理由与来源](CONTRIBUTION_AUDIT_2026-10-31.md) · [评分账本](contributions/2026-10-31.json) · [可复算结果](contributions/2026-10-31-results.json)

运行 `python3 contributions/recalculate.py --check` 可验证分数、占比、任期、作者和自审排除。分数为统一标准下的可复核评估，不把人工评判伪装成对真实价值或实际工时的精确测量。
