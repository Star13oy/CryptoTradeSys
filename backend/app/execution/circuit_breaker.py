from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.settings import Settings, get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled

_TABLE_NAME = "execution_circuit_breaker_state"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    state_key VARCHAR(64) PRIMARY KEY,
    updated_at DATETIME(6) NOT NULL,
    payload JSON NOT NULL
)
"""


class ExecutionCircuitBreakerState(BaseModel):
    enabled: bool = True
    is_open: bool = False
    failure_threshold: int = Field(default=2, ge=1)
    cooldown_seconds: float = Field(default=300.0, gt=0.0)
    consecutive_failures: int = Field(default=0, ge=0)
    last_failure_at: datetime | None = None
    opened_at: datetime | None = None
    resume_at: datetime | None = None
    last_reason: str | None = None
    last_trade_id: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionCircuitBreakerStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._path = Path(path or self._settings.execution_circuit_breaker_state_path)
        self._mysql = MySQLPersistence(self._settings)

    def load(self) -> ExecutionCircuitBreakerState | None:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            rows = self._mysql.fetch_json_rows(
                f"SELECT payload FROM {_TABLE_NAME} WHERE state_key = %s LIMIT 1",
                ("active",),
            )
            if not rows:
                return None
            return ExecutionCircuitBreakerState.model_validate(rows[0])
        if not self._path.exists():
            return None
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return ExecutionCircuitBreakerState.model_validate(payload)

    def save(self, state: ExecutionCircuitBreakerState) -> ExecutionCircuitBreakerState:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            self._mysql.execute(
                f"""
                REPLACE INTO {_TABLE_NAME} (state_key, updated_at, payload)
                VALUES (%s, %s, CAST(%s AS JSON))
                """,
                (
                    "active",
                    self._mysql.to_mysql_datetime(state.updated_at),
                    self._mysql.serialize(state),
                ),
            )
            return state
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state


class ExecutionCircuitBreakerService:
    def __init__(
        self,
        path: str | Path | None = None,
        *,
        enabled: bool = True,
        failure_threshold: int = 2,
        cooldown_seconds: float = 300.0,
        settings: Settings | None = None,
        store: ExecutionCircuitBreakerStore | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._enabled = enabled
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._store = store or ExecutionCircuitBreakerStore(path=path, settings=self._settings)

    def get_state(self, *, now: datetime | None = None) -> ExecutionCircuitBreakerState:
        state = self._load_state()
        effective_now = now or datetime.now(timezone.utc)
        if state.is_open and state.resume_at is not None and effective_now >= state.resume_at:
            state = state.model_copy(
                update={
                    "is_open": False,
                    "consecutive_failures": 0,
                    "opened_at": None,
                    "resume_at": None,
                    "last_reason": None,
                    "updated_at": effective_now,
                }
            )
            self._store.save(state)
        return state

    def ensure_allows_execution(self, *, now: datetime | None = None) -> ExecutionCircuitBreakerState:
        state = self.get_state(now=now)
        if state.enabled and state.is_open:
            resume_at = state.resume_at.isoformat() if state.resume_at is not None else "unknown"
            raise ValueError(f"live execution circuit breaker is open until {resume_at}")
        return state

    def record_failure(
        self,
        *,
        trade_id: str,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> ExecutionCircuitBreakerState:
        effective_now = occurred_at or datetime.now(timezone.utc)
        state = self.get_state(now=effective_now)
        if not state.enabled:
            return state

        consecutive_failures = state.consecutive_failures + 1
        is_open = consecutive_failures >= state.failure_threshold
        next_state = state.model_copy(
            update={
                "is_open": is_open,
                "consecutive_failures": consecutive_failures,
                "last_failure_at": effective_now,
                "opened_at": effective_now if is_open else None,
                "resume_at": effective_now + timedelta(seconds=state.cooldown_seconds) if is_open else None,
                "last_reason": reason,
                "last_trade_id": trade_id,
                "updated_at": effective_now,
            }
        )
        return self._store.save(next_state)

    def record_success(
        self,
        *,
        trade_id: str,
        occurred_at: datetime | None = None,
    ) -> ExecutionCircuitBreakerState:
        effective_now = occurred_at or datetime.now(timezone.utc)
        state = self.get_state(now=effective_now)
        if not state.enabled:
            return state
        next_state = state.model_copy(
            update={
                "is_open": False,
                "consecutive_failures": 0,
                "opened_at": None,
                "resume_at": None,
                "last_reason": None,
                "last_trade_id": trade_id,
                "updated_at": effective_now,
            }
        )
        return self._store.save(next_state)

    def manual_reset(
        self,
        *,
        occurred_at: datetime | None = None,
        reason: str = "manual reset",
    ) -> ExecutionCircuitBreakerState:
        effective_now = occurred_at or datetime.now(timezone.utc)
        state = self.get_state(now=effective_now)
        next_state = state.model_copy(
            update={
                "is_open": False,
                "consecutive_failures": 0,
                "opened_at": None,
                "resume_at": None,
                "last_reason": None,
                "updated_at": effective_now,
            }
        )
        return self._store.save(next_state)

    def _load_state(self) -> ExecutionCircuitBreakerState:
        stored = self._store.load()
        if stored is None:
            return ExecutionCircuitBreakerState(
                enabled=self._enabled,
                failure_threshold=self._failure_threshold,
                cooldown_seconds=self._cooldown_seconds,
            )
        return stored.model_copy(
            update={
                "enabled": self._enabled,
                "failure_threshold": self._failure_threshold,
                "cooldown_seconds": self._cooldown_seconds,
            }
        )
