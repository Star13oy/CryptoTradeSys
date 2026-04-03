from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    funding_rate: float
    perp_mid: float
    spot_mid: float
    perp_spread_bps: float
    spot_spread_bps: float


class OpportunityScore(BaseModel):
    symbol: str
    funding_rate: float
    net_edge_bps: float
    score: float
    risk_tag: str
