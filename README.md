# Crypto Funding Arb

一个面向个人自营场景的虚拟币量化交易系统原型，当前聚焦：

- `Binance` 单所
- `CEX 现货 + 永续` 对冲
- `资金费率套利` 主策略
- `24/7` 自动化运行底座
- `Paper / Live` 双模式
- 中文控制台前端

这个仓库现在更适合这样理解：它已经不是单纯的 UI 原型，而是一套可运行的 `Phase 1` 系统骨架，覆盖了行情、评分、风控、回测、执行、恢复、对账、补偿和对冲管理等关键链路，但还没有到“可放心无人值守实盘”的最终形态。

## 这套系统能做什么

当前已经具备这些核心能力：

- 读取 `Binance` 公共行情、资金费率、现货/永续盘口
- 扫描候选机会，并计算可解释的套利评分
- 输出 `allow / review / block` 风控决策
- 支持回测、数据集回放、策略参数推荐与人工确认应用
- 支持 `paper` 与 `live` 共用的交易账本和审计事件
- 支持执行编排、恢复计划、对账同步、补偿计划
- 支持对冲健康度分类、自动再平衡 worker、单笔一键再平衡
- 提供 7 个控制台页面，便于观察机会、持仓、风险和审计状态
- 支持 `JSON` 本地持久化，也支持切换到 `MySQL`

如果你要看更细的实现演进，请去看进度文档，而不是把 README 当 changelog：

- [阶段进度](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\superpowers\plans\2026-04-05-phase-1-progress-update.md)
- [应用架构](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\architecture\2026-04-05-application-architecture.md)
- [需求设计](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\superpowers\specs\2026-04-03-crypto-funding-arbitrage-design.md)

## 适合谁

当前版本适合：

- 个人自营交易者
- 想先跑 `paper` 或小额白名单 `live` 联调的人
- 想继续开发这套系统、补齐执行闭环的人

当前版本还不适合：

- 直接全自动大额生产实盘
- 多用户、多账户、多租户资管平台
- 依赖完整历史数据仓库和成熟运维体系的团队化生产环境

## 项目结构

```text
backend/                  FastAPI 后端、策略/执行/风控/回测/持久化
frontend/                 React + Vite 控制台前端
docs/architecture/        应用架构与关键技术文档
docs/superpowers/specs/   需求与设计文档
docs/superpowers/plans/   阶段计划与进度文档
```

后端主要模块：

- `backend/app/console/`：总览与扫描读服务
- `backend/app/opportunity/`：机会评分引擎
- `backend/app/risk/`：风控决策
- `backend/app/backtest/`：回测与回放
- `backend/app/adaptation/`：离线学习与参数建议
- `backend/app/execution/`：执行编排、熔断、适配器
- `backend/app/reconciliation/`：交易所回报同步与对账
- `backend/app/recovery/`：恢复计划与恢复 worker
- `backend/app/compensation/`：补偿计划与补偿 worker
- `backend/app/hedge/`：对冲健康度、再平衡计划与再平衡 worker
- `backend/app/persistence/`：JSON / MySQL 持久化与回填

前端页面：

- `/`：总览指挥台
- `/scan`：机会扫描页
- `/positions`：持仓监控
- `/risk`：风控中心
- `/backtest`：回测实验室
- `/models`：模型工作台
- `/audit`：审计与日志中心

## 快速开始

### 1. 环境准备

建议本机准备：

- `Python 3.12+`
- `Node.js 20+`
- `npm`
- `MySQL 8+` 可选

### 2. 启动后端

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e backend[dev]
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m pytest backend/tests -q
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

启动后可访问：

