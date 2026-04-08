from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

CompensationAction = Literal[
    "none",
    "sync_exchange_reports",
    "resume_open",
    "resume_close",
    "rebalance_hedge",
    "manual_review",
    "flatten_spot",
    "flatten_perp",
]
CompensationPriority = Literal["low", "medium", "high", "critical"]
CompensationExecutionOutcome = Literal["executed", "skipped", "failed"]


class CompensationPlan(BaseModel):
    trade_id: str
    symbol: str
    mode: Literal["paper", "live"]
    local_status: str
    recommended_action: CompensationAction = "none"
    priority: CompensationPriority = "low"
    actionable: bool = False
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class CompensationPlanListResponse(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plans: list[CompensationPlan] = Field(default_factory=list)


class CompensationExecutionItem(BaseModel):
    trade_id: str
    symbol: str
    action: CompensationAction
    outcome: CompensationExecutionOutcome
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class CompensationExecutionSummary(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempted_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    results: list[CompensationExecutionItem] = Field(default_factory=list)


class CompensationWorkerSnapshot(BaseModel):
    enabled: bool = False
    configured: bool = False
    running: bool = False
    interval_seconds: float = Field(default=30.0, gt=0.0)
    limit: int = Field(default=3, ge=1)
    exposure_limit_bps: float = Field(default=50.0, gt=0.0)
    total_runs: int = Field(default=0, ge=0)
    total_failed_runs: int = Field(default=0, ge=0)
    total_executed_actions: int = Field(default=0, ge=0)
    last_attempted_count: int = Field(default=0, ge=0)
    last_executed_count: int = Field(default=0, ge=0)
    last_skipped_count: int = Field(default=0, ge=0)
    last_failed_count: int = Field(default=0, ge=0)
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
