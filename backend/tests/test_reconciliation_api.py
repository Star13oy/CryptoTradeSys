from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import (
    get_audit_event_service,
    get_trade_ledger_service,
)
from app.audit import AuditEventService, AuditEventStore
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.main import app
from app.reconciliation import ExchangeOrderReport, ExchangeOrderReportStore, ReconciliationService


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_reconciliation_api_imports_reports_and_returns_summary() -> None:
    opened_at = datetime(2026, 4, 5, 15, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recon-api-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recon-api-audit")))
    report_store = ExchangeOrderReportStore(make_path("recon-api-reports"))
    reconciliation_service = ReconciliationService(report_store, ledger_service, audit_service)

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="recon-api-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=15,
                spot_notional=15000,
                perp_notional=14985,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="Live spot leg filled",
        payload={"trade_id": "recon-api-1", "orderId": "spot-api-1"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="Live perp leg filled",
        payload={"trade_id": "recon-api-1", "orderId": "perp-api-1"},
        tags=["execution", "live", "perp", "filled"],
    )

    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_reconciliation_service] = lambda: reconciliation_service
    client = TestClient(app)

    try:
        import_response = client.post(
            "/api/v1/algo/reconciliation/reports/import",
            json={
                "reports": [
                    ExchangeOrderReport(
                        venue="binance",
                        order_id="spot-api-1",
                        symbol="BTCUSDT",
                        leg="spot",
                        status="FILLED",
                        executed_qty=0.2,
                        cum_quote_qty=15000,
                        updated_at=opened_at + timedelta(minutes=1),
                    ).model_dump(mode="json"),
                    ExchangeOrderReport(
                        venue="binance",
                        order_id="perp-api-1",
                        symbol="BTCUSDT",
                        leg="perp",
                        status="FILLED",
                        executed_qty=0.2,
                        cum_quote_qty=14985,
                        updated_at=opened_at + timedelta(minutes=1),
                    ).model_dump(mode="json"),
                ],
                "mode": "replace",
            },
        )
        assert import_response.status_code == 200
        assert import_response.json()["total_reports"] == 2

        summary_response = client.get("/api/v1/algo/reconciliation/summary")
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()
        assert summary_payload["compared_trade_count"] == 1
        assert summary_payload["matched_trade_count"] == 1
        assert summary_payload["issue_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_reconciliation_api_lists_candidates() -> None:
    opened_at = datetime(2026, 4, 5, 17, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("recon-candidates-api-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("recon-candidates-api-audit")))
    report_store = ExchangeOrderReportStore(make_path("recon-candidates-api-reports"))
    reconciliation_service = ReconciliationService(report_store, ledger_service, audit_service)

    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="candidate-api-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=15,
                spot_notional=15000,
                perp_notional=14985,
            )
        ],
        mode="replace",
    )
    audit_service.record_event(
        event_type="execution.live.spot.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=5),
        summary="Live spot leg filled",
        payload={"trade_id": "candidate-api-1", "orderId": "spot-api-candidate-1"},
        tags=["execution", "live", "spot", "filled"],
    )
    audit_service.record_event(
        event_type="execution.live.perp.filled",
        source="execution-orchestrator",
        occurred_at=opened_at + timedelta(seconds=6),
        summary="Live perp leg filled",
        payload={"trade_id": "candidate-api-1", "orderId": "perp-api-candidate-1"},
        tags=["execution", "live", "perp", "filled"],
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="spot-api-candidate-1",
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

    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_reconciliation_service] = lambda: reconciliation_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/algo/reconciliation/candidates?only_attention=true")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["candidates"]) == 1
        assert payload["candidates"][0]["trade_id"] == "candidate-api-1"
        assert payload["candidates"][0]["missing_order_ids"] == ["perp-api-candidate-1"]
        assert payload["candidates"][0]["needs_attention"] is True
    finally:
        app.dependency_overrides.clear()


def test_reconciliation_api_syncs_reports_for_trade() -> None:
    class StubReconciliationService:
        def sync_reports_for_trade(self, trade_id: str):
            assert trade_id == "sync-api-1"
            return [
                ExchangeOrderReport(
                    venue="binance",
                    order_id="1001",
                    trade_id=trade_id,
                    symbol="BTCUSDT",
                    leg="spot",
                    status="FILLED",
                    executed_qty=0.2,
                    cum_quote_qty=15000,
                    updated_at=datetime(2026, 4, 5, 18, 0, tzinfo=timezone.utc),
                )
            ]

    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_reconciliation_service] = lambda: StubReconciliationService()
    client = TestClient(app)
    try:
        response = client.post("/api/v1/algo/reconciliation/sync/sync-api-1")
        assert response.status_code == 200
        payload = response.json()
        assert payload["imported_reports"] == 1
        assert payload["total_reports"] == 1
    finally:
        app.dependency_overrides.clear()


def test_reconciliation_api_syncs_attention_candidates() -> None:
    class StubReconciliationService:
        def sync_attention_candidates(self, *, limit: int | None = None):
            assert limit == 2
            return [
                ExchangeOrderReport(
                    venue="binance",
                    order_id="5001",
                    trade_id="sync-attn-1",
                    symbol="BTCUSDT",
                    leg="spot",
                    status="FILLED",
                    executed_qty=0.2,
                    cum_quote_qty=15000,
                    updated_at=datetime(2026, 4, 5, 19, 0, tzinfo=timezone.utc),
                )
            ]

    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_reconciliation_service] = lambda: StubReconciliationService()
    client = TestClient(app)
    try:
        response = client.post("/api/v1/algo/reconciliation/sync?limit=2")
        assert response.status_code == 200
        payload = response.json()
        assert payload["imported_reports"] == 1
        assert payload["total_reports"] == 1
    finally:
        app.dependency_overrides.clear()
