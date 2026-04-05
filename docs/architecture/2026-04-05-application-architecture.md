# 应用架构文档（Phase 1）

更新时间：2026-04-05  
适用范围：`crypto-funding-arb` 仓库当前 `phase-1` 工作树实现

## 1. 文档目标与系统边界

本文档描述当前已落地的应用架构，重点覆盖：

- 系统边界与职责划分
- 后端模块分层与核心数据流
- 运行模式（`paper` / `live`）差异
- 前后端、数据链路与执行链路
- 关键持久化对象与外部依赖
- 当前已实现与未实现边界

当前系统定位为：**Phase 1 可用骨架**。  
它已具备行情读取、机会打分、风险评估、回测/调参与执行编排（含基础 live 适配）能力，但尚未形成完整生产级自动交易闭环。

系统边界（当前）：

- 包含：
  - `frontend`：控制台 UI（7 页路由，其中 4 页接真实后端数据）
  - `backend`：FastAPI 服务、策略/风控/回测/调参、执行编排、JSON 持久化
  - 与 Binance 公共/签名 API 的对接客户端
- 不包含：
  - 持仓级真实状态机与自动化再平衡执行
  - 自动守护进程（巡检/熔断/自动恢复 worker）
  - 账号体系、权限体系、多租户与审计合规增强
  - 数据库/消息队列等生产级基础设施

## 2. 总体架构视图

当前采用“单体服务 + 前端控制台”的工程化拆分：

1. 前端（React + Vite）通过 `/api` 代理访问后端 HTTP 接口。
2. 后端（FastAPI）在进程内组织领域模块（行情、策略、风险、回测、调参、执行）。
3. 持久化以本地 JSON 文件为主（`backend/runtime/*.json`）。
4. 外部依赖主要是 Binance（公共行情 + 签名下单）。

这意味着当前架构优先“可验证功能闭环”与“低复杂度迭代”，而非分布式高可用。

## 3. 后端模块分层

后端入口位于 `backend/app/main.py`，通过路由聚合形成 API 面。

### 3.1 接口层（API）

- 路由：
  - `app/api/routes/dashboard.py`
  - `app/api/routes/scan.py`
  - `app/api/routes/algo.py`
- 主要职责：
  - 请求参数校验
  - 依赖注入（service/store/orchestrator）
  - 异常映射（如 `ValueError -> HTTP 400`）

### 3.2 应用服务层（Use Case / Orchestration）

- `console/read_service.py`：总览与扫描读取聚合
- `adaptation/service.py`：调参建议、包评估、手动确认后应用
- `execution/service.py`：执行编排、幂等、故障恢复流程
- `execution/read_service.py`：执行看板读模型（状态统计/恢复队列/事故）
- `hedge/service.py`：持仓健康分类与再平衡建议
- `reconciliation/service.py`：交易所回报导入后的账本/审计对账摘要
- `backtest/engine.py` + `backtest/dataset_service.py`：回测执行与数据集重放
- `journal/service.py`、`ledger/service.py`、`audit/service.py`：记录写入与查询封装

### 3.3 领域逻辑层（Domain）

- `strategy/*`：策略抽象与注册（默认 `funding-arb`）
- `opportunity/scorer.py`：机会评分（净边际、成本、basis、惩罚项）
- `risk/policy.py`：风险决策（`allow/review/block`）
- `market_data/service.py`：资金费率 + 买卖盘快照组装

### 3.4 基础设施层（Infra）

- `exchange/binance_public.py`：公共行情 HTTP 调用
- `exchange/binance_trading.py`：签名下单客户端
- `*/store.py`：文件持久化（JSON）
- `core/settings.py`：运行参数与环境变量配置

## 4. 核心数据流

## 4.1 扫描与总览链路（读链路）

1. 前端请求：
   - `/api/v1/dashboard/summary`
   - `/api/v1/scan/opportunities`
2. `ConsoleReadService` 拉取 Binance funding + spot/perp 盘口。
3. 当 `bookTicker` 不可用时，降级到 depth 快照拼装。
4. `build_market_snapshot` 组装快照，策略打分（默认 `funding-arb`）。
5. 返回机会列表与 `market_status`（是否 degraded、覆盖率等）给前端。

特点：该链路已贯通，且有“主盘口 -> 深度回退”的降级逻辑。

## 4.2 风控评估链路

1. 输入 `OpportunityScore` 到 `/api/v1/algo/risk/evaluate`。
2. `OpportunityRiskPolicy` 根据 score/edge/basis/cost/payback 输出：
   - `allow`
   - `review`
   - `block`
3. 返回理由、仓位上限比例、置信度。

## 4.3 回测与调参链路

1. 回测可直接传 periods，或从已导入数据集重放（`run-from-dataset`）。
2. 调参服务读取学习样本，生成：
   - 保守方案
   - 平衡方案
   - 进取方案
   - 系统自动推荐
3. 可先做“包评估”（against dataset），再执行 `apply`。
4. `apply` 强制要求 `confirmed=true`，避免无确认改参。

## 4.4 执行链路（paper/live 共用编排）

1. `/api/v1/algo/execution/execute` 接收 `open_hedge/close_hedge`。
2. `ExecutionOrchestrator` 先做幂等重放判断。
3. `paper`：
   - 以确定性状态流写入 ledger 与 audit（candidate/open/hedged/closed/failed...）。
4. `live`：
   - 先做预检（enabled、allowlist、max notional）。
   - 通过 `BinanceLiveExecutionAdapter` 调签名下单（spot/perp 双腿）。
   - 根据回包状态归一为 `filled/partial/failed/submitted`，并落 ledger/audit。
