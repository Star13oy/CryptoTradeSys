from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.hedge import HedgeManagerService
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.reconciliation import ExchangeOrderReport, ExchangeOrderReportStore


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_hedge_manager_service_classifies_exposure_and_recovery_states() -> None:
    opened_at = datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-healthy-1",
                mode="paper",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=10,
                spot_notional=20000,
                perp_notional=19990,
            ),
            TradeLedgerRecord(
                trade_id="hedge-rebalance-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="hedged",
                opened_at=opened_at + timedelta(minutes=5),
                net_exposure=160,
                spot_notional=10000,
                perp_notional=9840,
            ),
            TradeLedgerRecord(
                trade_id="hedge-recovery-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="SOLUSDT",
                status="recovery_pending",
                opened_at=opened_at + timedelta(minutes=10),
                net_exposure=120,
                spot_notional=5000,
                perp_notional=4880,
            ),
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.recovery.required",
        source="execution-orchestrator",
        severity="warning",
        occurred_at=opened_at + timedelta(minutes=11),
        summary="Recovery required after live open issue on SOLUSDT",
        payload={"trade_id": "hedge-recovery-1"},
        tags=["execution", "recovery", "live"],
    )

    overview = HedgeManagerService(ledger_service, audit_service).overview(exposure_limit_bps=50)

    assert overview.active_trade_count == 3
    assert overview.rebalance_required_count == 1
    assert overview.recovery_required_count == 1
    items = {item.trade_id: item for item in overview.items}
    assert items["hedge-healthy-1"].health == "healthy"
    assert items["hedge-healthy-1"].exposure_bps == 5.0
    assert items["hedge-rebalance-1"].health == "rebalance_required"
    assert items["hedge-rebalance-1"].exposure_bps == 160.0
    assert items["hedge-recovery-1"].health == "recovery_required"
    assert items["hedge-recovery-1"].latest_event_type == "execution.recovery.required"


def test_hedge_manager_service_builds_rebalance_plan() -> None:
    opened_at = datetime(2026, 4, 5, 13, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-plan-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-plan-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-plan-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=120,
                spot_notional=15000,
                perp_notional=14880,
            ),
            TradeLedgerRecord(
                trade_id="hedge-plan-2",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="recovery_pending",
                opened_at=opened_at + timedelta(minutes=2),
                net_exposure=60,
                spot_notional=8000,
                perp_notional=7940,
            ),
        ],
        mode="replace",
    )

    service = HedgeManagerService(ledger_service, audit_service)
    rebalance_plan = service.build_rebalance_plan("hedge-plan-1", exposure_limit_bps=50)
    recovery_plan = service.build_rebalance_plan("hedge-plan-2", exposure_limit_bps=50)

    assert rebalance_plan.recommended_action == "increase_perp_hedge"
    assert rebalance_plan.suggested_perp_notional_delta == 120
    assert rebalance_plan.estimated_post_rebalance_exposure_bps == 0.0
    assert recovery_plan.recommended_action == "recover_trade"
    assert "recovery" in recovery_plan.notes.lower()


