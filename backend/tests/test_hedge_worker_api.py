from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.hedge import HedgeRebalanceWorkerSnapshot
from app.main import app


def test_hedge_worker_status_api_returns_snapshot() -> None:
    class StubWorker:
        def snapshot(self) -> HedgeRebalanceWorkerSnapshot:
            return HedgeRebalanceWorkerSnapshot(
                enabled=True,
                configured=True,
                running=True,
                interval_seconds=30,
                limit=5,
                exposure_limit_bps=35.0,
                total_runs=4,
                total_failed_runs=1,
                total_executed_rebalances=3,
                last_attempted_count=2,
                last_executed_count=1,
                last_skipped_count=1,
                last_failed_count=0,
                last_success_at=datetime(2026, 4, 8, 20, 0, tzinfo=timezone.utc),
            )

    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_hedge_rebalance_worker] = lambda: StubWorker()
    client = TestClient(app)
    try:
        response = client.get("/api/v1/algo/hedge/worker")
        assert response.status_code == 200
        payload = response.json()
        assert payload["enabled"] is True
        assert payload["running"] is True
        assert payload["total_runs"] == 4
        assert payload["total_executed_rebalances"] == 3
        assert payload["last_executed_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_hedge_worker_run_api_executes_once() -> None:
    class StubWorker:
        async def run_once(self) -> HedgeRebalanceWorkerSnapshot:
            return HedgeRebalanceWorkerSnapshot(
                enabled=True,
                configured=True,
                running=False,
                interval_seconds=30,
                limit=5,
                exposure_limit_bps=35.0,
                total_runs=1,
                total_failed_runs=0,
                total_executed_rebalances=2,
                last_attempted_count=2,
                last_executed_count=2,
                last_skipped_count=0,
                last_failed_count=0,
                last_success_at=datetime(2026, 4, 8, 20, 30, tzinfo=timezone.utc),
            )

    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_hedge_rebalance_worker] = lambda: StubWorker()
    client = TestClient(app)
    try:
        response = client.post("/api/v1/algo/hedge/worker/run")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_runs"] == 1
        assert payload["total_executed_rebalances"] == 2
        assert payload["last_attempted_count"] == 2
        assert payload["last_executed_count"] == 2
    finally:
        app.dependency_overrides.clear()
