import asyncio
from datetime import datetime, timezone

from app.reconciliation import ExchangeOrderReport, ReconciliationWorker, ReconciliationWorkerSnapshot


def test_reconciliation_worker_run_once_updates_snapshot() -> None:
    class StubReconciliationService:
        def sync_attention_candidates(self, *, trading_client=None, limit: int | None = None):
            assert trading_client is not None
            assert limit == 2
            return [
                ExchangeOrderReport(
                    venue="binance",
                    order_id="7001",
                    trade_id="worker-1",
                    symbol="BTCUSDT",
                    leg="spot",
                    status="FILLED",
                    executed_qty=0.2,
                    cum_quote_qty=15000,
                    updated_at=datetime(2026, 4, 5, 21, 0, tzinfo=timezone.utc),
                ),
                ExchangeOrderReport(
                    venue="binance",
                    order_id="7002",
                    trade_id="worker-1",
                    symbol="BTCUSDT",
                    leg="perp",
                    status="FILLED",
                    executed_qty=0.2,
                    cum_quote_qty=14990,
                    updated_at=datetime(2026, 4, 5, 21, 0, 1, tzinfo=timezone.utc),
                ),
                ExchangeOrderReport(
                    venue="binance",
                    order_id="8001",
                    trade_id="worker-2",
                    symbol="ETHUSDT",
                    leg="spot",
                    status="PARTIALLY_FILLED",
                    executed_qty=4,
                    cum_quote_qty=10000,
                    updated_at=datetime(2026, 4, 5, 21, 0, 2, tzinfo=timezone.utc),
                ),
            ]

    worker = ReconciliationWorker(
        StubReconciliationService(),
        trading_client=object(),
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
    assert snapshot.last_imported_report_count == 3
    assert snapshot.last_synced_trade_count == 2
    assert snapshot.total_imported_reports == 3
    assert snapshot.last_error is None
    assert snapshot.last_success_at is not None


def test_reconciliation_worker_run_once_records_errors() -> None:
    class StubReconciliationService:
        def sync_attention_candidates(self, *, trading_client=None, limit: int | None = None):
            raise RuntimeError("exchange query failed")

    worker = ReconciliationWorker(
        StubReconciliationService(),
        trading_client=object(),
        enabled=True,
        interval_seconds=15,
        limit=2,
    )

    snapshot = asyncio.run(worker.run_once())

    assert snapshot.total_runs == 1
    assert snapshot.total_failed_runs == 1
    assert snapshot.last_imported_report_count == 0
    assert snapshot.last_synced_trade_count == 0
    assert snapshot.last_success_at is None
    assert snapshot.last_error == "exchange query failed"


def test_reconciliation_worker_start_runs_background_loop_until_stopped() -> None:
    class StubReconciliationService:
        def __init__(self) -> None:
            self.calls = 0

        def sync_attention_candidates(self, *, trading_client=None, limit: int | None = None):
            self.calls += 1
            return []

    service = StubReconciliationService()
    worker = ReconciliationWorker(
        service,
        trading_client=object(),
        enabled=True,
        interval_seconds=0.01,
        limit=1,
    )

    async def scenario() -> tuple[ReconciliationWorkerSnapshot, ReconciliationWorkerSnapshot, int]:
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
