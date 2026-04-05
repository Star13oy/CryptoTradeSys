from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.audit import AuditEventRecord
from app.ledger import TradeLedgerRecord

ExecutionAction = Literal["open_hedge", "close_hedge"]


class ExecutionIntentRequest(BaseModel):
    trade_id: str
    mode: Literal["paper", "live"]
    strategy_id: str
    symbol: str
    action: ExecutionAction
    spot_notional: float = Field(default=0.0, ge=0.0)
    perp_notional: float = Field(default=0.0, ge=0.0)
    realized_pnl: float = 0.0
    net_exposure: float | None = None
    notes: str | None = None
    simulate_perp_leg_failure: bool = False


class ExecutionResult(BaseModel):
    trade_id: str
    action: ExecutionAction
    mode: Literal["paper", "live"]
    symbol: str
    status: str
    ledger_record: TradeLedgerRecord
    events: list[AuditEventRecord] = Field(default_factory=list)
    executed_at: datetime
