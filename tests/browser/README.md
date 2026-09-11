# 本地工作台浏览器回归

先在 `src/bosshunter/web/frontend` 运行 `npm run build`。随后在仓库根目录、使用已安装的 Playwright 和 Chrome 运行：

```sh
node tests/browser/retry-feedback.cjs
```

`PLAYWRIGHT_MODULE` 可指向已有 Playwright 模块目录，`BROWSER_CHANNEL` 默认 `chrome`。测试只使用临时本地 HTTP 服务和合成岗位，阻止所有外部请求，不会向招聘平台发送信息。覆盖正常发送返回 409 时提示可见、最后一条失败重试入队并消失后成功提示仍可见，以及等待期间禁用按钮。断言失败时返回非零状态；截图和 JSON 写入 `output/playwright`。

## 可选面试岗位交接

使用同样的前端构建和 Playwright 环境运行：

```sh
node tests/browser/interview-handoff.cjs
```

该测试启动 BossHunter 合成 API 和两个不同端口的本地接收页，不需要安装 Interview Sim、配置模型或连接招聘平台。接收页只验证浏览器交接协议并显示内存草稿，不保存岗位、不调用 AI，也不会更改 BossHunter 的岗位或执行任务。

覆盖：

- `/jobs` 展开岗位后的准备面试入口，以及确认前禁止发送。
- Markdown 下载和预览仅含招聘字段，不包含合成的简历、密钥、HR、招呼语、评分理由或聊天标记。
- 精确来源和窗口握手、协议版本验证、单次发送，以及 `localhost` / `127.0.0.1` 两种本机地址；URL 仅包含接收模式和来源地址，不含 JD。
- 远程、带路径/参数、BossHunter 自身地址在打开标签前被拒绝。
- 弹窗拦截、停止等待、15 秒超时的恢复提示及监听器清理。超时使用浏览器虚拟时钟，不等待真实 15 秒。
- 1440px、1024px、768px、320px 视口下交接说明、确认和操作区域可见，以及所有页面无运行时/控制台错误、无外网请求、无写接口调用（窄屏检查只防止新增入口溢出，不代表承诺移动端支持）。

截图输出为 `output/playwright/interview-handoff-<宽度>.png`，结构化结果为 `interview-handoff-results.json`。`BROWSER_BUILD_DIR` 可选指向另一份已构建前端，供验证旧版本无法通过新增入口回归；默认使用本仓库 `dist`。该隔离接收页不替代真实 Interview Sim 跨项目集成验证。
