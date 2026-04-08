# Crypto Funding Arb

## 当前状态

截至 `2026-04-08`，这个仓库已经不再只是一个 UI 原型，而是包含了一个可运行的 `Phase 1` 后端基础设施，以及与 Stitch 原型对齐的多页面控制台外壳。

### 当前已实现

1. `Binance` 公共行情读取链路，覆盖现货、永续、资金费率和控制台摘要。
2. 可解释的机会评分引擎，包含：
   - `gross_edge_bps`
   - `trading_cost_bps`
   - `projected_net_edge_bps`
   - `payback_periods`
   - `expected_hold_periods`
3. 策略注册表与默认 `funding-arb` 策略运行时。
4. 风控策略层，支持 `allow / review / block` 决策。
5. 可重复、确定性的回测 / 回放引擎。
6. 离线自适应工作流，可生成：
   - `保守方案`
   - `平衡方案`
   - `进取方案`
   - `系统自动推荐`
7. 历史学习样本存储，以及把已完成交易转换成可复用学习样本的 `trade journal extractor`。
8. 历史回测数据集存储，支持导入、列出以及 `run-from-dataset` 回放。
9. 基于数据集的 tuning package 评估，可在一键应用前先对 `保守 / 平衡 / 进取 / 自动推荐` 四套配置做回放对比。
10. 共享交易账本存储，支持 `paper` 与 `live` 两种模式的导入、列表和过滤。
11. 审计事件存储，支持风控、执行、恢复相关事件的导入、列表和过滤。
12. 第一版执行编排器，可把 `open_hedge / close_hedge` 意图转成确定性的状态迁移、账本写入和审计事件。
13. 第一版已签名 `Binance` 交易客户端，以及 live 执行适配器边界，支持现货 / 永续市价单。
14. 执行可靠性控制，包括幂等重放、`recovery_pending` 状态、手动恢复入口，以及 live 模式下的 `enabled / allowlist / max notional` 预检。
15. 面向控制台的执行摘要 API，可暴露状态计数、恢复队列和最近事故。
16. 第一版 `hedge manager` 读模型，可把活跃交易分类成 `healthy / monitoring / rebalance_required / recovery_required`。
17. 对冲再平衡计划 API，可把暴露偏移转换成操作员可执行的建议动作和永续调整量提示。
18. 第一版对账底座，可导入交易所订单回报，并与 live ledger 和执行审计轨迹做对比。
19. tuning package 的人工确认应用流程，避免运行时参数被静默修改。
20. 可配置持久化后端：默认仍是 JSON，便于本地快速迭代；同时已支持 MySQL 用于保存 tuning state、learning samples、journal、datasets、ledger、audit events 和 exchange order reports。
21. 与 Stitch 项目对齐的 7 个控制台页面：
   - `总览指挥台`
   - `机会扫描页`
   - `持仓监控`
   - `风控中心`
   - `回测实验室`
   - `模型工作台`
   - `审计与日志中心`
