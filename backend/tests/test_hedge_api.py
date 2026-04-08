from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import (
    get_audit_event_service,
    get_execution_orchestrator,
    get_hedge_manager_service,
    get_trade_ledger_service,
)
from app.audit import AuditEventService, AuditEventStore
from app.execution import ExecutionOrchestrator
from app.hedge import HedgeManagerService
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.main import app
from app.reconciliation import ExchangeOrderReport, ExchangeOrderReportStore


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_hedge_api_returns_overview() -> None:
    opened_at = datetime(2026, 4, 5, 12, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-api-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-api-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-api-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=90,
                spot_notional=10000,
                perp_notional=9910,
            )
        ],
        mode="replace",
    )
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/algo/hedge/overview?exposure_limit_bps=50")
        assert response.status_code == 200
        payload = response.json()
        assert payload["active_trade_count"] == 1
        assert payload["rebalance_required_count"] == 1
        assert payload["items"][0]["trade_id"] == "hedge-api-1"
        assert payload["items"][0]["health"] == "rebalance_required"
    finally:
        app.dependency_overrides.clear()


def test_hedge_api_returns_rebalance_plan() -> None:
    opened_at = datetime(2026, 4, 5, 13, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-plan-api-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-plan-api-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-plan-api-1",
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
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/algo/hedge/rebalance-plan/hedge-plan-api-1?exposure_limit_bps=50")
        assert response.status_code == 200
        payload = response.json()
        assert payload["recommended_action"] == "increase_perp_hedge"
        assert payload["suggested_perp_notional_delta"] == 120
    finally:
        app.dependency_overrides.clear()


def test_hedge_api_executes_rebalance() -> None:
    opened_at = datetime(2026, 4, 8, 13, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-execute-api-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-execute-api-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-execute-api-1",
                mode="paper",
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
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/algo/hedge/rebalance/hedge-execute-api-1",
            json={
                "perp_quantity": 0.02,
                "exposure_limit_bps": 50,
                "notes": "manual rebalance",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "rebalance_hedge"
        assert payload["status"] == "hedged"
        assert payload["ledger_record"]["perp_notional"] == 15000
        assert payload["ledger_record"]["net_exposure"] == 0
    finally:
        app.dependency_overrides.clear()


def test_hedge_api_rejects_rebalance_when_trade_is_already_within_tolerance() -> None:
    opened_at = datetime(2026, 4, 8, 14, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-execute-noop-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-execute-noop-audit")))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-execute-noop-1",
                mode="paper",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=20,
                spot_notional=15000,
                perp_notional=14980,
            )
        ],
        mode="replace",
    )
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/algo/hedge/rebalance/hedge-execute-noop-1",
            json={"perp_quantity": 0.01},
        )
        assert response.status_code == 400
        assert "does not currently require hedge rebalance" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_hedge_api_executes_rebalance_with_inferred_quantity() -> None:
    opened_at = datetime(2026, 4, 8, 15, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-auto-api-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-auto-api-audit")))
    report_store = ExchangeOrderReportStore(make_path("hedge-auto-api-reports"))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-auto-api-1",
                mode="paper",
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
                order_id="perp-auto-api-1",
                trade_id="hedge-auto-api-1",
                symbol="BTCUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=1.5,
                cum_quote_qty=112500.0,
                updated_at=opened_at + timezone.utc.utcoffset(opened_at),
            )
        ],
        mode="replace",
    )
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    hedge_service = HedgeManagerService(ledger_service, audit_service, report_store=report_store)
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_hedge_manager_service] = lambda: hedge_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/algo/hedge/rebalance-auto/hedge-auto-api-1",
            json={"exposure_limit_bps": 50, "notes": "auto rebalance"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["action"] == "rebalance_hedge"
        assert payload["status"] == "hedged"
        assert payload["ledger_record"]["perp_notional"] == 15000
        assert payload["ledger_record"]["net_exposure"] == 0
    finally:
        app.dependency_overrides.clear()


def test_hedge_api_rejects_auto_rebalance_when_reference_price_missing() -> None:
    opened_at = datetime(2026, 4, 8, 15, 30, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-auto-api-missing-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-auto-api-missing-audit")))
    hedge_service = HedgeManagerService(
        ledger_service,
        audit_service,
        report_store=ExchangeOrderReportStore(make_path("hedge-auto-api-missing-reports")),
    )
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-auto-api-missing-1",
                mode="paper",
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
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_hedge_manager_service] = lambda: hedge_service
    client = TestClient(app)

    try:
        response = client.post("/api/v1/algo/hedge/rebalance-auto/hedge-auto-api-missing-1", json={})
        assert response.status_code == 400
        assert "cannot infer perp reference price" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_hedge_api_executes_auto_rebalance_without_request_body() -> None:
    opened_at = datetime(2026, 4, 8, 16, 0, tzinfo=timezone.utc)
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("hedge-auto-api-nobody-ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("hedge-auto-api-nobody-audit")))
    report_store = ExchangeOrderReportStore(make_path("hedge-auto-api-nobody-reports"))
    ledger_service.import_records(
        [
            TradeLedgerRecord(
                trade_id="hedge-auto-api-nobody-1",
                mode="paper",
                strategy_id="funding-arb",
                symbol="SOLUSDT",
                status="hedged",
                opened_at=opened_at,
                net_exposure=100,
                spot_notional=8000,
                perp_notional=7900,
            )
        ],
        mode="replace",
    )
    report_store.save(
        [
            ExchangeOrderReport(
                venue="binance",
                order_id="perp-auto-api-nobody-1",
                trade_id="hedge-auto-api-nobody-1",
                symbol="SOLUSDT",
                leg="perp",
                status="FILLED",
                executed_qty=100.0,
                cum_quote_qty=12500.0,
                updated_at=opened_at,
            )
        ],
        mode="replace",
    )
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    hedge_service = HedgeManagerService(ledger_service, audit_service, report_store=report_store)
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_hedge_manager_service] = lambda: hedge_service
    client = TestClient(app)

    try:
        response = client.post("/api/v1/algo/hedge/rebalance-auto/hedge-auto-api-nobody-1")
        assert response.status_code == 200
        payload = response.json()
        assert payload["ledger_record"]["net_exposure"] == 0
    finally:
        app.dependency_overrides.clear()
