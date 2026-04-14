from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from app.exchange.binance_public import BinancePublicClient
from app.market_data.service import build_market_snapshot
from app.strategy.funding_arb import FundingArbStrategy

from .schemas import HoldingMonitorWorkerSnapshot, HoldingMonitorResult
from .service import HoldingMonitorService


class HoldingMonitorWorker:
    def __init__(
        self,
        monitor_service: HoldingMonitorService,
        *,
        orchestrator: object | None = None,
        enabled: bool = False,
        interval_seconds: float = 60.0,
        max_hold_periods: float = 72.0,
    ) -> None:
        self._service = monitor_service
        self._orchestrator = orchestrator
        self._enabled = enabled
        self._interval_seconds = interval_seconds
        self._max_hold_periods = max_hold_periods
        self._public_client = BinancePublicClient()
        self._strategy = FundingArbStrategy()
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._snapshot = HoldingMonitorWorkerSnapshot(
            enabled=enabled,
            configured=orchestrator is not None,
            running=False,
            interval_seconds=interval_seconds,
            max_hold_periods=max_hold_periods,
        )

    def snapshot(self) -> HoldingMonitorWorkerSnapshot:
        return self._snapshot.model_copy(
            update={"running": self._task is not None and not self._task.done()}
        )

    async def start(self) -> None:
        if not self._enabled or self._orchestrator is None or self._task is not None:
            return
        self._task = asyncio.create_task(self._run_loop(), name="holding-monitor")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def run_once(self) -> HoldingMonitorWorkerSnapshot:
        if self._orchestrator is None:
            raise ValueError("holding monitor worker is not configured")

        async with self._lock:
            started_at = datetime.now(timezone.utc)
            self._snapshot.last_started_at = started_at
            self._snapshot.total_cycles += 1
            try:
                # Async: fetch market data
                funding = await self._public_client.fetch_funding_rates()
                perp = await self._public_client.fetch_perp_book_tickers()
                spot = await self._public_client.fetch_spot_book_tickers()
                # Sync: build + score + monitor
                snapshots = build_market_snapshot(funding, perp, spot)
                scores = self._strategy.score_snapshots(snapshots)
                result = await asyncio.to_thread(
                    self._service.run_monitor_cycle,
                    current_scores=scores,
                    orchestrator=self._orchestrator,
                    max_hold_periods=self._max_hold_periods,
                )
            except Exception as exc:
                finished_at = datetime.now(timezone.utc)
                self._snapshot.last_finished_at = finished_at
                self._snapshot.last_error = str(exc)
                self._snapshot.total_failed_cycles += 1
                return self.snapshot()

            finished_at = datetime.now(timezone.utc)
            self._snapshot.last_finished_at = finished_at
            self._snapshot.last_success_at = finished_at
            self._snapshot.last_error = None
            self._snapshot.last_cycle_result = result
            self._snapshot.total_closes_executed += result.close_executed
            return self.snapshot()

    async def _run_loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self._interval_seconds)
