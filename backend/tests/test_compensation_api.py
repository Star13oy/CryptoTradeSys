from fastapi.testclient import TestClient

from app.api.routes.algo import get_compensation_service
from app.main import app


def test_compensation_api_lists_plans() -> None:
    class StubCompensationService:
        def list_plans(self, *, symbol=None, only_actionable=False, exposure_limit_bps=50.0):
            assert only_actionable is True
            assert exposure_limit_bps == 75.0
            return [
                {
                    "trade_id": "comp-api-1",
                    "symbol": "BTCUSDT",
                    "mode": "live",
                    "local_status": "hedged",
                    "recommended_action": "sync_exchange_reports",
                    "priority": "critical",
                    "actionable": True,
                    "reason": "missing exchange reports",
                    "details": {"missing_order_ids": ["perp-1"]},
                }
            ]

    app.dependency_overrides[get_compensation_service] = lambda: StubCompensationService()
    client = TestClient(app)
    try:
        response = client.get("/api/v1/algo/compensation/plans?only_actionable=true&exposure_limit_bps=75")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["plans"]) == 1
        assert payload["plans"][0]["trade_id"] == "comp-api-1"
        assert payload["plans"][0]["recommended_action"] == "sync_exchange_reports"
        assert payload["plans"][0]["priority"] == "critical"
    finally:
        app.dependency_overrides.clear()


def test_compensation_api_executes_safe_actions() -> None:
    class StubCompensationService:
        def execute_safe_actions(self, *, orchestrator, symbol=None, limit=None, exposure_limit_bps=50.0):
            assert symbol == "BTCUSDT"
            assert limit == 3
            assert exposure_limit_bps == 75.0
            assert orchestrator is not None
            return {
                "generated_at": "2026-04-08T13:00:00Z",
                "attempted_count": 2,
                "executed_count": 1,
                "skipped_count": 1,
                "failed_count": 0,
                "results": [
                    {
                        "trade_id": "comp-exec-1",
                        "symbol": "BTCUSDT",
                        "action": "sync_exchange_reports",
                        "outcome": "executed",
                        "reason": "synced exchange reports",
                        "details": {"synced_report_count": 2},
                    },
                    {
                        "trade_id": "comp-exec-2",
                        "symbol": "BTCUSDT",
                        "action": "rebalance_hedge",
                        "outcome": "skipped",
                        "reason": "action is not in compensation safe execute allowlist",
                        "details": {},
                    },
                ],
            }

    app.dependency_overrides[get_compensation_service] = lambda: StubCompensationService()
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/algo/compensation/execute?symbol=BTCUSDT&limit=3&exposure_limit_bps=75"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["attempted_count"] == 2
        assert payload["executed_count"] == 1
        assert payload["skipped_count"] == 1
        assert payload["failed_count"] == 0
        assert payload["results"][0]["trade_id"] == "comp-exec-1"
        assert payload["results"][0]["outcome"] == "executed"
        assert payload["results"][1]["trade_id"] == "comp-exec-2"
        assert payload["results"][1]["outcome"] == "skipped"
    finally:
        app.dependency_overrides.clear()
