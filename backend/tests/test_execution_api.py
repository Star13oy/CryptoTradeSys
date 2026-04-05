from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import get_audit_event_service, get_execution_orchestrator
from app.audit import AuditEventService, AuditEventStore
from app.execution import ExecutionOrchestrator
from app.ledger import TradeLedgerService, TradeLedgerStore
from app.main import app


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_execution_api_runs_open_and_close_flow() -> None:
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit")))
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    client = TestClient(app)

    try:
        open_response = client.post(
            "/api/v1/algo/execution/execute",
            json={
                "trade_id": "api-exec-1",
                "mode": "paper",
                "strategy_id": "funding-arb",
                "symbol": "BTCUSDT",
                "action": "open_hedge",
                "spot_notional": 15000,
                "perp_notional": 14980,
            },
        )
        assert open_response.status_code == 200
        assert open_response.json()["status"] == "hedged"

        close_response = client.post(
            "/api/v1/algo/execution/execute",
            json={
                "trade_id": "api-exec-1",
                "mode": "paper",
                "strategy_id": "funding-arb",
                "symbol": "BTCUSDT",
                "action": "close_hedge",
                "realized_pnl": 21.2,
            },
        )
        assert close_response.status_code == 200
        payload = close_response.json()
        assert payload["status"] == "closed"
        assert payload["ledger_record"]["realized_pnl"] == 21.2
        assert len(payload["events"]) >= 2
    finally:
        app.dependency_overrides.clear()
