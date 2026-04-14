from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import TYPE_CHECKING

from app.audit import AuditEventRecord, AuditEventService
from app.ledger import TradeLedgerRecord, TradeLedgerService

from .adapters import BinanceLiveExecutionAdapter
from .circuit_breaker import ExecutionCircuitBreakerService
from .schemas import ExecutionIntentRequest, ExecutionLegReport, ExecutionRecoveryRequest, ExecutionResult

if TYPE_CHECKING:
    from app.safety.service import SafetyService


class ExecutionOrchestrator:
    def __init__(
        self,
        ledger_service: TradeLedgerService | None = None,
        audit_service: AuditEventService | None = None,
        live_adapter: BinanceLiveExecutionAdapter | None = None,
        circuit_breaker: ExecutionCircuitBreakerService | None = None,
        safety_service: SafetyService | None = None,
        *,
        live_execution_enabled: bool = False,
        live_symbol_allowlist: set[str] | None = None,
        max_live_notional: float | None = None,
    ) -> None:
        self._ledger_service = ledger_service or TradeLedgerService()
        self._audit_service = audit_service or AuditEventService()
        self._live_adapter = live_adapter
        self._circuit_breaker = circuit_breaker
        self._safety_service = safety_service
        self._live_execution_enabled = live_execution_enabled
        self._live_symbol_allowlist = live_symbol_allowlist or set()
        self._max_live_notional = max_live_notional

    def execute(self, request: ExecutionIntentRequest) -> ExecutionResult:
        occurred_at = datetime.now(timezone.utc)
        idempotent = self._handle_idempotent_replay(request, occurred_at)
        if idempotent is not None:
            return idempotent

        # Safety gate
        if self._safety_service is not None:
            if request.action == "open_hedge":
                self._safety_service.check_can_open()
            else:
                self._safety_service.check_can_operate(trade_id=request.trade_id)

        if request.mode == "live":
            self._validate_live_request(request)
            self._ensure_live_execution_allowed(request, occurred_at)
            try:
                result = self._execute_live(request, occurred_at)
            except Exception as exc:
                self._record_live_circuit_breaker_failure(request, occurred_at, str(exc))
                raise
            self._update_live_circuit_breaker_after_result(request, result, result.executed_at)
            return result
        if request.action == "open_hedge":
            return self._execute_open(request, occurred_at)
        return self._execute_close(request, occurred_at)

    def recover(self, request: ExecutionRecoveryRequest) -> ExecutionResult:
        base_time = datetime.now(timezone.utc)
        existing = self._ledger_service.get_record(request.trade_id)
        if existing is None:
            raise ValueError(f"trade '{request.trade_id}' not found in ledger")
        if existing.status not in {"failed", "recovery_pending"}:
            raise ValueError(f"trade '{request.trade_id}' is not in recoverable state")

        events: list[AuditEventRecord] = []
        events.append(
            self._record_event(
                event_type="execution.recovery.started",
                summary=f"Recovery started for {existing.symbol}",
                occurred_at=base_time,
                payload={"trade_id": request.trade_id, "action": request.action},
                tags=["execution", "recovery", existing.mode],
            )
        )

        if request.action == "resume_open":
            recovered = existing.model_copy(update={"status": "hedged", "notes": request.notes or existing.notes})
            self._ledger_service.save_record(recovered)
            events.append(
                self._record_event(
                    event_type="execution.recovery.perp.filled",
                    summary=f"Recovery filled missing perp leg for {existing.symbol}",
                    occurred_at=base_time + timedelta(milliseconds=1),
                    payload={"trade_id": request.trade_id},
                    tags=["execution", "recovery", "perp", existing.mode],
                )
            )
            events.append(
                self._record_event(
                    event_type="execution.recovery.completed",
                    summary=f"Recovery completed for {existing.symbol}",
                    occurred_at=base_time + timedelta(milliseconds=2),
                    payload={"trade_id": request.trade_id, "status": "hedged"},
                    tags=["execution", "recovery", "completed", existing.mode],
                )
            )
            return ExecutionResult(
                trade_id=existing.trade_id,
                action="open_hedge",
                mode=existing.mode,
                symbol=existing.symbol,
                status="hedged",
                ledger_record=recovered,
                events=events,
                executed_at=base_time + timedelta(milliseconds=2),
            )

        closed = existing.model_copy(
            update={
                "status": "closed",
                "closed_at": base_time + timedelta(milliseconds=2),
                "notes": request.notes or existing.notes,
            }
        )
        self._ledger_service.save_record(closed)
        events.append(
            self._record_event(
                event_type="execution.recovery.completed",
                summary=f"Close recovery completed for {existing.symbol}",
                occurred_at=base_time + timedelta(milliseconds=2),
                payload={"trade_id": request.trade_id, "status": "closed"},
                tags=["execution", "recovery", "completed", existing.mode],
            )
        )
        return ExecutionResult(
            trade_id=existing.trade_id,
            action="close_hedge",
            mode=existing.mode,
            symbol=existing.symbol,
            status="closed",
            ledger_record=closed,
            events=events,
            executed_at=base_time + timedelta(milliseconds=2),
        )

    def rebalance_hedge(
        self,
        *,
        trade_id: str,
        perp_notional_delta: float,
        perp_quantity: float,
        notes: str | None = None,
    ) -> ExecutionResult:
        base_time = datetime.now(timezone.utc)
        existing = self._ledger_service.get_record(trade_id)
        if existing is None:
            raise ValueError(f"trade '{trade_id}' not found in ledger")
        if existing.status not in {"hedged", "open"}:
            raise ValueError(f"trade '{trade_id}' is not in rebalancable state")
        if perp_quantity <= 0:
            raise ValueError("rebalance_hedge requires positive perp_quantity")
        if perp_notional_delta == 0:
            raise ValueError("rebalance_hedge requires non-zero perp_notional_delta")

        request_like = SimpleNamespace(
            trade_id=existing.trade_id,
            symbol=existing.symbol,
            action="rebalance_hedge",
        )
        events: list[AuditEventRecord] = []
        events.append(
            self._record_event(
                event_type="execution.rebalance.started",
                summary=f"Rebalance started for {existing.symbol}",
                occurred_at=base_time,
                payload={
                    "trade_id": trade_id,
                    "perp_notional_delta": perp_notional_delta,
                    "perp_quantity": perp_quantity,
                },
                tags=["execution", "rebalance", existing.mode],
            )
        )

        if existing.mode == "live":
            self._validate_live_rebalance_request(existing.symbol, abs(perp_notional_delta))
            self._ensure_live_execution_allowed(request_like, base_time)
            if self._live_adapter is None:
                raise ValueError("live execution adapter is not configured")
            try:
                report = self._live_adapter.rebalance_perp(
                    trade_id=existing.trade_id,
                    symbol=existing.symbol,
                    side="SELL" if perp_notional_delta > 0 else "BUY",
                    quantity=perp_quantity,
                    reduce_only=perp_notional_delta < 0,
                )
            except Exception as exc:
                self._record_live_circuit_breaker_failure(request_like, base_time, str(exc))
                raise
            events.append(
                self._record_live_leg_event(
                    existing.trade_id,
                    report,
                    base_time + timedelta(milliseconds=1),
                    prefix="execution.live.rebalance",
                )
            )
            if report.status != "filled":
                status = "failed" if report.status == "failed" else "recovery_pending"
                updated = existing.model_copy(update={"status": status, "notes": notes or existing.notes})
                self._ledger_service.save_record(updated)
                events.append(
                    self._record_event(
                        event_type="execution.recovery.required",
                        summary=f"Recovery required after rebalance issue on {existing.symbol}",
                        severity="critical" if status == "failed" else "warning",
                        occurred_at=base_time + timedelta(milliseconds=2),
                        payload={"trade_id": trade_id, "status": status},
                        tags=["execution", "recovery", existing.mode, "rebalance"],
                    )
                )
                result = ExecutionResult(
                    trade_id=existing.trade_id,
                    action="rebalance_hedge",
                    mode=existing.mode,
                    symbol=existing.symbol,
                    status=status,
                    ledger_record=updated,
                    events=events,
                    executed_at=base_time + timedelta(milliseconds=2),
                )
                self._update_live_circuit_breaker_after_result(request_like, result, result.executed_at)
                return result
        else:
            updated = existing

        updated = existing.model_copy(
            update={
                "status": "hedged",
                "perp_notional": round(existing.perp_notional + perp_notional_delta, 4),
                "net_exposure": round(existing.net_exposure - perp_notional_delta, 4),
                "notes": notes or existing.notes,
            }
        )
        self._ledger_service.save_record(updated)
        events.append(
            self._record_event(
                event_type="execution.rebalance.completed",
                summary=f"Rebalance completed for {existing.symbol}",
                occurred_at=base_time + timedelta(milliseconds=2),
                payload={
                    "trade_id": trade_id,
                    "perp_notional_delta": perp_notional_delta,
                    "perp_quantity": perp_quantity,
                    "status": "hedged",
                },
                tags=["execution", "rebalance", "completed", existing.mode],
            )
        )
        result = ExecutionResult(
            trade_id=existing.trade_id,
            action="rebalance_hedge",
            mode=existing.mode,
            symbol=existing.symbol,
            status="hedged",
            ledger_record=updated,
            events=events,
            executed_at=base_time + timedelta(milliseconds=2),
        )
        if existing.mode == "live":
            self._update_live_circuit_breaker_after_result(request_like, result, result.executed_at)
        return result

    def _execute_live(self, request: ExecutionIntentRequest, base_time: datetime) -> ExecutionResult:
        if self._live_adapter is None:
            raise ValueError("live execution adapter is not configured")
        if request.action == "open_hedge":
            return self._execute_live_open(request, base_time)
        return self._execute_live_close(request, base_time)

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

    def _execute_live_open(self, request: ExecutionIntentRequest, base_time: datetime) -> ExecutionResult:
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

        reports = self._live_adapter.open_hedge(request)
        for index, report in enumerate(reports, start=1):
            events.append(self._record_live_leg_event(request.trade_id, report, base_time + timedelta(milliseconds=index)))

        failed = any(report.status == "failed" for report in reports)
        partial = any(report.status == "partial" for report in reports)
        final_status = "failed" if failed else "recovery_pending" if partial else "hedged"
        record = record.model_copy(update={"status": final_status})
        self._ledger_service.save_record(record)
        if failed or partial:
            events.append(
                self._record_event(
                    event_type="execution.recovery.required",
                    summary=f"Recovery required after live open issue on {request.symbol}",
                    severity="critical" if failed else "warning",
                    occurred_at=base_time + timedelta(milliseconds=len(reports) + 1),
                    payload={"trade_id": request.trade_id, "status": final_status},
                    tags=["execution", "recovery", request.mode],
                )
            )
            executed_at = base_time + timedelta(milliseconds=len(reports) + 1)
        else:
            events.append(
                self._record_event(
                    event_type="execution.completed",
                    summary=f"Hedge open completed for {request.symbol}",
                    occurred_at=base_time + timedelta(milliseconds=len(reports) + 1),
                    payload={"trade_id": request.trade_id, "status": "hedged"},
                    tags=["execution", "completed", request.mode],
                )
            )
            executed_at = base_time + timedelta(milliseconds=len(reports) + 1)
        return ExecutionResult(
            trade_id=request.trade_id,
            action=request.action,
            mode=request.mode,
            symbol=request.symbol,
            status=final_status,
            ledger_record=record,
            events=events,
            executed_at=executed_at,
        )

    def _execute_live_close(self, request: ExecutionIntentRequest, base_time: datetime) -> ExecutionResult:
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
        reports = self._live_adapter.close_hedge(request, existing)
        for index, report in enumerate(reports, start=1):
            events.append(
                self._record_live_leg_event(
                    request.trade_id,
                    report,
                    base_time + timedelta(milliseconds=index),
                    prefix="execution.live.close",
                )
            )

        failed = any(report.status == "failed" for report in reports)
        partial = any(report.status == "partial" for report in reports)
        final_status = "failed" if failed else "recovery_pending" if partial else "closed"
        closed = closing.model_copy(
            update={
                "status": final_status,
                "closed_at": None if final_status != "closed" else base_time + timedelta(milliseconds=len(reports) + 1),
                "realized_pnl": request.realized_pnl,
                "notes": request.notes or closing.notes,
            }
        )
        self._ledger_service.save_record(closed)
        if failed or partial:
            events.append(
                self._record_event(
                    event_type="execution.recovery.required",
                    summary=f"Recovery required after live close issue on {request.symbol}",
                    severity="critical" if failed else "warning",
                    occurred_at=base_time + timedelta(milliseconds=len(reports) + 1),
                    payload={"trade_id": request.trade_id, "status": final_status},
                    tags=["execution", "recovery", request.mode],
                )
            )
        else:
            events.append(
                self._record_event(
                    event_type="execution.close.completed",
                    summary=f"Close completed for {request.symbol}",
                    occurred_at=base_time + timedelta(milliseconds=len(reports) + 1),
                    payload={"trade_id": request.trade_id, "realized_pnl": request.realized_pnl},
                    tags=["execution", "close", "completed", request.mode],
                )
            )
        return ExecutionResult(
            trade_id=request.trade_id,
            action=request.action,
            mode=request.mode,
            symbol=request.symbol,
            status=final_status,
            ledger_record=closed,
            events=events,
            executed_at=base_time + timedelta(milliseconds=len(reports) + 1),
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

    def _record_live_leg_event(
        self,
        trade_id: str,
        report: ExecutionLegReport,
        occurred_at: datetime,
        *,
        prefix: str = "execution.live",
    ) -> AuditEventRecord:
        return self._record_event(
            event_type=f"{prefix}.{report.leg}.{report.status}",
            summary=f"Live {report.leg} leg {report.status}",
            occurred_at=occurred_at,
            payload={"trade_id": trade_id, **report.payload},
            tags=["execution", "live", report.leg, report.status],
            severity="error" if report.status == "failed" else "info",
        )

    def _resolve_net_exposure(self, request: ExecutionIntentRequest) -> float:
        if request.net_exposure is not None:
            return request.net_exposure
        return round(request.spot_notional - request.perp_notional, 4)

    def _validate_live_request(self, request: ExecutionIntentRequest) -> None:
        if not self._live_execution_enabled:
            raise ValueError("live execution is disabled")
        if self._live_symbol_allowlist and request.symbol not in self._live_symbol_allowlist:
            raise ValueError(f"symbol '{request.symbol}' is not in live execution allowlist")
        requested_notional = max(request.spot_notional, request.perp_notional)
        if self._max_live_notional is not None and requested_notional > self._max_live_notional:
            raise ValueError("requested notional exceeds configured live notional limit")

    def _validate_live_rebalance_request(self, symbol: str, requested_notional: float) -> None:
        if not self._live_execution_enabled:
            raise ValueError("live execution is disabled")
        if self._live_symbol_allowlist and symbol not in self._live_symbol_allowlist:
            raise ValueError(f"symbol '{symbol}' is not in live execution allowlist")
        if self._max_live_notional is not None and requested_notional > self._max_live_notional:
            raise ValueError("requested notional exceeds configured live notional limit")

    def _ensure_live_execution_allowed(self, request: ExecutionIntentRequest, occurred_at: datetime) -> None:
        if self._circuit_breaker is None:
            return
        try:
            self._circuit_breaker.ensure_allows_execution(now=occurred_at)
        except ValueError as exc:
            self._record_event(
                event_type="execution.circuit_breaker.blocked",
                summary=f"Live execution blocked by circuit breaker for {request.symbol}",
                severity="critical",
                occurred_at=occurred_at,
                payload={"trade_id": request.trade_id, "reason": str(exc)},
                tags=["execution", "live", "circuit-breaker", "blocked"],
            )
            raise

    def _record_live_circuit_breaker_failure(
        self,
        request: ExecutionIntentRequest,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        if self._circuit_breaker is None:
            return
        previous = self._circuit_breaker.get_state(now=occurred_at)
        current = self._circuit_breaker.record_failure(
            trade_id=request.trade_id,
            reason=reason,
            occurred_at=occurred_at,
        )
        if not previous.is_open and current.is_open:
            self._record_event(
                event_type="execution.circuit_breaker.opened",
                summary=f"Live circuit breaker opened for {request.symbol}",
                severity="critical",
                occurred_at=occurred_at,
                payload={
                    "trade_id": request.trade_id,
                    "reason": reason,
                    "resume_at": None if current.resume_at is None else current.resume_at.isoformat(),
                },
                tags=["execution", "live", "circuit-breaker", "opened"],
            )

    def _update_live_circuit_breaker_after_result(
        self,
        request: ExecutionIntentRequest,
        result: ExecutionResult,
        occurred_at: datetime,
    ) -> None:
        if self._circuit_breaker is None:
            return
        if result.status in {"failed", "recovery_pending"}:
            self._record_live_circuit_breaker_failure(
                request,
                occurred_at,
                f"live {request.action} ended with status {result.status}",
            )
            return
        previous = self._circuit_breaker.get_state(now=occurred_at)
        current = self._circuit_breaker.record_success(
            trade_id=request.trade_id,
            occurred_at=occurred_at,
        )
        if previous.consecutive_failures > 0 and current.consecutive_failures == 0:
            self._record_event(
                event_type="execution.circuit_breaker.reset",
                summary=f"Live circuit breaker failure count reset after successful execution on {request.symbol}",
                occurred_at=occurred_at,
                payload={"trade_id": request.trade_id},
                tags=["execution", "live", "circuit-breaker", "reset"],
            )

    def _handle_idempotent_replay(
        self,
        request: ExecutionIntentRequest,
        occurred_at: datetime,
    ) -> ExecutionResult | None:
        existing = self._ledger_service.get_record(request.trade_id)
        if existing is None:
            return None
        if request.action == "open_hedge" and existing.status in {"open", "hedged", "closing", "closed", "recovery_pending"}:
            event = self._record_event(
                event_type="execution.idempotent.replay",
                summary=f"Replayed open intent for existing trade {request.trade_id}",
                occurred_at=occurred_at,
                payload={"trade_id": request.trade_id, "status": existing.status},
                tags=["execution", "idempotent", request.mode],
            )
            return ExecutionResult(
                trade_id=request.trade_id,
                action=request.action,
                mode=request.mode,
                symbol=request.symbol,
                status=existing.status,
                ledger_record=existing,
                events=[event],
                executed_at=occurred_at,
            )
        if request.action == "close_hedge" and existing.status == "closed":
            event = self._record_event(
                event_type="execution.idempotent.replay",
                summary=f"Replayed close intent for existing trade {request.trade_id}",
                occurred_at=occurred_at,
                payload={"trade_id": request.trade_id, "status": existing.status},
                tags=["execution", "idempotent", request.mode],
            )
            return ExecutionResult(
                trade_id=request.trade_id,
                action=request.action,
                mode=request.mode,
                symbol=request.symbol,
                status=existing.status,
                ledger_record=existing,
                events=[event],
                executed_at=occurred_at,
            )
        return None
