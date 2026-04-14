from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass, field

from app.audit import AuditEventService, AuditEventRecord

@dataclass
class SafetyState:
    frozen: bool = False
    new_positions_allowed: bool = True
    reduce_only_trades: set[str] = field(default_factory=set)
    paused_trades: set[str] = field(default_factory=set)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class SafetyService:
    def __init__(self, audit_service: AuditEventService | None = None) -> None:
        self._state = SafetyState()
        self._audit = audit_service or AuditEventService()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _record(self, event_type: str, summary: str, severity: str = "info", **payload) -> None:
        record = AuditEventRecord(
            event_id=f"safety-{event_type}-{self._state.updated_at.isoformat()}",
            event_type=event_type,
            severity=severity,
            source="safety",
            occurred_at=self._now(),
            summary=summary,
            payload=payload,
            tags=["safety"],
        )
        self._audit.save_record(record)

    def get_state(self) -> SafetyStateSnapshot:
        from .schemas import SafetyStateSnapshot
        return SafetyStateSnapshot(
            frozen=self._state.frozen,
            new_positions_allowed=self._state.new_positions_allowed,
            reduce_only_trades=sorted(self._state.reduce_only_trades),
            paused_trades=sorted(self._state.paused_trades),
            updated_at=self._state.updated_at,
        )

    def freeze_all(self, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.frozen = True
        self._state.updated_at = self._now()
        self._record("safety.frozen", f"全账户冻结: {reason or '手动触发'}", severity="critical")
        return self.get_state()

    def unfreeze_all(self, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.frozen = False
        self._state.updated_at = self._now()
        self._record("safety.unfrozen", f"解除冻结: {reason or '手动触发'}", severity="info")
        return self.get_state()

    def stop_new_positions(self, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.new_positions_allowed = False
        self._state.updated_at = self._now()
        self._record("safety.new_positions_stopped", f"停止新开仓: {reason or '手动触发'}", severity="warning")
        return self.get_state()

    def resume_new_positions(self, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.new_positions_allowed = True
        self._state.updated_at = self._now()
        self._record("safety.new_positions_resumed", f"恢复新开仓: {reason or '手动触发'}", severity="info")
        return self.get_state()

    def set_reduce_only(self, trade_id: str, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.reduce_only_trades.add(trade_id)
        self._state.updated_at = self._now()
        self._record("safety.reduce_only_set", f"设置仅减仓: {trade_id}", severity="warning", trade_id=trade_id)
        return self.get_state()

    def unset_reduce_only(self, trade_id: str, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.reduce_only_trades.discard(trade_id)
        self._state.updated_at = self._now()
        self._record("safety.reduce_only_cleared", f"取消仅减仓: {trade_id}", severity="info", trade_id=trade_id)
        return self.get_state()

    def pause_trade(self, trade_id: str, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.paused_trades.add(trade_id)
        self._state.updated_at = self._now()
        self._record("safety.trade_paused", f"暂停交易: {trade_id}", severity="warning", trade_id=trade_id)
        return self.get_state()

    def unpause_trade(self, trade_id: str, reason: str | None = None) -> SafetyStateSnapshot:
        self._state.paused_trades.discard(trade_id)
        self._state.updated_at = self._now()
        self._record("safety.trade_unpaused", f"恢复交易: {trade_id}", severity="info", trade_id=trade_id)
        return self.get_state()

    def check_can_open(self) -> None:
        """Raises ValueError if opening new positions is blocked."""
        if self._state.frozen:
            raise ValueError("account is frozen: all trading stopped")
        if not self._state.new_positions_allowed:
            raise ValueError("new positions are currently blocked")

    def check_can_operate(self, trade_id: str | None = None) -> None:
        """Raises ValueError if the trade or account is paused/frozen."""
        if self._state.frozen:
            raise ValueError("account is frozen: all trading stopped")
        if trade_id and trade_id in self._state.paused_trades:
            raise ValueError(f"trade '{trade_id}' is paused")

    def is_reduce_only(self, trade_id: str) -> bool:
        return trade_id in self._state.reduce_only_trades

    def emergency_close_all(self, *, orchestrator, ledger_service) -> EmergencyCloseResult:
        """Close all hedged/open positions immediately."""
        from .schemas import EmergencyCloseResult
        result = EmergencyCloseResult()
        records = ledger_service.list_records()
        active = [r for r in records if r.status in {"hedged", "open"}]
        if not active:
            self._record("safety.emergency_close_all", "紧急平仓: 无活跃持仓", severity="warning")
            return result
        self._record("safety.emergency_close_all", f"紧急平仓: 开始平仓 {len(active)} 个持仓", severity="critical")
        for record in active:
            try:
                self.check_can_operate(record.trade_id)
                from app.execution.schemas import ExecutionIntentRequest
                req = ExecutionIntentRequest(
                    trade_id=record.trade_id,
                    mode=record.mode,
                    action="close_hedge",
                    symbol=record.symbol,
                )
                orchestrator.execute(req)
                result.closed_count += 1
                result.results.append({"trade_id": record.trade_id, "outcome": "closed"})
            except ValueError as e:
                result.skipped_count += 1
                result.results.append({"trade_id": record.trade_id, "outcome": "skipped", "reason": str(e)})
            except Exception as e:
                result.failed_count += 1
                result.results.append({"trade_id": record.trade_id, "outcome": "failed", "reason": str(e)})
        return result

    def panic_sell(self, trade_id: str, *, orchestrator, ledger_service) -> EmergencyCloseResult:
        """Force close a single position immediately."""
        from .schemas import EmergencyCloseResult
        result = EmergencyCloseResult()
        record = ledger_service.get_record(trade_id)
        if record is None:
            raise ValueError(f"trade '{trade_id}' not found")
        if record.status not in {"hedged", "open"}:
            result.skipped_count = 1
            result.results.append({"trade_id": trade_id, "outcome": "skipped", "reason": f"status is {record.status}"})
            return result
        self._record("safety.panic_sell", f"强制平仓: {trade_id} ({record.symbol})", severity="critical", trade_id=trade_id)
        from app.execution.schemas import ExecutionIntentRequest
        req = ExecutionIntentRequest(
            trade_id=trade_id,
            mode=record.mode,
            action="close_hedge",
            symbol=record.symbol,
        )
        orchestrator.execute(req)
        result.closed_count = 1
        result.results.append({"trade_id": trade_id, "outcome": "closed"})
        return result
