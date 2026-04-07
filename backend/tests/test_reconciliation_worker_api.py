from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.reconciliation import ReconciliationWorkerSnapshot


def test_reconciliation_worker_status_api_returns_snapshot() -> None:
    class StubWorker:
        def snapshot(self) -> ReconciliationWorkerSnapshot:
            return ReconciliationWorkerSnapshot(
                enabled=True,
                configured=True,
                running=True,
                interval_seconds=30,
                limit=5,
                total_runs=4,
                total_failed_runs=1,
                total_imported_reports=6,
                last_imported_report_count=2,
                last_synced_trade_count=1,
                last_success_at=datetime(2026, 4, 6, 1, 0, tzinfo=timezone.utc),
            )

    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_reconciliation_worker] = lambda: StubWorker()
    client = TestClient(app)
    try:
        response = client.get("/api/v1/algo/reconciliation/worker")
        assert response.status_code == 200
        payload = response.json()
        assert payload["enabled"] is True
        assert payload["running"] is True
        assert payload["total_runs"] == 4
        assert payload["last_imported_report_count"] == 2
    finally:
        app.dependency_overrides.clear()


def test_reconciliation_worker_run_api_executes_once() -> None:
    class StubWorker:
        async def run_once(self) -> ReconciliationWorkerSnapshot:
            return ReconciliationWorkerSnapshot(
                enabled=True,
                configured=True,
                running=False,
                interval_seconds=30,
                limit=5,
                total_runs=1,
                total_failed_runs=0,
                total_imported_reports=2,
                last_imported_report_count=2,
                last_synced_trade_count=1,
                last_success_at=datetime(2026, 4, 6, 2, 0, tzinfo=timezone.utc),
            )

    from app.api.routes import algo as algo_routes

    app.dependency_overrides[algo_routes.get_reconciliation_worker] = lambda: StubWorker()
    client = TestClient(app)
    try:
        response = client.post("/api/v1/algo/reconciliation/worker/run")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_runs"] == 1
        assert payload["last_imported_report_count"] == 2
        assert payload["last_synced_trade_count"] == 1
    finally:
        app.dependency_overrides.clear()
