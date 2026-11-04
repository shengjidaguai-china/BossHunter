# 外包提示与规则更新

岗位池、工作台岗位卡片、详情弹窗及 CLI 确认列表使用同一份外包识别结果。红色“外包”表示公司名单或强关键词命中，黄色“疑似外包”表示弱关键词或结构线索命中；没有命中则不显示。标签属于规则提示，雇佣关系仍须人工核实，不能当作已核实的法律结论。

## 当前支持的证据

- L0：公司完整名称匹配。统一全半角、大小写、标点和常见公司法律后缀，不使用短名称子串匹配。例如“法本文化传媒有限公司”不会因为包含“法本”而命中名单。地区子公司、其他别名需要名单中的独立条目。
- L1：岗位名称、公司名称、JD、公司行业中的强关键词。
- L2：上述字段中的弱关键词及正则线索。
- L3：JD 和岗位名称中的结构线索，仅产生“疑似外包”；可通过 `detect_structural` 关闭。

“互联网”“自研产品”等描述不会抵消已有强证据。

## 回复证据与人工反馈闭环

- L4：开启 `use_reply_history` 后，监测到的 HR 回复只提取命中的强关键词，并把来源、关键词、截断摘要和时间写入独立证据表；同一岗位和同一消息不会重复入账。
- L5：岗位详情提供“标记外包”“标记误报”和“撤销标记”。标记只改变外包识别视图，不改变人工确认、投递状态或发送频率；每次变更写入岗位历史。
- L6：当同一规范化公司名或 HR 名下，达到 `forward_propagate_n` 个不同岗位的 L4/L5 证据时，为关联岗位增加 L6 关联证据。关联证据保留来源和岗位集合，不自动替代人工确认。

默认仍关闭 L4，避免单条误识别回复扩大影响；需要时在配置中显式开启：

```yaml
outsourcing_rules:
  use_reply_history: true
  use_user_marks: true
  forward_propagate_n: 2
```

岗位详情接口 `GET /api/jobs/<job_id>` 会返回 `outsourcing_evidence` 和 `outsourcing_label`；也可使用 `GET /api/jobs/<job_id>/outsourcing-evidence` 单独读取，使用 `POST /api/jobs/<job_id>/outsourcing-label` 写入 `confirmed`、`not_outsourcing` 或 `clear`。

## 自定义规则

在现有配置中添加以下内容即可；列表追加到内置规则，条目必须是字符串，公司建议填写完整名称。

```yaml
outsourcing_rules:
  enabled: true
  detect_structural: true
  companies_user:
    - 示例供应商有限公司
  keywords_hard_user:
    - 示例强信号
  keywords_soft_user:
    - 示例弱信号
```

设置 `enabled: false` 会清除识别提示。首次打开数据库会补齐外包字段，Web 数据库入口、采集入口和 CLI 确认入口会按当前配置刷新旧岗位，包括回收站岗位。规则版本变化或旧时间戳无效时才重算；重复读取不会反复改写时间戳。

刷新只修改外包字段，保留岗位状态、评分、回收站状态和投递历史。该补丁为已有五个外包字段增加 `outsourcing_rules_version` 列，以区分历史结果使用的规则。主分支的错误记录字段迁移仍独立保留。发布前应按项目流程审阅迁移；本次验证仅使用临时测试数据库。
