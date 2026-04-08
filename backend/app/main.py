from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.algo import (
    build_compensation_worker,
    build_hedge_rebalance_worker,
    build_reconciliation_worker,
    build_recovery_worker,
    router as algo_router,
)
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.scan import router as scan_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    hedge_rebalance_worker = build_hedge_rebalance_worker()
    reconciliation_worker = build_reconciliation_worker()
    recovery_worker = build_recovery_worker()
    compensation_worker = build_compensation_worker()
    app.state.hedge_rebalance_worker = hedge_rebalance_worker
    app.state.reconciliation_worker = reconciliation_worker
    app.state.recovery_worker = recovery_worker
    app.state.compensation_worker = compensation_worker
    await hedge_rebalance_worker.start()
    await reconciliation_worker.start()
    await recovery_worker.start()
    await compensation_worker.start()
    try:
        yield
    finally:
        await compensation_worker.stop()
        await recovery_worker.stop()
        await reconciliation_worker.stop()
        await hedge_rebalance_worker.stop()


app = FastAPI(title="Crypto Funding Arb", lifespan=lifespan)
app.include_router(algo_router)
app.include_router(dashboard_router)
app.include_router(scan_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
