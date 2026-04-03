# Crypto Funding Arb

## Phase 1 Vertical Slice

This phase delivers the first executable slice of the project:

1. FastAPI health endpoint
2. Public Binance market snapshot assembly
3. Deterministic funding-opportunity scoring
4. Read-only dashboard and scan APIs
5. React console pages for `总览指挥台` and `机会扫描页`

## Project Structure

- `backend/`: FastAPI service, exchange client, schemas, scoring logic, pytest suite
- `frontend/`: Vite + React console, Stitch-aligned page shells, Vitest suite
- `docs/superpowers/`: approved spec and implementation plans

## Local Setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e backend[dev]
Set-Location backend
..\.venv\Scripts\python -m pytest tests -q
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
Set-Location frontend
npm install
npm run test
npm run dev
```

## Current Scope

This repository intentionally stops before live execution. Authenticated trading, risk guard, hedging loops, backtesting, and the model workbench are planned for later phases.
