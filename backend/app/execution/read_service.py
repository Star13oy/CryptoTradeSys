from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.audit import AuditEventRecord, AuditEventService
from app.ledger import TradeLedgerRecord, TradeLedgerService

from .schemas import (
    ExecutionConsoleSnapshot,
    ExecutionIncident,
    ExecutionRecoveryQueueItem,
    ExecutionStatusCount,
)

STATUS_ORDER = [
    "candidate",
    "open",
    "hedged",
    "closing",
    "closed",
    "failed",
    "recovery_pending",
    "cancelled",
]
INCIDENT_SEVERITIES = {"warning", "error", "critical"}
RECOVERY_STATUSES = {"failed", "recovery_pending"}


class ExecutionReadService:
    def __init__(
        self,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._ledger_service = ledger_service or TradeLedgerService()
        self._audit_service = audit_service or AuditEventService()

    def snapshot(self, *, limit_incidents: int = 5) -> ExecutionConsoleSnapshot:
        records = self._ledger_service.list_records()
        events = self._audit_service.list_events(source="execution-orchestrator")
        latest_by_trade = self._build_latest_event_index(events)

        return ExecutionConsoleSnapshot(
            generated_at=datetime.now(timezone.utc),
            status_counts=self._build_status_counts(records),
            recovery_queue=self._build_recovery_queue(records, latest_by_trade),
            recent_incidents=self._build_recent_incidents(events, limit_incidents=limit_incidents),
        )

    def _build_status_counts(self, records: list[TradeLedgerRecord]) -> list[ExecutionStatusCount]:
        counts = Counter(record.status for record in records)
        return [
            ExecutionStatusCount(status=status, count=counts[status])
            for status in STATUS_ORDER
            if counts[status] > 0
        ]

    def _build_recovery_queue(
        self,
        records: list[TradeLedgerRecord],
        latest_by_trade: dict[str, AuditEventRecord],
    ) -> list[ExecutionRecoveryQueueItem]:
        queue = [
            record
            for record in records
            if record.status in RECOVERY_STATUSES
        ]
        ordered = sorted(queue, key=lambda record: (record.opened_at, record.trade_id), reverse=True)
        items: list[ExecutionRecoveryQueueItem] = []
        for record in ordered:
            latest_event = latest_by_trade.get(record.trade_id)
            items.append(
                ExecutionRecoveryQueueItem(
                    trade_id=record.trade_id,
                    mode=record.mode,
                    symbol=record.symbol,
                    status=record.status,
                    opened_at=record.opened_at,
                    net_exposure=record.net_exposure,
                    spot_notional=record.spot_notional,
                    perp_notional=record.perp_notional,
                    latest_event_type=None if latest_event is None else latest_event.event_type,
                    latest_event_summary=None if latest_event is None else latest_event.summary,
                    latest_event_severity=None if latest_event is None else latest_event.severity,
                )
            )
        return items

    def _build_recent_incidents(
        self,
        events: list[AuditEventRecord],
        *,
        limit_incidents: int,
    ) -> list[ExecutionIncident]:
        incidents = [
            event
            for event in events
            if event.severity in INCIDENT_SEVERITIES
        ]
        ordered = sorted(incidents, key=lambda event: (event.occurred_at, event.event_id), reverse=True)
        return [
            ExecutionIncident(
                event_id=event.event_id,
                event_type=event.event_type,
                severity=event.severity,
                occurred_at=event.occurred_at,
                summary=event.summary,
                trade_id=event.payload.get("trade_id"),
            )
            for event in ordered[:limit_incidents]
        ]

    def _build_latest_event_index(self, events: list[AuditEventRecord]) -> dict[str, AuditEventRecord]:
        latest_by_trade: dict[str, AuditEventRecord] = {}
        for event in events:
            trade_id = event.payload.get("trade_id")
            if isinstance(trade_id, str):
                latest_by_trade[trade_id] = event
        return latest_by_trade
