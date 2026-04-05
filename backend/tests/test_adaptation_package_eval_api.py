from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.adaptation.service import AdaptationService
from app.adaptation.store import TuningStateStore
from app.api.routes.algo import get_adaptation_service, get_backtest_dataset_service
from app.backtest import BacktestDataset, BacktestDatasetService, BacktestDatasetStore, BacktestPeriod
from app.main import app
from app.schemas.market import MarketSnapshot


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def make_dataset() -> BacktestDataset:
    return BacktestDataset(
        dataset_id="funding-validation",
        title="Funding Validation Window",
        periods=[
            BacktestPeriod(
                observed_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
                snapshots=[
                    MarketSnapshot(
                        symbol="BTCUSDT",
                        funding_rate=0.0008,
                        perp_mid=60006,
                        spot_mid=60000,
                        perp_spread_bps=0.4,
                        spot_spread_bps=0.3,
                    )
                ],
            ),
            BacktestPeriod(
                observed_at=datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc),
                snapshots=[
                    MarketSnapshot(
                        symbol="SOLUSDT",
                        funding_rate=0.0007,
                        perp_mid=180.12,
                        spot_mid=180,
                        perp_spread_bps=0.4,
                        spot_spread_bps=0.3,
                    )
                ],
            ),
        ],
    )


def sample_payload() -> list[dict]:
    return [
        {
            "trade_id": "trade-1",
            "symbol": "BTCUSDT",
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
    ]


def test_adaptation_package_eval_api_scores_packages_against_dataset() -> None:
    adaptation_service = AdaptationService(
        TuningStateStore(make_path("tuning")),
        sample_store_path=make_path("samples"),
    )
    dataset_service = BacktestDatasetService(BacktestDatasetStore(make_path("datasets")))
    dataset_service.import_dataset(make_dataset())

    app.dependency_overrides[get_adaptation_service] = lambda: adaptation_service
    app.dependency_overrides[get_backtest_dataset_service] = lambda: dataset_service
    client = TestClient(app)

    try:
        import_response = client.post(
            "/api/v1/algo/adaptation/samples/import",
            json={"mode": "replace", "samples": sample_payload()},
        )
        assert import_response.status_code == 200

        response = client.post(
            "/api/v1/algo/adaptation/evaluate-packages",
            json={"dataset_id": "funding-validation", "limit_recent_periods": 1},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["recommended_package_id"] == "auto"
        assert payload["metrics"]["trade_count"] == 2
        assert len(payload["evaluations"]) == 4
        assert payload["evaluations"][0]["selected_trades"] >= 0
        assert {item["package_id"] for item in payload["evaluations"]} == {
            "conservative",
            "balanced",
            "aggressive",
            "auto",
        }
    finally:
        app.dependency_overrides.clear()
