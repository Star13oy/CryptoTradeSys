from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import (
    get_audit_event_service,
    get_execution_orchestrator,
    get_trade_ledger_service,
)
from app.audit import AuditEventService, AuditEventStore
from app.execution import ExecutionIntentRequest, ExecutionLegReport, ExecutionOrchestrator
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


def test_execution_api_supports_recovery_flow() -> None:
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-recovery")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-recovery")))
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    client = TestClient(app)

    try:
        fail_response = client.post(
            "/api/v1/algo/execution/execute",
            json={
                "trade_id": "api-recover-1",
                "mode": "paper",
                "strategy_id": "funding-arb",
                "symbol": "ETHUSDT",
                "action": "open_hedge",
                "spot_notional": 10000,
                "perp_notional": 9950,
                "simulate_perp_leg_failure": True,
            },
        )
        assert fail_response.status_code == 200
        assert fail_response.json()["status"] == "failed"

        recovery_response = client.post(
            "/api/v1/algo/execution/recover",
            json={
                "trade_id": "api-recover-1",
                "action": "resume_open",
                "notes": "retry missing perp leg",
            },
        )
        assert recovery_response.status_code == 200
        payload = recovery_response.json()
        assert payload["status"] == "hedged"
        assert payload["ledger_record"]["status"] == "hedged"
    finally:
        app.dependency_overrides.clear()


def test_execution_api_blocks_live_when_disabled() -> None:
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-live-disabled")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-live-disabled")))
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/algo/execution/execute",
            json={
                "trade_id": "api-live-disabled-1",
                "mode": "live",
                "strategy_id": "funding-arb",
                "symbol": "BTCUSDT",
                "action": "open_hedge",
                "spot_notional": 15000,
                "perp_notional": 14980,
                "perp_quantity": 0.25,
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "live execution is disabled"
    finally:
        app.dependency_overrides.clear()


def test_execution_api_blocks_live_symbol_outside_allowlist() -> None:
    class StubLiveAdapter:
        def open_hedge(self, request) -> list[ExecutionLegReport]:
            return [ExecutionLegReport(leg="spot", status="filled", payload={"orderId": "spot-1"})]

        def close_hedge(self, request, existing) -> list[ExecutionLegReport]:
            raise NotImplementedError

    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-live-guard")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-live-guard")))
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=StubLiveAdapter(),
        live_execution_enabled=True,
        live_symbol_allowlist={"BTCUSDT"},
    )
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/algo/execution/execute",
            json={
                "trade_id": "api-live-guard-1",
                "mode": "live",
                "strategy_id": "funding-arb",
                "symbol": "ETHUSDT",
                "action": "open_hedge",
                "spot_notional": 10000,
                "perp_notional": 9950,
                "perp_quantity": 4,
            },
        )
        assert response.status_code == 400
        assert "allowlist" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_execution_api_runs_live_open_flow_when_guard_allows() -> None:
    class StubLiveAdapter:
        def open_hedge(self, request) -> list[ExecutionLegReport]:
            return [
                ExecutionLegReport(leg="spot", status="filled", payload={"orderId": "spot-1"}),
                ExecutionLegReport(leg="perp", status="filled", payload={"orderId": "perp-1"}),
            ]

        def close_hedge(self, request, existing) -> list[ExecutionLegReport]:
            raise NotImplementedError

    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-live-open")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-live-open")))
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=StubLiveAdapter(),
        live_execution_enabled=True,
        live_symbol_allowlist={"BTCUSDT"},
        max_live_notional=20000,
    )
    app.dependency_overrides[get_execution_orchestrator] = lambda: orchestrator
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/algo/execution/execute",
            json={
                "trade_id": "api-live-open-1",
                "mode": "live",
                "strategy_id": "funding-arb",
                "symbol": "BTCUSDT",
                "action": "open_hedge",
                "spot_notional": 15000,
                "perp_notional": 14980,
                "perp_quantity": 0.25,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "hedged"
        assert payload["ledger_record"]["status"] == "hedged"
    finally:
        app.dependency_overrides.clear()


def test_execution_api_returns_summary_snapshot() -> None:
    ledger_service = TradeLedgerService(TradeLedgerStore(make_path("ledger-summary")))
    audit_service = AuditEventService(AuditEventStore(make_path("audit-summary")))
    orchestrator = ExecutionOrchestrator(ledger_service, audit_service)
    orchestrator.execute(
        ExecutionIntentRequest(
            trade_id="api-summary-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="ETHUSDT",
            action="open_hedge",
            spot_notional=10000,
            perp_notional=9950,
            simulate_perp_leg_failure=True,
        )
    )
    app.dependency_overrides[get_trade_ledger_service] = lambda: ledger_service
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/algo/execution/summary?limit_incidents=3")
        assert response.status_code == 200
        payload = response.json()
        counts = {item["status"]: item["count"] for item in payload["status_counts"]}
        assert counts["failed"] == 1
        assert payload["recovery_queue"][0]["trade_id"] == "api-summary-1"
        assert payload["recent_incidents"][0]["event_type"] == "execution.recovery.required"
    finally:
        app.dependency_overrides.clear()
