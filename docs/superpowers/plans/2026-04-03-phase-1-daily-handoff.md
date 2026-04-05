# 2026-04-03 Phase 1 Daily Handoff

> Historical note: this file captures the stop point on `2026-04-03`. The newer state snapshot is documented in `docs/superpowers/plans/2026-04-05-phase-1-progress-update.md`.

## Workspace

- Repo: `D:\AICode\crypto-funding-arb`
- Active worktree: `D:\AICode\crypto-funding-arb\.worktrees\phase-1`
- Branch: `codex/phase-1`
- Status: local changes only, not committed

## What We Finished Today

### 1. Real public Binance read path is now usable under the current TUN setup

- Verified direct access to:
  - `api.binance.com`
  - `fapi.binance.com`
- Verified end-to-end `ConsoleReadService` can read real Binance public data without explicit proxy config.

### 2. Fixed real-market snapshot bugs

- Added support for Binance `lastFundingRate` payloads.
- Fixed zero-price rows causing `ZeroDivisionError`.
- Snapshot builder now skips invalid zero bid/ask rows.

### 3. Upgraded backend console contracts

- Added typed `ScanFilters`
- Added backend-generated `generated_at`
- Added `total_matches`
- Added `market_status`
  - `spot_source`
  - `perp_source`
  - `degraded`
  - `requested_symbols`
  - `quoted_symbols`

### 4. Upgraded scan API behavior

- `/api/v1/scan/opportunities` now accepts typed query filters:
  - `limit`
  - `positive_funding_only`
  - `min_net_edge_bps`
- Service now applies those filters before returning rows.
- Response now echoes applied filters.

### 5. Upgraded frontend console behavior

- Dashboard now shows backend freshness time instead of only React Query cache time.
- Opportunity Scan page now has real interactive filter controls instead of decorative chips.
- Scan page now shows:
  - server scan time
  - total matches
  - displayed rows
  - market source path
- Dashboard and Scan both surface market read status in operator-friendly language such as:
  - `现货主盘口 / 永续主盘口`
  - `现货深度回退 / 永续主盘口`

### 6. Corrected degraded vs coverage semantics

- `degraded=True` now means the read path actually fell back from `bookTicker` to `depth`.
- Partial hedgeable coverage alone does **not** mark the system degraded.
- Coverage is tracked separately through:
  - `requested_symbols`
  - `quoted_symbols`

## Key Files Updated

### Backend

- `backend/app/console/read_service.py`
- `backend/app/schemas/console.py`
- `backend/app/api/routes/scan.py`
- `backend/app/market_data/service.py`
- `backend/tests/test_console_read_service.py`
- `backend/tests/test_scan_api.py`
- `backend/tests/test_api_summary.py`
- `backend/tests/test_market_snapshot.py`

### Frontend

- `frontend/src/shared/contracts/console.ts`
- `frontend/src/shared/api/client.ts`
- `frontend/src/pages/dashboard/page.tsx`
- `frontend/src/pages/opportunity-scan/page.tsx`
- `frontend/src/styles.css`
- `frontend/src/tests/dashboard.page.test.tsx`
- `frontend/src/tests/dashboard.integration.test.tsx`
- `frontend/src/tests/opportunity-scan.page.test.tsx`
- `frontend/src/tests/opportunity-scan.integration.test.tsx`
- `frontend/src/tests/opportunity-scan.filters.test.tsx`

## Verification Run Today

### Backend

- Focused regressions passed
- Full suite passed: `10 passed`

### Frontend

- Focused UI/filter tests passed
- Full suite passed: `5 passed`
- Production build passed: `npm run build`

### Live Binance smoke test

Observed from the real service:

- `sources= bookTicker bookTicker`
- `degraded= False`
- `coverage= 292 / 457`

This means:

- primary read path is healthy
- no fallback is active
- not every futures funding candidate currently has a usable spot leg

## Current State For Tomorrow

- The code is already saved on disk.
- Nothing has been committed yet.
- The worktree is in a good stop point.
- Tomorrow we can continue directly from the current files without reconstructing context.

## Recommended Next Step

Pick one of these first:

1. Add `Apply / Reset` behavior and preserve previous rows while scan refetches.
2. Add richer degraded-read handling:
   - partial recovery on depth fallback
   - explicit transport vs fallback vs empty-book distinctions
3. Start the next Phase 1 slice after read console hardening.

## How To Preserve Tonight

No extra action is strictly required because the files are already written to disk in the worktree.

Practical rule:

- Do not delete the worktree
- Do not run destructive git cleanup
- Tomorrow reopen `D:\AICode\crypto-funding-arb\.worktrees\phase-1`

If we want stronger safety later, we can either:

- make a normal local commit
- or create a checkpoint commit before starting the next slice
