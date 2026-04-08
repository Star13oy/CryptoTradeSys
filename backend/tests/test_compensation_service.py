from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.compensation import CompensationPlan, CompensationService
from app.execution import ExecutionResult
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.reconciliation import ExchangeOrderReport, ExchangeOrderReportStore


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_compensation_service_prioritizes_missing_exchange_reports() -> None:
    opened_at = datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("comp-ledger-missing")))
    audit_service = AuditEventService(AuditEventStore(make_path("comp-audit-missing")))
    report_store = ExchangeOrderReportStore(make_path("comp-reports-missing"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="comp-missing-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                spot_notional=15000,
                perp_notional=14980,
                net_exposure=20,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="spot filled",
        payload={"trade_id": "comp-missing-1", "orderId": "spot-100"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="perp filled",
        payload={"trade_id": "comp-missing-1", "orderId": "perp-100"},
        tags=["execution", "live", "perp", "filled"],
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="spot-100",
                trade_id="comp-missing-1",
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

    plans = CompensationService(
        ledger_service=ledger_service,
        audit_service=audit_service,
        report_store=report_store,
    ).list_plans(only_actionable=True)

    assert len(plans) == 1
    plan = plans[0]
    assert plan.trade_id == "comp-missing-1"
    assert plan.recommended_action == "sync_exchange_reports"
    assert plan.priority == "critical"


def test_compensation_service_prefers_recovery_action_for_recovery_pending_trade() -> None:
    opened_at = datetime(2026, 4, 8, 11, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("comp-ledger-recovery")))
    audit_service = AuditEventService(AuditEventStore(make_path("comp-audit-recovery")))
    report_store = ExchangeOrderReportStore(make_path("comp-reports-recovery"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="comp-recovery-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="recovery_pending",
                opened_at=opened_at,
                spot_notional=10000,
                perp_notional=9960,
                net_exposure=40,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.intent.received",
        source="execution-orchestrator",
        occurred_at=opened_at,
        summary="open requested",
        payload={"trade_id": "comp-recovery-1", "action": "open_hedge"},
        tags=["execution", "live", "open_hedge"],
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="spot filled",
        payload={"trade_id": "comp-recovery-1", "orderId": "spot-200"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.partial",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="perp partial",
        payload={"trade_id": "comp-recovery-1", "orderId": "perp-200"},
        tags=["execution", "live", "perp", "partial"],
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="spot-200",
                trade_id="comp-recovery-1",
                symbol="ETHUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=4,
                cum_quote_qty=10000,
                updated_at=opened_at + timedelta(minutes=1),
            ),
            ExchangeOrderReport(
                venue="binance",
                order_id="perp-200",
                trade_id="comp-recovery-1",
                symbol="ETHUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=4,
                cum_quote_qty=9960,
                updated_at=opened_at + timedelta(minutes=1, seconds=1),
            ),
        ],
        mode="replace",
    )

    plans = CompensationService(
        ledger_service=ledger_service,
        audit_service=audit_service,
        report_store=report_store,
    ).list_plans(only_actionable=True)

    assert len(plans) == 1
    plan = plans[0]
    assert plan.trade_id == "comp-recovery-1"
    assert plan.recommended_action == "resume_open"
    assert plan.priority == "critical"


def test_compensation_service_returns_rebalance_plan_for_exposure_drift() -> None:
    opened_at = datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("comp-ledger-rebalance")))
    audit_service = AuditEventService(AuditEventStore(make_path("comp-audit-rebalance")))
    report_store = ExchangeOrderReportStore(make_path("comp-reports-rebalance"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="comp-rebalance-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="SOLUSDT",
                status="hedged",
                opened_at=opened_at,
                spot_notional=5000,
                perp_notional=4900,
                net_exposure=100,
            )
        ],
        mode="replace",
    )

    plans = CompensationService(
        ledger_service=ledger_service,
        audit_service=audit_service,
        report_store=report_store,
    ).list_plans(only_actionable=True)

    assert len(plans) == 1
    plan = plans[0]
    assert plan.trade_id == "comp-rebalance-1"
    assert plan.recommended_action == "rebalance_hedge"
    assert plan.priority == "medium"


