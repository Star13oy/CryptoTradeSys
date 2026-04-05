from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TradeMode = Literal["paper", "live"]
TradeLedgerStatus = Literal["candidate", "open", "hedged", "closing", "closed", "failed", "cancelled"]
LedgerWriteMode = Literal["append", "replace"]
TradeStatus = TradeLedgerStatus


class TradeLedgerRecord(BaseModel):
    trade_id: str
    mode: TradeMode
    strategy_id: str
    symbol: str
    status: TradeLedgerStatus
    opened_at: datetime
    closed_at: datetime | None = None
    net_exposure: float = 0.0
    spot_notional: float = Field(default=0.0, ge=0.0)
    perp_notional: float = Field(default=0.0, ge=0.0)
    realized_pnl: float = 0.0
    notes: str | None = None


class TradeLedgerImportRequest(BaseModel):
    trades: list[TradeLedgerRecord] = Field(default_factory=list)
    mode: LedgerWriteMode = "append"


class TradeLedgerListResponse(BaseModel):
    trades: list[TradeLedgerRecord] = Field(default_factory=list)


class TradeLedgerImportResponse(BaseModel):
    imported_trades: int
    total_trades: int
