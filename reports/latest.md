# 数据质量巡检报告

- 生成时间：2026-10-20 07:53:27
- 数据库：`C:\Users\雷神\Desktop\dq-sentinel\data\demo.db`
- 规则数：22
- 已标注误报（抑制）：0 条

## 一、总览

| 指标 | 值 |
| --- | --- |
| 违规行数（含重复计数） | 24 |
| P0 违规 | 11 |
| P1 违规 | 9 |
| P2 违规 | 4 |
| 规则覆盖率 | 100.0%（17/17 关键字段） |
| 检出率（Recall） | 100.0% |
| 误报率（1 - Precision） | 0.0% |
| F1 | 1.0000 |

## 二、规则结果

| 规则 | 表 | 级别 | 检查行数 | 违规行数 | 已抑制 |
| --- | --- | --- | --- | --- | --- |
| users.id 非空 | users | P0 | 202 | 1 | 0 |
| users.id 唯一 | users | P0 | 202 | 2 | 0 |
| users.phone 手机号格式 | users | P1 | 202 | 1 | 0 |
| users.email 邮箱格式 | users | P1 | 202 | 1 | 0 |
| users.signup_date 不晚于今天 | users | P1 | 202 | 1 | 0 |
| users.city 枚举 | users | P2 | 202 | 1 | 0 |
| users.name 非空 | users | P2 | 202 | 1 | 0 |
| products.id 非空 | products | P0 | 51 | 0 | 0 |
| products.id 唯一 | products | P0 | 51 | 2 | 0 |
| products.price 非空 | products | P1 | 51 | 1 | 0 |
| products.price 范围 | products | P1 | 51 | 1 | 0 |
| products.stock 范围 | products | P2 | 51 | 1 | 0 |
| products.category 枚举 | products | P2 | 51 | 1 | 0 |
| orders.id 非空 | orders | P0 | 801 | 0 | 0 |
| orders.id 唯一 | orders | P0 | 801 | 2 | 0 |
| orders.user_id 外键 | orders | P0 | 801 | 1 | 0 |
| orders.product_id 外键 | orders | P0 | 801 | 1 | 0 |
| orders.qty 范围 | orders | P1 | 801 | 1 | 0 |
| orders.status 枚举 | orders | P1 | 801 | 1 | 0 |
| orders.created_at 非空 | orders | P1 | 801 | 1 | 0 |
| orders.created_at 新鲜度（7 天） | orders | P1 | 801 | 1 | 0 |
| orders.amount 与 qty×price 一致 | orders | P0 | 801 | 2 | 0 |

## 三、违规明细（每规则前 5 条）

### users.id 非空

| rowid | 值 |
| --- | --- |
| 201 | id=None, name=用户NULL, phone=13800000000, email=null@example.com, signup_date=2026-09-20, city=北京 |

### users.id 唯一

| rowid | 值 |
| --- | --- |
| 5 | id=5, name=用户005, phone=13839345092, email=user005@example.com, signup_date=2026-09-03, city=上海 |
| 202 | id=5, name=用户005, phone=13839345092, email=user005@example.com, signup_date=2026-09-03, city=上海 |

### users.phone 手机号格式

| rowid | 值 |
| --- | --- |
| 7 | id=7, name=用户007, phone=12345, email=user007@example.com, signup_date=2026-01-06, city=杭州 |

### users.email 邮箱格式

| rowid | 值 |
| --- | --- |
| 9 | id=9, name=用户009, phone=13810872248, email=not-an-email, signup_date=2026-05-31, city=上海 |

### users.signup_date 不晚于今天

| rowid | 值 |
| --- | --- |
| 11 | id=11, name=用户011, phone=13838898923, email=user011@example.com, signup_date=2026-11-19, city=广州 |

### users.city 枚举

| rowid | 值 |
| --- | --- |
| 13 | id=13, name=用户013, phone=13858181396, email=user013@example.com, signup_date=2026-09-01, city=火星 |

### users.name 非空

| rowid | 值 |
| --- | --- |
| 15 | id=15, name=   , phone=13826753883, email=user015@example.com, signup_date=2026-01-19, city=深圳 |

### products.id 唯一

| rowid | 值 |
| --- | --- |
| 10 | id=109, name=商品09, category=家电, price=764.42, stock=232 |
| 51 | id=109, name=商品09, category=家电, price=764.42, stock=232 |

### products.price 非空

| rowid | 值 |
| --- | --- |
| 4 | id=103, name=商品03, category=食品, price=None, stock=370 |

### products.price 范围

| rowid | 值 |
| --- | --- |
| 2 | id=101, name=商品01, category=食品, price=-10.0, stock=248 |

### products.stock 范围

| rowid | 值 |
| --- | --- |
| 6 | id=105, name=商品05, category=数码, price=263.98, stock=-5 |

