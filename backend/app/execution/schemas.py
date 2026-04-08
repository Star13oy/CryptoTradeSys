from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.audit import AuditEventRecord
from app.ledger import TradeLedgerRecord

ExecutionAction = Literal["open_hedge", "close_hedge", "rebalance_hedge"]
RecoveryAction = Literal["resume_open", "resume_close"]


class ExecutionIntentRequest(BaseModel):
    trade_id: str
    mode: Literal["paper", "live"]
    strategy_id: str
    symbol: str
    action: ExecutionAction
    spot_notional: float = Field(default=0.0, ge=0.0)
    perp_notional: float = Field(default=0.0, ge=0.0)
    spot_quantity: float | None = None
    perp_quantity: float | None = None
    realized_pnl: float = 0.0
    net_exposure: float | None = None
    notes: str | None = None
    simulate_perp_leg_failure: bool = False


class ExecutionLegReport(BaseModel):
    leg: Literal["spot", "perp"]
    status: Literal["submitted", "filled", "partial", "failed"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionRecoveryRequest(BaseModel):
    trade_id: str
    action: RecoveryAction
    notes: str | None = None


class ExecutionResult(BaseModel):
    trade_id: str
    action: ExecutionAction
    mode: Literal["paper", "live"]
    symbol: str
    status: str
    ledger_record: TradeLedgerRecord
    events: list[AuditEventRecord] = Field(default_factory=list)
    executed_at: datetime


class ExecutionStatusCount(BaseModel):
    status: str
    count: int = Field(default=0, ge=0)


class ExecutionRecoveryQueueItem(BaseModel):
    trade_id: str
    mode: Literal["paper", "live"]
    symbol: str
    status: str
    opened_at: datetime
    net_exposure: float = 0.0
    spot_notional: float = Field(default=0.0, ge=0.0)
    perp_notional: float = Field(default=0.0, ge=0.0)
    latest_event_type: str | None = None
    latest_event_summary: str | None = None
    latest_event_severity: str | None = None


class ExecutionIncident(BaseModel):
    event_id: str
    event_type: str
    severity: str
    occurred_at: datetime
    summary: str
    trade_id: str | None = None


class ExecutionConsoleSnapshot(BaseModel):
    generated_at: datetime
    status_counts: list[ExecutionStatusCount] = Field(default_factory=list)
    recovery_queue: list[ExecutionRecoveryQueueItem] = Field(default_factory=list)
    recent_incidents: list[ExecutionIncident] = Field(default_factory=list)
