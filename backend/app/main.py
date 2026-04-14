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
from app.account.router import router as account_router
from app.safety.router import router as safety_router, SafetyService
from app.execution import ExecutionOrchestrator
from app.scheduler.router import router as scheduler_router
from app.scheduler.service import SchedulerService
from app.scheduler.worker import StrategySchedulerWorker
from app.monitor.router import router as monitor_router
from app.monitor.service import HoldingMonitorService
from app.monitor.worker import HoldingMonitorWorker
from app.auth.router import router as auth_router
from app.auth.service import AuthService
from app.auth.middleware import set_auth_service
from app.credentials.router import router as credentials_router
from app.trading.router import router as trading_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auth service
    auth_service = AuthService()
    set_auth_service(auth_service)
    app.state.auth_service = auth_service

    hedge_rebalance_worker = build_hedge_rebalance_worker()
    reconciliation_worker = build_reconciliation_worker()
    recovery_worker = build_recovery_worker()
    compensation_worker = build_compensation_worker()
    safety_service = SafetyService()
    app.state.hedge_rebalance_worker = hedge_rebalance_worker
    app.state.reconciliation_worker = reconciliation_worker
    app.state.recovery_worker = recovery_worker
    app.state.compensation_worker = compensation_worker
    app.state.safety_service = safety_service
    await hedge_rebalance_worker.start()
    await reconciliation_worker.start()
    await recovery_worker.start()
    await compensation_worker.start()

    # Monitor worker
    from app.core.settings import get_settings
    settings = get_settings()
    monitor_service = HoldingMonitorService(safety_service=safety_service)
    monitor_worker = HoldingMonitorWorker(
        monitor_service,
        orchestrator=ExecutionOrchestrator(safety_service=safety_service),
        enabled=settings.holding_monitor_enabled,
        interval_seconds=settings.holding_monitor_interval_seconds,
        max_hold_periods=settings.holding_monitor_max_hold_periods,
    )
    app.state.monitor_worker = monitor_worker
    await monitor_worker.start()

    # Scheduler worker
    scheduler_service = SchedulerService(safety_service=safety_service)
    scheduler_worker = StrategySchedulerWorker(
        scheduler_service,
        orchestrator=ExecutionOrchestrator(safety_service=safety_service),
        enabled=settings.scheduler_enabled,
        interval_seconds=settings.scheduler_interval_seconds,
        max_open_positions=settings.scheduler_max_open_positions,
        max_total_notional=settings.scheduler_max_total_notional,
        app_mode=settings.app_mode,
    )
    app.state.scheduler_worker = scheduler_worker
    await scheduler_worker.start()

    try:
        yield
    finally:
        await scheduler_worker.stop()
        await monitor_worker.stop()
        await compensation_worker.stop()
        await recovery_worker.stop()
        await reconciliation_worker.stop()
        await hedge_rebalance_worker.stop()


app = FastAPI(title="Crypto Funding Arb", lifespan=lifespan)
app.include_router(algo_router)
app.include_router(dashboard_router)
app.include_router(scan_router)
app.include_router(account_router)
app.include_router(safety_router)
app.include_router(monitor_router)
app.include_router(scheduler_router)
app.include_router(auth_router)
app.include_router(credentials_router)
app.include_router(trading_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