22. `JSON -> MySQL` 回填工具，以及一套 `reconciliation candidate` 读模型，用于暴露仍需要跟进交易所回报的交易。
23. 已签名的对账同步能力，可针对单笔 live trade 或 attention queue 中优先级最高的一批交易，主动从 Binance 拉取现货 / 永续订单状态并更新回报。
24. 轻量级 in-process `reconciliation worker`，带状态查询和手动触发 API，使 attention queue 同步不再只能靠操作员手动触发。
25. 总览页与扫描页已经展示原始行情细节，不再只有评分，包括 `spot/perp bid-ask`、`mid`、`basis` 和双腿点差成本。
26. 恢复规划层，可把 `failed / recovery_pending` 交易转成显式的 `resume_open / resume_close / manual_review` 计划，并只对当前安全可恢复的子集做批量自动执行。
27. 轻量级 in-process `recovery worker`，可按固定间隔自动执行安全可恢复的计划，并暴露 worker 状态与手动触发 API。
28. live execution 熔断器，可在连续 live 异常后自动阻断新的 live 请求，暴露状态查询与手动复位接口，并在成功执行后自动清零失败计数。
29. live adapter 已支持“安全重试”下单：当下单请求因链路异常失败时，会先按同一 `clientOrderId` 查询交易所订单状态，确认未下达后才做一次受控重试，避免盲目重复下单。
30. 补偿规划层已支持安全执行入口：`sync_exchange_reports`、恢复动作，以及在能从既有永续成交回报推导出参考价格时的 `rebalance_hedge` 都可以受控执行；其余仍未闭环的危险动作会被显式跳过并返回结构化结果。
31. 轻量级 in-process `compensation worker` 已落地，可按固定间隔轮询补偿安全动作，并暴露状态查询与手动触发 API。
32. `risk-center` 已接入对账候选与状态面板，可直接展示待关注交易、缺失订单与建议动作。
33. 已补上手动 hedge rebalance API：`POST /api/v1/algo/hedge/rebalance/{trade_id}`，用于对指定交易发起受控再平衡。
34. 轻量级 in-process `hedge rebalance worker` 已落地，可按固定间隔扫描 `rebalance_required` 仓位，并在能推导出安全数量时自动执行再平衡。
35. `positions` 已接入 `hedge worker` 状态卡与手动触发入口，`risk-center` 已接入 reconciliation / recovery / compensation worker 和 live circuit breaker 的手动触发入口。
36. 已补上单笔自动数量推导的再平衡执行入口：`POST /api/v1/algo/hedge/rebalance-auto/{trade_id}`，可直接从既有永续成交回报推导参考价与数量，供 `positions` 页做一键再平衡。

## 当前后端能力面

### 读接口与算法接口

1. `/health`
2. `/api/v1/dashboard/summary`
3. `/api/v1/scan/opportunities`
4. `/api/v1/algo/risk/evaluate`
5. `/api/v1/algo/backtest/run`
6. `/api/v1/algo/backtest/datasets`
7. `/api/v1/algo/backtest/datasets/import`
8. `/api/v1/algo/backtest/run-from-dataset`
9. `/api/v1/algo/adaptation/state`
10. `/api/v1/algo/adaptation/recommend`
11. `/api/v1/algo/adaptation/evaluate-packages`
12. `/api/v1/algo/adaptation/apply`
13. `/api/v1/algo/adaptation/samples`
14. `/api/v1/algo/adaptation/samples/import`
15. `/api/v1/algo/adaptation/samples/extract-from-journal`
16. `/api/v1/algo/journal/trades`
17. `/api/v1/algo/journal/trades/import`
18. `/api/v1/algo/ledger/trades`
19. `/api/v1/algo/ledger/trades/import`
20. `/api/v1/algo/audit/events`
21. `/api/v1/algo/audit/events/import`
22. `/api/v1/algo/execution/execute`
23. `/api/v1/algo/execution/recover`
24. `/api/v1/algo/execution/summary`
25. `/api/v1/algo/hedge/overview`
26. `/api/v1/algo/hedge/rebalance-plan/{trade_id}`
27. `/api/v1/algo/hedge/rebalance/{trade_id}`
28. `/api/v1/algo/hedge/rebalance-auto/{trade_id}`
29. `/api/v1/algo/hedge/worker`
30. `/api/v1/algo/hedge/worker/run`
31. `/api/v1/algo/reconciliation/reports`
32. `/api/v1/algo/reconciliation/reports/import`
33. `/api/v1/algo/reconciliation/summary`
34. `/api/v1/algo/reconciliation/candidates`
35. `/api/v1/algo/persistence/backfill-json`
36. `/api/v1/algo/reconciliation/sync/{trade_id}`
37. `/api/v1/algo/reconciliation/sync`
38. `/api/v1/algo/reconciliation/worker`
39. `/api/v1/algo/reconciliation/worker/run`
40. `/api/v1/algo/recovery/plans`
41. `/api/v1/algo/recovery/execute-auto`
42. `/api/v1/algo/recovery/worker`
43. `/api/v1/algo/recovery/worker/run`
44. `/api/v1/algo/execution/circuit-breaker`
45. `/api/v1/algo/execution/circuit-breaker/reset`
46. `/api/v1/algo/compensation/plans`
47. `/api/v1/algo/compensation/execute`
48. `/api/v1/algo/compensation/worker`
49. `/api/v1/algo/compensation/worker/run`

