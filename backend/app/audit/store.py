from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.core.settings import get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled

from .schemas import AuditEventRecord

_TABLE_NAME = "audit_events"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    row_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(191) NOT NULL,
    event_type VARCHAR(191) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    source VARCHAR(191) NOT NULL,
    occurred_at DATETIME(6) NOT NULL,
    summary TEXT NOT NULL,
    payload JSON NOT NULL,
    KEY idx_audit_events_event_id (event_id),
    KEY idx_audit_events_source_occurred_at (source, occurred_at),
    KEY idx_audit_events_severity_occurred_at (severity, occurred_at)
)
"""


class AuditEventStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._settings = get_settings()
        self._path = Path(path or self._settings.audit_event_path)
        self._mysql = MySQLPersistence(self._settings)

    def list(self) -> list[AuditEventRecord]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            payloads = self._mysql.fetch_json_rows(f"SELECT payload FROM {_TABLE_NAME} ORDER BY row_id")
            return [AuditEventRecord.model_validate(item) for item in payloads]
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [AuditEventRecord.model_validate(item) for item in payload]

    def save(
        self,
        events: list[AuditEventRecord],
        mode: Literal["append", "replace"] = "append",
    ) -> list[AuditEventRecord]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            persisted = list(events) if mode == "replace" else [*self.list(), *events]
            params = [
                (
                    event.event_id,
                    event.event_type,
                    event.severity,
                    event.source,
                    self._mysql.to_mysql_datetime(event.occurred_at),
                    event.summary,
                    self._mysql.serialize(event),
                )
                for event in persisted
            ]
            self._mysql.replace_rows(
                table_name=_TABLE_NAME,
                insert_sql=(
                    f"""
                    INSERT INTO {_TABLE_NAME}
                    (event_id, event_type, severity, source, occurred_at, summary, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, CAST(%s AS JSON))
                    """
                ),
                params=params,
            )
            return persisted
        persisted = list(events) if mode == "replace" else [*self.list(), *events]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([event.model_dump(mode="json") for event in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted

    def append(self, events: list[AuditEventRecord]) -> list[AuditEventRecord]:
        return self.save(events, mode="append")

    def replace(self, events: list[AuditEventRecord]) -> list[AuditEventRecord]:
        return self.save(events, mode="replace")
