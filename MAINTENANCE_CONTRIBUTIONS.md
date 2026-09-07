# BossHunter 维护贡献记录

本文件记录维护者对他人 PR 的审核、问题跟进、安全复核和治理交接等维护贡献；被主线采用的功能、修复、测试和文档等 PR 项目贡献另见 [CONTRIBUTORS.md](CONTRIBUTORS.md)。同一项成果不得在两类记录中重复计分。

## 责任与决定权

项目负责人 `@powerycy` 负责维护贡献评分及本文件，单方面决定分数、占比、证据采纳和发布定稿，无须其他维护者审批评分。维护者可以补充证据或提出更正，不能自行批准或合并涉及本人评分的修改。项目负责人不参评。

贡献评价与技术审核分开：项目负责人同时作为正式技术维护者，可按 [GOVERNANCE.md](GOVERNANCE.md) 参与技术审核、安全复核和合并，其有效批准按一人计入；本人提交或参与编写的技术改动不得自审计票。项目负责人继续不参评，贡献评分不自动授予或撤销维护权限，也不代替技术 PR 审批。

## 现任维护者贡献详情

本次核对截至 **2026-09-07 14:00（Asia/Shanghai）**。以下为项目负责人本次发布的任期基线试算，替代 9 月 3 日展示值；四位参评维护者任职均未满 30 天，仍不属于正式任期核算，不用于授予或撤销权限。项目负责人 @powerycy 不参评。

