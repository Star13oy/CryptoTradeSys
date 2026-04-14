from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class HoldingAlert(BaseModel):
    trade_id: str
    symbol: str
    alert_type: str
    severity: Literal["warning", "critical"]
    detail: str
    entry_funding_rate: float = 0.0
    current_funding_rate: float = 0.0
    hold_periods: float = 0.0
    max_hold_periods: float = 72.0


class HoldingMonitorAction(BaseModel):
    trade_id: str
    symbol: str
    action: Literal["close_hedge", "monitor"]
    alert: HoldingAlert | None = None
    outcome: Literal["executed", "skipped", "failed"] = "skipped"
    reason: str | None = None


class HoldingMonitorResult(BaseModel):
    evaluated_count: int = 0
    alert_count: int = 0
    close_executed: int = 0
    close_skipped: int = 0
    close_failed: int = 0
    actions: list[HoldingMonitorAction] = Field(default_factory=list)
    cycle_started_at: datetime
    cycle_finished_at: datetime


class HoldingMonitorWorkerSnapshot(BaseModel):
    enabled: bool = False
    configured: bool = False
    running: bool = False
    interval_seconds: float = 60.0
    max_hold_periods: float = 72.0
    total_cycles: int = 0
    total_failed_cycles: int = 0
    total_closes_executed: int = 0
    last_cycle_result: HoldingMonitorResult | None = None
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
