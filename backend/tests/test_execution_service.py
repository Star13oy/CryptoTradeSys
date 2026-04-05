from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.execution import (
    ExecutionIntentRequest,
    ExecutionLegReport,
    ExecutionOrchestrator,
    ExecutionRecoveryRequest,
)
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


def test_execution_service_live_mode_uses_adapter_reports() -> None:
    class StubLiveAdapter:
        def open_hedge(self, request: ExecutionIntentRequest) -> list[ExecutionLegReport]:
            return [
                ExecutionLegReport(leg="spot", status="filled", payload={"orderId": "spot-1"}),
                ExecutionLegReport(leg="perp", status="filled", payload={"orderId": "perp-1"}),
            ]

        def close_hedge(self, request: ExecutionIntentRequest, existing) -> list[ExecutionLegReport]:
            raise NotImplementedError

    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-live")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-live")))
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=StubLiveAdapter(),
        live_execution_enabled=True,
        live_symbol_allowlist={"BTCUSDT"},
    )

    result = orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-live-1",
            mode="live",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            action="open_hedge",
            spot_notional=15000,
            perp_notional=14980,
            perp_quantity=0.25,
        )
    )

    assert result.status == "hedged"
    events = audit_service.list_events(source="execution-orchestrator")
    assert [event.event_type for event in events][-3:] == [
        "execution.live.spot.filled",
        "execution.live.perp.filled",
        "execution.completed",
    ]


def test_execution_service_live_partial_fill_enters_recovery_pending() -> None:
    class PartialLiveAdapter:
        def open_hedge(self, request: ExecutionIntentRequest) -> list[ExecutionLegReport]:
            return [
                ExecutionLegReport(leg="spot", status="filled", payload={"orderId": "spot-1"}),
                ExecutionLegReport(leg="perp", status="partial", payload={"orderId": "perp-1"}),
            ]

        def close_hedge(self, request: ExecutionIntentRequest, existing) -> list[ExecutionLegReport]:
            raise NotImplementedError

    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-partial")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-partial")))
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=PartialLiveAdapter(),
        live_execution_enabled=True,
        live_symbol_allowlist={"BTCUSDT"},
    )

    result = orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-live-partial-1",
            mode="live",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            action="open_hedge",
            spot_notional=15000,
            perp_notional=14980,
            perp_quantity=0.25,
        )
    )

    assert result.status == "recovery_pending"
    record = ledger_service.get_record("exec-live-partial-1")
    assert record is not None
    assert record.status == "recovery_pending"
    events = audit_service.list_events(source="execution-orchestrator")
    assert [event.event_type for event in events][-2:] == [
        "execution.live.perp.partial",
        "execution.recovery.required",
    ]


def test_execution_service_replays_idempotent_open_without_duplicate_fill_flow() -> None:
    orchestrator, ledger_service, audit_service = build_service()
    request = ExecutionIntentRequest(
        trade_id="exec-idem-1",
        mode="paper",
        strategy_id="funding-arb",
        symbol="BTCUSDT",
        action="open_hedge",
        spot_notional=15000,
        perp_notional=14980,
    )

    first = orchestrator.execute(request)
    second = orchestrator.execute(request)

    assert first.status == "hedged"
    assert second.status == "hedged"
    record = ledger_service.get_record("exec-idem-1")
    assert record is not None
    assert record.status == "hedged"
    events = audit_service.list_events(source="execution-orchestrator")
    assert [event.event_type for event in events][-1:] == ["execution.idempotent.replay"]


def test_execution_service_recovers_failed_open_into_hedged() -> None:
    orchestrator, ledger_service, audit_service = build_service()
    orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="exec-recover-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="ETHUSDT",
            action="open_hedge",
            spot_notional=10000,
            perp_notional=9950,
            simulate_perp_leg_failure=True,
        )
    )

    result = orchestrator.recover(
        ExecutionRecoveryRequest(
            trade_id="exec-recover-1",
            action="resume_open",
            notes="resume failed perp leg",
        )
    )

    assert result.status == "hedged"
    record = ledger_service.get_record("exec-recover-1")
    assert record is not None
    assert record.status == "hedged"
    events = audit_service.list_events(source="execution-orchestrator")
    assert [event.event_type for event in events][-3:] == [
        "execution.recovery.started",
        "execution.recovery.perp.filled",
        "execution.recovery.completed",
    ]


def test_execution_service_blocks_live_symbol_outside_allowlist() -> None:
    class StubLiveAdapter:
        def open_hedge(self, request: ExecutionIntentRequest) -> list[ExecutionLegReport]:
            return [ExecutionLegReport(leg="spot", status="filled", payload={})]

        def close_hedge(self, request: ExecutionIntentRequest, existing) -> list[ExecutionLegReport]:
            raise NotImplementedError

    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-guard-symbol")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-guard-symbol")))
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=StubLiveAdapter(),
        live_symbol_allowlist={"BTCUSDT"},
        live_execution_enabled=True,
    )

    try:
        orchestrator.execute(
            ExecutionIntentRequest(
                trade_id="exec-guard-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                action="open_hedge",
                spot_notional=10000,
                perp_notional=9950,
                perp_quantity=4,
            )
        )
    except ValueError as exc:
        assert "not in live execution allowlist" in str(exc)
    else:
        raise AssertionError("expected allowlist guard to block live execution")


def test_execution_service_blocks_live_notional_above_limit() -> None:
    class StubLiveAdapter:
        def open_hedge(self, request: ExecutionIntentRequest) -> list[ExecutionLegReport]:
            return [ExecutionLegReport(leg="spot", status="filled", payload={})]

        def close_hedge(self, request: ExecutionIntentRequest, existing) -> list[ExecutionLegReport]:
            raise NotImplementedError

    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-guard-notional")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-guard-notional")))
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=StubLiveAdapter(),
        live_symbol_allowlist={"BTCUSDT"},
        live_execution_enabled=True,
        max_live_notional=12000,
    )

    try:
        orchestrator.execute(
            ExecutionIntentRequest(
                trade_id="exec-guard-2",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                action="open_hedge",
                spot_notional=15000,
                perp_notional=14980,
                perp_quantity=0.25,
            )
        )
    except ValueError as exc:
        assert "exceeds configured live notional limit" in str(exc)
    else:
        raise AssertionError("expected notional guard to block live execution")
