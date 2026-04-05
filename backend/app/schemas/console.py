from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.market import OpportunityScore


class AccountHealthSummary(BaseModel):
    mode: str
    exchange: str
    risk_state: str


class ScanFilters(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)
    positive_funding_only: bool = True
    min_net_edge_bps: float | None = Field(default=None, ge=0)


class MarketDataStatus(BaseModel):
    spot_source: str
    perp_source: str
    degraded: bool
    requested_symbols: int
    quoted_symbols: int


class DashboardSummary(BaseModel):
    generated_at: datetime
    account_health: AccountHealthSummary
    market_status: MarketDataStatus
    top_opportunities: list[OpportunityScore]
    paper_positions: list[dict] = Field(default_factory=list)


class ScanOpportunitiesResponse(BaseModel):
    generated_at: datetime
    applied_filters: ScanFilters
    market_status: MarketDataStatus
    total_matches: int
    rows: list[OpportunityScore]
