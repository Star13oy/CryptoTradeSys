from __future__ import annotations

from datetime import datetime, timezone

from app.audit import AuditEventService, AuditEventStore
from app.execution import ExecutionOrchestrator
from app.hedge import HedgeManagerService
from app.ledger import TradeLedgerRecord, TradeLedgerService, TradeLedgerStore
from app.reconciliation import ExchangeOrderReportStore, ReconciliationService
from app.recovery import RecoveryExecutionSummary, RecoveryService

from .schemas import (
    CompensationExecutionItem,
    CompensationExecutionSummary,
    CompensationPlan,
    CompensationPlanListResponse,
)

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}
SAFE_DIRECT_EXECUTION_ACTIONS = {"sync_exchange_reports"}
SAFE_RECOVERY_EXECUTION_ACTIONS = {"resume_open", "resume_close"}


class CompensationService:
    def __init__(
        self,
        *,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
        report_store: ExchangeOrderReportStore | None = None,
        reconciliation_service: ReconciliationService | None = None,
        recovery_service: RecoveryService | None = None,
        hedge_service: HedgeManagerService | None = None,
    ) -> None:
        self._ledger_service = ledger_service or TradeLedgerService(TradeLedgerStore())
        self._audit_service = audit_service or AuditEventService(AuditEventStore())
        self._report_store = report_store or ExchangeOrderReportStore()
        self._reconciliation_service = reconciliation_service or ReconciliationService(
            self._report_store,
            self._ledger_service,
            self._audit_service,
        )
        self._recovery_service = recovery_service or RecoveryService(
            self._ledger_service,
            self._audit_service,
            self._reconciliation_service,
        )
        self._hedge_service = hedge_service or HedgeManagerService(
            self._ledger_service,
            self._audit_service,
        )

    def list_plans(
        self,
        *,
        symbol: str | None = None,
        only_actionable: bool = False,
        exposure_limit_bps: float = 50.0,
    ) -> list[CompensationPlan]:
        records = self._ledger_service.list_records(mode="live", symbol=symbol)
        candidates_by_trade = {
            candidate.trade_id: candidate
            for candidate in self._reconciliation_service.list_candidates(symbol=symbol)
        }
        recovery_by_trade = {
            plan.trade_id: plan
            for plan in self._recovery_service.list_plans(symbol=symbol)
        }

        plans = [
            self._build_plan(
                record,
                candidate=candidates_by_trade.get(record.trade_id),
                recovery_plan=recovery_by_trade.get(record.trade_id),
                exposure_limit_bps=exposure_limit_bps,
            )
            for record in records
        ]
        if only_actionable:
            plans = [plan for plan in plans if plan.actionable]
        return sorted(
            plans,
            key=lambda item: (
                PRIORITY_ORDER[item.priority],
                item.trade_id,
            ),
        )

    def response(
        self,
        *,
        symbol: str | None = None,
        only_actionable: bool = False,
        exposure_limit_bps: float = 50.0,
    ) -> CompensationPlanListResponse:
        return CompensationPlanListResponse(
            generated_at=datetime.now(timezone.utc),
            plans=self.list_plans(
                symbol=symbol,
                only_actionable=only_actionable,
                exposure_limit_bps=exposure_limit_bps,
            ),
        )

    def execute_safe_actions(
        self,
        *,
        orchestrator: ExecutionOrchestrator,
        symbol: str | None = None,
        limit: int | None = None,
        exposure_limit_bps: float = 50.0,
    ) -> CompensationExecutionSummary:
        plans = self.list_plans(
            symbol=symbol,
            only_actionable=True,
            exposure_limit_bps=exposure_limit_bps,
        )
        if limit is not None:
            plans = plans[:limit]

        result_by_trade: dict[str, CompensationExecutionItem] = {}
        recovery_plans: list[CompensationPlan] = []
        for plan in plans:
            action = plan.recommended_action
            if action in SAFE_DIRECT_EXECUTION_ACTIONS:
                result_by_trade[plan.trade_id] = self._execute_direct_safe_action(plan)
                continue
            if action in SAFE_RECOVERY_EXECUTION_ACTIONS:
                recovery_plans.append(plan)
                continue
            if action == "rebalance_hedge":
                result_by_trade[plan.trade_id] = self._execute_rebalance_action(
                    plan,
                    orchestrator=orchestrator,
                )
                continue
            result_by_trade[plan.trade_id] = CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=action,
                outcome="skipped",
                reason="action is not in compensation safe execute allowlist",
                details={},
            )

        if recovery_plans:
            result_by_trade.update(
                self._execute_recovery_actions(
                    plans=recovery_plans,
                    orchestrator=orchestrator,
                )
            )

        ordered_results = [
            result_by_trade[plan.trade_id]
            for plan in plans
            if plan.trade_id in result_by_trade
        ]
        return CompensationExecutionSummary(
            generated_at=datetime.now(timezone.utc),
            attempted_count=len(plans),
            executed_count=sum(1 for item in ordered_results if item.outcome == "executed"),
            skipped_count=sum(1 for item in ordered_results if item.outcome == "skipped"),
            failed_count=sum(1 for item in ordered_results if item.outcome == "failed"),
            results=ordered_results,
        )

    def _execute_direct_safe_action(self, plan: CompensationPlan) -> CompensationExecutionItem:
        try:
            synced_reports = self._reconciliation_service.sync_reports_for_trade(plan.trade_id)
        except ValueError as exc:
            return CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=plan.recommended_action,
                outcome="failed",
                reason=str(exc),
                details={},
            )

        return CompensationExecutionItem(
            trade_id=plan.trade_id,
            symbol=plan.symbol,
            action=plan.recommended_action,
            outcome="executed",
            reason="synced exchange reports",
            details={
                "synced_report_count": len(synced_reports),
            },
        )

    def _execute_rebalance_action(
        self,
        plan: CompensationPlan,
        *,
        orchestrator: ExecutionOrchestrator,
    ) -> CompensationExecutionItem:
        perp_notional_delta = float(plan.details.get("suggested_perp_notional_delta") or 0.0)
        if perp_notional_delta == 0:
            return CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=plan.recommended_action,
                outcome="skipped",
                reason="missing suggested_perp_notional_delta for rebalance action",
                details={},
            )
        reference_price = self._infer_latest_perp_reference_price(plan.trade_id)
        if reference_price is None or reference_price <= 0:
            return CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=plan.recommended_action,
                outcome="skipped",
                reason="cannot infer perp reference price for rebalance action",
                details={},
            )
        perp_quantity = round(abs(perp_notional_delta) / reference_price, 6)
        if perp_quantity <= 0:
            return CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=plan.recommended_action,
                outcome="skipped",
                reason="calculated perp quantity is zero",
                details={"reference_price": reference_price},
            )
        try:
            result = orchestrator.rebalance_hedge(
                trade_id=plan.trade_id,
                perp_notional_delta=perp_notional_delta,
                perp_quantity=perp_quantity,
                notes="auto compensation rebalance",
            )
        except ValueError as exc:
            return CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=plan.recommended_action,
                outcome="failed",
                reason=str(exc),
                details={"reference_price": reference_price, "perp_quantity": perp_quantity},
            )
        return CompensationExecutionItem(
            trade_id=plan.trade_id,
            symbol=plan.symbol,
            action=plan.recommended_action,
            outcome="executed",
            reason="executed hedge rebalance",
            details={
                "reference_price": reference_price,
                "perp_quantity": perp_quantity,
                "status": result.status,
            },
        )

    def _execute_recovery_actions(
        self,
        *,
        plans: list[CompensationPlan],
        orchestrator: ExecutionOrchestrator,
    ) -> dict[str, CompensationExecutionItem]:
        trade_ids = {plan.trade_id for plan in plans}
        try:
            recovery_summary = self._recovery_service.execute_actionable_plans(
                orchestrator=orchestrator,
                trade_ids=trade_ids,
            )
        except ValueError as exc:
            return {
                plan.trade_id: CompensationExecutionItem(
                    trade_id=plan.trade_id,
                    symbol=plan.symbol,
                    action=plan.recommended_action,
                    outcome="failed",
                    reason=str(exc),
                    details={},
                )
                for plan in plans
            }
        if isinstance(recovery_summary, dict):
            recovery_summary = RecoveryExecutionSummary.model_validate(recovery_summary)

        executed_by_trade = {
            result.trade_id: result
            for result in recovery_summary.results
        }
        skipped_by_trade = {
            item.trade_id: item
            for item in recovery_summary.skipped
        }

        results: dict[str, CompensationExecutionItem] = {}
        for plan in plans:
            executed = executed_by_trade.get(plan.trade_id)
            if executed is not None:
                results[plan.trade_id] = CompensationExecutionItem(
                    trade_id=plan.trade_id,
                    symbol=plan.symbol,
                    action=plan.recommended_action,
                    outcome="executed",
                    reason="delegated to recovery safe auto execution",
                    details={
                        "execution_action": executed.action,
                        "status": executed.status,
                    },
                )
                continue
            skipped = skipped_by_trade.get(plan.trade_id)
            if skipped is not None:
                results[plan.trade_id] = CompensationExecutionItem(
                    trade_id=plan.trade_id,
                    symbol=plan.symbol,
                    action=plan.recommended_action,
                    outcome="skipped",
                    reason=skipped.reason,
                    details={},
                )
                continue
            results[plan.trade_id] = CompensationExecutionItem(
                trade_id=plan.trade_id,
                symbol=plan.symbol,
                action=plan.recommended_action,
                outcome="failed",
                reason="recovery execution returned no result for actionable plan",
                details={},
            )
        return results

    def _infer_latest_perp_reference_price(self, trade_id: str) -> float | None:
        reports = [
            report
            for report in self._report_store.list()
            if report.trade_id == trade_id
            and report.leg == "perp"
            and report.executed_qty > 0
            and report.cum_quote_qty > 0
        ]
        if not reports:
            return None
        latest = max(reports, key=lambda report: (report.updated_at, report.report_id))
        return latest.cum_quote_qty / latest.executed_qty

    def _build_plan(
        self,
        record: TradeLedgerRecord,
        *,
        candidate,
        recovery_plan,
        exposure_limit_bps: float,
    ) -> CompensationPlan:
        if candidate is not None and candidate.missing_order_ids:
            return CompensationPlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                mode=record.mode,
                local_status=record.status,
                recommended_action="sync_exchange_reports",
                priority="critical",
                actionable=True,
                reason="missing exchange reports",
                details={
                    "missing_order_ids": candidate.missing_order_ids,
                    "expected_order_ids": candidate.expected_order_ids,
                },
            )

        if recovery_plan is not None and recovery_plan.recommended_action in {"resume_open", "resume_close"}:
            return CompensationPlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                mode=record.mode,
                local_status=record.status,
                recommended_action=recovery_plan.recommended_action,
                priority="critical" if recovery_plan.auto_executable else "high",
                actionable=recovery_plan.auto_executable,
                reason="recovery plan is actionable" if recovery_plan.auto_executable else "recovery requires operator decision",
                details={
                    "exchange_statuses": recovery_plan.exchange_statuses,
                    "missing_order_ids": recovery_plan.missing_order_ids,
                    "reasons": recovery_plan.reasons,
                },
            )

        if recovery_plan is not None and recovery_plan.recommended_action == "manual_review":
            return CompensationPlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                mode=record.mode,
                local_status=record.status,
                recommended_action="manual_review",
                priority="high" if record.status in {"failed", "recovery_pending"} else "low",
                actionable=False,
                reason="recovery context is ambiguous",
                details={
                    "exchange_statuses": recovery_plan.exchange_statuses,
                    "missing_order_ids": recovery_plan.missing_order_ids,
                    "reasons": recovery_plan.reasons,
                },
            )

        hedge_plan = self._hedge_service.build_rebalance_plan(
            record.trade_id,
            exposure_limit_bps=exposure_limit_bps,
        )
        if hedge_plan.recommended_action in {"increase_perp_hedge", "reduce_perp_hedge"}:
            return CompensationPlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                mode=record.mode,
                local_status=record.status,
                recommended_action="rebalance_hedge",
                priority="medium",
                actionable=True,
                reason="net exposure drift exceeds tolerance",
                details={
                    "hedge_action": hedge_plan.recommended_action,
                    "suggested_perp_notional_delta": hedge_plan.suggested_perp_notional_delta,
                    "estimated_post_rebalance_exposure_bps": hedge_plan.estimated_post_rebalance_exposure_bps,
                },
            )

        return CompensationPlan(
            trade_id=record.trade_id,
            symbol=record.symbol,
            mode=record.mode,
            local_status=record.status,
            recommended_action="none",
            priority="low",
            actionable=False,
            reason="no compensation action required",
            details={},
        )
