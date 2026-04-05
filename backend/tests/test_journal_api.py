from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.adaptation.service import AdaptationService
from app.adaptation.store import TuningStateStore
from app.api.routes.algo import get_adaptation_service, get_trade_journal_service
from app.journal.service import TradeJournalService
from app.journal.store import TradeJournalStore
from app.main import app


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def make_trade_payload() -> dict:
    return {
        "trades": [
            {
                "trade_id": "trade-1",
                "symbol": "BTCUSDT",
                "opened_at": "2026-04-01T00:00:00Z",
                "closed_at": "2026-04-01T08:00:00Z",
                "score": 95,
                "risk_tag": "guarded",
                "net_edge_bps": -0.4,
                "projected_net_edge_bps": 2.6,
                "basis_bps": 6.8,
                "realized_pnl_bps": -1.8,
                "max_drawdown_bps": 9.5,
                "hold_periods": 9,
            },
            {
                "trade_id": "trade-2",
                "symbol": "ETHUSDT",
                "opened_at": "2026-04-02T00:00:00Z",
                "closed_at": "2026-04-02T08:00:00Z",
                "score": 82,
                "risk_tag": "guarded",
                "net_edge_bps": -0.2,
                "projected_net_edge_bps": 2.2,
                "basis_bps": 7.4,
                "realized_pnl_bps": -0.6,
                "max_drawdown_bps": 7.2,
                "hold_periods": 8,
            },
        ],
        "mode": "replace",
    }


def test_journal_api_imports_lists_and_extracts_learning_samples() -> None:
    adaptation_service = AdaptationService(
        TuningStateStore(make_path("tuning")),
        sample_store_path=make_path("samples"),
    )
    journal_service = TradeJournalService(TradeJournalStore(make_path("journal")))
    app.dependency_overrides[get_adaptation_service] = lambda: adaptation_service
    app.dependency_overrides[get_trade_journal_service] = lambda: journal_service
    client = TestClient(app)

    try:
        import_response = client.post("/api/v1/algo/journal/trades/import", json=make_trade_payload())
        assert import_response.status_code == 200
        assert import_response.json()["total_trades"] == 2

        list_response = client.get("/api/v1/algo/journal/trades")
        assert list_response.status_code == 200
        assert len(list_response.json()["trades"]) == 2

        extract_response = client.post(
            "/api/v1/algo/adaptation/samples/extract-from-journal",
            json={"mode": "replace", "symbol": "BTCUSDT", "limit": 1},
        )
        assert extract_response.status_code == 200
        assert extract_response.json()["imported_samples"] == 1

        recommend_response = client.post("/api/v1/algo/adaptation/recommend", json={})
        assert recommend_response.status_code == 200
        assert recommend_response.json()["metrics"]["trade_count"] == 1
    finally:
        app.dependency_overrides.clear()
