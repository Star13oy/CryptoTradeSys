from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from app.execution import ExecutionOrchestrator

from .schemas import RecoveryWorkerSnapshot
from .service import RecoveryService


class RecoveryWorker:
    def __init__(
        self,
        recovery_service: RecoveryService,
        *,
        orchestrator: ExecutionOrchestrator | object | None = None,
        enabled: bool = False,
        interval_seconds: float = 30.0,
        limit: int = 3,
    ) -> None:
        self._service = recovery_service
        self._orchestrator = orchestrator
        self._enabled = enabled
        self._interval_seconds = interval_seconds
        self._limit = limit
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._snapshot = RecoveryWorkerSnapshot(
            enabled=enabled,
            configured=orchestrator is not None,
            running=False,
            interval_seconds=interval_seconds,
            limit=limit,
        )

    def snapshot(self) -> RecoveryWorkerSnapshot:
        return self._snapshot.model_copy(
            update={
                "running": self._task is not None and not self._task.done(),
            }
        )

    async def start(self) -> None:
        if not self._enabled or self._orchestrator is None or self._task is not None:
            return
        self._task = asyncio.create_task(self._run_loop(), name="recovery-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def run_once(self) -> RecoveryWorkerSnapshot:
        if self._orchestrator is None:
            raise ValueError("recovery worker is not configured with an execution orchestrator")

        async with self._lock:
            started_at = datetime.now(timezone.utc)
            self._snapshot.last_started_at = started_at
            self._snapshot.total_runs += 1
            try:
                summary = await asyncio.to_thread(
                    self._service.execute_actionable_plans,
                    orchestrator=self._orchestrator,
                    limit=self._limit,
                )
            except Exception as exc:
                finished_at = datetime.now(timezone.utc)
                self._snapshot.last_finished_at = finished_at
                self._snapshot.last_error = str(exc)
                self._snapshot.last_attempted_count = 0
                self._snapshot.last_executed_count = 0
                self._snapshot.last_skipped_count = 0
                self._snapshot.total_failed_runs += 1
                return self.snapshot()

            finished_at = datetime.now(timezone.utc)
            self._snapshot.last_finished_at = finished_at
            self._snapshot.last_success_at = finished_at
            self._snapshot.last_error = None
            self._snapshot.last_attempted_count = summary.attempted_count
            self._snapshot.last_executed_count = summary.executed_count
            self._snapshot.last_skipped_count = summary.skipped_count
            self._snapshot.total_executed_recoveries += summary.executed_count
            return self.snapshot()

    async def _run_loop(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self._interval_seconds)
