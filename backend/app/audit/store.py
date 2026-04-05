from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.core.settings import get_settings

from .schemas import AuditEventRecord


class AuditEventStore:
    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        self._path = Path(path or settings.audit_event_path)

    def list(self) -> list[AuditEventRecord]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [AuditEventRecord.model_validate(item) for item in payload]

    def save(
        self,
        events: list[AuditEventRecord],
        mode: Literal["append", "replace"] = "append",
    ) -> list[AuditEventRecord]:
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
