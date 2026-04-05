from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.audit import AuditEventRecord, AuditEventService
from app.ledger import TradeLedgerRecord, TradeLedgerService

from .schemas import HedgeHealth, HedgeOverview, HedgeOverviewItem, HedgeRebalancePlan

ACTIVE_STATUSES = {"candidate", "open", "hedged", "closing", "failed", "recovery_pending"}
RECOVERY_STATUSES = {"failed", "recovery_pending"}
MONITORING_STATUSES = {"candidate", "open", "closing"}
HEALTH_ORDER = {
    "recovery_required": 0,
    "rebalance_required": 1,
    "monitoring": 2,
    "healthy": 3,
}


class HedgeManagerService:
    def __init__(
        self,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._ledger_service = ledger_service or TradeLedgerService()
        self._audit_service = audit_service or AuditEventService()

    def overview(self, *, exposure_limit_bps: float = 50.0) -> HedgeOverview:
        records = [
            record
            for record in self._ledger_service.list_records()
            if record.status in ACTIVE_STATUSES
        ]
        latest_by_trade = self._build_latest_event_index(
            self._audit_service.list_events(source="execution-orchestrator")
        )
        items = [
            self._build_item(record, latest_by_trade.get(record.trade_id), exposure_limit_bps)
            for record in records
        ]
        ordered = sorted(
            items,
            key=lambda item: (
                HEALTH_ORDER[item.health],
                item.opened_at,
                item.trade_id,
            ),
            reverse=False,
        )
        counts = Counter(item.health for item in ordered)
        return HedgeOverview(
            generated_at=datetime.now(timezone.utc),
            exposure_limit_bps=exposure_limit_bps,
            active_trade_count=len(ordered),
            healthy_count=counts["healthy"],
            monitoring_count=counts["monitoring"],
            rebalance_required_count=counts["rebalance_required"],
            recovery_required_count=counts["recovery_required"],
            items=ordered,
        )

    def build_rebalance_plan(
        self,
        trade_id: str,
        *,
        exposure_limit_bps: float = 50.0,
    ) -> HedgeRebalancePlan:
        record = self._ledger_service.get_record(trade_id)
        if record is None:
            raise ValueError(f"trade '{trade_id}' not found in ledger")
        exposure_bps = self._calculate_exposure_bps(record)
        health = self._classify_health(record, exposure_bps, exposure_limit_bps)
        if health == "recovery_required":
            return HedgeRebalancePlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                status=record.status,
                health=health,
                exposure_limit_bps=exposure_limit_bps,
                net_exposure=record.net_exposure,
                exposure_bps=exposure_bps,
                recommended_action="recover_trade",
                notes="Trade is in recovery state and should be reconciled before rebalancing.",
            )
        if health == "monitoring":
            return HedgeRebalancePlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                status=record.status,
                health=health,
                exposure_limit_bps=exposure_limit_bps,
                net_exposure=record.net_exposure,
                exposure_bps=exposure_bps,
                recommended_action="monitor_only",
                notes="Trade is still transitioning; monitor execution before rebalancing.",
            )
        if health == "rebalance_required":
            action = "increase_perp_hedge" if record.net_exposure > 0 else "reduce_perp_hedge"
            return HedgeRebalancePlan(
                trade_id=record.trade_id,
                symbol=record.symbol,
                status=record.status,
                health=health,
                exposure_limit_bps=exposure_limit_bps,
                net_exposure=record.net_exposure,
                exposure_bps=exposure_bps,
                recommended_action=action,
                suggested_perp_notional_delta=round(record.net_exposure, 4),
                estimated_post_rebalance_exposure_bps=0.0,
                notes="Rebalance suggestion assumes perp hedge notional is adjusted to neutralize net exposure.",
            )
        return HedgeRebalancePlan(
            trade_id=record.trade_id,
            symbol=record.symbol,
            status=record.status,
            health=health,
            exposure_limit_bps=exposure_limit_bps,
            net_exposure=record.net_exposure,
            exposure_bps=exposure_bps,
            recommended_action="none",
            notes="Exposure is within configured tolerance.",
        )

    def _build_item(
        self,
        record: TradeLedgerRecord,
        latest_event: AuditEventRecord | None,
        exposure_limit_bps: float,
    ) -> HedgeOverviewItem:
        exposure_bps = self._calculate_exposure_bps(record)
        health = self._classify_health(record, exposure_bps, exposure_limit_bps)
        return HedgeOverviewItem(
            trade_id=record.trade_id,
            mode=record.mode,
            symbol=record.symbol,
            status=record.status,
            health=health,
            opened_at=record.opened_at,
            spot_notional=record.spot_notional,
            perp_notional=record.perp_notional,
            net_exposure=record.net_exposure,
            exposure_bps=exposure_bps,
            latest_event_type=None if latest_event is None else latest_event.event_type,
            latest_event_summary=None if latest_event is None else latest_event.summary,
            latest_event_severity=None if latest_event is None else latest_event.severity,
        )

    def _classify_health(
        self,
        record: TradeLedgerRecord,
        exposure_bps: float,
        exposure_limit_bps: float,
    ) -> HedgeHealth:
        if record.status in RECOVERY_STATUSES:
            return "recovery_required"
        if record.status in MONITORING_STATUSES:
            return "monitoring"
        if exposure_bps > exposure_limit_bps:
            return "rebalance_required"
        return "healthy"

    def _calculate_exposure_bps(self, record: TradeLedgerRecord) -> float:
        reference_notional = max(record.spot_notional, record.perp_notional, 1.0)
        exposure_bps = abs(record.net_exposure) / reference_notional * 10000
        return round(exposure_bps, 2)

    def _build_latest_event_index(self, events: list[AuditEventRecord]) -> dict[str, AuditEventRecord]:
        latest_by_trade: dict[str, AuditEventRecord] = {}
        for event in events:
            trade_id = event.payload.get("trade_id")
            if isinstance(trade_id, str):
                latest_by_trade[trade_id] = event
        return latest_by_trade
