from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.routes.algo import get_recovery_service
from app.execution import ExecutionResult
from app.ledger import TradeLedgerRecord
from app.main import app


def test_recovery_api_lists_plans() -> None:
    class StubRecoveryService:
        def list_plans(self, *, symbol=None, only_actionable=False):
            assert only_actionable is True
            return [
                {
                    "trade_id": "plan-1",
                    "mode": "paper",
                    "symbol": "ETHUSDT",
                    "status": "failed",
                    "recommended_action": "resume_open",
                    "auto_executable": True,
                    "latest_event_type": "execution.recovery.required",
                    "latest_event_summary": "recovery needed",
                    "missing_order_ids": [],
                    "exchange_statuses": [],
                    "reasons": ["paper trade can use deterministic recovery flow"],
                }
            ]

    app.dependency_overrides[get_recovery_service] = lambda: StubRecoveryService()
    client = TestClient(app)
    try:
        response = client.get("/api/v1/algo/recovery/plans?only_actionable=true")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["plans"]) == 1
        assert payload["plans"][0]["trade_id"] == "plan-1"
        assert payload["plans"][0]["recommended_action"] == "resume_open"
    finally:
        app.dependency_overrides.clear()


def test_recovery_api_executes_auto_plans() -> None:
    class StubRecoveryService:
        def execute_actionable_plans(self, *, orchestrator, limit=None):
            assert limit == 2
            return {
                "generated_at": "2026-04-07T12:30:00Z",
                "attempted_count": 2,
                "executed_count": 1,
                "skipped_count": 1,
                "results": [
                    ExecutionResult(
                        trade_id="recover-api-1",
                        action="open_hedge",
                        mode="paper",
                        symbol="ETHUSDT",
                        status="hedged",
                        ledger_record=TradeLedgerRecord(
                            trade_id="recover-api-1",
                            mode="paper",
                            strategy_id="funding-arb",
                            symbol="ETHUSDT",
                            status="hedged",
                            opened_at=datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc),
                        ),
                        events=[],
                        executed_at=datetime(2026, 4, 7, 12, 30, tzinfo=timezone.utc),
                    )
                ],
                "skipped": [
                    {"trade_id": "recover-api-2", "reason": "manual review required"}
                ],
            }

    app.dependency_overrides[get_recovery_service] = lambda: StubRecoveryService()
    client = TestClient(app)
    try:
        response = client.post("/api/v1/algo/recovery/execute-auto?limit=2")
        assert response.status_code == 200
        payload = response.json()
        assert payload["attempted_count"] == 2
        assert payload["executed_count"] == 1
        assert payload["skipped_count"] == 1
        assert payload["results"][0]["trade_id"] == "recover-api-1"
        assert payload["skipped"][0]["trade_id"] == "recover-api-2"
    finally:
        app.dependency_overrides.clear()
