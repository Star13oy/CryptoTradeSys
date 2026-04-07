from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.algo import build_reconciliation_worker, router as algo_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.scan import router as scan_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = build_reconciliation_worker()
    app.state.reconciliation_worker = worker
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title="Crypto Funding Arb", lifespan=lifespan)
app.include_router(algo_router)
app.include_router(dashboard_router)
app.include_router(scan_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
