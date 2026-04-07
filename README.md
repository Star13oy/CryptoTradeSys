# Crypto Funding Arb

## Status

As of `2026-04-05`, this repository is no longer just a UI prototype. It now contains a usable phase-1 backend foundation plus a Stitch-aligned multi-page console shell.

### Implemented so far

1. Public Binance read path for spot, perp, funding, and console summaries.
2. Explainable opportunity scoring with:
   - `gross_edge_bps`
   - `trading_cost_bps`
   - `projected_net_edge_bps`
   - `payback_periods`
   - `expected_hold_periods`
3. Strategy registry and default `funding-arb` strategy runtime.
4. Risk policy layer with `allow / review / block` decisions.
5. Deterministic backtest / replay engine.
6. Offline adaptation workflow that recommends:
   - `保守方案`
   - `平衡方案`
   - `进取方案`
   - `系统自动推荐`
7. Historical learning sample storage plus a trade-journal extractor for turning completed trades into reusable learning samples.
8. Historical backtest dataset storage with import, listing, and `run-from-dataset` replay.
9. Dataset-backed tuning-package evaluation so `保守 / 平衡 / 进取 / 自动推荐` can be replayed against stored windows before one-click apply.
10. Shared trade ledger storage with import/list/filter support for `paper` and `live` records.
11. Audit event storage with import/list/filter support for risk, execution, and recovery events.
12. A first execution orchestrator that turns `open_hedge / close_hedge` intents into deterministic state transitions, ledger writes, and audit events.
13. A first authenticated Binance trading client plus live execution adapter boundary for signed spot/perp market orders.
14. Execution reliability controls including idempotent replay handling, `recovery_pending` state, manual recovery actions, and live-mode preflight guards for `enabled / allowlist / max notional`.
15. An execution read-side summary API that exposes status counts, recovery queue items, and recent incidents for the console.
16. A first hedge-manager read model that classifies active trades into `healthy / monitoring / rebalance_required / recovery_required`.
17. A hedge rebalance-plan API that translates exposure drift into an operator-facing recommended action and perp-notional adjustment hint.
18. A first reconciliation foundation that imports exchange order reports and compares them against live ledger plus execution audit trails.
19. Manual-confirmation apply flow so tuning packages do not silently change runtime behavior.
20. Configurable persistence backends: JSON remains the default for fast local iteration, and MySQL is now available for tuning state, learning samples, journal records, datasets, ledger, audit events, and exchange order reports.
21. Seven console pages aligned to the Stitch project:
   - `总览指挥台`
   - `机会扫描页`
   - `持仓监控`
   - `风控中心`
   - `回测实验室`
   - `模型工作台`
   - `审计与日志中心`
22. JSON-to-MySQL backfill tooling plus a reconciliation candidate read model for surfacing trades that still need exchange-report follow-up.
23. Authenticated reconciliation sync that can pull spot/perp order status from Binance for a specific live trade or the highest-priority attention queue, then upsert the resulting exchange reports.
24. A lightweight in-process reconciliation worker with status and manual-run APIs so attention-queue exchange sync can run on an interval instead of only by operator trigger.
25. Dashboard and scan pages now surface raw market detail alongside strategy scores, including `spot/perp bid-ask`, `mid`, `basis`, and combined spread cost.

## Current Backend Surface

### Read and algo APIs

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
27. `/api/v1/algo/reconciliation/reports`
28. `/api/v1/algo/reconciliation/reports/import`
29. `/api/v1/algo/reconciliation/summary`
30. `/api/v1/algo/reconciliation/candidates`
31. `/api/v1/algo/persistence/backfill-json`
32. `/api/v1/algo/reconciliation/sync/{trade_id}`
33. `/api/v1/algo/reconciliation/sync`
34. `/api/v1/algo/reconciliation/worker`
35. `/api/v1/algo/reconciliation/worker/run`

### Runtime modules

