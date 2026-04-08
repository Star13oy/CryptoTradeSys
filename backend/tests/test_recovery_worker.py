import asyncio
from datetime import datetime, timezone

from app.execution import ExecutionResult
from app.ledger import TradeLedgerRecord
from app.recovery import RecoveryExecutionSummary, RecoveryWorker, RecoveryWorkerSnapshot


def test_recovery_worker_run_once_updates_snapshot() -> None:
    class StubRecoveryService:
        def execute_actionable_plans(self, *, orchestrator=None, limit: int | None = None, symbol: str | None = None):
            assert orchestrator is not None
            assert limit == 2
            assert symbol is None
            return RecoveryExecutionSummary(
                generated_at=datetime(2026, 4, 8, 1, 0, tzinfo=timezone.utc),
                attempted_count=2,
                executed_count=1,
                skipped_count=1,
                results=[
                    ExecutionResult(
                        trade_id="recover-1",
                        action="open_hedge",
                        mode="paper",
                        symbol="BTCUSDT",
                        status="hedged",
                        ledger_record=TradeLedgerRecord(
                            trade_id="recover-1",
                            mode="paper",
                            strategy_id="funding-arb",
                            symbol="BTCUSDT",
                            status="hedged",
                            opened_at=datetime(2026, 4, 8, 0, 59, tzinfo=timezone.utc),
                            net_exposure=0,
                        ),
                        executed_at=datetime(2026, 4, 8, 1, 0, tzinfo=timezone.utc),
                    )
                ],
            )

    worker = RecoveryWorker(
        StubRecoveryService(),
        orchestrator=object(),
        enabled=True,
        interval_seconds=15,
        limit=2,
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
    assert snapshot.total_executed_recoveries == 1
    assert snapshot.last_error is None
    assert snapshot.last_success_at is not None


def test_recovery_worker_run_once_records_errors() -> None:
    class StubRecoveryService:
        def execute_actionable_plans(self, *, orchestrator=None, limit: int | None = None, symbol: str | None = None):
            raise RuntimeError("recovery execution failed")

    worker = RecoveryWorker(
        StubRecoveryService(),
        orchestrator=object(),
        enabled=True,
        interval_seconds=15,
        limit=2,
    )

    snapshot = asyncio.run(worker.run_once())

    assert snapshot.total_runs == 1
    assert snapshot.total_failed_runs == 1
    assert snapshot.last_attempted_count == 0
    assert snapshot.last_executed_count == 0
    assert snapshot.last_skipped_count == 0
    assert snapshot.total_executed_recoveries == 0
    assert snapshot.last_success_at is None
    assert snapshot.last_error == "recovery execution failed"


def test_recovery_worker_start_runs_background_loop_until_stopped() -> None:
    class StubRecoveryService:
        def __init__(self) -> None:
            self.calls = 0

        def execute_actionable_plans(self, *, orchestrator=None, limit: int | None = None, symbol: str | None = None):
            self.calls += 1
            return RecoveryExecutionSummary(
                generated_at=datetime(2026, 4, 8, 1, 0, tzinfo=timezone.utc),
                attempted_count=0,
                executed_count=0,
                skipped_count=0,
            )

    service = StubRecoveryService()
    worker = RecoveryWorker(
        service,
        orchestrator=object(),
        enabled=True,
        interval_seconds=0.01,
        limit=1,
    )

    async def scenario() -> tuple[RecoveryWorkerSnapshot, RecoveryWorkerSnapshot, int]:
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