### 运行时模块

- `backend/app/console/`：控制台读服务
- `backend/app/opportunity/`：评分引擎
- `backend/app/strategy/`：策略抽象与注册表
- `backend/app/risk/`：风控策略
- `backend/app/backtest/`：回放 / 回测引擎
- `backend/app/adaptation/`：离线学习与 tuning recommendation
- `backend/app/journal/`：已完成交易 journal 与样本提取桥接
- `backend/app/ledger/`：共享的 paper/live 交易账本
- `backend/app/audit/`：审计事件持久化与查询
- `backend/app/execution/`：执行意图编排、恢复流程和执行摘要读模型
- `backend/app/hedge/`：对冲健康度分类与再平衡 / 恢复概览
- `backend/app/reconciliation/`：交易所订单回报、账本 / 审计对账摘要
- `backend/app/reconciliation/worker.py`：基于间隔轮询的 attention queue 同步 worker 与运行状态快照
- `backend/app/recovery/`：恢复规划、动作可执行性判断与自动恢复摘要
- `backend/app/compensation/`：补偿计划生成、安全执行 allowlist 与结构化执行结果
- `backend/app/compensation/worker.py`：补偿安全动作的轻量级轮询 worker
- `backend/app/persistence/`：可选 MySQL 持久化与后端选择逻辑
- `backend/app/persistence/migration.py`：`JSON -> MySQL` 回填服务与摘要 schema
- `backend/app/exchange/binance_trading.py`：已签名 Binance 交易客户端
- `backend/app/reconciliation/service.py`：对账摘要、候选列表，以及基于交易所订单查询的单笔 / 批量同步

## 项目结构

- `backend/`：FastAPI 服务、交易所客户端、schemas、算法与测试
- `frontend/`：Vite + React 控制台、与 Stitch 对齐的页面、前端测试
- `docs/superpowers/specs/`：设计与需求文档
- `docs/superpowers/plans/`：实施计划与进度文档
- `docs/architecture/`：架构说明与技术深潜文档

## 验证快照

当前 worktree 最新验证结果：

