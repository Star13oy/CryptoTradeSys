from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.audit import AuditEventRecord, AuditEventService
from app.exchange.binance_trading import BinanceTradingClient
from app.ledger import TradeLedgerRecord, TradeLedgerService

from .schemas import (
    ExchangeOrderReport,
    ReconciliationCandidate,
    ReconciliationIssue,
    ReconciliationSummary,
)
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
        live_records = self._list_reconciliation_records()
        audit_events = self._audit_service.list_events(source="execution-orchestrator")
        reports_by_order_id = self._build_report_index(self._store.list())
        expected_order_ids = self._build_expected_order_id_index(audit_events)

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

    def list_candidates(
        self,
        *,
        symbol: str | None = None,
        only_attention: bool = False,
    ) -> list[ReconciliationCandidate]:
        live_records = self._list_reconciliation_records()
        if symbol is not None:
            live_records = [record for record in live_records if record.symbol == symbol]
        audit_events = self._audit_service.list_events(source="execution-orchestrator")
        reports_by_order_id = self._build_report_index(self._store.list())
        expected_order_ids = self._build_expected_order_id_index(audit_events)
        latest_event_by_trade = self._build_latest_event_index(audit_events)

        candidates: list[ReconciliationCandidate] = []
        for record in live_records:
            trade_id = record.trade_id
            expected_ids = expected_order_ids.get(trade_id, [])
            available_reports = [
                reports_by_order_id[order_id]
                for order_id in expected_ids
                if order_id in reports_by_order_id
            ]
            reported_order_ids = [report.order_id for report in available_reports]
            missing_order_ids = [order_id for order_id in expected_ids if order_id not in reports_by_order_id]
            exchange_statuses = [report.status for report in available_reports]
            latest_report_at = max((report.updated_at for report in available_reports), default=None)
            suggested_action = "inspect_exchange" if missing_order_ids else self._suggest_action(record.status, exchange_statuses)
            needs_attention = bool(missing_order_ids) or (
                bool(available_reports) and self._is_status_mismatch(record.status, available_reports)
            )
            candidate = ReconciliationCandidate(
                trade_id=trade_id,
                symbol=record.symbol,
                local_status=record.status,
                expected_order_ids=expected_ids,
                reported_order_ids=reported_order_ids,
                missing_order_ids=missing_order_ids,
                exchange_statuses=exchange_statuses,
                latest_event_at=latest_event_by_trade.get(trade_id),
                latest_report_at=latest_report_at,
                suggested_action=suggested_action,
                needs_attention=needs_attention,
            )
            if only_attention and not candidate.needs_attention:
                continue
            candidates.append(candidate)

        return sorted(
            candidates,
            key=lambda item: (
                item.needs_attention,
                item.latest_event_at or datetime.min.replace(tzinfo=timezone.utc),
                item.trade_id,
            ),
            reverse=True,
        )

    def sync_reports_for_trade(
        self,
        trade_id: str,
        *,
        trading_client: BinanceTradingClient | None = None,
    ) -> list[ExchangeOrderReport]:
        record = self._ledger_service.get_record(trade_id)
        if record is None:
            raise ValueError(f"trade '{trade_id}' not found in ledger")
        if record.mode != "live":
            raise ValueError(f"trade '{trade_id}' is not a live trade")

        events = self._audit_service.list_events(source="execution-orchestrator")
        expected_orders = self._build_expected_order_requests(record, events)
        if not expected_orders:
            return []

        client = trading_client or BinanceTradingClient()
        synced: list[ExchangeOrderReport] = []
        for order_request in expected_orders:
            if order_request["leg"] == "spot":
                payload = client.get_spot_order(
                    symbol=record.symbol,
                    order_id=order_request["order_id"],
                    orig_client_order_id=order_request["client_order_id"],
                )
            else:
                payload = client.get_perp_order(
                    symbol=record.symbol,
                    order_id=order_request["order_id"],
                    orig_client_order_id=order_request["client_order_id"],
                )
            synced.append(self._to_exchange_report(record.trade_id, order_request["leg"], payload))
        self._upsert_reports(synced)
        return synced

    def sync_attention_candidates(
        self,
        *,
        trading_client: BinanceTradingClient | None = None,
        limit: int | None = None,
    ) -> list[ExchangeOrderReport]:
        candidates = self.list_candidates(only_attention=True)
        if limit is not None:
            candidates = candidates[:limit]

        synced: list[ExchangeOrderReport] = []
        for candidate in candidates:
            synced.extend(
                self.sync_reports_for_trade(
                    candidate.trade_id,
                    trading_client=trading_client,
                )
            )
        return synced

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

    def _build_expected_order_requests(
        self,
        record: TradeLedgerRecord,
        events: list[AuditEventRecord],
    ) -> list[dict[str, str]]:
        requests: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for event in events:
            if event.event_type not in EVENT_TYPES_WITH_ORDER_ID:
                continue
            if event.payload.get("trade_id") != record.trade_id:
                continue
            order_id = event.payload.get("orderId")
            if order_id is None:
                continue
            leg = "perp" if ".perp." in event.event_type else "spot"
            key = (leg, str(order_id))
            if key in seen:
                continue
            seen.add(key)
            requests.append(
                {
                    "leg": leg,
                    "order_id": str(order_id),
                    "client_order_id": str(event.payload.get("clientOrderId")) if event.payload.get("clientOrderId") else "",
                }
            )
        return requests

    def _build_latest_event_index(self, events: list[AuditEventRecord]) -> dict[str, datetime]:
        result: dict[str, datetime] = {}
        for event in events:
            trade_id = event.payload.get("trade_id")
            if not isinstance(trade_id, str):
                continue
            previous = result.get(trade_id)
            if previous is None or event.occurred_at > previous:
                result[trade_id] = event.occurred_at
        return result

    def _list_reconciliation_records(self) -> list[TradeLedgerRecord]:
        return [
            record
            for record in self._ledger_service.list_records(mode="live")
            if record.status in {"hedged", "recovery_pending", "failed", "closing", "closed"}
        ]

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

    def _to_exchange_report(self, trade_id: str, leg: str, payload: dict) -> ExchangeOrderReport:
        update_time = payload.get("updateTime") or payload.get("update_time")
        if isinstance(update_time, (int, float)):
            updated_at = datetime.fromtimestamp(update_time / 1000, tz=timezone.utc)
        else:
            updated_at = datetime.now(timezone.utc)
        cum_quote_qty = payload.get("cummulativeQuoteQty")
        if cum_quote_qty is None:
            cum_quote_qty = payload.get("cumQuote")
        return ExchangeOrderReport(
            venue="binance",
            order_id=str(payload.get("orderId")),
            client_order_id=payload.get("clientOrderId"),
            trade_id=trade_id,
            symbol=str(payload.get("symbol")),
            leg=leg,
            status=str(payload.get("status", "UNKNOWN")),
            executed_qty=float(payload.get("executedQty", 0.0)),
            cum_quote_qty=float(cum_quote_qty or 0.0),
            updated_at=updated_at,
        )

    def _upsert_reports(self, reports: list[ExchangeOrderReport]) -> list[ExchangeOrderReport]:
        merged: dict[str, ExchangeOrderReport] = {report.order_id: report for report in self._store.list()}
        for report in reports:
            merged[report.order_id] = report
        persisted = list(merged.values())
        self._store.save(persisted, mode="replace")
        return persisted
