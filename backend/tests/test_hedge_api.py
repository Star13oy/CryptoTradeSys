from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import get_audit_event_service, get_trade_ledger_service
from app.audit import AuditEventService, AuditEventStore
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.main import app


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
