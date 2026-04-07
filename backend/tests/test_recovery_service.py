from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.execution import ExecutionOrchestrator
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.reconciliation import ExchangeOrderReport, ExchangeOrderReportStore, ReconciliationService


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def build_services():
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recovery-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recovery-audit")))
    report_store = ExchangeOrderReportStore(make_path("recovery-reports"))
    reconciliation_service = ReconciliationService(report_store, ledger_service, audit_service)
    return ledger_service, audit_service, report_store, reconciliation_service


def test_recovery_service_builds_actionable_plan_for_paper_failed_open() -> None:
    from app.recovery import RecoveryService

    opened_at = datetime(2026, 4, 7, 10, 0, tzinfo=timezone.utc)
    ledger_service, audit_service, _, reconciliation_service = build_services()

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="paper-recovery-1",
                mode="paper",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="failed",
                opened_at=opened_at,
                spot_notional=10000,
                perp_notional=9950,
                net_exposure=50,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.intent.received",
        source="execution-orchestrator",
        occurred_at=opened_at,
        summary="open hedge intent",
        payload={"trade_id": "paper-recovery-1", "action": "open_hedge"},
        tags=["execution", "paper"],
    )
    audit_service.record_event(
        event_type="execution.recovery.required",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=2),
        summary="manual recovery required",
        severity="critical",
        payload={"trade_id": "paper-recovery-1", "status": "failed"},
        tags=["execution", "recovery", "paper"],
    )

    plans = RecoveryService(ledger_service, audit_service, reconciliation_service).list_plans()

    assert len(plans) == 1
    plan = plans[0]
    assert plan.trade_id == "paper-recovery-1"
    assert plan.recommended_action == "resume_open"
    assert plan.auto_executable is True
    assert "paper trade can use deterministic recovery flow" in plan.reasons


def test_recovery_service_requires_manual_review_when_live_trade_has_missing_reports() -> None:
    from app.recovery import RecoveryService

    opened_at = datetime(2026, 4, 7, 11, 0, tzinfo=timezone.utc)
    ledger_service, audit_service, report_store, reconciliation_service = build_services()

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="live-recovery-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="recovery_pending",
                opened_at=opened_at,
                spot_notional=15000,
                perp_notional=14980,
                net_exposure=20,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.intent.received",
        source="execution-orchestrator",
        occurred_at=opened_at,
        summary="close hedge intent",
        payload={"trade_id": "live-recovery-1", "action": "close_hedge"},
        tags=["execution", "live"],
    )
    audit_service.record_event(
        event_type="execution.live.close.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=1),
        summary="spot close filled",
        payload={"trade_id": "live-recovery-1", "orderId": "close-spot-1"},
        tags=["execution", "live", "spot"],
    )
    audit_service.record_event(
        event_type="execution.live.close.perp.partial",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=2),
        summary="perp close partial",
        payload={"trade_id": "live-recovery-1", "orderId": "close-perp-1"},
        tags=["execution", "live", "perp"],
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="close-spot-1",
                trade_id="live-recovery-1",
                symbol="BTCUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=0.2,
                cum_quote_qty=15000,
                updated_at=opened_at + timedelta(minutes=1),
            )
        ],
        mode="replace",
    )

    plans = RecoveryService(ledger_service, audit_service, reconciliation_service).list_plans()

    assert len(plans) == 1
    plan = plans[0]
    assert plan.recommended_action == "manual_review"
    assert plan.auto_executable is False
    assert plan.missing_order_ids == ["close-perp-1"]
    assert "missing exchange reports require operator review" in plan.reasons


def test_recovery_service_executes_only_actionable_plans() -> None:
    from app.recovery import RecoveryService

    opened_at = datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc)
    ledger_service, audit_service, _, reconciliation_service = build_services()

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="recover-auto-1",
                mode="paper",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="failed",
                opened_at=opened_at,
                spot_notional=10000,
                perp_notional=9950,
            ),
            TradeLedgerRecord(
                trade_id="recover-auto-2",
                mode="paper",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="failed",
                opened_at=opened_at + timedelta(minutes=1),
                spot_notional=15000,
                perp_notional=14980,
            ),
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.intent.received",
        source="execution-orchestrator",
        occurred_at=opened_at,
        summary="open hedge intent",
        payload={"trade_id": "recover-auto-1", "action": "open_hedge"},
        tags=["execution"],
    )
    audit_service.record_event(
        event_type="execution.intent.received",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=1),
        summary="close hedge intent",
        payload={"trade_id": "recover-auto-2", "action": "close_hedge"},
        tags=["execution"],
    )

    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    summary = RecoveryService(ledger_service, audit_service, reconciliation_service).execute_actionable_plans(
        orchestrator=orchestrator,
        limit=1,
    )

    assert summary.attempted_count == 1
    assert summary.executed_count == 1
    assert summary.skipped_count == 0
    assert len(summary.results) == 1
    assert summary.results[0].trade_id == "recover-auto-1"
    assert summary.results[0].status == "hedged"
