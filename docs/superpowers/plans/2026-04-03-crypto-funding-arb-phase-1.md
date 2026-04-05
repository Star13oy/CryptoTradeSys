# Crypto Funding Arbitrage Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build phase 1 of `crypto-funding-arb`: a working vertical slice with real Binance public market snapshots, deterministic funding-opportunity scoring, paper-only dashboard data, and the first two Stitch-aligned console pages.

**Architecture:** This phase intentionally stops before live execution. The backend is a FastAPI modular monolith with typed settings and a thin public Binance client; the frontend is a React + TypeScript console that implements `总览指挥台` and `机会扫描页` using typed API contracts. Persisted paper trading, live execution, and backtesting are deferred to later plans.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic Settings, httpx, pytest, React, TypeScript, Vite, React Router, TanStack Query, Vitest

---

## Implementation Status Update

As of `2026-04-05`, this plan has been materially exceeded. Phase 1 is no longer just a vertical slice for two pages.

### Already delivered in the active worktree

1. Repo bootstrap and typed backend/frontend foundations.
2. Real Binance public read path with fallback handling.
3. Dashboard and scan APIs backed by `ConsoleReadService`.
4. Stitch-aligned console skeleton for all 7 planned operator pages.
5. Explainable scoring engine with projected edge and payback semantics.
6. Strategy registry and default `funding-arb` runtime.
7. Risk policy layer with `allow / review / block`.
8. Deterministic backtest engine and algo API surface.
9. Offline adaptation recommendation service with:
   - `保守 / 平衡 / 进取 / 自动推荐`
   - manual confirmation before apply
   - runtime tuning state persistence

### Still missing after this phase

1. Authenticated execution and order orchestration.
2. Persistent trade / position ledger.
3. Historical market and trade data ingestion.
4. Frontend wiring for backtest, adaptation, and model tuning.
5. Live rebalance, circuit-breaker, and recovery workers.

### How to read the rest of this file

The task list below remains useful as the original phase-1 execution baseline, but it is no longer an exact reflection of current repository status. Treat it as the historical implementation plan that got us here.

## Scope Decision

The approved design is too large for a single implementation plan. This document covers only:

1. Repo bootstrap
2. Typed backend foundation
3. Public Binance market snapshot assembly
4. Deterministic opportunity scoring
5. Dashboard + scan APIs
6. The first two Stitch-based pages

Deferred to later plans:

1. Authenticated Binance trading
2. Live risk guard workers and circuit breakers
3. Hedge manager and rebalance loop
4. Durable audit storage
5. Historical data replay at scale
6. Model workbench frontend wiring
7. Adaptation center frontend wiring

## Planned File Structure

- `README.md`
- `.gitignore`
- `backend/pyproject.toml`
- `backend/app/main.py`
- `backend/app/core/settings.py`
- `backend/app/schemas/market.py`
- `backend/app/exchange/binance_public.py`
- `backend/app/market_data/service.py`
- `backend/app/opportunity/scorer.py`
- `backend/app/api/routes/dashboard.py`
- `backend/app/api/routes/scan.py`
- `backend/tests/...`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/app/router.tsx`
- `frontend/src/shared/api/client.ts`
- `frontend/src/pages/dashboard/page.tsx`
- `frontend/src/pages/opportunity-scan/page.tsx`
- `frontend/src/tests/...`

## Stitch Alignment

This phase maps to the existing Stitch project `projects/10365151989515025592`:

1. `总览指挥台 (优化全中文)` -> `projects/10365151989515025592/screens/af5b8004ba3a48f19e912b1e668546db`
2. `机会扫描页 (优化全中文)` -> `projects/10365151989515025592/screens/3c48b28f34074cc4bfdb37b32fb52032`

### Task 1: Bootstrap The Repo And Backend Health Slice

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`

- [ ] **Step 1: Write the failing health test**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_health.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write the minimal repo skeleton**

```toml
# backend/pyproject.toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "crypto-funding-arb-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.30,<1",
  "pydantic-settings>=2.6,<3",
  "httpx>=0.28,<1",
]

[project.optional-dependencies]
dev = ["pytest>=8,<9"]

[tool.pytest.ini_options]
pythonpath = ["backend"]
```

