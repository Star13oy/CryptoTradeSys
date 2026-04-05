# 2026-04-05 Phase 1 Progress Update

## Workspace

- Repo: `D:\AICode\crypto-funding-arb`
- Active worktree: `D:\AICode\crypto-funding-arb\.worktrees\phase-1`
- Branch: `codex/phase-1`
- Status: local changes only, not committed

## Executive Summary

项目当前已经从“需求 + 原型”推进到“可运行的只读控制台 + 可验证的算法底座”。

目前最重要的事实是：

1. 前端 7 个页面都已经有 Stitch 对齐的控制台骨架。
2. 后端已经不只是行情读取，而是具备了评分、策略、风控、回测和离线自适应建议包能力。
3. 后端现在已经具备 `交易账本 -> 学习样本 -> tuning package -> 历史数据集回测验证` 这条闭环。
4. `paper/live` 共用交易账本和事件审计底座也已经落地，后面可以直接给执行器复用。
5. `execution orchestrator` 的第一版状态机也已经落地，能把 `open_hedge / close_hedge` 意图落成 ledger 状态迁移和 audit 事件流。
6. 已补上 authenticated Binance trading client 和 live adapter 边界，live 模式不再只是 stub。

## What Is Implemented

### 1. Console and read path

已实现：

1. `Binance` 公共行情读取。
2. `ConsoleReadService` 驱动的总览与扫描 API。
3. `bookTicker -> depth` 的回退逻辑。
4. typed filters、freshness、market status、coverage 元数据。

### 2. Frontend operator shell

已实现：

1. `总览指挥台`
2. `机会扫描页`
3. `持仓监控`
4. `风控中心`
5. `回测实验室`
6. `模型工作台`
7. `审计与日志中心`

当前这些页面以原型级交互和后端合同接线为主，尚未全部联到真实算法流程。

### 3. Algorithm core

已实现：

1. 可解释评分引擎：
   - `gross_edge_bps`
   - `trading_cost_bps`
   - `projected_net_edge_bps`
   - `payback_periods`
   - `expected_hold_periods`
2. 默认 `funding-arb` 策略。
3. 风控策略：
   - `allow`
   - `review`
   - `block`
4. deterministic replay / backtest engine。

### 4. Offline adaptation workflow

已实现：

1. 基于已完成交易样本的离线总结能力。
2. 生成四个建议包：
   - `保守方案`
   - `平衡方案`
   - `进取方案`
   - `系统自动推荐`
3. 自动推荐默认采用 `稳定优先`。
4. 应用建议包时必须 `confirmed=true`。
5. 已支持历史学习样本导入与持久化，不再只能手工在请求体里喂样本。
6. 已支持从 completed trade journal records 提取学习样本，并支持按 `symbol` 过滤与最近 `N` 条截取，且输出顺序 deterministic。
7. 已应用的 tuning state 会影响：
   - 评分运行时
   - 风控运行时
   - 回测运行时
8. 已支持历史回测数据集导入、列出、按数据集回放，以及对 `保守 / 平衡 / 进取 / 自动推荐` 四套 tuning package 做数据集验证。
9. 已支持共享 trade ledger 与 audit event 的导入、列出、过滤，为后续执行与恢复流程铺底。
10. 已支持 execution orchestrator 的首版 paper flow，可对 `open_hedge / close_hedge` 做确定性状态迁移，并在单腿失败时进入 `failed + recovery required` 轨道。
11. 已支持 authenticated Binance spot/perp 下单客户端、请求签名与 live adapter 对接，但还未进入真实实盘联调阶段。

## Real Progress Against The Original Design

### 已经实质进入实现阶段的模块

1. `Exchange Gateway` 的公共读路径
2. `Market Data Service`
3. `Opportunity Engine`
4. `Strategy Runtime`
5. `Risk Guard` 的规则内核
6. `Historical Backtesting and Replay` 的第一版内核
7. `Historical Data Repository` 的第一版手工导入与回放接口
8. `Custom Strategy and Model Framework` 的第一版接口

### 仍然是主要缺口的模块

1. `Execution Orchestrator` 在真实 live 交易所响应下的补偿、重试、部分成交恢复
2. `Portfolio Hedge Manager`
3. 持仓与执行状态机在共享 ledger 上的进一步细化
4. 更完整的历史数据仓库与自动采集
5. live risk / rebalance / recovery 进程
6. 自适应建议包的前端工作台联调

## Verification Snapshot

### Backend

- Full backend suite: `55 passed`

覆盖范围包括：

1. health
2. market snapshot
3. dashboard/scan API
4. scoring engine
5. strategy registry
6. console read service
7. risk policy
8. backtest engine
9. algo API
10. adaptation service / API
11. adaptation sample store / import flow
12. trade journal extractor / deterministic slicing flow
13. trade journal import/list API
14. historical backtest dataset store / import / replay
15. tuning package dataset evaluation API
16. shared trade ledger store / service / API
17. audit event store / service / API
18. execution orchestrator service / API
19. authenticated Binance trading client + live adapter

### Live scoring smoke result

在 projected-edge 口径校准后，真实扫描结果不再出现“样本几乎全为 0 分”的状态。

一次真实烟测结果：

1. returned rows: `25`
2. positive score rows: `8`

这说明当前评分模型已经开始更接近真实资金费率套利的持有期逻辑，而不是只按单期 funding 粗暴扣一次建仓成本。

## Recommended Next Slice

最推荐的下一段工作顺序：

1. 用真实测试账户对 live adapter 做小额白名单联调，并补 partial fill / retry / idempotency。
2. 接入真实历史市场数据，并把已导入交易样本与当时市场上下文自动关联。
3. 把 `adaptation/backtest/ledger/execution` 接到 `模型工作台 / 回测实验室`。
4. 再往下推进 hedge loop 与 recovery worker。

## Practical Note

在最近一次 backend 重启验证中，本地 `8000` 旧进程被停掉过。代码和测试是好的，但如果要继续看本地 API 页面，需要重新启动后端开发服务。
