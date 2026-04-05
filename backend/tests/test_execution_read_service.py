from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.execution.read_service import ExecutionReadService
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_execution_read_service_builds_snapshot_for_console() -> None:
    opened_at = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("execution-read-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("execution-read-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="exec-read-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="recovery_pending",
                opened_at=opened_at,
                net_exposure=20,
                spot_notional=15000,
                perp_notional=14980,
            ),
            TradeLedgerRecord(
                trade_id="exec-read-2",
                mode="paper",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="failed",
                opened_at=opened_at + timedelta(minutes=5),
                net_exposure=50,
                spot_notional=10000,
                perp_notional=9950,
            ),
            TradeLedgerRecord(
                trade_id="exec-read-3",
                mode="paper",
                strategy_id="funding-arb",
                symbol="SOLUSDT",
                status="closed",
                opened_at=opened_at + timedelta(minutes=10),
                closed_at=opened_at + timedelta(minutes=20),
                net_exposure=0,
                spot_notional=5000,
                perp_notional=4990,
                realized_pnl=18.5,
            ),
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.recovery.required",
        source="execution-orchestrator",
        severity="warning",
        occurred_at=opened_at + timedelta(minutes=1),
        summary="Recovery required for BTCUSDT",
        payload={"trade_id": "exec-read-1"},
        tags=["execution", "recovery"],
    )
    audit_service.record_event(
        event_type="execution.leg.perp.failed",
        source="execution-orchestrator",
        severity="error",
        occurred_at=opened_at + timedelta(minutes=6),
        summary="Perp leg failed for ETHUSDT",
        payload={"trade_id": "exec-read-2"},
        tags=["execution", "failure"],
    )
    audit_service.record_event(
        event_type="execution.completed",
        source="execution-orchestrator",
        severity="info",
        occurred_at=opened_at + timedelta(minutes=21),
        summary="Close completed for SOLUSDT",
        payload={"trade_id": "exec-read-3"},
        tags=["execution", "completed"],
    )

    snapshot = ExecutionReadService(ledger_service, audit_service).snapshot(limit_incidents=2)

    counts = {item.status: item.count for item in snapshot.status_counts}
    assert counts["recovery_pending"] == 1
    assert counts["failed"] == 1
    assert counts["closed"] == 1
    assert [item.trade_id for item in snapshot.recovery_queue] == ["exec-read-2", "exec-read-1"]
    assert snapshot.recovery_queue[0].latest_event_type == "execution.leg.perp.failed"
    assert snapshot.recovery_queue[1].latest_event_summary == "Recovery required for BTCUSDT"
    assert [item.event_type for item in snapshot.recent_incidents] == [
        "execution.leg.perp.failed",
        "execution.recovery.required",
    ]