def test_compensation_service_execute_safe_actions_delegates_recovery_and_skips_unsafe_actions() -> None:
    class StubReconciliationService:
        def __init__(self) -> None:
            self.synced_trade_ids: list[str] = []

        def sync_reports_for_trade(self, trade_id: str):
            self.synced_trade_ids.append(trade_id)
            return [{"order_id": "perp-1"}]

    class StubRecoveryService:
        def __init__(self) -> None:
            self.received_trade_ids: set[str] | None = None
            self.received_orchestrator = None

        def execute_actionable_plans(self, *, orchestrator, symbol=None, limit=None, trade_ids=None):
            self.received_orchestrator = orchestrator
            self.received_trade_ids = trade_ids
            return {
                "generated_at": "2026-04-08T13:00:00Z",
                "attempted_count": 1,
                "executed_count": 1,
                "skipped_count": 0,
                "results": [
                    ExecutionResult(
                        trade_id="comp-exec-recovery-1",
                        action="open_hedge",
                        mode="live",
                        symbol="ETHUSDT",
                        status="hedged",
                        ledger_record=TradeLedgerRecord(
                            trade_id="comp-exec-recovery-1",
                            mode="live",
                            strategy_id="funding-arb",
                            symbol="ETHUSDT",
                            status="hedged",
                            opened_at=datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc),
                        ),
                        events=[],
                        executed_at=datetime(2026, 4, 8, 13, 0, tzinfo=timezone.utc),
                    )
                ],
                "skipped": [],
            }

    reconciliation_service = StubReconciliationService()
    recovery_service = StubRecoveryService()
    service = CompensationService(
        reconciliation_service=reconciliation_service,
        recovery_service=recovery_service,
    )
    service.list_plans = lambda **kwargs: [  # type: ignore[method-assign]
        CompensationPlan(
            trade_id="comp-exec-sync-1",
            symbol="BTCUSDT",
            mode="live",
            local_status="hedged",
            recommended_action="sync_exchange_reports",
            priority="critical",
            actionable=True,
            reason="missing exchange reports",
            details={"missing_order_ids": ["perp-1"]},
        ),
        CompensationPlan(
            trade_id="comp-exec-recovery-1",
            symbol="ETHUSDT",
            mode="live",
            local_status="recovery_pending",
            recommended_action="resume_open",
            priority="critical",
            actionable=True,
            reason="recovery plan is actionable",
            details={},
        ),
        CompensationPlan(
            trade_id="comp-exec-hedge-1",
            symbol="SOLUSDT",
            mode="live",
            local_status="hedged",
            recommended_action="rebalance_hedge",
            priority="medium",
            actionable=True,
            reason="net exposure drift exceeds tolerance",
            details={},
        ),
    ]

    summary = service.execute_safe_actions(orchestrator=object())

    assert summary.attempted_count == 3
    assert summary.executed_count == 2
    assert summary.skipped_count == 1
    assert summary.failed_count == 0
    assert reconciliation_service.synced_trade_ids == ["comp-exec-sync-1"]
    assert recovery_service.received_trade_ids == {"comp-exec-recovery-1"}
    outcome_by_trade = {item.trade_id: item.outcome for item in summary.results}
    assert outcome_by_trade["comp-exec-sync-1"] == "executed"
    assert outcome_by_trade["comp-exec-recovery-1"] == "executed"
    assert outcome_by_trade["comp-exec-hedge-1"] == "skipped"


def test_compensation_service_execute_safe_actions_marks_failures() -> None:
    class StubReconciliationService:
        def sync_reports_for_trade(self, trade_id: str):
            raise ValueError(f"cannot sync {trade_id}")

    service = CompensationService(
        reconciliation_service=StubReconciliationService(),
    )
    service.list_plans = lambda **kwargs: [  # type: ignore[method-assign]
        CompensationPlan(
            trade_id="comp-exec-fail-1",
            symbol="BTCUSDT",
            mode="live",
            local_status="hedged",
            recommended_action="sync_exchange_reports",
            priority="critical",
            actionable=True,
            reason="missing exchange reports",
            details={},
        ),
    ]

    summary = service.execute_safe_actions(orchestrator=object())

    assert summary.attempted_count == 1
    assert summary.executed_count == 0
    assert summary.skipped_count == 0
    assert summary.failed_count == 1
    assert summary.results[0].outcome == "failed"
    assert "cannot sync comp-exec-fail-1" in summary.results[0].reason


def test_compensation_service_executes_rebalance_when_quantity_can_be_inferred() -> None:
    opened_at = datetime(2026, 4, 8, 15, 0, tzinfo=timezone.utc)
    report_store = ExchangeOrderReportStore(make_path("comp-reports-rebalance-execute"))

    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="perp-300",
                trade_id="comp-exec-hedge-2",
                symbol="BTCUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=2,
                cum_quote_qty=150000,
                updated_at=opened_at,
            )
        ],
        mode="replace",
    )

    class StubOrchestrator:
        def __init__(self) -> None:
            self.received = None

        def rebalance_hedge(self, *, trade_id: str, perp_notional_delta: float, perp_quantity: float, notes: str | None = None):
            self.received = {
                "trade_id": trade_id,
                "perp_notional_delta": perp_notional_delta,
                "perp_quantity": perp_quantity,
                "notes": notes,
            }
            return ExecutionResult(
                trade_id=trade_id,
                action="rebalance_hedge",
                mode="live",
                symbol="BTCUSDT",
                status="hedged",
                ledger_record=TradeLedgerRecord(
                    trade_id=trade_id,
                    mode="live",
                    strategy_id="funding-arb",
                    symbol="BTCUSDT",
                    status="hedged",
                    opened_at=opened_at,
                    spot_notional=15000,
                    perp_notional=15000,
                    net_exposure=0,
                ),
                events=[],
                executed_at=opened_at,
            )

    service = CompensationService(report_store=report_store)
    service.list_plans = lambda **kwargs: [  # type: ignore[method-assign]
        CompensationPlan(
            trade_id="comp-exec-hedge-2",
            symbol="BTCUSDT",
            mode="live",
            local_status="hedged",
            recommended_action="rebalance_hedge",
            priority="medium",
            actionable=True,
            reason="net exposure drift exceeds tolerance",
            details={"suggested_perp_notional_delta": 150},
        ),
    ]

    orchestrator = StubOrchestrator()
    summary = service.execute_safe_actions(orchestrator=orchestrator)

    assert orchestrator.received == {
        "trade_id": "comp-exec-hedge-2",
        "perp_notional_delta": 150,
        "perp_quantity": 0.002,
        "notes": "auto compensation rebalance",
    }
    assert summary.executed_count == 1
    assert summary.skipped_count == 0
    assert summary.failed_count == 0
    assert summary.results[0].trade_id == "comp-exec-hedge-2"
    assert summary.results[0].outcome == "executed"
    assert summary.results[0].action == "rebalance_hedge"
