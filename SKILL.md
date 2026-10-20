---
name: dq-sentinel
description: 数据质量巡检与治理 skill。对 SQLite 数据表做自动剖析（空值率、唯一率、分布）、按 JSON 规则检查完整性/唯一性/有效性/一致性/及时性，输出 Markdown 报告与修复建议，并支持与 ground truth 对比计算检出率与误报率。适用于湖仓入仓前校验、营销/订单/用户等业务表巡检、报表产出前的质量门禁。
---

# 数据质量哨兵（dq-sentinel）

**解决的问题**：数据治理里“发现问题”通常靠人工抽查和事后复盘。本 skill 把 **剖析 → 规则检查 → 报告 → 修复建议 → 质量门禁** 做成一条可复用的流水线，让每次巡检都能留下可对比的指标。

## 何时使用

- 入仓前对源表做质量体检（完整性、唯一性、有效性）
- 营销 / 订单 / 用户 / 商品等业务表的日常巡检
- 报表、指标产出前的质量门禁
- 数据质量事故复盘：把一次事故沉淀成一条规则

## 快速开始

```bash
python scripts/dq.py demo                              # 生成演示库 + 巡检 + 评测 + 报告
python scripts/dq.py init --clean                      # 干净库（CI 门禁基线）
python scripts/make_demo_duck.py                       # DuckDB 演示库（需 pip install duckdb）
python scripts/dq.py check --db data/demo.duckdb       # 在 DuckDB 上跑同一套规则
python scripts/dq.py profile                           # 输出表结构与字段分布画像
python scripts/dq.py check                             # 按 rules/rules.json 巡检并写报告
python scripts/dq.py check --fail-on P0                # CI 门禁：P0 违规时退出码 1
python scripts/dq.py check --min-coverage 0.8          # 覆盖率门禁：低于 80% 退出码 1
python scripts/dq.py evaluate                          # 与 ground truth 对比，算检出率 / 误报率
python scripts/dq.py mark --table users --rowid 7 \
  --rule "users.phone 手机号格式" --reason "测试账号"    # 标注误报（下轮巡检自动抑制）
python scripts/dq.py suggest                           # 从画像生成候选规则
python scripts/dq.py suggest --llm                     # 尝试 LLM 润色（需 DQ_LLM_BASE 等）
python scripts/dq.py history                           # 查看历次巡检趋势
python scripts/dq.py unmark --table users --rowid 7     # 取消误报标注
```

输出：

- `reports/latest.md` —— 人读报告（总览、规则结果、违规明细、评测、修复建议）
- `reports/latest.html` —— 可视化报告（指标卡片、趋势 sparkline、规则表）
- `reports/latest.json` —— 机读结果，供 CI 或看板消费
- `rules/candidates.json` —— 候选规则（`already_exists` 标出是否已被现有规则覆盖）
- `data/feedback.json` —— 误报标注记录
- `data/history.jsonl` —— 历次巡检趋势（规则数、违规数、检出率、覆盖率）

## 规则配置（rules/rules.json）

每条规则包含 `name` / `type` / `severity` 与类型参数：

| type | 作用 | 关键参数 | 对应质量维度 |
| --- | --- | --- | --- |
| `not_null` | 字段非空 | `column` | 完整性 |
| `unique` | 业务键唯一 | `columns` | 唯一性 |
| `range` | 数值范围 | `column` / `min` / `max` | 有效性 |
| `regex` | 格式校验 | `column` / `pattern` | 有效性 |
| `enum` | 枚举值 | `column` / `values` | 有效性 |
| `foreign_key` | 外键存在性 | `column` / `ref_table` / `ref_column` | 完整性 |
| `freshness` | 数据及时性 | `column` / `max_age_days` | 及时性 |
| `expression` | 自定义 SQL | `violation_sql`（必须 `SELECT rowid`） | 一致性 |
| `duplicate_rows` | 整行/列组合重复 | `columns`（可选，默认全部列） | 唯一性 |
| `null_rate` | 列空值率超阈值 | `column` / `max_rate` | 完整性 |

示例（订单金额一致性）：

```json
{
  "name": "orders.amount 与 qty×price 一致",
  "type": "expression",
  "violation_sql": "SELECT o.rowid FROM orders o WHERE o.unit_price IS NOT NULL AND ABS(o.amount - o.qty * o.unit_price) > 0.01",
  "severity": "P0"
}
```

## Agent 工作流

1. `profile`：先看表结构、空值率、枚举分布，判断哪些字段值得配规则
2. 读业务描述，在 `rules.json` 补规则，每条规则写清 `design_basis`（为什么这么定）；
   也可以先跑 `suggest` 拿候选规则，人工确认后合并
3. `check`：生成报告，按 P0 → P1 → P2 处理
4. 按报告里的“修复建议”改数据或补维表映射
5. 有 ground truth 时 `evaluate`，把误报逐条归因：
   确认是规则误报的，用 `mark` 标注（下轮自动抑制），并在 `rules.json` 调整阈值/白名单
6. 接入 CI：`check --fail-on P0`，P0 违规即退出码 1，阻断发布

## 误报处置（mark / unmark）

```bash
python scripts/dq.py mark --table orders --rowid 23 --rule "orders.created_at 新鲜度（7 天）" --reason "补跑中，已知延迟"
```

- 标注写入 `data/feedback.json`，`check` 时自动抑制，并在报告“已抑制”列体现
- `--rule` 省略为 `*` 表示该行所有规则都抑制
- **抑制不是删除**：原始违规仍保留在 `latest.json` 的规则结果里（`suppressed` 计数），评测时按抑制后口径计算

## 候选规则（suggest）

`suggest` 基于画像启发式生成规则（主键→非空+唯一、`*_id`→外键、电话/邮箱→正则、
时间→非空+新鲜度、数值→分位范围、低基数文本→枚举），每条带 `design_basis`。

- 结果写入 `rules/candidates.json`，`already_exists` 标出已被覆盖的规则
- `suggest --llm` 在配置 `DQ_LLM_BASE` / `DQ_LLM_KEY` / `DQ_LLM_MODEL` 时调用
  OpenAI 兼容接口润色；未配置或失败会自动回退启发式结果

## 评测口径

- 检出率 = TP / (TP + FN)
- 误报率 = FP / (TP + FP)
- 规则覆盖率 = 被规则覆盖的关键字段 / 关键字段总数（主键、外键、时间、电话/邮箱、数值、低基数文本）
- 按问题类型统计漏报，用于 badcase 归因（和测试里的误报治理同一套方法）

## 目录结构

```
dq-sentinel/
├── SKILL.md
├── README.md
├── rules/rules.json          # 巡检规则
├── references/rule-catalog.md
├── scripts/
│   ├── dq.py                 # CLI：init/check/profile/evaluate/demo
│   └── make_demo.py          # 生成演示数据并注入 20 类脏数据
├── data/                     # 生成的 demo.db / ground_truth.json
├── reports/                  # 生成的 latest.md / latest.json
└── tests/test_smoke.py       # 冒烟测试
```

## 扩展

- 换 DuckDB：替换 `connect()` 与 `PRAGMA table_info`
- 接 Spark/Hive：把 `table_rows` 换成下推 SQL，避免全量拉取
- LLM 增强：用表名/字段名/业务描述生成候选规则，结果必须人工确认
- 维度扩展：加 `duplicate_rows`（整行重复）、`null_pattern`（空值聚集）等规则
