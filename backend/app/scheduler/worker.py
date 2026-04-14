from __future__ import annotations
import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from app.exchange.binance_public import BinancePublicClient
from app.market_data.service import build_market_snapshot

from .schemas import SchedulerWorkerSnapshot
from .service import SchedulerService


class StrategySchedulerWorker:
    def __init__(
        self,
        scheduler_service: SchedulerService,
        *,
        orchestrator: object | None = None,
        enabled: bool = False,
        interval_seconds: float = 60.0,
        max_open_positions: int = 3,
        max_total_notional: float = 25000.0,
        app_mode: str = "paper",
    ) -> None:
        self._service = scheduler_service
        self._orchestrator = orchestrator
        self._enabled = enabled
        self._interval_seconds = interval_seconds
        self._max_open_positions = max_open_positions
        self._max_total_notional = max_total_notional
        self._app_mode = app_mode
        self._public_client = BinancePublicClient()
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._snapshot = SchedulerWorkerSnapshot(
            enabled=enabled,
            configured=orchestrator is not None,
            running=False,
            interval_seconds=interval_seconds,
            max_open_positions=max_open_positions,
            max_total_notional=max_total_notional,
        )

    def snapshot(self) -> SchedulerWorkerSnapshot:
        return self._snapshot.model_copy(
            update={"running": self._task is not None and not self._task.done()}
        )

    async def start(self) -> None:
        if not self._enabled or self._orchestrator is None or self._task is not None:
            return
        self._task = asyncio.create_task(self._run_loop(), name="strategy-scheduler")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def run_once(self) -> SchedulerWorkerSnapshot:
        if self._orchestrator is None:
            raise ValueError("scheduler worker is not configured with an execution orchestrator")

        async with self._lock:
            started_at = datetime.now(timezone.utc)
            self._snapshot.last_started_at = started_at
            self._snapshot.total_cycles += 1
            try:
                # Async: fetch market data
                funding = await self._public_client.fetch_funding_rates()
                perp = await self._public_client.fetch_perp_book_tickers()
                spot = await self._public_client.fetch_spot_book_tickers()
                # Sync: build snapshots + run cycle
                snapshots = build_market_snapshot(funding, perp, spot)
                result = await asyncio.to_thread(
                    self._service.run_cycle,
                    snapshots=snapshots,
                    orchestrator=self._orchestrator,
                    app_mode=self._app_mode,
                    max_open_positions=self._max_open_positions,
                    max_total_notional=self._max_total_notional,
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
            self._snapshot.total_actions_executed += result.actions_executed
            return self.snapshot()

    async def _run_loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self._interval_seconds)
