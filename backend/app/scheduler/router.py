from fastapi import APIRouter, Depends, Request

from .schemas import SchedulerWorkerSnapshot
from .worker import StrategySchedulerWorker

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


@router.get("/state", response_model=SchedulerWorkerSnapshot)
async def get_scheduler_state(request: Request):
    worker: StrategySchedulerWorker | None = getattr(request.app.state, "scheduler_worker", None)
    if worker is None:
        return SchedulerWorkerSnapshot()
    return worker.snapshot()


@router.post("/run", response_model=SchedulerWorkerSnapshot)
async def run_scheduler_once(request: Request):
    worker: StrategySchedulerWorker | None = getattr(request.app.state, "scheduler_worker", None)
    if worker is None:
        raise ValueError("scheduler worker is not configured")
    return await worker.run_once()
