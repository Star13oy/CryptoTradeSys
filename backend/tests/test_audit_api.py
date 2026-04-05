from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes.algo import get_audit_event_service
from app.audit.service import AuditEventService
from app.audit.store import AuditEventStore
from app.main import app


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def make_payload() -> dict:
    return {
        "events": [
            {
                "event_id": "event-1",
                "event_type": "risk.review",
                "severity": "warning",
                "source": "risk-policy",
                "occurred_at": "2026-04-05T08:00:00Z",
                "summary": "Opportunity downgraded to review",
                "payload": {"symbol": "BTCUSDT", "decision": "review"},
                "tags": ["risk", "review"],
            },
            {
                "event_id": "event-2",
                "event_type": "executor.force-exit",
                "severity": "critical",
                "source": "execution-orchestrator",
                "occurred_at": "2026-04-05T09:00:00Z",
                "summary": "Forced exit triggered after hedge mismatch",
                "payload": {"symbol": "ETHUSDT", "mismatch_bps": 17.2},
                "tags": ["execution", "hedge"],
            },
        ],
        "mode": "replace",
    }


def test_audit_api_imports_lists_and_filters_events() -> None:
    audit_service = AuditEventService(AuditEventStore(make_path("audit")))
    app.dependency_overrides[get_audit_event_service] = lambda: audit_service
    client = TestClient(app)

    try:
        import_response = client.post("/api/v1/algo/audit/events/import", json=make_payload())
        assert import_response.status_code == 200
        assert import_response.json()["total_events"] == 2

        list_response = client.get("/api/v1/algo/audit/events")
        assert list_response.status_code == 200
        assert len(list_response.json()["events"]) == 2

        filtered_response = client.get("/api/v1/algo/audit/events?severity=critical&limit=1")
        assert filtered_response.status_code == 200
        payload = filtered_response.json()
        assert len(payload["events"]) == 1
        assert payload["events"][0]["event_id"] == "event-2"
    finally:
        app.dependency_overrides.clear()
