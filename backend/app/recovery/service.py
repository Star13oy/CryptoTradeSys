from __future__ import annotations

from datetime import datetime, timezone

from app.audit import AuditEventRecord, AuditEventService
from app.execution import ExecutionOrchestrator, ExecutionRecoveryRequest
from app.ledger import TradeLedgerRecord, TradeLedgerService
from app.reconciliation import ReconciliationCandidate, ReconciliationService

from .schemas import (
    RecoveryExecutionSkip,
    RecoveryExecutionSummary,
    RecoveryPlan,
)

RECOVERABLE_STATUSES = {"failed", "recovery_pending"}


class RecoveryService:
    def __init__(
        self,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
        reconciliation_service: ReconciliationService | None = None,
    ) -> None:
        self._ledger_service = ledger_service or TradeLedgerService()
        self._audit_service = audit_service or AuditEventService()
        self._reconciliation_service = reconciliation_service or ReconciliationService()

    def list_plans(
        self,
        *,
        symbol: str | None = None,
        only_actionable: bool = False,
    ) -> list[RecoveryPlan]:
        records = [
            record
            for record in self._ledger_service.list_records(symbol=symbol)
            if record.status in RECOVERABLE_STATUSES
        ]
        events = self._audit_service.list_events(source="execution-orchestrator")
        latest_event_by_trade = self._build_latest_event_index(events)
        intent_by_trade = self._build_intent_action_index(events)
        candidate_by_trade = {
            candidate.trade_id: candidate
            for candidate in self._reconciliation_service.list_candidates()
        }

        plans = [
            self._build_plan(
                record,
                latest_event=latest_event_by_trade.get(record.trade_id),
                latest_intent_action=intent_by_trade.get(record.trade_id),
                reconciliation_candidate=candidate_by_trade.get(record.trade_id),
            )
            for record in records
        ]
        if only_actionable:
            plans = [plan for plan in plans if plan.auto_executable]
        return sorted(
            plans,
            key=lambda plan: (
                not plan.auto_executable,
                plan.mode != "paper",
                plan.trade_id,
            ),
        )

    def execute_actionable_plans(
        self,
        *,
        orchestrator: ExecutionOrchestrator,
        limit: int | None = None,
        symbol: str | None = None,
        trade_ids: set[str] | None = None,
    ) -> RecoveryExecutionSummary:
        plans = self.list_plans(symbol=symbol, only_actionable=True)
        if trade_ids is not None:
            plans = [plan for plan in plans if plan.trade_id in trade_ids]
        if limit is not None:
            plans = plans[:limit]

        results = []
        skipped: list[RecoveryExecutionSkip] = []
        for plan in plans:
            try:
                results.append(
                    orchestrator.recover(
                        ExecutionRecoveryRequest(
                            trade_id=plan.trade_id,
                            action=plan.recommended_action,
                            notes="auto recovery from recovery planner",
                        )
                    )
                )
            except ValueError as exc:
                skipped.append(RecoveryExecutionSkip(trade_id=plan.trade_id, reason=str(exc)))

        return RecoveryExecutionSummary(
            generated_at=datetime.now(timezone.utc),
            attempted_count=len(plans),
            executed_count=len(results),
            skipped_count=len(skipped),
            results=results,
            skipped=skipped,
        )

    def _build_plan(
        self,
        record: TradeLedgerRecord,
        *,
        latest_event: AuditEventRecord | None,
        latest_intent_action: str | None,
        reconciliation_candidate: ReconciliationCandidate | None,
    ) -> RecoveryPlan:
        reasons: list[str] = []
        missing_order_ids: list[str] = []
        exchange_statuses: list[str] = []

        if record.mode == "paper":
            reasons.append("paper trade can use deterministic recovery flow")
            return RecoveryPlan(
                trade_id=record.trade_id,
                mode=record.mode,
                symbol=record.symbol,
                status=record.status,
                recommended_action=self._infer_recovery_action(latest_intent_action, latest_event),
                auto_executable=True,
                latest_event_type=None if latest_event is None else latest_event.event_type,
                latest_event_summary=None if latest_event is None else latest_event.summary,
                reasons=reasons,
            )

        if reconciliation_candidate is None:
            reasons.append("live trade requires reconciliation context before auto recovery")
            return RecoveryPlan(
                trade_id=record.trade_id,
                mode=record.mode,
                symbol=record.symbol,
                status=record.status,
                recommended_action="manual_review",
                auto_executable=False,
                latest_event_type=None if latest_event is None else latest_event.event_type,
                latest_event_summary=None if latest_event is None else latest_event.summary,
                reasons=reasons,
            )

        missing_order_ids = reconciliation_candidate.missing_order_ids
        exchange_statuses = reconciliation_candidate.exchange_statuses
        if missing_order_ids:
            reasons.append("missing exchange reports require operator review")
            return RecoveryPlan(
                trade_id=record.trade_id,
                mode=record.mode,
                symbol=record.symbol,
                status=record.status,
                recommended_action="manual_review",
                auto_executable=False,
                latest_event_type=None if latest_event is None else latest_event.event_type,
                latest_event_summary=None if latest_event is None else latest_event.summary,
                missing_order_ids=missing_order_ids,
                exchange_statuses=exchange_statuses,
                reasons=reasons,
            )

        if reconciliation_candidate.suggested_action == "inspect_exchange":
            reasons.append("exchange or local status mismatch requires operator review")
            return RecoveryPlan(
                trade_id=record.trade_id,
                mode=record.mode,
                symbol=record.symbol,
                status=record.status,
                recommended_action="manual_review",
                auto_executable=False,
                latest_event_type=None if latest_event is None else latest_event.event_type,
                latest_event_summary=None if latest_event is None else latest_event.summary,
                missing_order_ids=missing_order_ids,
                exchange_statuses=exchange_statuses,
                reasons=reasons,
            )

        if reconciliation_candidate.suggested_action in {"resume_open", "resume_close"}:
            reasons.append(f"reconciliation suggests {reconciliation_candidate.suggested_action}")
            return RecoveryPlan(
                trade_id=record.trade_id,
                mode=record.mode,
                symbol=record.symbol,
                status=record.status,
                recommended_action=reconciliation_candidate.suggested_action,
                auto_executable=True,
                latest_event_type=None if latest_event is None else latest_event.event_type,
                latest_event_summary=None if latest_event is None else latest_event.summary,
                missing_order_ids=missing_order_ids,
                exchange_statuses=exchange_statuses,
                reasons=reasons,
            )

        reasons.append("live trade requires explicit reconciliation recovery action")
        return RecoveryPlan(
            trade_id=record.trade_id,
            mode=record.mode,
            symbol=record.symbol,
            status=record.status,
            recommended_action="manual_review",
            auto_executable=False,
            latest_event_type=None if latest_event is None else latest_event.event_type,
            latest_event_summary=None if latest_event is None else latest_event.summary,
            missing_order_ids=missing_order_ids,
            exchange_statuses=exchange_statuses,
            reasons=reasons,
        )

    def _build_latest_event_index(self, events: list[AuditEventRecord]) -> dict[str, AuditEventRecord]:
        latest_by_trade: dict[str, AuditEventRecord] = {}
        for event in events:
            trade_id = event.payload.get("trade_id")
            if not isinstance(trade_id, str):
                continue
            previous = latest_by_trade.get(trade_id)
            if previous is None or event.occurred_at > previous.occurred_at:
                latest_by_trade[trade_id] = event
        return latest_by_trade

    def _build_intent_action_index(self, events: list[AuditEventRecord]) -> dict[str, str]:
        latest_intent_by_trade: dict[str, tuple[datetime, str]] = {}
        for event in events:
            if event.event_type != "execution.intent.received":
                continue
            trade_id = event.payload.get("trade_id")
            action = event.payload.get("action")
            if not isinstance(trade_id, str) or not isinstance(action, str):
                continue
            previous = latest_intent_by_trade.get(trade_id)
            if previous is None or event.occurred_at > previous[0]:
                latest_intent_by_trade[trade_id] = (event.occurred_at, action)
        return {trade_id: action for trade_id, (_, action) in latest_intent_by_trade.items()}

    def _infer_recovery_action(
        self,
        latest_intent_action: str | None,
        latest_event: AuditEventRecord | None,
    ) -> str:
        if latest_intent_action == "close_hedge":
            return "resume_close"
        if latest_event is not None and "close" in latest_event.event_type:
            return "resume_close"
        return "resume_open"
