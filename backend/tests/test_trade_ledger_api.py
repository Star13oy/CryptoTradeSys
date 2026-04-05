from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import get_trade_ledger_service
from app.ledger.service import TradeLedgerService
from app.ledger.store import TradeLedgerStore
from app.ledger.schemas import TradeLedgerRecord
from app.main import app


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def make_records() -> list[TradeLedgerRecord]:
    return [
        TradeLedgerRecord(
            trade_id="ledger-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            status="open",
            opened_at=datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
            closed_at=None,
            net_exposure=0.0,
            spot_notional=15000,
            perp_notional=14980,
            realized_pnl=0.0,
            notes="paper open",
        ),
        TradeLedgerRecord(
            trade_id="ledger-2",
            mode="live",
            strategy_id="funding-arb",
            symbol="ETHUSDT",
            status="closed",
            opened_at=datetime(2026, 4, 4, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc),
            net_exposure=12.5,
            spot_notional=10000,
            perp_notional=9950,
            realized_pnl=42.8,
            notes="live close",
        ),
    ]


def test_trade_ledger_api_imports_lists_and_filters_records() -> None:
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger")))
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    client = TestClient(app)

    try:
        import_response = client.post(
            "/api/v1/algo/ledger/trades/import",
            json={"trades": [item.model_dump(mode="json") for item in make_records()], "mode": "replace"},
        )
        assert import_response.status_code == 200
        assert import_response.json()["total_trades"] == 2

        list_response = client.get("/api/v1/algo/ledger/trades")
        assert list_response.status_code == 200
        assert len(list_response.json()["trades"]) == 2

        filtered_response = client.get("/api/v1/algo/ledger/trades?mode=live&status=closed")
        assert filtered_response.status_code == 200
        payload = filtered_response.json()
        assert len(payload["trades"]) == 1
        assert payload["trades"][0]["trade_id"] == "ledger-2"
    finally:
        app.dependency_overrides.clear()