```python
# backend/app/main.py
from fastapi import FastAPI


app = FastAPI(title="Crypto Funding Arb")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

```json
// frontend/package.json
{
  "name": "crypto-funding-arb-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.59.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "ES2020"],
    "module": "ESNext",
    "jsx": "react-jsx",
    "moduleResolution": "Bundler",
    "strict": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
  },
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_health.py -q`

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md backend/pyproject.toml backend/app/main.py backend/tests/test_health.py frontend/package.json frontend/tsconfig.json frontend/vite.config.ts
git commit -m "chore: bootstrap repo and backend health slice"
```

### Task 2: Add Typed Settings And Public Market Snapshot Assembly

**Files:**
- Create: `backend/app/core/settings.py`
- Create: `backend/app/schemas/market.py`
- Create: `backend/app/exchange/binance_public.py`
- Create: `backend/app/market_data/service.py`
- Create: `backend/tests/test_market_snapshot.py`

- [ ] **Step 1: Write the failing market snapshot test**

```python
# backend/tests/test_market_snapshot.py
from app.market_data.service import build_market_snapshot


def test_build_market_snapshot_merges_rows() -> None:
    funding_rows = [{"symbol": "BTCUSDT", "fundingRate": "0.0002"}]
    perp_rows = [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}]
    spot_rows = [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}]

    snapshots = build_market_snapshot(funding_rows, perp_rows, spot_rows)

    assert len(snapshots) == 1
    assert snapshots[0].symbol == "BTCUSDT"
    assert snapshots[0].funding_rate == 0.0002
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_market_snapshot.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.market_data.service'`

- [ ] **Step 3: Add settings, schema, client, and snapshot service**

```python
# backend/app/core/settings.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FUNDING_ARB_", env_file=".env", extra="ignore")

    app_mode: str = "paper"
    exchange_name: str = "binance"
    binance_perp_base_url: str = "https://fapi.binance.com"
    binance_spot_base_url: str = "https://api.binance.com"
    scan_limit: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/app/schemas/market.py
from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    funding_rate: float
    perp_mid: float
    spot_mid: float
    perp_spread_bps: float
    spot_spread_bps: float
```

```python
# backend/app/exchange/binance_public.py
import httpx

from app.core.settings import get_settings


class BinancePublicClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.perp_base = settings.binance_perp_base_url
        self.spot_base = settings.binance_spot_base_url

    async def fetch_funding_rates(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.perp_base}/fapi/v1/premiumIndex")
            response.raise_for_status()
            return response.json()
```

```python
# backend/app/market_data/service.py
from app.schemas.market import MarketSnapshot


def build_market_snapshot(funding_rows: list[dict], perp_rows: list[dict], spot_rows: list[dict]) -> list[MarketSnapshot]:
    perp_map = {row["symbol"]: row for row in perp_rows}
    spot_map = {row["symbol"]: row for row in spot_rows}
    snapshots: list[MarketSnapshot] = []

    for funding in funding_rows:
        symbol = funding["symbol"]
        if symbol not in perp_map or symbol not in spot_map:
            continue

        perp = perp_map[symbol]
        spot = spot_map[symbol]
        perp_mid = (float(perp["bidPrice"]) + float(perp["askPrice"])) / 2
        spot_mid = (float(spot["bidPrice"]) + float(spot["askPrice"])) / 2

        snapshots.append(
            MarketSnapshot(
                symbol=symbol,
                funding_rate=float(funding["fundingRate"]),
                perp_mid=perp_mid,
                spot_mid=spot_mid,
                perp_spread_bps=((float(perp["askPrice"]) - float(perp["bidPrice"])) / perp_mid) * 10000,
                spot_spread_bps=((float(spot["askPrice"]) - float(spot["bidPrice"])) / spot_mid) * 10000,
            )
        )

    return snapshots
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_market_snapshot.py -q`

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/settings.py backend/app/schemas/market.py backend/app/exchange/binance_public.py backend/app/market_data/service.py backend/tests/test_market_snapshot.py
git commit -m "feat: add typed settings and public market snapshot assembly"
```

### Task 3: Implement Deterministic Opportunity Scoring And Read APIs

**Files:**
- Modify: `backend/app/schemas/market.py`
- Create: `backend/app/opportunity/scorer.py`
- Create: `backend/app/api/routes/dashboard.py`
- Create: `backend/app/api/routes/scan.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_summary.py`

- [ ] **Step 1: Write the failing API summary test**

```python
# backend/tests/test_api_summary.py
from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_summary_contains_ranked_opportunities() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["top_opportunities"]) >= 1
    assert payload["top_opportunities"][0]["symbol"] == "BTCUSDT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_api_summary.py -q`

