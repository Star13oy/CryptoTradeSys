from datetime import datetime

from pydantic import BaseModel, Field
from typing import Literal


class CompletedTradeRecord(BaseModel):
    trade_id: str
    symbol: str
    opened_at: datetime
    closed_at: datetime
    score: float
    risk_tag: str
    net_edge_bps: float
    projected_net_edge_bps: float
    basis_bps: float
    realized_pnl_bps: float
    max_drawdown_bps: float = 0.0
    hold_periods: float = Field(default=0.0, ge=0.0)


class TradeJournalImportRequest(BaseModel):
    trades: list[CompletedTradeRecord] = Field(default_factory=list)
    mode: Literal["append", "replace"] = "append"


class TradeJournalListResponse(BaseModel):
    trades: list[CompletedTradeRecord] = Field(default_factory=list)


class TradeJournalImportResponse(BaseModel):
    imported_trades: int
    total_trades: int
