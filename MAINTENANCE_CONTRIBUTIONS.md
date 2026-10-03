# BossHunter 维护贡献记录

记录对他人工作的实质审核、安全复核、问题推进及交接。本人功能、修复、测试和文档实现计入 [项目贡献](CONTRIBUTORS.md)，同一成果不重复计入两榜。项目负责人 @powerycy 负责结果确认，不参评。

## 现任维护者贡献详情

截至 **2026-09-28 10:38（Asia/Shanghai）**，按任期累计有效成果评估，经项目负责人确认后定稿。@yukinoshi 与 @yuppiez99999 按任职起日已满 30 天；@fengziliang43-cmyk 与 @bianshilong0604 尚未满 30 天，仍为试算。占比合计 **100.0%**。

沿用维护闭环与影响 /40、Review 与安全质量 /30、响应与推进成果 /20、协作与交接 /10 四维，每维按 0–5 级折算权重、最多使用三项代表成果；占比用最大余数法保留一位小数。已完成的审核可计维护成果，未修复或未合入的问题不计为修复闭环。

| 维护者 | 贡献占比 | 维护贡献摘要 | 代表证据 |
|---|---:|---|---|
| [@yukinoshi](https://github.com/yukinoshi) | **25.5%** | 复核简历失败恢复的状态保护与历史记录；定制简历人工确认和路径边界；独立对照基线验证 WebSocket 端点兼容。 | [#92 验证](https://github.com/shengjidaguai-china/BossHunter/pull/92#pullrequestreview-5077287271) · [#143 安全复核](https://github.com/shengjidaguai-china/BossHunter/pull/143#pullrequestreview-5124301792) · [#249 独立验证](https://github.com/shengjidaguai-china/BossHunter/pull/249#pullrequestreview-5313324854) |
| [@yuppiez99999](https://github.com/yuppiez99999) | **25.5%** | 独立复核风控暂停提示与模型发现凭据边界，对照主线区分既有测试失败；指出移动端默认全网监听等阻塞风险，未把未合入方案视为修复闭环。 | [#189 基线对照复核](https://github.com/shengjidaguai-china/BossHunter/pull/189#pullrequestreview-5161673105) · [#204 阻塞意见](https://github.com/shengjidaguai-china/BossHunter/pull/204#pullrequestreview-5149691088) · [#212 Review](https://github.com/shengjidaguai-china/BossHunter/pull/212#pullrequestreview-5161688265) |
| [@bianshilong0604](https://github.com/bianshilong0604) | **24.8%（试算）** | 招呼语隐私与网址边界复核；定位 macOS 启动器空格路径故障并追踪修复；验证薪资换算不猜测无单位数据。 | [#88 复核](https://github.com/shengjidaguai-china/BossHunter/pull/88#issuecomment-5466342761) · [#238 请求修改](https://github.com/shengjidaguai-china/BossHunter/pull/238#pullrequestreview-5300604146) / [修复复核](https://github.com/shengjidaguai-china/BossHunter/pull/238#pullrequestreview-5324891025) · [#241 Review](https://github.com/shengjidaguai-china/BossHunter/pull/241#pullrequestreview-5274630828) |
| [@fengziliang43-cmyk](https://github.com/fengziliang43-cmyk) | **24.2%（试算）** | 独立检查构建交付与薪资失败策略，区分主线既有失败；完成薪资预筛定向验证与后续审核交接，未合入部分只计已完成审核。 | [#147 构建验证](https://github.com/shengjidaguai-china/BossHunter/pull/147#pullrequestreview-5124304248) · [#205 独立复核](https://github.com/shengjidaguai-china/BossHunter/pull/205#pullrequestreview-5189782344) · [#252 验证与交接](https://github.com/shengjidaguai-china/BossHunter/pull/252#pullrequestreview-5330009474) |

@bianshilong0604 的审核团队邀请已接受，身份说明按已合并的 [#200](https://github.com/shengjidaguai-china/BossHunter/pull/200) 和 [维护者记录](MAINTAINERS.md) 同步。

## 候选维护者（观察期）

| GitHub | 擅长方向 | 观察期开始 | 状态 |
|---|---|---|---|
| [@shuaigechz-cloud](https://github.com/shuaigechz-cloud) | 会话与消息链路、招呼语约束、定制简历与人工确认 | 2026-09-07 | 观察中（Triage；已接受邀请） |

身份沿用 [候选维护者记录](MAINTAINERS.md#候选维护者观察期)，推荐/带教人待指定。其已采纳的实现已计入项目贡献总榜；候选期独立维护成果尚待核实，本次维持候选身份，不纳入正式维护者贡献占比，不涉及晋升或权限变更。

[维护者身份、任期与候选记录](MAINTAINERS.md) · [治理规则](GOVERNANCE.md)
