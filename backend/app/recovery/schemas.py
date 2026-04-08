from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.execution import ExecutionResult

RecoveryRecommendedAction = Literal["resume_open", "resume_close", "manual_review"]


class RecoveryPlan(BaseModel):
    trade_id: str
    mode: Literal["paper", "live"]
    symbol: str
    status: str
    recommended_action: RecoveryRecommendedAction
    auto_executable: bool = False
    latest_event_type: str | None = None
    latest_event_summary: str | None = None
    missing_order_ids: list[str] = Field(default_factory=list)
    exchange_statuses: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RecoveryPlanListResponse(BaseModel):
    plans: list[RecoveryPlan] = Field(default_factory=list)


class RecoveryExecutionSkip(BaseModel):
    trade_id: str
    reason: str


class RecoveryExecutionSummary(BaseModel):
    generated_at: datetime
    attempted_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    results: list[ExecutionResult] = Field(default_factory=list)
    skipped: list[RecoveryExecutionSkip] = Field(default_factory=list)


class RecoveryWorkerSnapshot(BaseModel):
    enabled: bool = False
    configured: bool = False
    running: bool = False
    interval_seconds: float = Field(default=30.0, gt=0.0)
    limit: int = Field(default=3, ge=1)
    total_runs: int = Field(default=0, ge=0)
    total_failed_runs: int = Field(default=0, ge=0)
    total_executed_recoveries: int = Field(default=0, ge=0)
    last_attempted_count: int = Field(default=0, ge=0)
    last_executed_count: int = Field(default=0, ge=0)
    last_skipped_count: int = Field(default=0, ge=0)
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