Expected: FAIL with `assert 404 == 200`

- [ ] **Step 3: Add score schema, scorer, and read-only APIs**

```python
# backend/app/schemas/market.py
from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    funding_rate: float
    perp_mid: float
    spot_mid: float
    perp_spread_bps: float
    spot_spread_bps: float


class OpportunityScore(BaseModel):
    symbol: str
    funding_rate: float
    net_edge_bps: float
    score: float
    risk_tag: str
```

```python
# backend/app/opportunity/scorer.py
from app.schemas.market import MarketSnapshot, OpportunityScore


def score_snapshot(snapshot: MarketSnapshot, taker_fee_bps: float = 0.4) -> OpportunityScore:
    gross_edge_bps = snapshot.funding_rate * 10000
    trading_cost_bps = (taker_fee_bps * 2) + snapshot.perp_spread_bps + snapshot.spot_spread_bps
    net_edge_bps = gross_edge_bps - trading_cost_bps
    risk_tag = "normal" if net_edge_bps > 0 else "thin-edge"
    score = max(net_edge_bps, 0) * 10
    return OpportunityScore(
        symbol=snapshot.symbol,
        funding_rate=snapshot.funding_rate,
        net_edge_bps=net_edge_bps,
        score=score,
        risk_tag=risk_tag,
    )
```

```python
# backend/app/api/routes/dashboard.py
from fastapi import APIRouter

from app.market_data.service import build_market_snapshot
from app.opportunity.scorer import score_snapshot


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary() -> dict:
    snapshots = build_market_snapshot(
        [{"symbol": "BTCUSDT", "fundingRate": "0.0002"}],
        [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}],
        [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}],
    )
    scores = [score_snapshot(snapshot).model_dump() for snapshot in snapshots]
    return {
        "account_health": {"mode": "paper", "exchange": "binance", "risk_state": "normal"},
        "top_opportunities": scores,
        "paper_positions": [],
    }
```

```python
# backend/app/api/routes/scan.py
from fastapi import APIRouter

from app.market_data.service import build_market_snapshot
from app.opportunity.scorer import score_snapshot


router = APIRouter(prefix="/api/v1/scan", tags=["scan"])


@router.get("/opportunities")
async def get_scan() -> dict:
    snapshots = build_market_snapshot(
        [{"symbol": "BTCUSDT", "fundingRate": "0.0002"}],
        [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}],
        [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}],
    )
    return {"rows": [score_snapshot(snapshot).model_dump() for snapshot in snapshots]}
```

```python
# backend/app/main.py
from fastapi import FastAPI

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.scan import router as scan_router


app = FastAPI(title="Crypto Funding Arb")
app.include_router(dashboard_router)
app.include_router(scan_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_api_summary.py -q`

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/market.py backend/app/opportunity/scorer.py backend/app/api/routes/dashboard.py backend/app/api/routes/scan.py backend/app/main.py backend/tests/test_api_summary.py
git commit -m "feat: add scoring and read-only dashboard apis"
```

### Task 4: Build The Dashboard And Scan Pages

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/shared/api/client.ts`
- Create: `frontend/src/pages/dashboard/page.tsx`
- Create: `frontend/src/pages/opportunity-scan/page.tsx`
- Create: `frontend/src/tests/dashboard.page.test.tsx`
- Create: `frontend/src/tests/opportunity-scan.page.test.tsx`

