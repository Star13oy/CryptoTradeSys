from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class SafetyStateSnapshot(BaseModel):
    frozen: bool = False
    new_positions_allowed: bool = True
    reduce_only_trades: list[str] = Field(default_factory=list)
    paused_trades: list[str] = Field(default_factory=list)
    updated_at: datetime

class EmergencyCloseResult(BaseModel):
    closed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    results: list[dict] = Field(default_factory=list)

class SafetyActionRequest(BaseModel):
    trade_id: str | None = None
    reason: str | None = None
