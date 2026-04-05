from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.audit import AuditEventRecord, AuditEventService
from app.ledger import TradeLedgerRecord, TradeLedgerService

from .schemas import ExecutionIntentRequest, ExecutionResult


class ExecutionOrchestrator:
    def __init__(
        self,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._ledger_service = ledger_service or TradeLedgerService()
        self._audit_service = audit_service or AuditEventService()

    def execute(self, request: ExecutionIntentRequest) -> ExecutionResult:
        occurred_at = datetime.now(timezone.utc)
        if request.action == "open_hedge":
            return self._execute_open(request, occurred_at)
        return self._execute_close(request, occurred_at)

    def _execute_open(self, request: ExecutionIntentRequest, base_time: datetime) -> ExecutionResult:
        events: list[AuditEventRecord] = []
        events.append(
            self._record_event(
                event_type="execution.intent.received",
                summary=f"Received {request.action} intent for {request.symbol}",
                occurred_at=base_time,
                payload=request.model_dump(mode="json"),
                tags=["execution", request.mode, request.action],
            )
        )

        record = TradeLedgerRecord(
            trade_id=request.trade_id,
            mode=request.mode,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            status="candidate",
            opened_at=base_time,
            net_exposure=self._resolve_net_exposure(request),
            spot_notional=request.spot_notional,
            perp_notional=request.perp_notional,
            realized_pnl=0.0,
            notes=request.notes,
        )
        self._ledger_service.save_record(record)

        record = record.model_copy(update={"status": "open"})
        self._ledger_service.save_record(record)
        events.append(
            self._record_event(
                event_type="execution.leg.spot.filled",
                summary=f"Spot leg filled for {request.symbol}",
                occurred_at=base_time + timedelta(milliseconds=1),
                payload={"trade_id": request.trade_id, "spot_notional": request.spot_notional},
                tags=["execution", "spot", request.mode],
            )
        )

        if request.simulate_perp_leg_failure:
            record = record.model_copy(update={"status": "failed"})
            self._ledger_service.save_record(record)
            events.append(
                self._record_event(
                    event_type="execution.leg.perp.failed",
                    summary=f"Perp leg failed for {request.symbol}",
                    severity="error",
                    occurred_at=base_time + timedelta(milliseconds=2),
                    payload={"trade_id": request.trade_id, "perp_notional": request.perp_notional},
                    tags=["execution", "perp", "failure", request.mode],
                )
            )
            events.append(
                self._record_event(
                    event_type="execution.recovery.required",
                    summary=f"Recovery required after partial fill on {request.symbol}",
                    severity="critical",
                    occurred_at=base_time + timedelta(milliseconds=3),
                    payload={"trade_id": request.trade_id, "status": "failed"},
                    tags=["execution", "recovery", request.mode],
                )
            )
            return ExecutionResult(
                trade_id=request.trade_id,
                action=request.action,
                mode=request.mode,
                symbol=request.symbol,
                status="failed",
                ledger_record=record,
                events=events,
                executed_at=base_time + timedelta(milliseconds=3),
            )

        record = record.model_copy(update={"status": "hedged"})
        self._ledger_service.save_record(record)
        events.append(
            self._record_event(
                event_type="execution.leg.perp.filled",
                summary=f"Perp leg filled for {request.symbol}",
                occurred_at=base_time + timedelta(milliseconds=2),
                payload={"trade_id": request.trade_id, "perp_notional": request.perp_notional},
                tags=["execution", "perp", request.mode],
            )
        )
        if request.mode == "live":
            events.append(
                self._record_event(
                    event_type="execution.live.stubbed",
                    summary=f"Live execution adapter is not wired yet for {request.symbol}",
                    severity="warning",
                    occurred_at=base_time + timedelta(milliseconds=3),
                    payload={"trade_id": request.trade_id},
                    tags=["execution", "live", "stub"],
                )
            )
            completed_at = base_time + timedelta(milliseconds=4)
        else:
            completed_at = base_time + timedelta(milliseconds=3)
        events.append(
            self._record_event(
                event_type="execution.completed",
                summary=f"Hedge open completed for {request.symbol}",
                occurred_at=completed_at,
                payload={"trade_id": request.trade_id, "status": "hedged"},
                tags=["execution", "completed", request.mode],
            )
        )
        return ExecutionResult(
            trade_id=request.trade_id,
            action=request.action,
            mode=request.mode,
            symbol=request.symbol,
            status="hedged",
            ledger_record=record,
            events=events,
            executed_at=completed_at,
        )

    def _execute_close(self, request: ExecutionIntentRequest, base_time: datetime) -> ExecutionResult:
        existing = self._ledger_service.get_record(request.trade_id)
        if existing is None:
            raise ValueError(f"trade '{request.trade_id}' not found in ledger")

        events: list[AuditEventRecord] = []
        events.append(
            self._record_event(
                event_type="execution.intent.received",
                summary=f"Received {request.action} intent for {request.symbol}",
                occurred_at=base_time,
                payload=request.model_dump(mode="json"),
                tags=["execution", request.mode, request.action],
            )
        )

        closing = existing.model_copy(update={"status": "closing"})
        self._ledger_service.save_record(closing)
        events.append(
            self._record_event(
                event_type="execution.close.started",
                summary=f"Close started for {request.symbol}",
                occurred_at=base_time + timedelta(milliseconds=1),
                payload={"trade_id": request.trade_id},
                tags=["execution", "close", request.mode],
            )
        )

        closed = closing.model_copy(
            update={
                "status": "closed",
                "closed_at": base_time + timedelta(milliseconds=2),
                "realized_pnl": request.realized_pnl,
                "notes": request.notes or closing.notes,
            }
        )
        self._ledger_service.save_record(closed)
        events.append(
            self._record_event(
                event_type="execution.close.completed",
                summary=f"Close completed for {request.symbol}",
                occurred_at=base_time + timedelta(milliseconds=2),
                payload={"trade_id": request.trade_id, "realized_pnl": request.realized_pnl},
                tags=["execution", "close", "completed", request.mode],
            )
        )
        return ExecutionResult(
            trade_id=request.trade_id,
            action=request.action,
            mode=request.mode,
            symbol=request.symbol,
            status="closed",
            ledger_record=closed,
            events=events,
            executed_at=base_time + timedelta(milliseconds=2),
        )

    def _record_event(
        self,
        *,
        event_type: str,
        summary: str,
        occurred_at: datetime,
        payload: dict,
        tags: list[str],
        severity: str = "info",
    ) -> AuditEventRecord:
        return self._audit_service.record_event(
            event_type=event_type,
            source="execution-orchestrator",
            summary=summary,
            severity=severity,
            occurred_at=occurred_at,
            payload=payload,
            tags=tags,
        )

    def _resolve_net_exposure(self, request: ExecutionIntentRequest) -> float:
        if request.net_exposure is not None:
            return request.net_exposure
        return round(request.spot_notional - request.perp_notional, 4)