5. `recover` 可对 `failed/recovery_pending` 执行人工恢复动作。

## 4.5 持仓健康与对账链路

1. `/api/v1/algo/hedge/overview` 从 ledger + audit 中读取活跃交易。
2. `HedgeManagerService` 计算：
   - `healthy`
   - `monitoring`
   - `rebalance_required`
   - `recovery_required`
3. `/api/v1/algo/hedge/rebalance-plan/{trade_id}` 会把净暴露偏移转换成可执行建议：
   - `increase_perp_hedge`
   - `reduce_perp_hedge`
   - `recover_trade`
   - `monitor_only`
4. `/api/v1/algo/reconciliation/reports/import` 用于导入交易所订单回报快照。
5. `/api/v1/algo/reconciliation/summary` 把 imported exchange reports 与 live ledger + execution audit 对照，识别：
   - `missing_exchange_report`
   - `status_mismatch`

## 5. 运行模式：paper vs live

运行参数来自 `FUNDING_ARB_*` 环境变量（`app/core/settings.py`）。

- `paper`（默认）
  - `app_mode=paper`
  - 执行不依赖真实交易所成交回报，走本地状态机模拟
  - 用于联调、演示、流程验证

- `live`
  - 需开启 `live_execution_enabled=true`
  - 需配置 `binance_api_key/binance_api_secret`
  - 受 `live_symbol_allowlist` 与 `max_live_notional` 约束
  - 已可发起真实签名下单请求，但仍属于“基础 live 适配阶段”

关键结论：`live` 已有入口与保护栏，但尚未达到生产级执行可靠性。

## 6. 前后端与数据/执行链路

## 6.1 前端结构与接入现状

- 技术栈：React 19 + React Router + TanStack Query + Vite
- 路由共 7 页：
  - `/` 总览
  - `/scan` 扫描
  - `/positions` 持仓
  - `/risk` 风控
  - `/backtest` 回测
  - `/models` 模型
  - `/audit` 审计
- 实际后端接入状态：
  - 已接：`DashboardPage`、`OpportunityScanPage`、`PositionMonitorPage`、`RiskCenterPage`
  - 未接（静态原型数据）：`BacktestLabPage`、`ModelWorkbenchPage`、`AuditLogCenterPage`

## 6.2 请求链路

1. 前端通过 `apiGet` 发起请求。
2. Vite dev server 将 `/api` 代理到 `http://127.0.0.1:8000`。
3. FastAPI 返回 JSON，前端以 Query 状态管理加载/错误/刷新。

## 6.3 执行观察链路

- 后端已提供 `/api/v1/algo/execution/summary`（执行读模型）。
- 当前 `RiskCenterPage` 已接该接口，`PositionMonitorPage` 已接 hedge overview / rebalance plan。
- `审计中心 / 回测实验室 / 模型工作台` 仍未接入这些真实后端能力。

## 7. 关键持久化设计（当前）

当前为文件持久化，路径可由环境变量覆盖，默认在 `backend/runtime/`：

- `tuning-state.json`：当前激活调参包与配置
- `learning-samples.json`：学习样本
- `trade-journal.json`：交易日志（用于样本抽取）
- `backtest-datasets.json`：回测数据集
- `trade-ledger.json`：统一交易台账（paper/live）
- `audit-events.json`：审计事件（风险/执行/恢复）
- `exchange-order-reports.json`：导入的交易所订单回报快照

特点：

- 优点：轻量、可读、便于本地与测试快速迭代
- 限制：不适合高并发、多实例一致性与强事务场景

## 8. 外部依赖与接口边界

后端 Python 依赖（核心）：

- `fastapi`
- `uvicorn`
- `pydantic-settings`
- `httpx`

前端依赖（核心）：

- `react` / `react-dom`
- `react-router-dom`
- `@tanstack/react-query`
- `vite`

外部系统依赖：

- Binance Public REST（funding、bookTicker、depth）
- Binance Signed REST（spot/perp market order）

## 9. 已实现 / 未实现边界（按当前代码）

## 9.1 已实现

- 行情读取与扫描打分主链路（含降级）
- 策略注册与默认 funding-arb 策略
- 风控策略评估
- 回测执行、数据集导入/列表/重放
- 样本导入、交易日志抽取、调参推荐与手动确认应用
- 统一 ledger + audit + journal 文件持久化
- 执行编排（paper + live 基础适配）、幂等重放、恢复接口
- 执行读侧摘要 API
- hedge manager 读模型、再平衡建议接口与 reconciliation 摘要
- 前端 7 页路由框架与其中 4 页真实后端接入

## 9.2 未实现或未闭环

- 生产级执行可靠性：
  - 自动拉取交易所成交回报并持续对账
  - 完整重试/补偿策略
  - 交易所异常语义分层处理
- 持仓管理与 hedge manager 的持续化闭环
- 自动化守护进程（巡检、熔断、恢复 worker）
- 前端对回测/模型/持仓/风控/审计/执行摘要接口的完整对接
- 认证鉴权、权限、操作审计增强
- 数据库/消息队列等生产基础设施替换 JSON 存储

## 10. 新成员上手建议（基于当前阶段）

1. 先跑通后端健康与两条读接口（dashboard/scan），确认环境可用。
2. 再理解 `strategy -> scorer -> risk -> backtest` 的决策链。
3. 最后进入 `execution`，区分 `paper` 与 `live` 的状态流与保护栏。
4. 前端优先从已接入页面入手，再逐页替换静态页为真实 API。

---

如需进入下一阶段（生产化），建议优先推进：  
`执行可靠性闭环 > 前端全链路接入 > 持久化升级（DB）> 守护进程化`。
