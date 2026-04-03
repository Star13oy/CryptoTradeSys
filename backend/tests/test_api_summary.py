from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_summary_contains_ranked_opportunities() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["top_opportunities"]) >= 1
    assert payload["top_opportunities"][0]["symbol"] == "BTCUSDT"
