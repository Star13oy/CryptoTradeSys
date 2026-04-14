from __future__ import annotations
from datetime import datetime, timezone
import uuid

from app.audit import AuditEventService, AuditEventRecord
from app.execution.schemas import ExecutionIntentRequest
from app.ledger import TradeLedgerService
from app.risk.policy import OpportunityRiskPolicy
from app.schemas.market import MarketSnapshot, OpportunityScore
from app.strategy.funding_arb import FundingArbStrategy
from app.safety.service import SafetyService

from .schemas import SchedulerCycleAction, SchedulerCycleResult


class SchedulerService:
    def __init__(
        self,
        *,
        safety_service: SafetyService | None = None,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
        strategy: FundingArbStrategy | None = None,
        risk_policy: OpportunityRiskPolicy | None = None,
    ) -> None:
        self._safety = safety_service or SafetyService()
        self._ledger = ledger_service or TradeLedgerService()
        self._audit = audit_service or AuditEventService()
        self._strategy = strategy or FundingArbStrategy()
        self._risk_policy = risk_policy or OpportunityRiskPolicy()

    def run_cycle(
        self,
        *,
        snapshots: list[MarketSnapshot],
        orchestrator,
        app_mode: str = "paper",
        max_open_positions: int = 3,
        max_total_notional: float = 25000.0,
    ) -> SchedulerCycleResult:
        started_at = datetime.now(timezone.utc)
        actions: list[SchedulerCycleAction] = []
        executed = 0
        skipped = 0
        failed = 0

        # 1. Check safety state
        try:
            self._safety.check_can_open()
        except ValueError:
            # System frozen or no new positions - still check close signals
            pass

        # 2. Score all snapshots
        scored = self._strategy.score_snapshots(snapshots)
        score_map = {s.symbol: s for s in scored}

        # 3. Count active positions
        records = self._ledger.list_records()
        active = [r for r in records if r.status in {"hedged", "open"}]
        active_count = len(active)
        active_notional = sum(max(r.spot_notional, r.perp_notional) for r in active)

        # 4. Open new positions for "allow" opportunities
        for score in scored:
            if score.risk_tag == "blocked":
                continue
            decision = self._risk_policy.evaluate(score)
            if decision.decision != "allow":
                continue
            # Check limits
            if active_count >= max_open_positions:
                break
            if active_notional >= max_total_notional:
                break
            # Check safety
            try:
                self._safety.check_can_open()
            except ValueError:
                break
            # Generate trade
            trade_id = f"sch-{uuid.uuid4().hex[:8]}"
            notional = 1000.0  # default per-trade notional
            try:
                req = ExecutionIntentRequest(
                    trade_id=trade_id,
                    mode=app_mode,
                    strategy_id=self._strategy.strategy_id,
                    symbol=score.symbol,
                    action="open_hedge",
                    spot_notional=notional,
                    perp_notional=notional,
                )
                orchestrator.execute(req)
                executed += 1
                active_count += 1
                active_notional += notional
                actions.append(SchedulerCycleAction(
                    action="open_hedge", symbol=score.symbol, trade_id=trade_id,
                    score=score.score, risk_decision=decision.decision, reason="scheduler auto-open",
                ))
            except Exception as exc:
                failed += 1
                actions.append(SchedulerCycleAction(
                    action="open_hedge", symbol=score.symbol, trade_id=trade_id,
                    score=score.score, risk_decision=decision.decision, reason=f"failed: {exc}",
                ))

        # 5. Check close signals for existing hedged positions
        for record in active:
            if record.status != "hedged":
                continue
            current_score = score_map.get(record.symbol)
            if current_score is None:
                continue
            try:
                self._safety.check_can_operate(trade_id=record.trade_id)
            except ValueError:
                continue
            close_reason = self._evaluate_close_signal(record, current_score)
            if close_reason is None:
                continue
            try:
                req = ExecutionIntentRequest(
                    trade_id=record.trade_id,
                    mode=record.mode,
                    strategy_id=self._strategy.strategy_id,
                    symbol=record.symbol,
                    action="close_hedge",
                )
                orchestrator.execute(req)
                executed += 1
                actions.append(SchedulerCycleAction(
                    action="close_hedge", symbol=record.symbol, trade_id=record.trade_id,
                    score=current_score.score, risk_decision="auto", reason=close_reason,
                ))
            except Exception as exc:
                failed += 1
                actions.append(SchedulerCycleAction(
                    action="close_hedge", symbol=record.symbol, trade_id=record.trade_id,
                    score=current_score.score, risk_decision="auto", reason=f"failed: {exc}",
                ))

        finished_at = datetime.now(timezone.utc)
        result = SchedulerCycleResult(
            cycle_started_at=started_at,
            cycle_finished_at=finished_at,
            snapshots_evaluated=len(scored),
            positions_evaluated=len(active),
            actions_generated=len(actions),
            actions_executed=executed,
            actions_skipped=skipped,
            actions_failed=failed,
            actions=actions,
        )
        # Audit log
        self._audit.save_record(AuditEventRecord(
            event_id=f"scheduler-cycle-{started_at.isoformat()}",
            event_type="scheduler.cycle.completed",
            severity="info",
            source="strategy-scheduler",
            occurred_at=finished_at,
            summary=f"调度周期完成: 评估{len(scored)}个标的, 执行{executed}个动作",
            payload={"evaluated": len(scored), "executed": executed, "failed": failed},
            tags=["scheduler"],
        ))
        return result

    def _evaluate_close_signal(self, record, current_score: OpportunityScore) -> str | None:
        # Funding rate reversed: was positive, now negative (or vice versa)
        if current_score.funding_rate < 0:
            return "funding_rate_reversed"
        # Net edge turned negative
        if current_score.net_edge_bps < 0:
            return "net_edge_negative"
        return None