def test_hedge_manager_service_executes_auto_rebalance_actions() -> None:
    opened_at = datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-exec-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-exec-audit")))
    report_store = ExchangeOrderReportStore(make_path("hedge-exec-reports"))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-exec-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=120,
                spot_notional=15000,
                perp_notional=14880,
            ),
            TradeLedgerRecord(
                trade_id="hedge-exec-2",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="hedged",
                opened_at=opened_at + timedelta(minutes=1),
                net_exposure=80,
                spot_notional=10000,
                perp_notional=9920,
            ),
        ],
        mode="replace",
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="perp-exec-1",
                trade_id="hedge-exec-1",
                symbol="BTCUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=2.0,
                cum_quote_qty=150000.0,
                updated_at=opened_at + timedelta(seconds=5),
            )
        ],
        mode="replace",
    )

    class StubOrchestrator:
        def __init__(self) -> None:
            self.calls: list[dict[str, float | str | None]] = []

        def rebalance_hedge(self, *, trade_id: str, perp_notional_delta: float, perp_quantity: float, notes: str | None = None):
            self.calls.append(
                {
                    "trade_id": trade_id,
                    "perp_notional_delta": perp_notional_delta,
                    "perp_quantity": perp_quantity,
                    "notes": notes,
                }
            )
            return None

    orchestrator = StubOrchestrator()
    summary = HedgeManagerService(
        ledger_service,
        audit_service,
        report_store=report_store,
    ).execute_auto_rebalance_actions(
        orchestrator=orchestrator,
        exposure_limit_bps=50.0,
    )

    assert summary.attempted_count == 2
    assert summary.executed_count == 1
    assert summary.skipped_count == 1
    assert summary.failed_count == 0
    assert orchestrator.calls == [
        {
            "trade_id": "hedge-exec-1",
            "perp_notional_delta": 120.0,
            "perp_quantity": 0.0016,
            "notes": "auto hedge rebalance",
        }
    ]
    outcomes = {item.trade_id: item.outcome for item in summary.results}
    assert outcomes["hedge-exec-1"] == "executed"
    assert outcomes["hedge-exec-2"] == "skipped"


def test_hedge_manager_service_executes_single_rebalance_plan_with_inferred_quantity() -> None:
    opened_at = datetime(2026, 4, 8, 19, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-single-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-single-audit")))
    report_store = ExchangeOrderReportStore(make_path("hedge-single-reports"))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-single-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=120,
                spot_notional=15000,
                perp_notional=14880,
            )
        ],
        mode="replace",
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="perp-single-1",
                trade_id="hedge-single-1",
                symbol="BTCUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=1.5,
                cum_quote_qty=112500.0,
                updated_at=opened_at + timedelta(seconds=3),
            )
        ],
        mode="replace",
    )

    class StubOrchestrator:
        def __init__(self) -> None:
            self.calls: list[dict[str, float | str | None]] = []

        def rebalance_hedge(self, *, trade_id: str, perp_notional_delta: float, perp_quantity: float, notes: str | None = None):
            self.calls.append(
                {
                    "trade_id": trade_id,
                    "perp_notional_delta": perp_notional_delta,
                    "perp_quantity": perp_quantity,
                    "notes": notes,
                }
            )
            return {"status": "ok"}

    orchestrator = StubOrchestrator()
    result = HedgeManagerService(
        ledger_service,
        audit_service,
        report_store=report_store,
    ).execute_rebalance_plan(
        "hedge-single-1",
        orchestrator=orchestrator,
        notes="single rebalance",
    )

    assert result == {"status": "ok"}
    assert orchestrator.calls == [
        {
            "trade_id": "hedge-single-1",
            "perp_notional_delta": 120.0,
            "perp_quantity": 0.0016,
            "notes": "single rebalance",
        }
    ]


def test_hedge_manager_service_rejects_single_rebalance_when_reference_price_missing() -> None:
    opened_at = datetime(2026, 4, 8, 19, 30, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-single-missing-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-single-missing-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-single-missing-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=90,
                spot_notional=10000,
                perp_notional=9910,
            )
        ],
        mode="replace",
    )

    class StubOrchestrator:
        def rebalance_hedge(self, **_: object) -> None:
            raise AssertionError("rebalance_hedge should not be called when reference price is missing")

    service = HedgeManagerService(
        ledger_service,
        audit_service,
        report_store=ExchangeOrderReportStore(make_path("hedge-single-missing-reports")),
    )

    try:
        service.execute_rebalance_plan("hedge-single-missing-1", orchestrator=StubOrchestrator())
    except ValueError as exc:
        assert "cannot infer perp reference price" in str(exc)
    else:
        raise AssertionError("expected ValueError when reference price is missing")
