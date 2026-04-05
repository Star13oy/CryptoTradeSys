from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.audit import AuditEventRecord, AuditEventService
from app.ledger import TradeLedgerRecord, TradeLedgerService

from .schemas import ExchangeOrderReport, ReconciliationIssue, ReconciliationSummary
from .store import ExchangeOrderReportStore

EVENT_TYPES_WITH_ORDER_ID = {
    "execution.live.spot.filled",
    "execution.live.perp.filled",
    "execution.live.spot.partial",
    "execution.live.perp.partial",
    "execution.live.close.spot.filled",
    "execution.live.close.perp.filled",
    "execution.live.close.spot.partial",
    "execution.live.close.perp.partial",
}


class ReconciliationService:
    def __init__(
        self,
        store: ExchangeOrderReportStore | None = None,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._store = store or ExchangeOrderReportStore()
        self._ledger_service = ledger_service or TradeLedgerService()
        self._audit_service = audit_service or AuditEventService()

    def import_reports(
        self,
        reports: list[ExchangeOrderReport],
        *,
        mode: str = "append",
    ) -> list[ExchangeOrderReport]:
        return self._store.save(reports, mode=mode)

    def list_reports(
        self,
        *,
        symbol: str | None = None,
        order_id: str | None = None,
    ) -> list[ExchangeOrderReport]:
        reports = self._store.list()
        if symbol is not None:
            reports = [report for report in reports if report.symbol == symbol]
        if order_id is not None:
            reports = [report for report in reports if report.order_id == order_id]
        return sorted(reports, key=lambda report: (report.updated_at, report.report_id), reverse=True)

    def build_summary(self) -> ReconciliationSummary:
        live_records = [
            record
            for record in self._ledger_service.list_records(mode="live")
            if record.status in {"hedged", "recovery_pending", "failed", "closing", "closed"}
        ]
        reports_by_order_id = self._build_report_index(self._store.list())
        expected_order_ids = self._build_expected_order_id_index(
            self._audit_service.list_events(source="execution-orchestrator")
        )

        issues: list[ReconciliationIssue] = []
        for record in live_records:
            trade_issues = self._build_trade_issues(record, expected_order_ids.get(record.trade_id, []), reports_by_order_id)
            issues.extend(trade_issues)

        issue_counter = Counter(issue.issue_type for issue in issues)
        issue_trade_ids = {issue.trade_id for issue in issues}
        return ReconciliationSummary(
            generated_at=datetime.now(timezone.utc),
            compared_trade_count=len(live_records),
            matched_trade_count=max(len(live_records) - len(issue_trade_ids), 0),
            issue_count=len(issues),
            missing_exchange_report_count=issue_counter["missing_exchange_report"],
            status_mismatch_count=issue_counter["status_mismatch"],
            issues=issues,
        )

    def _build_trade_issues(
        self,
        record: TradeLedgerRecord,
        order_ids: list[str],
        reports_by_order_id: dict[str, ExchangeOrderReport],
    ) -> list[ReconciliationIssue]:
        issues: list[ReconciliationIssue] = []
        missing_order_ids = [order_id for order_id in order_ids if order_id not in reports_by_order_id]
        if missing_order_ids:
            issues.append(
                ReconciliationIssue(
                    trade_id=record.trade_id,
                    symbol=record.symbol,
                    issue_type="missing_exchange_report",
                    local_status=record.status,
                    missing_order_ids=missing_order_ids,
                    suggested_action="inspect_exchange",
                    summary=f"Missing exchange reports for {record.symbol}: {', '.join(missing_order_ids)}",
                )
            )

        available_reports = [
            reports_by_order_id[order_id]
            for order_id in order_ids
            if order_id in reports_by_order_id
        ]
        if available_reports and self._is_status_mismatch(record.status, available_reports):
            exchange_statuses = [report.status for report in available_reports]
            issues.append(
                ReconciliationIssue(
                    trade_id=record.trade_id,
                    symbol=record.symbol,
                    issue_type="status_mismatch",
                    local_status=record.status,
                    exchange_statuses=exchange_statuses,
                    suggested_action=self._suggest_action(record.status, exchange_statuses),
                    summary=f"Local status '{record.status}' does not match exchange reports for {record.symbol}",
                )
            )
        return issues

    def _build_report_index(self, reports: list[ExchangeOrderReport]) -> dict[str, ExchangeOrderReport]:
        latest_by_order_id: dict[str, ExchangeOrderReport] = {}
        for report in sorted(reports, key=lambda item: (item.updated_at, item.report_id)):
            latest_by_order_id[report.order_id] = report
        return latest_by_order_id

    def _build_expected_order_id_index(self, events: list[AuditEventRecord]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for event in events:
            if event.event_type not in EVENT_TYPES_WITH_ORDER_ID:
                continue
            trade_id = event.payload.get("trade_id")
            order_id = event.payload.get("orderId")
            if isinstance(trade_id, str) and isinstance(order_id, str):
                result.setdefault(trade_id, [])
                if order_id not in result[trade_id]:
                    result[trade_id].append(order_id)
        return result

    def _is_status_mismatch(self, local_status: str, reports: list[ExchangeOrderReport]) -> bool:
        normalized_statuses = {self._normalize_status(report.status) for report in reports}
        if local_status in {"hedged", "closed"}:
            return normalized_statuses != {"filled"}
        if local_status in {"recovery_pending", "failed"}:
            return normalized_statuses == {"filled"}
        return False

    def _suggest_action(self, local_status: str, exchange_statuses: list[str]) -> str:
        normalized_statuses = {self._normalize_status(status) for status in exchange_statuses}
        if local_status in {"recovery_pending", "failed"} and normalized_statuses == {"filled"}:
            return "resume_open"
        if local_status == "closed" and normalized_statuses == {"filled"}:
            return "resume_close"
        return "inspect_exchange"

    def _normalize_status(self, status: str) -> str:
        normalized = status.strip().upper()
        if normalized == "FILLED":
            return "filled"
        if normalized == "PARTIALLY_FILLED":
            return "partial"
        if normalized in {"NEW", "PENDING_NEW"}:
            return "submitted"
        if normalized in {"CANCELED", "EXPIRED", "REJECTED"}:
            return "failed"
        return normalized.lower()
