from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

HedgeHealth = Literal["healthy", "monitoring", "rebalance_required", "recovery_required"]
RebalanceAction = Literal[
    "none",
    "monitor_only",
    "recover_trade",
    "increase_perp_hedge",
    "reduce_perp_hedge",
]


class HedgeOverviewItem(BaseModel):
    trade_id: str
    mode: Literal["paper", "live"]
    symbol: str
    status: str
    health: HedgeHealth
    opened_at: datetime
    spot_notional: float = Field(default=0.0, ge=0.0)
    perp_notional: float = Field(default=0.0, ge=0.0)
    net_exposure: float = 0.0
    exposure_bps: float = 0.0
    latest_event_type: str | None = None
    latest_event_summary: str | None = None
    latest_event_severity: str | None = None


class HedgeOverview(BaseModel):
    generated_at: datetime
    exposure_limit_bps: float = Field(default=0.0, ge=0.0)
    active_trade_count: int = Field(default=0, ge=0)
    healthy_count: int = Field(default=0, ge=0)
    monitoring_count: int = Field(default=0, ge=0)
    rebalance_required_count: int = Field(default=0, ge=0)
    recovery_required_count: int = Field(default=0, ge=0)
    items: list[HedgeOverviewItem] = Field(default_factory=list)


class HedgeRebalancePlan(BaseModel):
    trade_id: str
    symbol: str
    status: str
    health: HedgeHealth
    exposure_limit_bps: float = Field(default=0.0, ge=0.0)
    net_exposure: float = 0.0
    exposure_bps: float = 0.0
    recommended_action: RebalanceAction = "none"
    suggested_perp_notional_delta: float = 0.0
    estimated_post_rebalance_exposure_bps: float = 0.0
    notes: str = ""


HedgeRebalanceExecutionOutcome = Literal["executed", "skipped", "failed"]


class HedgeRebalanceExecutionItem(BaseModel):
    trade_id: str
    symbol: str
    action: RebalanceAction
    outcome: HedgeRebalanceExecutionOutcome
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class HedgeRebalanceExecutionSummary(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempted_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    results: list[HedgeRebalanceExecutionItem] = Field(default_factory=list)


class HedgeRebalanceWorkerSnapshot(BaseModel):
    enabled: bool = False
    configured: bool = False
    running: bool = False
    interval_seconds: float = Field(default=30.0, gt=0.0)
    limit: int = Field(default=3, ge=1)
    exposure_limit_bps: float = Field(default=50.0, gt=0.0)
    total_runs: int = Field(default=0, ge=0)
    total_failed_runs: int = Field(default=0, ge=0)
    total_executed_rebalances: int = Field(default=0, ge=0)
    last_attempted_count: int = Field(default=0, ge=0)
    last_executed_count: int = Field(default=0, ge=0)
    last_skipped_count: int = Field(default=0, ge=0)
    last_failed_count: int = Field(default=0, ge=0)
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class HedgeRebalanceExecutionRequest(BaseModel):
    perp_quantity: float = Field(gt=0.0)
    exposure_limit_bps: float = Field(default=50.0, ge=0.0)
    notes: str | None = None


class HedgeAutoRebalanceExecutionRequest(BaseModel):
    exposure_limit_bps: float = Field(default=50.0, ge=0.0)
    notes: str | None = None
