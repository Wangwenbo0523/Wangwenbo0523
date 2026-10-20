# LLM vs 启发式：候选规则对比

> 目标：验证 `suggest --llm` 是否值得用，以及“LLM 生成 → 人工确认”到底在确认什么。
> 模型：`deepseek-chat`（OpenAI 兼容接口），输入同一份 profile 与启发式候选。

## 结果概览

| 方式 | 候选数 | 其中新增（未被现有规则覆盖） |
| --- | --- | --- |
| 启发式 | 22 | 4 |
| LLM（deepseek-chat） | 35 | 17 |

结构校验（`normalize_candidates`）在入库前过滤掉：类型不支持、表/列不存在、参数缺失的候选。
LLM 原始返回 37 条，过滤后 35 条。

## LLM 补充的好规则（建议采纳）

| 规则 | 为什么有价值 |
| --- | --- |
| `users.phone 唯一` | 手机号是用户唯一标识，重复意味着账号合并问题 |
| `users.email 唯一` | 同上 |
| `products.price 非负` | 负价格会直接污染 GMV 类指标 |
| `products.stock 非负` | 负库存常见于超卖/回滚异常 |
| `orders.created_at 不晚于当前时间` | 未来时间戳通常意味着时区或写入错误 |
| `orders.status 非空` | 状态缺失会让下游漏斗统计失真 |

## LLM 的三个坑（这就是“人工确认”要确认的东西）

### 1. 枚举被脏数据污染

LLM 直接照着 profiling 结果生成枚举：

- `users.city 枚举` → 6 个值，包含注入的 `火星`
- `products.category 枚举` → 5 个值，包含注入的 `未知`
- `orders.status 枚举` → 5 个值，包含注入的 `未知状态`

**后果**：如果直接采纳，脏值会被写进白名单，`city='火星'` 这类问题反而**检不出来**。
枚举必须对着业务字典确认，不能照着数据抄。

### 2. 把数据分布当成业务边界

LLM 用 1%/99% 分位生成范围：

- `orders.qty 范围 [0, 6]` —— 演示数据最大 qty=5，但业务上 10 件、20 件的订单是合理的
- `orders.amount 范围 [0, 9712]` —— 大额订单会被误判
- `products.price 范围 [-10, 2159]` —— 下界直接带上了脏值 -10

**后果**：范围规则应来自业务口径（合同/报价单/价格表），而不是历史分位。

### 3. 语义错配

LLM 给 `users.signup_date` 生成了 `新鲜度（7 天）` 规则。
注册日期是**历史事实**，不是分区数据，不该有“7 天内更新”的要求。

**后果**：演示库里 194/202 个用户会被判违规——一条规则制造 96% 的误报。

## 结论

1. **启发式做底**：主键、外键、时间、电话/邮箱、枚举这些结构化的规则，规则引擎生成更稳
2. **LLM 做补充**：唯一性、非负、未来时间这类“业务常识”规则，LLM 确实能想到启发式没想到的
3. **两道闸门**：
   - 结构闸门（已实现）：类型/表/列/参数校验
   - 语义闸门（人工）：枚举对业务字典、范围对业务口径、时间字段判断是否真的需要新鲜度
4. **默认不入库**：`candidates.json` 只是候选，标了 `already_exists`，合并进 `rules.json` 需要人评审

## 复现

```bash
export DQ_LLM_BASE=https://api.deepseek.com
export DQ_LLM_KEY=***           # 不要提交到仓库
export DQ_LLM_MODEL=deepseek-chat
python scripts/dq.py suggest --llm
python scripts/dq.py suggest    # 对照组：启发式
```

输出：`rules/candidates.json`（含 `source` 字段，标明 heuristic / llm）。
