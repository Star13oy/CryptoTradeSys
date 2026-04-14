from __future__ import annotations
from datetime import datetime, timezone

from app.audit import AuditEventService, AuditEventRecord
from app.execution.schemas import ExecutionIntentRequest
from app.ledger import TradeLedgerService
from app.safety.service import SafetyService
from app.schemas.market import OpportunityScore
from app.strategy.funding_arb import FundingArbStrategy

from .schemas import HoldingAlert, HoldingMonitorAction, HoldingMonitorResult


class HoldingMonitorService:
    def __init__(
        self,
        *,
        safety_service: SafetyService | None = None,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._safety = safety_service or SafetyService()
        self._ledger = ledger_service or TradeLedgerService()
        self._audit = audit_service or AuditEventService()

    def run_monitor_cycle(
        self,
        *,
        current_scores: list[OpportunityScore],
        orchestrator,
        max_hold_periods: float = 72.0,
    ) -> HoldingMonitorResult:
        started_at = datetime.now(timezone.utc)
        actions: list[HoldingMonitorAction] = []
        executed = 0
        skipped = 0
        failed = 0

        score_map = {s.symbol: s for s in current_scores}
        records = self._ledger.list_records()
        hedged = [r for r in records if r.status == "hedged"]

        for record in hedged:
            current_score = score_map.get(record.symbol)
            alert = self._check_position(record, current_score, max_hold_periods)
            if alert is None:
                continue

            if alert.severity == "warning":
                # Just log, don't close
                actions.append(HoldingMonitorAction(
                    trade_id=record.trade_id, symbol=record.symbol,
                    action="monitor", alert=alert, outcome="skipped", reason="warning only",
                ))
                continue

            # Critical alert: attempt to close
            try:
                self._safety.check_can_operate(trade_id=record.trade_id)
            except ValueError as e:
                skipped += 1
                actions.append(HoldingMonitorAction(
                    trade_id=record.trade_id, symbol=record.symbol,
                    action="close_hedge", alert=alert, outcome="skipped", reason=str(e),
                ))
                continue

            try:
                req = ExecutionIntentRequest(
                    trade_id=record.trade_id,
                    mode=record.mode,
                    strategy_id="holding-monitor",
                    symbol=record.symbol,
                    action="close_hedge",
                )
                orchestrator.execute(req)
                executed += 1
                actions.append(HoldingMonitorAction(
                    trade_id=record.trade_id, symbol=record.symbol,
                    action="close_hedge", alert=alert, outcome="executed", reason=alert.detail,
                ))
            except Exception as exc:
                failed += 1
                actions.append(HoldingMonitorAction(
                    trade_id=record.trade_id, symbol=record.symbol,
                    action="close_hedge", alert=alert, outcome="failed", reason=str(exc),
                ))

        finished_at = datetime.now(timezone.utc)
        result = HoldingMonitorResult(
            evaluated_count=len(hedged),
            alert_count=len(actions),
            close_executed=executed,
            close_skipped=skipped,
            close_failed=failed,
            actions=actions,
            cycle_started_at=started_at,
            cycle_finished_at=finished_at,
        )

        # Audit
        self._audit.save_record(AuditEventRecord(
            event_id=f"monitor-cycle-{started_at.isoformat()}",
            event_type="monitor.cycle.completed",
            severity="info",
            source="holding-monitor",
            occurred_at=finished_at,
            summary=f"监控周期完成: 评估{len(hedged)}个持仓, {len(actions)}个告警, 执行{executed}个平仓",
            payload={"evaluated": len(hedged), "alerts": len(actions), "executed": executed},
            tags=["monitor"],
        ))
        return result

    def _check_position(self, record, current_score: OpportunityScore | None, max_hold_periods: float) -> HoldingAlert | None:
        now = datetime.now(timezone.utc)
        # Calculate hold periods (8-hour funding periods)
        hold_seconds = (now - record.opened_at).total_seconds() if record.opened_at else 0
        hold_periods = hold_seconds / 28800.0  # 8 hours = 28800 seconds

        current_funding = current_score.funding_rate if current_score else 0.0

        # 1. Funding rate reversed: was positive (short perp gets paid), now negative
        if current_funding < 0 and hold_periods > 1:
            return HoldingAlert(
                trade_id=record.trade_id, symbol=record.symbol,
                alert_type="funding_reversed", severity="critical",
                detail=f"资金费率反转: 当前 {current_funding:.6f}",
                current_funding_rate=current_funding, hold_periods=hold_periods,
                max_hold_periods=max_hold_periods,
            )

        # 2. Max hold exceeded
        if hold_periods > max_hold_periods:
            return HoldingAlert(
                trade_id=record.trade_id, symbol=record.symbol,
                alert_type="max_hold_exceeded", severity="critical",
                detail=f"超过最大持仓周期: {hold_periods:.1f}/{max_hold_periods:.0f}",
                current_funding_rate=current_funding, hold_periods=hold_periods,
                max_hold_periods=max_hold_periods,
            )

        # 3. Net edge negative
        if current_score and current_score.net_edge_bps < 0:
            return HoldingAlert(
                trade_id=record.trade_id, symbol=record.symbol,
                alert_type="negative_edge", severity="critical",
                detail=f"净边缘转负: {current_score.net_edge_bps:.1f} bps",
                current_funding_rate=current_funding, hold_periods=hold_periods,
                max_hold_periods=max_hold_periods,
            )

        # 4. Score deteriorated (warning only)
        if current_score and current_score.score < 10:
            return HoldingAlert(
                trade_id=record.trade_id, symbol=record.symbol,
                alert_type="score_deteriorated", severity="warning",
                detail=f"评分恶化: {current_score.score:.1f}",
                current_funding_rate=current_funding, hold_periods=hold_periods,
                max_hold_periods=max_hold_periods,
            )

        return None