- [ ] **Step 1: Write the failing dashboard page test**

```tsx
// frontend/src/tests/dashboard.page.test.tsx
import { render, screen } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";


test("dashboard page renders the Chinese title", () => {
  render(<DashboardPage />);
  expect(screen.getByText("总览指挥台")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/tests/dashboard.page.test.tsx`

Expected: FAIL with `Failed to resolve import "../pages/dashboard/page"`

- [ ] **Step 3: Write the page shell and route wiring**

```tsx
// frontend/src/shared/api/client.ts
export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}
```

```tsx
// frontend/src/pages/dashboard/page.tsx
export function DashboardPage() {
  return (
    <main style={{ background: "#0c1323", color: "#dce2f9", minHeight: "100vh", padding: 24 }}>
      <p>Paper Trading / Binance</p>
      <h1>总览指挥台</h1>
      <section>
        <h2>账户健康</h2>
        <p>这里对齐 Stitch 的主状态区和机会总览区。</p>
      </section>
    </main>
  );
}
```

```tsx
// frontend/src/pages/opportunity-scan/page.tsx
export function OpportunityScanPage() {
  return (
    <main style={{ background: "#0c1323", color: "#dce2f9", minHeight: "100vh", padding: 24 }}>
      <p>Funding / Spread / Risk</p>
      <h1>机会扫描页</h1>
      <section>
        <h2>候选机会表</h2>
        <p>这里对齐 Stitch 的扫描表格和详情抽屉。</p>
      </section>
    </main>
  );
}
```

```tsx
// frontend/src/app/router.tsx
import { createBrowserRouter } from "react-router-dom";

import { DashboardPage } from "../pages/dashboard/page";
import { OpportunityScanPage } from "../pages/opportunity-scan/page";

export const router = createBrowserRouter([
  { path: "/", element: <DashboardPage /> },
  { path: "/scan", element: <OpportunityScanPage /> },
]);
```

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import { router } from "./app/router";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
```

```tsx
// frontend/src/tests/opportunity-scan.page.test.tsx
import { render, screen } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";


test("scan page renders the Chinese title", () => {
  render(<OpportunityScanPage />);
  expect(screen.getByText("机会扫描页")).toBeTruthy();
});
```

- [ ] **Step 4: Run dashboard and scan page tests**

Run:

```bash
cd frontend
npm run test -- src/tests/dashboard.page.test.tsx src/tests/opportunity-scan.page.test.tsx
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main.tsx frontend/src/app/router.tsx frontend/src/shared/api/client.ts frontend/src/pages/dashboard/page.tsx frontend/src/pages/opportunity-scan/page.tsx frontend/src/tests/dashboard.page.test.tsx frontend/src/tests/opportunity-scan.page.test.tsx
git commit -m "feat: add stitch-aligned dashboard and scan pages"
```

### Task 5: Run The Vertical Slice End-To-End And Document It

**Files:**
- Modify: `README.md`
- Modify: `frontend/src/pages/dashboard/page.tsx`
- Modify: `frontend/src/pages/opportunity-scan/page.tsx`
- Create: `frontend/src/tests/dashboard.integration.test.tsx`
- Create: `frontend/src/tests/opportunity-scan.integration.test.tsx`

- [ ] **Step 1: Write the failing scan API smoke test**

```tsx
// frontend/src/tests/dashboard.integration.test.tsx
import { render, screen, waitFor } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";


test("dashboard page renders a fetched opportunity row", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        account_health: { mode: "paper", exchange: "binance", risk_state: "normal" },
        top_opportunities: [{ symbol: "BTCUSDT", net_edge_bps: 0.7, score: 7, risk_tag: "normal", funding_rate: 0.0002 }],
        paper_positions: [],
      }),
    }) as Response) as typeof fetch;

  render(<DashboardPage />);

  await waitFor(() => expect(screen.getByText("BTCUSDT")).toBeTruthy());
});
```

```tsx
// frontend/src/tests/opportunity-scan.integration.test.tsx
import { render, screen, waitFor } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";


