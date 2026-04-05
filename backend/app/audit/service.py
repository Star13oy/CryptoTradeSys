from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .schemas import AuditEventRecord, AuditSeverity
from .store import AuditEventStore


class AuditEventService:
    def __init__(self, store: AuditEventStore | None = None) -> None:
        self._store = store or AuditEventStore()

    def list_events(
        self,
        *,
        severity: AuditSeverity | None = None,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[AuditEventRecord]:
        filtered = [
            event
            for event in self._store.list()
            if (severity is None or event.severity == severity) and (source is None or event.source == source)
        ]
        ordered = sorted(filtered, key=lambda event: (event.occurred_at, event.event_id))
        if limit is None:
            return ordered
        return ordered[-limit:]

    def record_event(
        self,
        *,
        event_type: str,
        source: str,
        summary: str,
        severity: AuditSeverity = "info",
        occurred_at: datetime | None = None,
        payload: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        event_id: str | None = None,
    ) -> AuditEventRecord:
        event = AuditEventRecord(
            event_id=event_id or uuid4().hex,
            event_type=event_type,
            severity=severity,
            source=source,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            summary=summary,
            payload={} if payload is None else payload,
            tags=[] if tags is None else tags,
        )
        self._store.append([event])
        return event

    def import_events(
        self,
        events: list[AuditEventRecord],
        mode: str = "append",
    ) -> list[AuditEventRecord]:
        return self._store.save(events, mode=mode)

    def record_events(self, events: list[AuditEventRecord], mode: str = "append") -> list[AuditEventRecord]:
        return self.import_events(events, mode=mode)


AuditService = AuditEventService
