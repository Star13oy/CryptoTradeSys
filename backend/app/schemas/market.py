from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    symbol: str
    funding_rate: float
    perp_mid: float
    spot_mid: float
    perp_spread_bps: float
    spot_spread_bps: float


class ScoreBreakdown(BaseModel):
    carry_component: float = 0.0
    annualized_component: float = 0.0
    cost_penalty: float = 0.0
    basis_penalty: float = 0.0
    projected_edge_bps: float = 0.0
    base_edge_score: float = 0.0
    basis_penalty_score: float = 0.0
    basis_penalty_bps: float = 0.0
    final_score: float = 0.0


class OpportunityScore(BaseModel):
    symbol: str
    funding_rate: float
    net_edge_bps: float
    score: float
    risk_tag: str
    gross_edge_bps: float = 0.0
    trading_cost_bps: float = 0.0
    annualized_funding_rate_pct: float = 0.0
    basis_bps: float = 0.0
    projected_net_edge_bps: float = 0.0
    payback_periods: float = 0.0
    expected_hold_periods: int = 1
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