- `backend/app/console/`: console read service
- `backend/app/opportunity/`: scoring engine
- `backend/app/strategy/`: strategy abstraction and registry
- `backend/app/risk/`: risk policy
- `backend/app/backtest/`: replay / backtest engine
- `backend/app/adaptation/`: offline learning and tuning recommendations
- `backend/app/journal/`: completed-trade journal and extraction bridge
- `backend/app/ledger/`: shared paper/live trade ledger
- `backend/app/audit/`: event audit persistence and query surface
- `backend/app/execution/`: execution intent orchestration, recovery flow, and execution summary read model
- `backend/app/hedge/`: hedge-health classification and rebalance/recovery overview
- `backend/app/reconciliation/`: imported exchange-order reports and ledger/audit reconciliation summary
- `backend/app/reconciliation/worker.py`: interval-based attention-queue sync worker and runtime snapshot
- `backend/app/persistence/`: optional MySQL persistence helpers and backend selection
- `backend/app/persistence/migration.py`: JSON-to-MySQL backfill service and summary schema
- `backend/app/exchange/binance_trading.py`: authenticated Binance trading client for signed order placement
- `backend/app/reconciliation/service.py`: reconciliation summary, candidate list, and authenticated trade/batch exchange sync

## Project Structure

- `backend/`: FastAPI service, exchange client, schemas, algorithms, tests
- `frontend/`: Vite + React console, Stitch-aligned pages, tests
- `docs/superpowers/specs/`: design and requirements docs
- `docs/superpowers/plans/`: implementation plans and progress updates
- `docs/architecture/`: living architecture and technical deep-dive docs

## Verification Snapshot

Latest verified status in this worktree:

1. Full backend suite: `86 passed, 6 skipped`
2. Focused reconciliation-worker slice: `5 passed`
3. Full frontend suite: `18 passed`
4. Frontend production build: `vite build` passed
5. Real Binance smoke test after the projected-edge scoring update produced positive-ranked opportunities again instead of all-zero scoring.
6. Trade-journal extraction now supports symbol filtering, recent-N slicing, and deterministic ordering.
7. Historical backtest datasets can now be imported, listed, replayed, and used to compare tuning packages before apply.
8. Hedge overview now classifies active trades by exposure drift and recovery state so positions/risk pages can consume a stable backend contract.
9. Hedge rebalance plans now convert drift into explicit `increase/reduce perp hedge` recommendations for operator tooling.
10. Reconciliation can now import exchange order snapshots and flag missing exchange reports or local/exchange status mismatches.
11. Reconciliation can now list trade-centric candidate contexts so operators can see expected order ids, reported order ids, and missing legs before opening the summary drawer.
12. JSON-backed historical state can now be backfilled into MySQL without duplicating previously imported payloads.
13. A specific live trade can now trigger authenticated exchange-order sync so reconciliation is no longer limited to manual report imports.
14. The risk center now consumes reconciliation candidates directly, so attention-needed trades show up in the UI without demo-only placeholders.
15. The reconciliation service can now batch-sync the highest-priority attention queue, which is now wired into a lightweight interval worker.
16. Dashboard and scan now expose raw `spot/perp bid-ask`, `mid`, `basis`, and spread-cost detail instead of only derived scores.

## Local Setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e backend[dev]
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m pytest backend/tests -q
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Backend with MySQL persistence

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

A ready-to-edit template is available at `.env.example`.

For opt-in MySQL persistence tests:

```powershell
$env:FUNDING_ARB_RUN_MYSQL_TESTS = "1"
.\.venv\Scripts\python -m pytest backend/tests/test_mysql_store_integration.py -q
```

To backfill existing JSON state into MySQL once the database backend is enabled:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/persistence/backfill-json"
```

To sync exchange order reports for a specific live trade:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/sync/<trade_id>"
```

To batch-sync the current attention queue:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/sync?limit=5"
```

To inspect or manually tick the reconciliation worker once it is enabled:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/worker"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/algo/reconciliation/worker/run"
```

### Frontend

```powershell
Set-Location frontend
npm install
npm run test
npm run build
npm run dev
```

## What Is Still Missing

This repository still stops short of a true production trading loop. The next major gaps are:

1. Real authenticated Binance execution adapters now have preflight guards and recovery rails, but still need exchange-grade fill reconciliation, retry policy, and live rollback/compensation against real responses.
2. Position ledger enrichment and hedge manager action execution on top of the current hedge overview read model.
3. Authenticated ingestion / sync for richer historical market + trade data instead of manual dataset import.
4. Frontend integration for backtest, model tuning, ledger, execution, and adaptation controls beyond the dashboard/scan/positions/risk surfaces already wired.
5. Live guard daemons for circuit breakers, rebalance, and recovery workers.
6. Migration/backfill utilities and stronger transactional guarantees on top of the newly added MySQL backend.
7. Moving the new in-process reconciliation worker into a more production-ready daemon/supervisor model with stronger persistence, alerting, and multi-process safety.
