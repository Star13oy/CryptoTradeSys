from __future__ import annotations
from pydantic import BaseModel, Field

class ManualOrderRequest(BaseModel):
    symbol: str
    side: str  # "long" = buy spot + short perp, "short" = sell spot + long perp
    notional: float = Field(gt=0)
    mode: str = "paper"  # "paper" | "live"

class OrderPreview(BaseModel):
    symbol: str
    side: str
    notional: float
    spot_price: float = 0.0
    perp_price: float = 0.0
    funding_rate: float = 0.0
    estimated_fees_usd: float = 0.0
    estimated_net_edge_bps: float = 0.0
    risk_decision: str = "allow"

class OrderResult(BaseModel):
    trade_id: str
    status: str
    spot_filled: float = 0.0
    perp_filled: float = 0.0
    executed_at: str

class SymbolInfo(BaseModel):
    symbol: str
    funding_rate: float = 0.0
    mark_price: float = 0.0
