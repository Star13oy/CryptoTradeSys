from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

AuditSeverity = Literal["debug", "info", "warning", "error", "critical"]


class AuditEventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    severity: AuditSeverity = "info"
    source: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class AuditEventImportRequest(BaseModel):
    events: list[AuditEventRecord] = Field(default_factory=list)
    mode: Literal["append", "replace"] = "append"


class AuditEventListResponse(BaseModel):
    events: list[AuditEventRecord] = Field(default_factory=list)


class AuditEventImportResponse(BaseModel):
    imported_events: int
    total_events: int


AuditEvent = AuditEventRecord
