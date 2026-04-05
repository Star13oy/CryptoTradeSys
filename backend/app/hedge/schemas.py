from __future__ import annotations

from datetime import datetime
from typing import Literal

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
