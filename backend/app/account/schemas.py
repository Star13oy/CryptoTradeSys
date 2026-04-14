from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class AssetBalance(BaseModel):
    asset: str
    balance: float = 0.0
    available: float = 0.0
    cross_unrealized_pnl: float = 0.0

class PositionInfo(BaseModel):
    symbol: str
    position_side: str = "BOTH"
    position_amt: float = 0.0
    unrealized_pnl: float = 0.0
    liquidation_price: float | None = None
    mark_price: float = 0.0
    entry_price: float = 0.0
    leverage: int = 1

class AccountBalanceSnapshot(BaseModel):
    total_usdt_equity: float = 0.0
    available_usdt: float = 0.0
    usdt_in_positions: float = 0.0
    unrealized_pnl: float = 0.0
    assets: list[AssetBalance] = Field(default_factory=list)
    fetched_at: datetime

class AccountSummary(BaseModel):
    balance: AccountBalanceSnapshot | None = None
    positions: list[PositionInfo] = Field(default_factory=list)
    active_position_count: int = 0
    fetched_at: datetime
