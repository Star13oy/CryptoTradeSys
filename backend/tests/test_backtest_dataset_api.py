from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.adaptation.sample_store import LearningSampleStore
from app.adaptation.service import AdaptationService
from app.adaptation.store import TuningStateStore
from app.api.routes.algo import get_adaptation_service, get_backtest_dataset_service
from app.backtest.dataset_service import BacktestDatasetService
from app.backtest.dataset_store import BacktestDatasetStore
from app.main import app


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def make_dataset_payload() -> dict:
    return {
        "dataset_id": "funding-apr-01",
        "title": "Funding Replay 2026-04-01",
        "source": "manual_import",
        "periods": [
            {
                "observed_at": "2026-04-01T00:00:00Z",
                "snapshots": [
                    {
                        "symbol": "BTCUSDT",
                        "funding_rate": 0.0008,
                        "perp_mid": 60006,
                        "spot_mid": 60000,
                        "perp_spread_bps": 0.4,
                        "spot_spread_bps": 0.3,
                    }
                ],
            },
            {
                "observed_at": "2026-04-01T08:00:00Z",
                "snapshots": [
                    {
                        "symbol": "SOLUSDT",
                        "funding_rate": 0.0007,
                        "perp_mid": 180.12,
                        "spot_mid": 180,
                        "perp_spread_bps": 0.4,
                        "spot_spread_bps": 0.3,
                    }
                ],
            },
        ],
    }


def test_backtest_dataset_api_imports_lists_and_runs_dataset() -> None:
    adaptation_service = AdaptationService(
        TuningStateStore(make_path("tuning")),
        LearningSampleStore(make_path("samples")),
    )
    dataset_service = BacktestDatasetService(BacktestDatasetStore(make_path("datasets")))
    app.dependency_overrides[get_adaptation_service] = lambda: adaptation_service
    app.dependency_overrides[get_backtest_dataset_service] = lambda: dataset_service
    client = TestClient(app)

    try:
        import_response = client.post("/api/v1/algo/backtest/datasets/import", json=make_dataset_payload())
        assert import_response.status_code == 200
        assert import_response.json()["dataset"]["dataset_id"] == "funding-apr-01"

        list_response = client.get("/api/v1/algo/backtest/datasets")
        assert list_response.status_code == 200
        assert len(list_response.json()["datasets"]) == 1
        assert list_response.json()["datasets"][0]["period_count"] == 2

        run_response = client.post(
            "/api/v1/algo/backtest/run-from-dataset",
            json={
                "dataset_id": "funding-apr-01",
                "config": {
                    "notional_per_trade": 10000,
                    "min_score": 50,
                    "top_k": 1,
                },
                "limit_recent_periods": 1,
            },
        )
        assert run_response.status_code == 200
        payload = run_response.json()
        assert payload["periods_processed"] == 1
        assert payload["selected_trades"] == 1
        assert payload["trades"][0]["symbol"] == "SOLUSDT"
    finally:
        app.dependency_overrides.clear()