- [健康检查](http://127.0.0.1:8000/health)

### 3. 启动前端

```powershell
Set-Location frontend
npm install
npm run dev
```

启动后可访问：

- [总览指挥台](http://127.0.0.1:5173/)
- [机会扫描页](http://127.0.0.1:5173/scan)
- [持仓监控](http://127.0.0.1:5173/positions)
- [风控中心](http://127.0.0.1:5173/risk)
- [回测实验室](http://127.0.0.1:5173/backtest)
- [模型工作台](http://127.0.0.1:5173/models)
- [审计与日志中心](http://127.0.0.1:5173/audit)

## 最小运行配置

完整环境变量模板见：

- [.env.example](D:\AICode\crypto-funding-arb\.worktrees\phase-1\.env.example)

最常用的配置项是这些：

### 基础模式

- `FUNDING_ARB_APP_MODE`
  - `paper`：默认，适合联调与流程验证
  - `live`：实盘模式
- `FUNDING_ARB_STORAGE_BACKEND`
  - `json`：默认，写本地文件
  - `mysql`：写入 MySQL

### MySQL 持久化

如果你要切到 MySQL：

```powershell
mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS crypto_funding_arb;"
$env:FUNDING_ARB_STORAGE_BACKEND = "mysql"
$env:FUNDING_ARB_MYSQL_HOST = "127.0.0.1"
$env:FUNDING_ARB_MYSQL_PORT = "3306"
$env:FUNDING_ARB_MYSQL_USER = "root"
$env:FUNDING_ARB_MYSQL_PASSWORD = "root"
$env:FUNDING_ARB_MYSQL_DATABASE = "crypto_funding_arb"
```

然后再启动后端。

### Live 执行相关

如果你要做真实小额联调，还需要：

- `FUNDING_ARB_LIVE_EXECUTION_ENABLED=true`
- `FUNDING_ARB_BINANCE_API_KEY=...`
- `FUNDING_ARB_BINANCE_API_SECRET=...`
- `FUNDING_ARB_LIVE_SYMBOL_ALLOWLIST=BTCUSDT,ETHUSDT`
- `FUNDING_ARB_MAX_LIVE_NOTIONAL=...`

建议始终配白名单和较小的 `max_live_notional`。

## 常用页面怎么看

### 总览指挥台

适合先看系统有没有“活着”：

- 当前候选机会
- 行情链路状态
- 扫描覆盖率
- 头部机会的 `spot/perp bid-ask`、`basis`、评分

### 机会扫描页

适合看策略为何选中某个标的：

- `funding_rate`
- `basis_bps`
- `gross_edge_bps`
- `trading_cost_bps`
- `projected_net_edge_bps`
- `score`

### 持仓监控

适合看对冲是否漂移：

- 活跃对冲仓位
- `healthy / monitoring / rebalance_required / recovery_required`
- 单笔再平衡建议
- 自动再平衡 worker 状态
- 选中交易的一键“执行再平衡”

### 风控中心

适合看系统是否开始“失控”：

- 执行摘要
- 对账候选
- 恢复 worker
- 补偿 worker
- `live circuit breaker`

## 常用操作

### 1. 回填 JSON 到 MySQL

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/persistence/backfill-json"
```

### 2. 同步某笔交易的交易所订单回报

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/sync/<trade_id>"
```

### 3. 批量同步当前 attention queue

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/sync?limit=5"
```

### 4. 查看恢复计划，或执行安全可恢复项

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/plans"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/execute-auto?limit=2"
```

### 5. 查看补偿计划，或执行安全补偿动作

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/plans?only_actionable=true"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/execute?limit=3"
```

### 6. 手动触发 worker

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/worker/run"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/recovery/worker/run"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/compensation/worker/run"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/hedge/worker/run"
```

### 7. 单笔自动再平衡

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/hedge/rebalance-auto/<trade_id>"
```

### 8. 查看或复位实盘熔断器

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/execution/circuit-breaker"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/execution/circuit-breaker/reset"
```

## 当前验证状态

最近一次完整验证结果：

- 后端：`132 passed, 6 skipped`
- 前端：`29 passed`
- 前端构建：`vite build` 通过

如果你只想确认系统有没有起稳，最实用的检查是：

- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- [http://127.0.0.1:5173/](http://127.0.0.1:5173/)

## 文档索引

进一步阅读建议按这个顺序：

1. [需求设计文档](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\superpowers\specs\2026-04-03-crypto-funding-arbitrage-design.md)
2. [应用架构文档](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\architecture\2026-04-05-application-architecture.md)
3. [消息安全与执行可靠性](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\architecture\2026-04-05-execution-reliability-and-message-safety.md)
4. [阶段进度文档](D:\AICode\crypto-funding-arb\.worktrees\phase-1\docs\superpowers\plans\2026-04-05-phase-1-progress-update.md)

## 当前边界与缺口

这套系统已经能跑，但还没到“完整生产实盘系统”。当前主要缺口仍然包括：

- 真实交易所成交回报下的更完整补偿与回滚闭环
- `flatten_*` 这类危险动作的自动化与更严格风控
- 更完整的历史市场/交易数据自动采集
- 更生产化的 worker / daemon / supervisor 形态
- 更强的事务一致性、告警和多实例安全
- 回测、模型、审计页面的更深联调

如果你的目标是：

- 小额白名单 `paper / live` 联调：现在已经可以继续推进
- 真正无人值守、大额、生产级实盘：还需要继续开发
