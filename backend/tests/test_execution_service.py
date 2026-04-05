from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.execution import ExecutionIntentRequest, ExecutionOrchestrator
from app.ledger import TradeLedgerService, TradeLedgerStore


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def build_service() -> tuple[ExecutionOrchestrator, TradeLedgerService, AuditEventService]:
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit")))
    return ExecutionOrchestrator(ledger_service, audit_service), ledger_service, audit_service


def test_execution_service_opens_paper_hedge_and_records_events() -> None:
    orchestrator, ledger_service, audit_service = build_service()

    result = orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-open-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            action="open_hedge",
            spot_notional=15000,
            perp_notional=14980,
        )
    )

    assert result.status == "hedged"
    record = ledger_service.get_record("exec-open-1")
    assert record is not None
    assert record.status == "hedged"
    events = audit_service.list_events(source="execution-orchestrator")
    assert [event.event_type for event in events] == [
        "execution.intent.received",
        "execution.leg.spot.filled",
        "execution.leg.perp.filled",
        "execution.completed",
    ]


def test_execution_service_marks_failed_when_perp_leg_simulation_breaks() -> None:
    orchestrator, ledger_service, audit_service = build_service()

    result = orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-fail-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="ETHUSDT",
            action="open_hedge",
            spot_notional=10000,
            perp_notional=9950,
            simulate_perp_leg_failure=True,
        )
    )

    assert result.status == "failed"
    record = ledger_service.get_record("exec-fail-1")
    assert record is not None
    assert record.status == "failed"
    events = audit_service.list_events(source="execution-orchestrator")
    assert [event.event_type for event in events][-2:] == [
        "execution.leg.perp.failed",
        "execution.recovery.required",
    ]


def test_execution_service_closes_existing_trade() -> None:
    orchestrator, ledger_service, _ = build_service()
    orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-close-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="SOLUSDT",
            action="open_hedge",
            spot_notional=5000,
            perp_notional=4990,
        )
    )

    result = orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-close-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="SOLUSDT",
            action="close_hedge",
            realized_pnl=18.5,
            notes="take profit",
        )
    )

    assert result.status == "closed"
    record = ledger_service.get_record("exec-close-1")
    assert record is not None
    assert record.status == "closed"
    assert record.realized_pnl == 18.5
    assert record.closed_at is not None
