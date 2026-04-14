from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SchedulerCycleAction(BaseModel):
    action: Literal["open_hedge", "close_hedge"]
    symbol: str
    trade_id: str
    score: float
    risk_decision: str
    reason: str


class SchedulerCycleResult(BaseModel):
    cycle_started_at: datetime
    cycle_finished_at: datetime
    snapshots_evaluated: int = 0
    positions_evaluated: int = 0
    actions_generated: int = 0
    actions_executed: int = 0
    actions_skipped: int = 0
    actions_failed: int = 0
    actions: list[SchedulerCycleAction] = Field(default_factory=list)


class SchedulerWorkerSnapshot(BaseModel):
    enabled: bool = False
    configured: bool = False
    running: bool = False
    interval_seconds: float = 60.0
    max_open_positions: int = 3
    max_total_notional: float = 25000.0
    total_cycles: int = 0
    total_failed_cycles: int = 0
    total_actions_executed: int = 0
    last_cycle_result: SchedulerCycleResult | None = None
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
