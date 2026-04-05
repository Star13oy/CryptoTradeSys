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
20. Seven console pages aligned to the Stitch project:
   - `总览指挥台`
   - `机会扫描页`
   - `持仓监控`
   - `风控中心`
   - `回测实验室`
   - `模型工作台`
   - `审计与日志中心`

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
- `backend/app/exchange/binance_trading.py`: authenticated Binance trading client for signed order placement

## Project Structure

- `backend/`: FastAPI service, exchange client, schemas, algorithms, tests
- `frontend/`: Vite + React console, Stitch-aligned pages, tests
- `docs/superpowers/specs/`: design and requirements docs
- `docs/superpowers/plans/`: implementation plans and progress updates
- `docs/architecture/`: living architecture and technical deep-dive docs

## Verification Snapshot

Latest verified status in this worktree:

1. Full backend suite: `73 passed`
2. Full frontend suite: `17 passed`
3. Frontend production build: `vite build` passed
4. Real Binance smoke test after the projected-edge scoring update produced positive-ranked opportunities again instead of all-zero scoring.
5. Trade-journal extraction now supports symbol filtering, recent-N slicing, and deterministic ordering.
6. Historical backtest datasets can now be imported, listed, replayed, and used to compare tuning packages before apply.
7. Hedge overview now classifies active trades by exposure drift and recovery state so positions/risk pages can consume a stable backend contract.
8. Hedge rebalance plans now convert drift into explicit `increase/reduce perp hedge` recommendations for operator tooling.
9. Reconciliation can now import exchange order snapshots and flag missing exchange reports or local/exchange status mismatches.

## Local Setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e backend[dev]
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m pytest backend/tests -q
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000
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
4. Frontend integration for backtest, model tuning, ledger, execution, and adaptation controls.
5. Live guard daemons for circuit breakers, rebalance, and recovery workers.
