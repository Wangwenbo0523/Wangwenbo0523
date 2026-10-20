# Changelog

## v0.7 — 2026-10-20

- 新增规则类型 **`duplicate_rows`**（整行/列组合重复）与 **`null_rate`**（列空值率超阈值）
- 演示数据新增“姓名空值聚集”（15 行），规则 22 → 26，违规 24 → 61，检出率/误报率保持 100%/0%
- 修复 DuckDB 下 `duplicate_rows` 的 rowid 映射（改用 `__dq_rid__`）
- 测试增至 8 条（新增规则类型用例）

## v0.6 — 2026-10-20

- **LLM 联调**（deepseek-chat）：候选规则 35 条（启发式 22 条），新增 17 条
- 新增 `normalize_candidates` 结构校验：类型/表/列/参数不合法直接丢弃，并标注 `already_exists`
- 新增 [docs/llm-compare.md](docs/llm-compare.md)：记录 LLM 补充的好规则与三个坑（枚举污染、分布当边界、语义错配）
- `candidates.json` 保留一次 LLM 运行结果作为样本

## v0.5 — 2026-10-20

- 新增 **可视化 HTML 报告** `reports/latest.html`（指标卡片、趋势 sparkline、规则表、违规明细）
- 测试补充 HTML 报告断言（7 条）
- CI 上传报告产物

## v0.4 — 2026-10-20

- 新增 **覆盖率门禁** `--min-coverage`（0–1），低于阈值退出码 1
- `gate_exit()` 统一 P0 与覆盖率判定，CI 使用 `--fail-on P0 --min-coverage 0.8`
- 测试新增覆盖率门禁用例（7 条）

## v0.3 — 2026-10-20

- 新增 **DuckDB 后端**：`make_demo_duck.py` 生成演示库，`check/profile/evaluate/suggest` 支持 `--db`
- 兼容处理：DuckDB `rowid` 从 0 开始 → 用 `__dq_rid__` 对齐 ground truth；`date('now','localtime')` → `CAST(current_date AS VARCHAR)`
- 测试新增 DuckDB 后端用例（6 条，CI 安装 duckdb 后执行）
- 文档补充 DuckDB 用法

## v0.2 — 2026-10-20

- 新增 **规则覆盖率**（关键字段覆盖，报告与 JSON 同步输出）
- 新增 **历史趋势**：每次巡检追加 `data/history.jsonl`，`history` 命令查看
- 新增 **误报标注**：`mark` / `unmark`，巡检自动抑制并在报告单列
- 新增 **CI 门禁**：`check --fail-on P0`，P0 违规退出码 1；附 GitHub Actions 示例
- 新增 **候选规则**：`suggest` 启发式生成，`--llm` 可接 OpenAI 兼容接口
- 新增 **文档**：SKILL.md、README.md、docs/workflow.md、references/rule-catalog.md
- 测试：5 条冒烟测试（指标、报告、抑制、门禁、候选规则）

## v0.1 — 2026-10-20

- 初始版本：演示库（users / products / orders）、20 类脏数据、22 条规则
- 剖析（profile）、巡检（check）、报告（latest.md / latest.json）、评测（evaluate）
- 基线指标：检出率 100%、误报率 0%、F1 1.0
