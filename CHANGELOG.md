# Changelog

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
