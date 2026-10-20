# 数据质量巡检报告

- 生成时间：2026-10-20 09:12:33
- 数据库：`C:\Users\雷神\Desktop\dq-sentinel\data\demo.db`
- 规则数：26
- 已标注误报（抑制）：0 条

## 一、总览

| 指标 | 值 |
| --- | --- |
| 违规行数（含重复计数） | 61 |
| P0 违规 | 11 |
| P1 违规 | 31 |
| P2 违规 | 19 |
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
| users.name 非空 | users | P2 | 202 | 16 | 0 |
| users 整行重复 | users | P1 | 202 | 2 | 0 |
| users.name 空值率 | users | P1 | 202 | 16 | 0 |
| products.id 非空 | products | P0 | 51 | 0 | 0 |
| products.id 唯一 | products | P0 | 51 | 2 | 0 |
| products.price 非空 | products | P1 | 51 | 1 | 0 |
| products.price 范围 | products | P1 | 51 | 1 | 0 |
| products.stock 范围 | products | P2 | 51 | 1 | 0 |
| products.category 枚举 | products | P2 | 51 | 1 | 0 |
| products 整行重复 | products | P1 | 51 | 2 | 0 |
| orders.id 非空 | orders | P0 | 801 | 0 | 0 |
| orders.id 唯一 | orders | P0 | 801 | 2 | 0 |
| orders.user_id 外键 | orders | P0 | 801 | 1 | 0 |
| orders.product_id 外键 | orders | P0 | 801 | 1 | 0 |
| orders.qty 范围 | orders | P1 | 801 | 1 | 0 |
| orders.status 枚举 | orders | P1 | 801 | 1 | 0 |
| orders.created_at 非空 | orders | P1 | 801 | 1 | 0 |
| orders.created_at 新鲜度（7 天） | orders | P1 | 801 | 1 | 0 |
| orders.amount 与 qty×price 一致 | orders | P0 | 801 | 2 | 0 |
| orders 整行重复 | orders | P1 | 801 | 2 | 0 |

## 三、违规明细（每规则前 5 条）

### users.id 非空

| rowid | 值 |
| --- | --- |
| 201 | id=None, name=用户NULL, phone=13800000000, email=null@example.com, signup_date=2026-09-20, city=北京 |

### users.id 唯一

| rowid | 值 |
| --- | --- |
| 5 | id=5, name=用户005, phone=13836798789, email=user005@example.com, signup_date=2026-02-07, city=上海 |
| 202 | id=5, name=用户005, phone=13836798789, email=user005@example.com, signup_date=2026-02-07, city=上海 |

### users.phone 手机号格式

| rowid | 值 |
| --- | --- |
| 7 | id=7, name=用户007, phone=12345, email=user007@example.com, signup_date=2026-06-25, city=上海 |

### users.email 邮箱格式

| rowid | 值 |
| --- | --- |
| 9 | id=9, name=用户009, phone=13820534423, email=not-an-email, signup_date=2026-08-20, city=深圳 |

### users.signup_date 不晚于今天

| rowid | 值 |
| --- | --- |
| 11 | id=11, name=用户011, phone=13859821155, email=user011@example.com, signup_date=2026-11-19, city=杭州 |

### users.city 枚举

| rowid | 值 |
| --- | --- |
| 13 | id=13, name=用户013, phone=13875874779, email=user013@example.com, signup_date=2026-06-02, city=火星 |

### users.name 非空

| rowid | 值 |
| --- | --- |
| 15 | id=15, name=   , phone=13887398691, email=user015@example.com, signup_date=2026-06-29, city=上海 |
| 30 | id=30, name=, phone=13870495821, email=user030@example.com, signup_date=2026-05-30, city=上海 |
| 31 | id=31, name=, phone=13827601200, email=user031@example.com, signup_date=2026-01-01, city=杭州 |
| 32 | id=32, name=, phone=13823404289, email=user032@example.com, signup_date=2026-06-25, city=广州 |
| 33 | id=33, name=, phone=13884536479, email=user033@example.com, signup_date=2026-06-22, city=深圳 |

### users 整行重复

| rowid | 值 |
| --- | --- |
| 5 | id=5, name=用户005, phone=13836798789, email=user005@example.com, signup_date=2026-02-07, city=上海 |
| 202 | id=5, name=用户005, phone=13836798789, email=user005@example.com, signup_date=2026-02-07, city=上海 |

### users.name 空值率