| 维护者 | 贡献占比 | 维护贡献摘要 | 代表证据 |
|---|---:|---|---|
| [@yukinoshi](https://github.com/yukinoshi) | **27.8%（试算）** | 城市快照审核发现四项陈旧测试夹具，作者修复后合入；核实 AI 运行环境异常的敏感信息边界；完成定制简历人工确认、母版与路径边界检查。 | [#156 Review](https://github.com/shengjidaguai-china/BossHunter/pull/156#pullrequestreview-5124257029) · [#179 Review](https://github.com/shengjidaguai-china/BossHunter/pull/179#pullrequestreview-5122026768) · [#143 Review](https://github.com/shengjidaguai-china/BossHunter/pull/143#pullrequestreview-5124301792) |
| [@yuppiez99999](https://github.com/yuppiez99999) | **27.8%（试算）** | 保留 51job API 安全复核与历史协作成果；补充评分解释持久化/白名单审核和账号风险咨询分类闭环。本人采集、城市数据与构建 PR 均只计项目贡献。 | [#142 安全复核](https://github.com/shengjidaguai-china/BossHunter/pull/142#pullrequestreview-5074202801) · [#77 Review](https://github.com/shengjidaguai-china/BossHunter/pull/77#pullrequestreview-5124525090) · [#168 咨询闭环](https://github.com/shengjidaguai-china/BossHunter/issues/168#issuecomment-5551623715) |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | **22.9%（试算）** | 验证前端构建与 wheel 交付，并明确 sdist 等未解决限制；独立复测编排测试并纠正覆盖率基线；真实布局复现监测风险漏检，阻止有缺口的方案直接合入。 | [#147 Review](https://github.com/shengjidaguai-china/BossHunter/pull/147#pullrequestreview-5124304248) · [#151 Review](https://github.com/shengjidaguai-china/BossHunter/pull/151#pullrequestreview-5124304668) · [#73 Review](https://github.com/shengjidaguai-china/BossHunter/pull/73#pullrequestreview-5124305409) |
| [@bianshilong0604](https://github.com/bianshilong0604) | **21.5%（试算）** | 保留招呼语网址、简历隐私、重复发送和任务并发的历史审核成果；本次未核实新增独立维护成果，不因最近几天无新增记录扣除累计成果。 | [#88 首轮](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5463732307) · [#88 复核](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5466342761) · [#90 Review](https://github.com/shengjidaguai-china/BossHunter/pull/90#issuecomment-5463882496) |

### 本次任期评分明细

等级按下文既有 0–5 级标准判断，不按评论或批准次数累加；对未完成的 PR 只记录已经完成的检查，不宣称交付闭环。四个等级依次为维护闭环与影响、Review 与安全质量、响应与推进成果、协作与交接。同分按 GitHub ID 排序，百分比用最大余数法保留一位小数并补齐至 100.0%。

| 维护者 | 四维等级 | 四维加权得分 | 任期综合分 | 贡献占比 |
|---|---|---|---:|---:|
| [@yukinoshi](https://github.com/yukinoshi) | 4 / 4 / 4 / 4 | 32 / 24 / 16 / 8 | 80 | 27.8%（试算） |
| [@yuppiez99999](https://github.com/yuppiez99999) | 4 / 4 / 4 / 4 | 32 / 24 / 16 / 8 | 80 | 27.8%（试算） |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | 3 / 4 / 3 / 3 | 24 / 24 / 12 / 6 | 66 | 22.9%（试算） |
| [@bianshilong0604](https://github.com/bianshilong0604) | 3 / 4 / 2 / 3 | 24 / 24 / 8 / 6 | 62 | 21.5%（试算） |

总分 **288**。每个维度使用上表同一组最多三项代表证据，不将其拆成多条累加。等级判断依据：

- @yuppiez99999：历史安全复核、跨改动兼容检查和咨询闭环形成持续协作结果，四维均为 4；新一轮分流和催办本身不追加分数。
- @yukinoshi：城市数据回归定位后由作者修复，运行环境问题从诊断建议到独立复核闭环，简历安全检查覆盖具体边界，四维均为 4。#143 的旧批准已被新提交撤销，仅保留其检查内容作为历史工作证据，不视为当前有效批准。
- @fengziliang43-cmyk：真实浏览器、覆盖率复测和打包验证能发现测试未覆盖的问题，审核质量为 4；已完成的审核交付、推进及交接为 3。#147 的 sdist/安装限制仍未解决，#73 关闭也不等于其问题已经修复，不按完整修复成果计分。
- @bianshilong0604：#88 的复核闭环和隐私边界识别支持 3 / 4；#90 尚未合入，推进只计 2，协作计 3。综合分是本次按历史证据重新列明的 62 分，不从旧百分比反推。

### 去重与状态核对

- @yuppiez99999 对 #142 的 Review 仅计本页；其本人 #147、#151、#153、#155–#159、#162、#170 的实现、测试及相应 Issue 关闭不重复计维护分。
- @yukinoshi 在 #77 的代码补丁及其问题发现/修复闭环归项目贡献；@fengziliang43-cmyk 在 #158 的共同实现及其发现/修复闭环也归项目贡献，本次维护评分排除这两组成果。#145 的补丁仍未合入，暂不新增项目分，其同一问题闭环也不进入本次维护评分。
- 空白批准、已撤销批准的权限效力、参与修改后的自审、机器人输出和纯合并次数均不计分；评价有正文证据的具体检查或已验证的协作结果。
- 维护者身份沿用 [MAINTAINERS.md](MAINTAINERS.md)。[#186](https://github.com/shengjidaguai-china/BossHunter/issues/186) 仍待申请人补齐资料与边界确认，尚未进入候选观察期。

## 维护贡献评估

维护贡献只衡量维护者在审核、治理、响应和交接中产生的结果，与 [项目贡献榜](CONTRIBUTORS.md) 分开。维护者自己提交的功能、修复、测试和文档属于项目贡献，不进入维护评分。

维护者任职满 30 天后进行首次正式核算。每次核算都使用从任期开始至核算日的全部有效维护证据，不限定为最近 30 天，也不按 30 天周期切段或重置。任期综合得分满分 100，按以下四个维度评估：

| 评估维度 | 权重 | 重点看什么 |
|---|:---:|---|
| 维护闭环与影响 | 40 | 全项目的风险、回归、发布或积压问题是否真正完成处理，而不是发了多少条评论 |
| Review 与安全质量 | 30 | 对他人 PR 的判断是否准确，是否发现关键风险并完成独立验证 |
| 响应与推进成果 | 20 | 是否对全项目的 PR/Issue 作出有效响应，并推动形成明确下一步或可验证结果 |
| 协作与交接 | 10 | 协作认领、候选带教和交接文档是否产生可核实结果 |

每个维度先按 0–5 级评分，再乘以权重：

| 等级 | 判定标准 |
|:---:|---|
| 0 | 无可核实证据，或负责范围长期无人处理 |
| 1 | 有回应或建议，但尚未形成可验证结果 |
| 2 | 已推进部分工作，但闭环、验证或交接仍不完整 |
| 3 | 完成应尽维护责任，有可追溯证据和明确结果 |
| 4 | 产生超出常规的质量或效率改善，且经独立复核 |
| 5 | 防止重大风险、完成重要事故/发布闭环，或形成可复用的治理改进 |

单项得分计算为 `等级 ÷ 5 × 该维度权重`；任期综合得分为四项之和。贡献占比为 `个人任期综合得分 ÷ 所有参评现任维护者任期综合得分总和 × 100%`。核算看任期内成果的质量、影响和闭环程度，不把 PR、Issue 或评论数量直接累加为分数。

评估与发布遵循以下规则：

- 任职未满 30 天时可以公布用于校验口径的基线试算，但必须明确标记“试算”和项目负责人定稿状态；试算不作为权限、晋升或离任依据。任职满 30 天并由项目负责人定稿后，才能发布正式贡献占比。
- 每人每个维度最多引用 3 项代表性成果；评分看结果质量、风险和持续性，不按 PR、Issue、评论或提交数量累加。
- 同一问题、风险或交付闭环即使拆成多个 PR/Issue 也只作为一项证据；模板化评论、机械批准和 AI/机器人活动不计分。
- 单纯接纳建议、请求更多信息或给出未落地的方向，只能作为 1–2 级过程证据，不能单独支撑“已完成”结论。
- 每位维护者的任期评分、贡献占比和最终发布结果由项目负责人 `@powerycy` 单方面决定，无须被评维护者、其他维护者或双人复核批准。维护者可以提交事实证据和更正意见，最终采纳与评分由项目负责人定稿。
- 贡献占比与当前活跃状态分开判断；停止活跃不会扣除已经形成的任期贡献。连续 14 天无维护活动仍按离任规则单独处理。
- 安全证据可以隐去漏洞细节，由负责技术检查的维护者提供结果和证据链接供评分参考；评分不要求项目负责人重新审核技术代码，也不代替技术 PR 所需的安全复核。


## 更新与发布

- 本文件的记录、评分和评分口径由项目负责人决定，通过独立贡献文档 PR 留存变更依据，不要求维护者批准评分本身。
- 项目负责人提交的评分 PR，以 PR 描述或评论中明确的定稿决定作为评分授权；维护者只核对格式、证据链接和展示同步，不重新评定或否决评分。
- 对评分有异议时，提交具体证据和更正请求，由项目负责人决定；旧记录保留，修订说明记录日期和原因。
- README 的维护贡献摘要由维护者依据本文件同一数据快照同步，不重新评分，也不因同步展示要求项目负责人审核整个 README。
- 若 PR 同时包含技术改动、维护者任免、权限或技术审核规则，应拆为技术或治理 PR，按对应规则独立审核。

## 历史基线

### 2026-09-03（原始试算，未定稿）

以下保留原始记录；当时的 Issue/PR 状态只表示历史核对结果，不代表本次状态。

<details>
<summary>展开 2026-09-03 原始试算</summary>


以下沿用 2026-09-03 的历史基线试算，数值和证据原样迁入，尚未由项目负责人定稿；迁移不代表本次重新评分或批准已有分数。

以下为截至 **2026-09-03** 已核实的维护活动摘要，仅记录对他人 PR 的 Review、Issue 治理、安全复核和交付协作，不计入本人提交的功能、修复、测试或文档。

| 维护者 | 贡献占比 | 维护贡献摘要 | 代表证据 |
|---|---:|---|---|
| [@yuppiez99999](https://github.com/yuppiez99999) | **33.9%（试算）** | 对 51job API 采集完成只读边界、失败关闭、速率控制、断点续采和真实环境验证检查；持续梳理积压 PR 的风险、冲突与合并阻塞项，并主动让原贡献者方案承接合并。 | [#142 安全复核](https://github.com/shengjidaguai-china/BossHunter/pull/142#pullrequestreview-5074202801) · [#139 Review](https://github.com/shengjidaguai-china/BossHunter/pull/139#pullrequestreview-5084448426) · [#89 协作复核](https://github.com/shengjidaguai-china/BossHunter/pull/89#pullrequestreview-5056851017) |
| [@yukinoshi](https://github.com/yukinoshi) | **28.8%（试算）** | 对简历失败恢复 PR 完成全量测试、前端类型检查和安全红线验证并批准；为评分解释和招呼语队列改动处理冲突、补充合并方案与完整验证。 | [#92 Review](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5089153466) · [#77 合并分析](https://github.com/shengjidaguai-china/BossHunter/pull/77#issuecomment-5466530159) · [#86 合并验证](https://github.com/shengjidaguai-china/BossHunter/pull/86#issuecomment-5466756964) |
| [@bianshilong0604](https://github.com/bianshilong0604) | **26.3%（试算）** | 在招呼语网址防护中识别简历隐私、可信网址来源和重复发送边界问题，并在修改后完成复核；同时审查招呼语生成流程的岗位状态与任务并发风险。 | [#88 首轮 Review](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5463732307) · [#88 复核](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5466342761) · [#90 Review](https://github.com/shengjidaguai-china/BossHunter/pull/90#issuecomment-5463882496) |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | **11.0%（试算）** | 对安全锁是否应随账号切换重置完成风险边界研判，并对一键投递失效问题提出分层排查与复现信息要求；相关 Issue 尚未闭环。 | [#78 风险研判](https://github.com/shengjidaguai-china/BossHunter/issues/78#issuecomment-5452233325) · [#93 问题排查](https://github.com/shengjidaguai-china/BossHunter/issues/93#issuecomment-5452071152) |



</details>
