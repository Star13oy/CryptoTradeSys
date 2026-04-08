import asyncio
from datetime import datetime, timezone

from app.hedge import (
    HedgeRebalanceExecutionSummary,
    HedgeRebalanceWorker,
    HedgeRebalanceWorkerSnapshot,
)


def test_hedge_worker_run_once_updates_snapshot() -> None:
    class StubHedgeService:
        def execute_auto_rebalance_actions(self, *, orchestrator=None, symbol=None, limit=None, exposure_limit_bps=50.0):
            assert orchestrator is not None
            assert symbol is None
            assert limit == 2
            assert exposure_limit_bps == 35.0
            return HedgeRebalanceExecutionSummary(
                generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=timezone.utc),
                attempted_count=2,
                executed_count=1,
                skipped_count=1,
                failed_count=0,
            )

    worker = HedgeRebalanceWorker(
        StubHedgeService(),
        orchestrator=object(),
        enabled=True,
        interval_seconds=15,
        limit=2,
        exposure_limit_bps=35.0,
    )

    snapshot = asyncio.run(worker.run_once())

    assert snapshot.enabled is True
    assert snapshot.configured is True
    assert snapshot.running is False
    assert snapshot.total_runs == 1
    assert snapshot.total_failed_runs == 0
    assert snapshot.last_attempted_count == 2
    assert snapshot.last_executed_count == 1
    assert snapshot.last_skipped_count == 1
    assert snapshot.last_failed_count == 0
    assert snapshot.total_executed_rebalances == 1
    assert snapshot.last_error is None
    assert snapshot.last_success_at is not None


def test_hedge_worker_run_once_records_errors() -> None:
    class StubHedgeService:
        def execute_auto_rebalance_actions(self, *, orchestrator=None, symbol=None, limit=None, exposure_limit_bps=50.0):
            raise RuntimeError("hedge auto rebalance failed")

    worker = HedgeRebalanceWorker(
        StubHedgeService(),
        orchestrator=object(),
        enabled=True,
        interval_seconds=15,
        limit=2,
        exposure_limit_bps=35.0,
    )

    snapshot = asyncio.run(worker.run_once())

    assert snapshot.total_runs == 1
    assert snapshot.total_failed_runs == 1
    assert snapshot.last_attempted_count == 0
    assert snapshot.last_executed_count == 0
    assert snapshot.last_skipped_count == 0
    assert snapshot.last_failed_count == 0
    assert snapshot.total_executed_rebalances == 0
    assert snapshot.last_success_at is None
    assert snapshot.last_error == "hedge auto rebalance failed"


def test_hedge_worker_start_runs_background_loop_until_stopped() -> None:
    class StubHedgeService:
        def __init__(self) -> None:
            self.calls = 0

        def execute_auto_rebalance_actions(self, *, orchestrator=None, symbol=None, limit=None, exposure_limit_bps=50.0):
            self.calls += 1
            return HedgeRebalanceExecutionSummary(
                generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=timezone.utc),
                attempted_count=0,
                executed_count=0,
                skipped_count=0,
                failed_count=0,
            )

    service = StubHedgeService()
    worker = HedgeRebalanceWorker(
        service,
        orchestrator=object(),
        enabled=True,
        interval_seconds=0.01,
        limit=1,
        exposure_limit_bps=35.0,
    )

    async def scenario() -> tuple[HedgeRebalanceWorkerSnapshot, HedgeRebalanceWorkerSnapshot, int]:
        await worker.start()
        await asyncio.sleep(0.04)
        running_snapshot = worker.snapshot()
        await worker.stop()
        stopped_snapshot = worker.snapshot()
        return running_snapshot, stopped_snapshot, service.calls

    running_snapshot, stopped_snapshot, calls = asyncio.run(scenario())

    assert calls >= 1
    assert running_snapshot.running is True
    assert stopped_snapshot.running is False
    assert stopped_snapshot.total_runs >= 1