| rowid | 值 |
| --- | --- |
| 15 | id=15, name=   , phone=13887398691, email=user015@example.com, signup_date=2026-06-29, city=上海 |
| 30 | id=30, name=, phone=13870495821, email=user030@example.com, signup_date=2026-05-30, city=上海 |
| 31 | id=31, name=, phone=13827601200, email=user031@example.com, signup_date=2026-01-01, city=杭州 |
| 32 | id=32, name=, phone=13823404289, email=user032@example.com, signup_date=2026-06-25, city=广州 |
| 33 | id=33, name=, phone=13884536479, email=user033@example.com, signup_date=2026-06-22, city=深圳 |

### products.id 唯一

| rowid | 值 |
| --- | --- |
| 10 | id=109, name=商品09, category=食品, price=1760.79, stock=213 |
| 51 | id=109, name=商品09, category=食品, price=1760.79, stock=213 |

### products.price 非空

| rowid | 值 |
| --- | --- |
| 4 | id=103, name=商品03, category=服饰, price=None, stock=405 |

### products.price 范围

| rowid | 值 |
| --- | --- |
| 2 | id=101, name=商品01, category=服饰, price=-10.0, stock=47 |

### products.stock 范围

| rowid | 值 |
| --- | --- |
| 6 | id=105, name=商品05, category=数码, price=1799.06, stock=-5 |

### products.category 枚举

| rowid | 值 |
| --- | --- |
| 8 | id=107, name=商品07, category=未知, price=1618.6, stock=40 |

### products 整行重复

| rowid | 值 |
| --- | --- |
| 10 | id=109, name=商品09, category=食品, price=1760.79, stock=213 |
| 51 | id=109, name=商品09, category=食品, price=1760.79, stock=213 |

### orders.id 唯一

| rowid | 值 |
| --- | --- |
| 26 | id=10025, user_id=113, product_id=148, qty=2, unit_price=935.27, amount=1870.54, status=已完成, created_at=2026-10-20 04:12:31 |
| 801 | id=10025, user_id=113, product_id=148, qty=2, unit_price=935.27, amount=1870.54, status=已完成, created_at=2026-10-20 04:12:31 |

### orders.user_id 外键

| rowid | 值 |
| --- | --- |
| 5 | id=10004, user_id=99999, product_id=115, qty=5, unit_price=1009.78, amount=5048.9, status=已完成, created_at=2026-10-17 23:12:31 |

### orders.product_id 外键

| rowid | 值 |
| --- | --- |
| 8 | id=10007, user_id=143, product_id=88888, qty=3, unit_price=905.62, amount=2716.86, status=已发货, created_at=2026-10-17 09:12:31 |

### orders.qty 范围

| rowid | 值 |
| --- | --- |
| 11 | id=10010, user_id=110, product_id=126, qty=0, unit_price=152.57, amount=305.14, status=已发货, created_at=2026-10-16 05:12:31 |

### orders.status 枚举

| rowid | 值 |
| --- | --- |
| 17 | id=10016, user_id=196, product_id=120, qty=2, unit_price=1147.17, amount=2294.34, status=未知状态, created_at=2026-10-15 09:12:31 |

### orders.created_at 非空

| rowid | 值 |
| --- | --- |
| 20 | id=10019, user_id=156, product_id=148, qty=5, unit_price=935.27, amount=4676.35, status=已支付, created_at=None |

### orders.created_at 新鲜度（7 天）

| rowid | 值 |
| --- | --- |
| 23 | id=10022, user_id=126, product_id=145, qty=3, unit_price=1170.18, amount=3510.54, status=已完成, created_at=2026-10-10 09:12:31 |

### orders.amount 与 qty×price 一致

| rowid | 值 |
| --- | --- |
| 11 | id=10010, user_id=110, product_id=126, qty=0, unit_price=152.57, amount=305.14, status=已发货, created_at=2026-10-16 05:12:31 |
| 14 | id=10013, user_id=135, product_id=108, qty=3, unit_price=1562.44, amount=4692.32, status=已支付, created_at=2026-10-14 11:12:31 |

### orders 整行重复

| rowid | 值 |
| --- | --- |
| 26 | id=10025, user_id=113, product_id=148, qty=2, unit_price=935.27, amount=1870.54, status=已完成, created_at=2026-10-20 04:12:31 |
| 801 | id=10025, user_id=113, product_id=148, qty=2, unit_price=935.27, amount=1870.54, status=已完成, created_at=2026-10-20 04:12:31 |

## 四、评测（与 ground truth 对比）

| 指标 | 值 |
| --- | --- |
| TP | 38 |
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