1. Full backend suite: `132 passed, 6 skipped`
2. Focused reconciliation-worker slice: `5 passed`
3. Full frontend suite: `29 passed`
4. Frontend production build: `vite build` passed
5. 在 `projected-edge` 口径校准后，真实 Binance 烟测已不再出现“全为零分”的情况，系统能筛出正分机会。
6. `trade journal` 提取已支持按 `symbol` 过滤、最近 `N` 条截取和确定性顺序。
7. 历史回测数据集已支持导入、列出、回放，以及用于 tuning package 应用前评估。
8. `hedge overview` 已能按暴露偏移与恢复状态做分类，供持仓页和风控页直接消费。
9. `hedge rebalance plan` 已能把漂移转换为明确的 `increase/reduce perp hedge` 建议。
10. 对账层已能导入交易所订单快照，并识别缺失回报与本地 / 交易所状态不一致。
11. 对账层已能给出以交易为中心的 candidate context，展示预期订单、已回报订单和缺失腿。
12. JSON 历史状态已支持幂等回填到 MySQL，避免重复导入。
13. 单笔 live trade 已支持触发已签名交易所查询，因此对账不再局限于手工导入。
14. 风控中心已经直接消费 `reconciliation candidates`，需要关注的交易会直接出现在 UI 中，而不是占位演示数据。
15. `risk-center` 已补上状态面板，能把对账候选、缺失订单与建议动作集中展示出来。
16. `reconciliation service` 已支持对高优先级 attention queue 做批量同步，并通过轻量级 interval worker 运行。
17. 总览与扫描页现在会展示原始 `spot/perp bid-ask`、`mid`、`basis` 和 spread 成本，而不是只显示派生评分。
18. 恢复规划层现在可以把 `failed / recovery_pending` 交易分类为 `resume_open / resume_close / manual_review`，且自动恢复接口只会执行当前对账上下文下安全的那部分计划。
19. 补偿执行接口现在会返回逐笔结构化结果，并且只允许安全动作进入自动执行；`rebalance_hedge` 在能从既有永续成交回报推导数量时也可受控执行。
20. 补偿 worker 状态接口和手动触发接口已经可用，本地重启后的 [worker status](http://127.0.0.1:8000/api/v1/algo/compensation/worker) 会返回快照。
21. `positions` 页现在已经支持对当前选中且确实需要再平衡的交易做“一键执行再平衡”，无需操作员手工输入永续数量。

## 本地启动

### 后端

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e backend[dev]
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m pytest backend/tests -q
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 使用 MySQL 持久化的后端

```powershell
mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS crypto_funding_arb;"
$env:FUNDING_ARB_STORAGE_BACKEND = "mysql"
$env:FUNDING_ARB_MYSQL_HOST = "127.0.0.1"
$env:FUNDING_ARB_MYSQL_PORT = "3306"
$env:FUNDING_ARB_MYSQL_USER = "root"
$env:FUNDING_ARB_MYSQL_PASSWORD = "root"
$env:FUNDING_ARB_MYSQL_DATABASE = "crypto_funding_arb"
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

可直接编辑的环境变量模板见 `.env.example`。

如需运行可选的 MySQL 持久化测试：

```powershell
$env:FUNDING_ARB_RUN_MYSQL_TESTS = "1"
.\.venv\Scripts\python -m pytest backend/tests/test_mysql_store_integration.py -q
```

启用数据库后端后，如需将现有 JSON 状态回填到 MySQL：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/persistence/backfill-json"
```

如需为指定 live trade 同步交易所订单回报：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/sync/<trade_id>"
```

如需批量同步当前 attention queue：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/sync?limit=5"
```

启用 `reconciliation worker` 后，如需查看状态或手动触发一轮：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/worker"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/worker/run"
```

如需查看恢复计划，或只执行可自动恢复的子集：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/plans"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/execute-auto?limit=2"
```

如需查看补偿计划，或只执行补偿安全 allowlist 中的动作：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/plans?only_actionable=true"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/execute?limit=3"
```

启用 `compensation worker` 后，如需查看状态或手动触发一轮：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/worker"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/worker/run"
```

如需对单笔活跃仓位直接执行自动数量推导的再平衡：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/hedge/rebalance-auto/<trade_id>"
```

启用 `recovery worker` 后，如需查看状态或手动触发一轮：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/worker"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/worker/run"
```

如需查看 live 熔断器状态，或手动复位：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/execution/circuit-breaker"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/execution/circuit-breaker/reset"
```

### 前端

```powershell
Set-Location frontend
npm install
npm run test
npm run build
npm run dev
```

## 仍未完成的部分

这个仓库距离真正的生产级交易闭环还有差距，主要缺口包括：

1. 已签名 Binance 执行链路虽然已经有预检、恢复轨道和恢复规划，但还缺真正交易所级别的成交回报对账、重试策略，以及基于真实响应的回滚 / 补偿。
2. 在当前 `hedge overview` 读模型之上，还缺持仓账本补强和 `hedge manager` 的动作执行闭环。
3. 更完整的已签名历史市场 / 历史交易数据采集与同步，而不是只靠手工导入数据集。
4. 前端仍需把回测、模型、账本、执行、自适应和恢复控制真正接到页面上，目前已接好的仍主要是 dashboard / scan / positions / risk。
5. live 场景下虽然已有基础 `circuit breaker`、安全重试下单、`rebalance_hedge` 的受控执行、手动 hedge rebalance API、`compensation worker` 与 `hedge rebalance worker`，但还缺 `flatten_*` 这类动作的自动化闭环，以及更生产化的守护进程形态。
6. 基于 MySQL 的更强事务边界、回填工具和一致性保证还需要继续补。
7. 当前的 in-process reconciliation / recovery worker 还要进一步升级为更接近生产的 daemon / supervisor 形态，补上更强的持久化、告警与多进程安全。
