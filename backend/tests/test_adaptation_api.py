from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.adaptation.service import AdaptationService
from app.adaptation.store import TuningStateStore
from app.api.routes.algo import get_adaptation_service
from app.main import app


def build_payload() -> dict:
    return {
        "samples": [
            {
                "symbol": "BTCUSDT",
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
                "symbol": "ETHUSDT",
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
    }


def make_state_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}.json"


def test_adaptation_api_recommends_and_applies_selected_package() -> None:
    service = AdaptationService(TuningStateStore(make_state_path()))
    app.dependency_overrides[get_adaptation_service] = lambda: service
    client = TestClient(app)

    try:
        recommend_response = client.post("/api/v1/algo/adaptation/recommend", json=build_payload())
        assert recommend_response.status_code == 200
        recommend_payload = recommend_response.json()
        assert recommend_payload["recommended_package_id"] == "auto"
        auto_package = next(pkg for pkg in recommend_payload["packages"] if pkg["package_id"] == "auto")

        apply_response = client.post(
            "/api/v1/algo/adaptation/apply",
            json={"package": auto_package, "confirmed": True},
        )
        assert apply_response.status_code == 200
        assert apply_response.json()["active_package_id"] == "auto"

        state_response = client.get("/api/v1/algo/adaptation/state")
        assert state_response.status_code == 200
        assert state_response.json()["active_package_id"] == "auto"
    finally:
        app.dependency_overrides.clear()


def test_adaptation_api_can_import_samples_and_recommend_from_store() -> None:
    service = AdaptationService(TuningStateStore(make_state_path()), sample_store_path=make_state_path())
    app.dependency_overrides[get_adaptation_service] = lambda: service
    client = TestClient(app)

    try:
        import_response = client.post(
            "/api/v1/algo/adaptation/samples/import",
            json={
                "mode": "replace",
                "samples": build_payload()["samples"],
            },
        )
        assert import_response.status_code == 200
        assert import_response.json()["total_samples"] == 2

        list_response = client.get("/api/v1/algo/adaptation/samples")
        assert list_response.status_code == 200
        assert len(list_response.json()["samples"]) == 2

        recommend_response = client.post("/api/v1/algo/adaptation/recommend", json={})
        assert recommend_response.status_code == 200
        assert recommend_response.json()["metrics"]["trade_count"] == 2
    finally:
        app.dependency_overrides.clear()
