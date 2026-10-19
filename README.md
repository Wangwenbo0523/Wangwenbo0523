# dq-sentinel · 数据质量哨兵

一个可复用的 **Agent Skill**：对业务数据表做自动剖析、规则检查、质量报告与修复建议，并用 ground truth 评测检出率与误报率。

> 演示库：`users` / `products` / `orders` 三张表，注入 **20 类脏数据**，**22 条规则**，检出率 **100%**、误报率 **0%**。

## 为什么做这个

数据治理里“发现问题”通常靠人工抽查：漏报多、口径不统一、复盘完就忘。
这个 skill 把流程固化成一条流水线：

```
剖析（profile） → 规则检查（check） → 报告（report） → 修复建议 → 评测（evaluate） → CI 门禁
```

每条规则都对应一个数据质量维度（完整性 / 唯一性 / 有效性 / 一致性 / 及时性），
每个结论都能回到 rowid，方便定位和复盘。

## 快速开始

环境：Python 3.9+，无第三方依赖（标准库 `sqlite3`）。

```bash
cd dq-sentinel
python scripts/dq.py demo
```

输出示例：

```
== dq-sentinel demo ==
表：users / products / orders
规则 22 条，违规 24 行
检出率 100.0%，误报率 0.0%，F1 1.0000
报告已写入：reports/latest.md
```

> 24 是“规则命中次数”，23 是“问题行数”（有一行同时触发数量与金额两条规则）。

其他命令：

| 命令 | 作用 |
| --- | --- |
| `python scripts/dq.py init` | 生成演示库（含 20 类脏数据与 ground truth） |
| `python scripts/dq.py profile` | 输出表结构、空值率、枚举分布 |
| `python scripts/dq.py check` | 按 `rules/rules.json` 巡检并写报告 |
| `python scripts/dq.py check --fail-on P0` | CI 门禁：P0 违规时退出码 1 |
| `python scripts/dq.py evaluate` | 与 ground truth 对比，算检出率 / 误报率 |
| `python scripts/dq.py mark --table users --rowid 7 --rule "users.phone 手机号格式" --reason "测试账号"` | 标注误报，下轮自动抑制 |
| `python scripts/dq.py unmark --table users --rowid 7` | 取消误报标注 |
| `python scripts/dq.py suggest` | 从画像生成候选规则（`rules/candidates.json`） |
| `python scripts/dq.py suggest --llm` | 调用 LLM 润色（需 `DQ_LLM_BASE` / `DQ_LLM_KEY`） |
| `python scripts/dq.py history` | 查看历次巡检趋势（`data/history.jsonl`） |
| `python tests/test_smoke.py` | 冒烟测试（指标、误报抑制、门禁、候选规则） |

## 规则怎么写

见 `rules/rules.json`。支持 8 种规则类型：`not_null` / `unique` / `range` /
`regex` / `enum` / `foreign_key` / `freshness` / `expression`。

自定义一致性规则用 `expression`，写一段返回 `rowid` 的 SQL 即可：

```json
{
  "name": "orders.amount 与 qty×price 一致",
  "type": "expression",
  "violation_sql": "SELECT o.rowid FROM orders o WHERE o.unit_price IS NOT NULL AND ABS(o.amount - o.qty * o.unit_price) > 0.01",
  "severity": "P0"
}
```

## 评测方法

`tests`/`data` 里的 ground truth 记录了每条注入问题的 `(table, rowid, issue)`。
`evaluate` 按行计算：

- 检出率 = TP / (TP + FN)
- 误报率 = FP / (TP + FP)
- 按问题类型统计漏报，用于 badcase 归因
- 规则覆盖率 = 被规则覆盖的关键字段 / 关键字段总数（主键、外键、时间、电话/邮箱、数值、低基数文本）

当前演示：23 个问题行全部命中，无漏报、无误报；17 个关键字段全部有规则覆盖。

## 历史趋势

每次 `check` / `demo` 会向 `data/history.jsonl` 追加一行（规则数、违规数、P0/P1/P2、
检出率、覆盖率）。用 `python scripts/dq.py history` 查看，方便判断治理是在变好还是变坏。

### 误报标注

真实巡检里规则会误报（业务允许的空值、历史数据、维表延迟）。用 `mark` 标注后，
`check` 会自动抑制并在报告里单列“已抑制”数量；原始违规仍保留在 `latest.json`，方便复盘。

```bash
python scripts/dq.py mark --table orders --rowid 23 --rule "orders.created_at 新鲜度（7 天）" --reason "补跑中"
```

### CI 门禁

```bash
python scripts/dq.py check --fail-on P0
```

P0 违规时退出码为 1，可直接接在发布流水线里（示例见 `.github/workflows/dq-gate.yml`）。

### 候选规则

```bash
python scripts/dq.py suggest        # 启发式
python scripts/dq.py suggest --llm  # 配置了 DQ_LLM_BASE 时调用 LLM 润色
```

输出 `rules/candidates.json`，`already_exists` 标出已被现有规则覆盖的项，人工确认后合并进 `rules.json`。

## 3 分钟演示脚本

1. **背景**：数据入仓前靠人工抽查，漏报和误报都说不清
2. **做法**：把检查做成规则 + 报告 + 评测，每条规则有设计依据
3. **指标**：3 张表、20 类脏数据、22 条规则，检出率 100%、误报率 0%
4. **业务映射**：脏数据会让报表偏差，这个 skill 可以挂在发布前做门禁

## 路线图

- [x] `--fail-on P0`：CI 门禁模式
- [x] 误报标注（`mark` / `unmark`），巡检自动抑制
- [x] 候选规则生成（启发式 + 可选 LLM 润色）
- [x] 规则覆盖率指标（关键字段覆盖）
- [x] 历史趋势（`history.jsonl` + `history` 命令）
- [ ] DuckDB / Spark 适配（SQL 下推）
- [ ] 整行重复、空值聚集等扩展规则
- [ ] HTML 报告与趋势图

## 目录

```
dq-sentinel/
├── SKILL.md
├── README.md
├── rules/rules.json
├── references/rule-catalog.md
├── scripts/{dq.py, make_demo.py}
├── data/{demo.db, ground_truth.json, manifest.json}
├── reports/{latest.md, latest.json}
└── tests/test_smoke.py
```
