# 可选的本地面试准备

此功能将选定岗位交给面试工具，不改变 BossHunter 的采集、确认、投递或监测流程，也不标记岗位“已发送”。无需安装面试工具即可导出 JD；直接联通目前是关联功能 PR 中的配套协议，不代表已有版本均已支持。

配套接收实现：[Interview Sim PR #1](https://github.com/miaomiao636/interview-sim/pull/1)，测试分支为 `feat/bosshunter-job-handoff`。在接收端正式合并/发布前，测试者需检出该分支并按其快速开始安装；普通用户可继续使用 Markdown，不必替换已有稳定安装。上游提案见 [BossHunter #216](https://github.com/shengjidaguai-china/BossHunter/issues/216)。

## 用法

1. 在“岗位池”展开岗位，或从工作台打开岗位详情，点击“准备面试”。
2. 展开“查看将交接的岗位内容”，核对公司、岗位、城市、薪资原文、学历和完整 JD。不会包含你的简历、Key、HR 字段、评分理由、招呼语或聊天记录；但 JD 原文本身仍可能包含招聘方联系方式。
3. 可直接“下载 JD（Markdown）”，交给其他 Agent，或在 [Interview Sim](https://github.com/miaomiao636/interview-sim) 的岗位文件导入中选择。当前 Interview Sim v1.5.0 支持这一手动方式。
4. 使用直接联通时，另行安装支持 `interview-sim:job` v1 协议的 Interview Sim 配套版本，让 Agent 启动它（`interview-sim web`）。将服务实际输出的地址填入本地地址栏，不能打开源文件 `index.html`，也不能使用 GitHub Pages 文档站点。
5. 勾选确认后点击“打开并交接岗位”。新标签页中只出现**未保存岗位草稿**。自行补充真实简历，核对职责/要求后保存，再选择面试官、声音与难度；交接本身不调用模型或开始面试。

两套应用应在同一电脑分别运行；使用桌面 Windows、macOS、Linux 的标准浏览器消息机制，不依赖特定 Agent。Agent 只负责按各项目文档安装/启动。关闭应用服务后须重新启动；入口不会扫描端口、执行命令或自动安装软件。

## 地址与失败提示

- 仅支持 `http://127.0.0.1:端口` / `http://localhost:端口` 的根地址，端口范围 1–65535，不含默认 80。不支持 HTTPS、IPv6、路径、参数、凭据、域名或局域网地址。两端的 origin 必须不同。
- 默认填入 `http://127.0.0.1:8800` 只是示例；端口被占用时应使用面试服务实际输出的地址。`localhost` 与 `127.0.0.1` 属于不同 origin，不能依赖跳转来替换。
- 地址只保存在当前 BossHunter 浏览器的本地设置中，岗位内容不写入浏览器持久存储。
- 新标签页被拦截：允许本地站点打开弹窗后再试。
- 15 秒未收到确认：检查是否启动服务、是否使用支持交接的版本、是否填对地址；先核对新页是否已有草稿，避免重复保存。可以停止等待或使用 Markdown 降级。
- JD 超过 15,000 个 JavaScript 字符，或结构字段超限：直接交接会拒绝，不截断；Markdown 仍保留完整原文。
- 接收到草稿不等于保存或面试完成；刷新未保存草稿会丢失，可重新从来源岗位交接。

## 协议与隐私边界

本实现没有新增服务端端点、CORS 许可、第三方运行依赖或数据库结构。两项目分别安装和授权，未把任何一方源码复制到另一项目中。

浏览器仅在明确用户点击后打开 `/?import=job&source=<来源 origin>`，URL 不含岗位资料。接收端清理这两个路由参数，以防刷新重复导入。新标签页必须保留 `opener` 才能完成握手，因此**只应连接用户信任、确实由其启动的本地面试服务**；回环地址不等于进程身份认证。

双方对每条消息验证精确 `event.origin` 和 `event.source`，发送时指定精确 `targetOrigin`，禁止 `*`；不跟随跳转到其他 origin，不从任意 iframe 接收。握手顺序：

1. 接收页向 opener 发 `{ "type": "interview-sim:ready", "version": 1 }`。
2. 来源页最多发一次 `{ "type": "interview-sim:job", "version": 1, "job": { ... } }`。
3. 接收页校验并展示草稿后发 `{ "type": "interview-sim:received", "version": 1 }`，清除监听并断开 opener。来源页收到确认后清理监听和计时器；未收到时 15 秒超时。接收页最多等待 30 秒。

`job` **仅允许且必须含有**下列字符串字段：

| 字段 | 上限 | 含义 |
|---|---:|---|
| `company` | 160 | 公司 |
| `target_role` | 160 | 岗位，不能为空 |
| `city` | 80 | 城市 |
| `salary` | 100 | 薪资原文，不强制解析 |
| `education` | 80 | 学历原文 |
| `jd` | 15,000 | JD，不能为空 |

字段缺失、未知字段、错误类型、错误版本、超长内容应拒收。岗位文本始终作为数据处理，不作为 HTML 或 Agent 指令执行。接收后依然由用户核对/保存，调用远程模型时遵循面试应用自身的配置与隐私说明。

## 验证

```bash
node --experimental-strip-types --test tests/js/interview_handoff.test.ts
npm --prefix src/bosshunter/web/frontend run build
node tests/browser/interview-handoff.cjs
```

Node 单测使用 Node 22.6+ 的类型剥离功能。浏览器测试沿用仓库 `PLAYWRIGHT_MODULE` / `BROWSER_CHANNEL` 配置，见 [浏览器测试说明](../tests/browser/README.md)。全部使用合成岗位、临时本地 HTTP 服务，不访问招聘平台、真实简历或模型服务。
