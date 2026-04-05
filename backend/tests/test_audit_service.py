from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.audit import AuditEventStore, AuditService


def make_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-audit-service.json"


def test_audit_service_records_and_lists_events() -> None:
    service = AuditService(AuditEventStore(make_path()))

    event = service.record_event(
        event_type="trade.executed",
        severity="info",
        source="execution-engine",
        occurred_at=datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc),
        summary="submitted a funding arbitrage trade",
        payload={"symbol": "BTCUSDT", "size": 0.25},
        tags=["trade", "execution"],
    )

    events = service.list_events()

    assert len(events) == 1
    assert events[0].event_id == event.event_id
    assert events[0].source == "execution-engine"
    assert events[0].payload["symbol"] == "BTCUSDT"


def test_audit_service_records_multiple_events() -> None:
    service = AuditService(AuditEventStore(make_path()))

    first = service.record_event(
        event_type="risk.reviewed",
        severity="warning",
        source="risk-policy",
        summary="review required before release",
    )
    second = service.record_event(
        event_type="system.startup",
        severity="info",
        source="bootstrap",
        summary="backend service started",
        tags=["startup"],
    )

    events = service.list_events()

    assert len(events) == 2
    assert {item.event_id for item in events} == {first.event_id, second.event_id}
