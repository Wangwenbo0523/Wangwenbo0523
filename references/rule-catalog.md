# 规则目录（rule catalog）

每条规则 = 一个检查项 + 一个质量维度 + 一个严重级别。
新增规则时，先回答三个问题：

1. 这条规则防的是什么问题？（对应哪次事故 / 哪个报表口径）
2. 违规时业务影响是什么？（影响多少行、哪些指标）
3. 误报可能来自哪里？（空值、历史数据、维表变更）

## 规则类型

| type | 检查什么 | 参数 | 维度 | 典型误报来源 |
| --- | --- | --- | --- | --- |
| `not_null` | 字段为空或全空格 | `column` | 完整性 | 业务允许的空值（如未填写手机号） |
| `unique` | 业务键重复 | `columns` | 唯一性 | 软删除、多版本共存 |
| `range` | 数值越界 | `column` / `min` / `max` | 有效性 | 单位不一致（元/分）、测试数据 |
| `regex` | 格式不符 | `column` / `pattern` | 有效性 | 历史脏数据未清洗 |
| `enum` | 枚举值不在白名单 | `column` / `values` | 有效性 | 新增枚举未同步维表 |
| `foreign_key` | 关联键找不到主表 | `column` / `ref_table` / `ref_column` | 完整性 | 维表延迟、跨库同步 |
| `freshness` | 数据超过 N 天未更新 | `column` / `max_age_days` | 及时性 | 节假日、调度暂停 |
| `expression` | 自定义 SQL 违规 | `violation_sql` | 一致性 | 口径变更、浮点误差 |
| `duplicate_rows` | 整行或指定列组合重复 | `columns`（可选） | 唯一性 | 软删除、多版本 |
| `null_rate` | 列空值率超过阈值 | `column` / `max_rate` | 完整性 | 业务允许的大面积空值 |

## 示例：订单金额一致性

```json
{
  "name": "orders.amount 与 qty×price 一致",
  "type": "expression",
  "violation_sql": "SELECT o.rowid FROM orders o WHERE o.unit_price IS NOT NULL AND ABS(o.amount - o.qty * o.unit_price) > 0.01",
  "severity": "P0"
}
```

**design_basis**：订单金额必须等于数量 × 下单时单价；用 `unit_price` 而不是商品当前价，
避免商品调价后把历史订单误判为异常。容差 0.01 元用于吸收浮点误差。

## 维度与规则映射

| 维度 | 规则 | 回答的问题 |
| --- | --- | --- |
| 完整性 | `not_null` / `foreign_key` | 该有的数据有没有 |
| 唯一性 | `unique` | 同一条业务记录是否重复 |
| 有效性 | `range` / `regex` / `enum` | 值是否在业务允许范围内 |
| 一致性 | `expression` | 字段之间、表之间的关系是否自洽 |
| 及时性 | `freshness` | 数据是否按约定时间产出 |

## 严重级别建议

- **P0**：阻断发布（主键空/重复、外键孤儿、金额不平）
- **P1**：当班修复（格式错误、及时性延迟、关键枚举缺失）
- **P2**：排期修复（非关键字段空值、分布异常）
