from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ExchangeLeg = Literal["spot", "perp"]
ExchangeReportWriteMode = Literal["append", "replace"]
IssueType = Literal["missing_exchange_report", "status_mismatch"]
SuggestedAction = Literal["none", "inspect_exchange", "resume_open", "resume_close"]


class ExchangeOrderReport(BaseModel):
    report_id: str = Field(default_factory=lambda: uuid4().hex)
    venue: str
    order_id: str
    client_order_id: str | None = None
    trade_id: str | None = None
    symbol: str
    leg: ExchangeLeg
    status: str
    executed_qty: float = Field(default=0.0, ge=0.0)
    cum_quote_qty: float = Field(default=0.0, ge=0.0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExchangeOrderReportImportRequest(BaseModel):
    reports: list[ExchangeOrderReport] = Field(default_factory=list)
    mode: ExchangeReportWriteMode = "append"


class ExchangeOrderReportImportResponse(BaseModel):
    imported_reports: int
    total_reports: int


class ExchangeOrderReportListResponse(BaseModel):
    reports: list[ExchangeOrderReport] = Field(default_factory=list)


class ReconciliationIssue(BaseModel):
    trade_id: str
    symbol: str
    issue_type: IssueType
    local_status: str
    exchange_statuses: list[str] = Field(default_factory=list)
    missing_order_ids: list[str] = Field(default_factory=list)
    suggested_action: SuggestedAction = "none"
    summary: str


class ReconciliationSummary(BaseModel):
    generated_at: datetime
    compared_trade_count: int = Field(default=0, ge=0)
    matched_trade_count: int = Field(default=0, ge=0)
    issue_count: int = Field(default=0, ge=0)
    missing_exchange_report_count: int = Field(default=0, ge=0)
    status_mismatch_count: int = Field(default=0, ge=0)
    issues: list[ReconciliationIssue] = Field(default_factory=list)