### products.category 枚举

| rowid | 值 |
| --- | --- |
| 8 | id=107, name=商品07, category=未知, price=1289.07, stock=443 |

### orders.id 唯一

| rowid | 值 |
| --- | --- |
| 26 | id=10025, user_id=78, product_id=128, qty=1, unit_price=1371.68, amount=1371.68, status=已完成, created_at=2026-10-16 09:53:27 |
| 801 | id=10025, user_id=78, product_id=128, qty=1, unit_price=1371.68, amount=1371.68, status=已完成, created_at=2026-10-16 09:53:27 |

### orders.user_id 外键

| rowid | 值 |
| --- | --- |
| 5 | id=10004, user_id=99999, product_id=120, qty=1, unit_price=519.92, amount=519.92, status=已支付, created_at=2026-10-14 14:53:27 |

### orders.product_id 外键

| rowid | 值 |
| --- | --- |
| 8 | id=10007, user_id=33, product_id=88888, qty=1, unit_price=1896.04, amount=1896.04, status=已发货, created_at=2026-10-14 14:53:27 |

### orders.qty 范围

| rowid | 值 |
| --- | --- |
| 11 | id=10010, user_id=48, product_id=130, qty=0, unit_price=1070.16, amount=4280.64, status=待支付, created_at=2026-10-16 21:53:27 |

### orders.status 枚举

| rowid | 值 |
| --- | --- |
| 17 | id=10016, user_id=159, product_id=137, qty=4, unit_price=1618.32, amount=6473.28, status=未知状态, created_at=2026-10-17 13:53:27 |

### orders.created_at 非空

| rowid | 值 |
| --- | --- |
| 20 | id=10019, user_id=177, product_id=110, qty=1, unit_price=660.42, amount=660.42, status=已完成, created_at=None |

### orders.created_at 新鲜度（7 天）

| rowid | 值 |
| --- | --- |
| 23 | id=10022, user_id=109, product_id=140, qty=5, unit_price=1764.45, amount=8822.25, status=待支付, created_at=2026-10-10 07:53:27 |

### orders.amount 与 qty×price 一致

| rowid | 值 |
| --- | --- |
| 11 | id=10010, user_id=48, product_id=130, qty=0, unit_price=1070.16, amount=4280.64, status=待支付, created_at=2026-10-16 21:53:27 |
| 14 | id=10013, user_id=64, product_id=109, qty=5, unit_price=764.42, amount=3827.1, status=待支付, created_at=2026-10-18 05:53:27 |

## 四、评测（与 ground truth 对比）

| 指标 | 值 |
| --- | --- |
| TP | 23 |
| FP | 0 |
| FN | 0 |
| 检出率 | 100.0% |
| 误报率 | 0.0% |

## 五、修复建议

- **users.id 非空**：定位空值来源，补默认值或在入仓前过滤；必要时在 ETL 加非空校验。
- **users.id 唯一**：确认是否重复写入（幂等问题），按业务键去重并加唯一约束。
- **users.phone 手机号格式**：统一清洗规则（去空格、正则替换），并抽样复核。
- **users.email 邮箱格式**：统一清洗规则（去空格、正则替换），并抽样复核。
- **users.signup_date 不晚于今天**：按表达式定位计算逻辑，修正后回归验证。
- **users.city 枚举**：补充维表映射，未知值转“其他”并登记。
- **users.name 非空**：定位空值来源，补默认值或在入仓前过滤；必要时在 ETL 加非空校验。
- **products.id 唯一**：确认是否重复写入（幂等问题），按业务键去重并加唯一约束。
- **products.price 非空**：定位空值来源，补默认值或在入仓前过滤；必要时在 ETL 加非空校验。
- **products.price 范围**：检查上游单位/精度/数据口径，修正后加范围校验。
- **products.stock 范围**：检查上游单位/精度/数据口径，修正后加范围校验。
- **products.category 枚举**：补充维表映射，未知值转“其他”并登记。
- **orders.id 唯一**：确认是否重复写入（幂等问题），按业务键去重并加唯一约束。
- **orders.user_id 外键**：补维表或修正关联键；入仓前做孤儿键检查。
- **orders.product_id 外键**：补维表或修正关联键；入仓前做孤儿键检查。
- **orders.qty 范围**：检查上游单位/精度/数据口径，修正后加范围校验。
- **orders.status 枚举**：补充维表映射，未知值转“其他”并登记。
- **orders.created_at 非空**：定位空值来源，补默认值或在入仓前过滤；必要时在 ETL 加非空校验。
- **orders.created_at 新鲜度（7 天）**：检查调度依赖与分区产出，恢复后补跑；对延迟加告警。
- **orders.amount 与 qty×price 一致**：按表达式定位计算逻辑，修正后回归验证。
