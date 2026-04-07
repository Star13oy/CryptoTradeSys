from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from app.exchange.binance_trading import BinanceTradingClient

from .schemas import ReconciliationWorkerSnapshot
from .service import ReconciliationService


class ReconciliationWorker:
    def __init__(
        self,
        reconciliation_service: ReconciliationService,
        *,
        trading_client: BinanceTradingClient | object | None = None,
        enabled: bool = False,
        interval_seconds: float = 30.0,
        limit: int = 5,
    ) -> None:
        self._service = reconciliation_service
        self._trading_client = trading_client
        self._enabled = enabled
        self._interval_seconds = interval_seconds
        self._limit = limit
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._snapshot = ReconciliationWorkerSnapshot(
            enabled=enabled,
            configured=trading_client is not None,
            running=False,
            interval_seconds=interval_seconds,
            limit=limit,
        )

    def snapshot(self) -> ReconciliationWorkerSnapshot:
        return self._snapshot.model_copy(
            update={
                "running": self._task is not None and not self._task.done(),
            }
        )

    async def start(self) -> None:
        if not self._enabled or self._trading_client is None or self._task is not None:
            return
        self._task = asyncio.create_task(self._run_loop(), name="reconciliation-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def run_once(self) -> ReconciliationWorkerSnapshot:
        if self._trading_client is None:
            raise ValueError("reconciliation worker is not configured with an authenticated trading client")

        async with self._lock:
            started_at = datetime.now(timezone.utc)
            self._snapshot.last_started_at = started_at
            self._snapshot.total_runs += 1
            try:
                reports = await asyncio.to_thread(
                    self._service.sync_attention_candidates,
                    trading_client=self._trading_client,
                    limit=self._limit,
                )
            except Exception as exc:
                finished_at = datetime.now(timezone.utc)
                self._snapshot.last_finished_at = finished_at
                self._snapshot.last_error = str(exc)
                self._snapshot.last_imported_report_count = 0
                self._snapshot.last_synced_trade_count = 0
                self._snapshot.total_failed_runs += 1
                return self.snapshot()

            finished_at = datetime.now(timezone.utc)
            synced_trade_ids = {
                report.trade_id
                for report in reports
                if report.trade_id
            }
            self._snapshot.last_finished_at = finished_at
            self._snapshot.last_success_at = finished_at
            self._snapshot.last_error = None
            self._snapshot.last_imported_report_count = len(reports)
            self._snapshot.last_synced_trade_count = len(synced_trade_ids)
            self._snapshot.total_imported_reports += len(reports)
            return self.snapshot()

    async def _run_loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self._interval_seconds)
