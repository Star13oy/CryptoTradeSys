from fastapi import APIRouter, Depends, Request

from .schemas import HoldingMonitorWorkerSnapshot
from .worker import HoldingMonitorWorker

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])


@router.get("/state", response_model=HoldingMonitorWorkerSnapshot)
async def get_monitor_state(request: Request):
    worker: HoldingMonitorWorker | None = getattr(request.app.state, "monitor_worker", None)
    if worker is None:
        return HoldingMonitorWorkerSnapshot()
    return worker.snapshot()


@router.post("/run", response_model=HoldingMonitorWorkerSnapshot)
async def run_monitor_once(request: Request):
    worker: HoldingMonitorWorker | None = getattr(request.app.state, "monitor_worker", None)
    if worker is None:
        raise ValueError("holding monitor worker is not configured")
    return await worker.run_once()
