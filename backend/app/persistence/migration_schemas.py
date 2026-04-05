from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BackfillSectionResult(BaseModel):
    source_path: str
    found: bool = False
    source_records: int = 0
    imported: int = 0
    skipped: int = 0


class PersistenceBackfillSummary(BaseModel):
    backend: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sections: dict[str, BackfillSectionResult] = Field(default_factory=dict)