test("scan page renders fetched rows", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        rows: [{ symbol: "BTCUSDT", score: 7, risk_tag: "normal" }],
      }),
    }) as Response) as typeof fetch;

  render(<OpportunityScanPage />);

  await waitFor(() => expect(screen.getByText("BTCUSDT")).toBeTruthy());
});
```

- [ ] **Step 2: Run test to verify current slice still has a gap**

Run: `cd frontend && npm run test -- src/tests/dashboard.integration.test.tsx src/tests/opportunity-scan.integration.test.tsx`

Expected: FAIL because the current pages are still static and do not render fetched API rows

- [ ] **Step 3: Fix any shape drift and write the startup README**

````md
# README.md

## Phase 1 Vertical Slice

This phase delivers:

1. FastAPI health endpoint
2. Public Binance market snapshot assembly
3. Deterministic funding opportunity scoring
4. Read-only dashboard and scan APIs
5. React dashboard and opportunity scan pages

## Local Commands

```bash
pip install -e backend[dev]
cd frontend
npm install
cd ..
python -m pytest backend/tests -q
uvicorn app.main:app --app-dir backend --reload --port 8000
cd frontend && npm run dev
```
````

```tsx
// frontend/src/pages/dashboard/page.tsx
import { useEffect, useState } from "react";

type DashboardSummary = {
  account_health: { mode: string; exchange: string; risk_state: string };
  top_opportunities: Array<{ symbol: string; net_edge_bps: number; score: number; risk_tag: string }>;
};

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    fetch("/api/v1/dashboard/summary")
      .then((response) => response.json())
      .then(setData);
  }, []);

  return (
    <main style={{ background: "#0c1323", color: "#dce2f9", minHeight: "100vh", padding: 24 }}>
      <p>Paper Trading / Binance</p>
      <h1>总览指挥台</h1>
      <section>
        <h2>账户健康</h2>
        <p>{data?.account_health.risk_state ?? "loading"}</p>
      </section>
      <section>
        <h2>Top Opportunities</h2>
        {data?.top_opportunities.map((row) => (
          <p key={row.symbol}>{row.symbol}</p>
        ))}
      </section>
    </main>
  );
}
```

```tsx
// frontend/src/pages/opportunity-scan/page.tsx
import { useEffect, useState } from "react";

type ScanRow = { symbol: string; score: number; risk_tag: string };

export function OpportunityScanPage() {
  const [rows, setRows] = useState<ScanRow[]>([]);

  useEffect(() => {
    fetch("/api/v1/scan/opportunities")
      .then((response) => response.json())
      .then((payload) => setRows(payload.rows));
  }, []);

  return (
    <main style={{ background: "#0c1323", color: "#dce2f9", minHeight: "100vh", padding: 24 }}>
      <p>Funding / Spread / Risk</p>
      <h1>机会扫描页</h1>
      <section>
        <h2>候选机会表</h2>
        {rows.map((row) => (
          <p key={row.symbol}>{row.symbol}</p>
        ))}
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run the full phase-1 smoke suite**

Run:

```bash
python -m pytest backend/tests -q
cd frontend
npm run test
```

Expected:

```text
all backend tests passed
all frontend tests passed
```

- [ ] **Step 5: Commit**

```bash
git add README.md frontend/src/tests/dashboard.integration.test.tsx frontend/src/tests/opportunity-scan.integration.test.tsx frontend/src/pages/dashboard/page.tsx frontend/src/pages/opportunity-scan/page.tsx
git commit -m "docs: finalize phase 1 vertical slice handoff"
```

## Coverage Review

This plan covers the approved spec items that should exist before live trading:

1. Project bootstrap
2. Exchange abstraction starting point
3. Public market data ingestion
4. Opportunity scoring
5. Dashboard-first frontend
6. Scan page aligned with Stitch

This plan intentionally does not claim to satisfy:

1. Live execution
2. Strong risk guard
3. Hedge management
4. Audit trail
5. Backtesting
6. Custom model framework

Those need dedicated follow-up plans after this vertical slice is implemented cleanly.
