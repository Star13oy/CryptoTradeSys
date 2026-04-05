from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.reconciliation import (
    ExchangeOrderReport,
    ExchangeOrderReportStore,
    ReconciliationService,
)


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_reconciliation_service_flags_missing_reports_and_status_mismatch() -> None:
    opened_at = datetime(2026, 4, 5, 14, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recon-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recon-audit")))
    report_store = ExchangeOrderReportStore(make_path("recon-reports"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="recon-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=20,
                spot_notional=15000,
                perp_notional=14980,
            ),
            TradeLedgerRecord(
                trade_id="recon-2",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="recovery_pending",
                opened_at=opened_at + timedelta(minutes=3),
                net_exposure=80,
                spot_notional=10000,
                perp_notional=9920,
            ),
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="Live spot leg filled",
        payload={"trade_id": "recon-1", "orderId": "spot-1"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="Live perp leg filled",
        payload={"trade_id": "recon-1", "orderId": "perp-1"},
        tags=["execution", "live", "perp", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=3, seconds=5),
        summary="Live spot leg filled",
        payload={"trade_id": "recon-2", "orderId": "spot-2"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.partial",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=3, seconds=6),
        summary="Live perp leg partial",
        payload={"trade_id": "recon-2", "orderId": "perp-2"},
        tags=["execution", "live", "perp", "partial"],
    )

    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="spot-1",
                symbol="BTCUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=0.2,
                cum_quote_qty=15000,
                updated_at=opened_at + timedelta(minutes=1),
            ),
            ExchangeOrderReport(
                venue="binance",
                order_id="spot-2",
                symbol="ETHUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=4,
                cum_quote_qty=10000,
                updated_at=opened_at + timedelta(minutes=4),
            ),
            ExchangeOrderReport(
                venue="binance",
                order_id="perp-2",
                symbol="ETHUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=4,
                cum_quote_qty=9920,
                updated_at=opened_at + timedelta(minutes=4, seconds=10),
            ),
        ],
        mode="replace",
    )

    summary = ReconciliationService(report_store, ledger_service, audit_service).build_summary()

    assert summary.compared_trade_count == 2
    assert summary.matched_trade_count == 0
    assert summary.missing_exchange_report_count == 1
    assert summary.status_mismatch_count == 1
    issues = {issue.trade_id: issue for issue in summary.issues}
    assert issues["recon-1"].issue_type == "missing_exchange_report"
    assert "perp-1" in issues["recon-1"].missing_order_ids
    assert issues["recon-2"].issue_type == "status_mismatch"
    assert issues["recon-2"].suggested_action == "resume_open"

