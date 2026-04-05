from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventRecord, AuditEventService, AuditEventStore


def make_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-audit.json"


def make_events() -> list[AuditEventRecord]:
    return [
        AuditEventRecord(
            event_id="event-1",
            event_type="risk.review",
            severity="warning",
            source="risk-policy",
            occurred_at=datetime(2026, 4, 5, 8, 0, tzinfo=timezone.utc),
            summary="Opportunity downgraded to review",
            payload={"symbol": "BTCUSDT", "decision": "review"},
            tags=["risk", "review"],
        ),
        AuditEventRecord(
            event_id="event-2",
            event_type="executor.force-exit",
            severity="critical",
            source="execution-orchestrator",
            occurred_at=datetime(2026, 4, 5, 9, 0, tzinfo=timezone.utc),
            summary="Forced exit triggered after hedge mismatch",
            payload={"symbol": "ETHUSDT", "mismatch_bps": 17.2},
            tags=["execution", "hedge"],
        ),
    ]


def test_audit_store_and_service_support_append_replace_and_filters() -> None:
    store = AuditEventStore(make_path())
    service = AuditEventService(store)

    persisted = service.import_events(make_events(), mode="replace")
    assert len(persisted) == 2

    critical = service.list_events(severity="critical", limit=1)
    assert len(critical) == 1
    assert critical[0].event_id == "event-2"

    appended = service.import_events(make_events()[:1], mode="append")
    assert len(appended) == 3
