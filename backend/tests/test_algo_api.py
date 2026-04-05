from fastapi.testclient import TestClient

from app.main import app


def test_risk_evaluate_endpoint_returns_policy_decision() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/algo/risk/evaluate",
        json={
            "symbol": "BTCUSDT",
            "funding_rate": 0.0008,
            "net_edge_bps": 6.5,
            "score": 140.14,
            "risk_tag": "normal",
            "gross_edge_bps": 8.0,
            "trading_cost_bps": 1.5,
            "annualized_funding_rate_pct": 87.6,
            "basis_bps": 1.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allow"
    assert payload["max_position_fraction"] == 1.0


def test_backtest_run_endpoint_replays_periods() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/algo/backtest/run",
        json={
            "periods": [
                {
                    "snapshots": [
                        {
                            "symbol": "BTCUSDT",
                            "funding_rate": 0.0008,
                            "perp_mid": 60006,
                            "spot_mid": 60000,
                            "perp_spread_bps": 0.4,
                            "spot_spread_bps": 0.3,
                        }
                    ]
                },
                {
                    "snapshots": [
                        {
                            "symbol": "SOLUSDT",
                            "funding_rate": 0.0007,
                            "perp_mid": 180.12,
                            "spot_mid": 180,
                            "perp_spread_bps": 0.4,
                            "spot_spread_bps": 0.3,
                        }
                    ]
                },
            ],
            "config": {
                "notional_per_trade": 10000,
                "min_score": 50,
                "top_k": 1,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["periods_processed"] == 2
    assert payload["selected_trades"] == 2
    assert payload["estimated_total_pnl"] > 0
    assert payload["trades"][0]["symbol"] == "BTCUSDT"
