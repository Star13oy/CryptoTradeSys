from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventService, AuditEventStore
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.reconciliation import (
    ExchangeOrderReport,
    ExchangeOrderReportListResponse,
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


def test_reconciliation_service_lists_candidates_from_ledger_and_audit_context() -> None:
    opened_at = datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recon-candidates-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recon-candidates-audit")))
    report_store = ExchangeOrderReportStore(make_path("recon-candidates-reports"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="candidate-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=10,
                spot_notional=15000,
                perp_notional=14990,
            ),
            TradeLedgerRecord(
                trade_id="candidate-2",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="recovery_pending",
                opened_at=opened_at + timedelta(minutes=1),
                net_exposure=40,
                spot_notional=10000,
                perp_notional=9960,
            ),
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="BTC spot filled",
        payload={"trade_id": "candidate-1", "orderId": "btc-spot-1"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="BTC perp filled",
        payload={"trade_id": "candidate-1", "orderId": "btc-perp-1"},
        tags=["execution", "live", "perp", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=1, seconds=5),
        summary="ETH spot filled",
        payload={"trade_id": "candidate-2", "orderId": "eth-spot-1"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.partial",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=1, seconds=6),
        summary="ETH perp partial",
        payload={"trade_id": "candidate-2", "orderId": "eth-perp-1"},
        tags=["execution", "live", "perp", "partial"],
    )

    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="btc-spot-1",
                symbol="BTCUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=0.2,
                cum_quote_qty=15000,
                updated_at=opened_at + timedelta(minutes=1),
            ),
            ExchangeOrderReport(
                venue="binance",
                order_id="eth-spot-1",
                symbol="ETHUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=4,
                cum_quote_qty=10000,
                updated_at=opened_at + timedelta(minutes=2),
            ),
            ExchangeOrderReport(
                venue="binance",
                order_id="eth-perp-1",
                symbol="ETHUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=4,
                cum_quote_qty=9960,
                updated_at=opened_at + timedelta(minutes=2, seconds=10),
            ),
        ],
        mode="replace",
    )

    candidates = ReconciliationService(report_store, ledger_service, audit_service).list_candidates(only_attention=True)

    assert len(candidates) == 2
    latest = {candidate.trade_id: candidate for candidate in candidates}
    assert latest["candidate-1"].needs_attention is True
    assert latest["candidate-1"].missing_order_ids == ["btc-perp-1"]
    assert latest["candidate-1"].reported_order_ids == ["btc-spot-1"]
    assert latest["candidate-2"].needs_attention is True
    assert latest["candidate-2"].missing_order_ids == []
    assert latest["candidate-2"].suggested_action == "resume_open"


def test_reconciliation_service_syncs_reports_from_exchange_client() -> None:
    opened_at = datetime(2026, 4, 5, 18, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recon-sync-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recon-sync-audit")))
    report_store = ExchangeOrderReportStore(make_path("recon-sync-reports"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="sync-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=10,
                spot_notional=15000,
                perp_notional=14990,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="spot filled",
        payload={"trade_id": "sync-1", "orderId": "1001", "clientOrderId": "sync-1-spot-open"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.partial",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="perp partial",
        payload={"trade_id": "sync-1", "orderId": "2001", "clientOrderId": "sync-1-perp-open"},
        tags=["execution", "live", "perp", "partial"],
    )

    class StubTradingClient:
        def get_spot_order(self, **kwargs):
            assert kwargs["order_id"] == "1001"
            return {
                "symbol": "BTCUSDT",
                "orderId": "1001",
                "clientOrderId": "sync-1-spot-open",
                "status": "FILLED",
                "executedQty": "0.2",
                "cummulativeQuoteQty": "15000",
                "updateTime": 1775344800000,
            }

        def get_perp_order(self, **kwargs):
            assert kwargs["order_id"] == "2001"
            return {
                "symbol": "BTCUSDT",
                "orderId": "2001",
                "clientOrderId": "sync-1-perp-open",
                "status": "PARTIALLY_FILLED",
                "executedQty": "0.18",
                "cumQuote": "13490",
                "updateTime": 1775344801000,
            }

    service = ReconciliationService(report_store, ledger_service, audit_service)

    synced = service.sync_reports_for_trade("sync-1", trading_client=StubTradingClient())

    assert len(synced) == 2
    reports = {report.order_id: report for report in report_store.list()}
    assert reports["1001"].leg == "spot"
    assert reports["1001"].status == "FILLED"
    assert reports["1001"].trade_id == "sync-1"
    assert reports["2001"].leg == "perp"
    assert reports["2001"].status == "PARTIALLY_FILLED"
    assert reports["2001"].trade_id == "sync-1"


def test_reconciliation_service_syncs_attention_candidates_with_limit() -> None:
    opened_at = datetime(2026, 4, 5, 19, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recon-sync-many-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recon-sync-many-audit")))
    report_store = ExchangeOrderReportStore(make_path("recon-sync-many-reports"))

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="sync-many-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                spot_notional=15000,
                perp_notional=14990,
            ),
            TradeLedgerRecord(
                trade_id="sync-many-2",
                mode="live",
                strategy_id="funding-arb",
                symbol="ETHUSDT",
                status="recovery_pending",
                opened_at=opened_at + timedelta(minutes=1),
                spot_notional=10000,
                perp_notional=9960,
            ),
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="btc spot",
        payload={"trade_id": "sync-many-1", "orderId": "3001", "clientOrderId": "sync-many-1-spot-open"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="btc perp",
        payload={"trade_id": "sync-many-1", "orderId": "3002", "clientOrderId": "sync-many-1-perp-open"},
        tags=["execution", "live", "perp", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=1, seconds=5),
        summary="eth spot",
        payload={"trade_id": "sync-many-2", "orderId": "4001", "clientOrderId": "sync-many-2-spot-open"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.partial",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(minutes=1, seconds=6),
        summary="eth perp",
        payload={"trade_id": "sync-many-2", "orderId": "4002", "clientOrderId": "sync-many-2-perp-open"},
        tags=["execution", "live", "perp", "partial"],
    )

    class StubTradingClient:
        def get_spot_order(self, **kwargs):
            return {
                "symbol": kwargs["symbol"],
                "orderId": kwargs["order_id"],
                "clientOrderId": kwargs["orig_client_order_id"],
                "status": "FILLED",
                "executedQty": "0.2",
                "cummulativeQuoteQty": "15000",
                "updateTime": 1775348400000,
            }

        def get_perp_order(self, **kwargs):
            return {
                "symbol": kwargs["symbol"],
                "orderId": kwargs["order_id"],
                "clientOrderId": kwargs["orig_client_order_id"],
                "status": "FILLED",
                "executedQty": "0.2",
                "cumQuote": "14990",
                "updateTime": 1775348401000,
            }

    service = ReconciliationService(report_store, ledger_service, audit_service)

    synced = service.sync_attention_candidates(trading_client=StubTradingClient(), limit=1)

    assert len(synced) == 2
    assert {report.trade_id for report in synced} == {"sync-many-2"}
    assert {report.order_id for report in synced} == {"4001", "4002"}
