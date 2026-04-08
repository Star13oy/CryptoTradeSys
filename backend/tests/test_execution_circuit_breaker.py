from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.execution import ExecutionCircuitBreakerService


def make_path(suffix: str) -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-{suffix}.json"


def test_circuit_breaker_opens_after_threshold_and_auto_closes_after_cooldown() -> None:
    service = ExecutionCircuitBreakerService(
        path=make_path("circuit-breaker"),
        enabled=True,
        failure_threshold=2,
        cooldown_seconds=60,
    )
    started_at = datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc)

    first = service.record_failure(
        trade_id="cb-1",
        reason="perp leg failed",
        occurred_at=started_at,
    )
    assert first.is_open is False
    assert first.consecutive_failures == 1

    second = service.record_failure(
        trade_id="cb-2",
        reason="perp leg failed again",
        occurred_at=started_at + timedelta(seconds=5),
    )
    assert second.is_open is True
    assert second.consecutive_failures == 2
    assert second.resume_at == started_at + timedelta(seconds=65)

    try:
        service.ensure_allows_execution(now=started_at + timedelta(seconds=30))
    except ValueError as exc:
        assert "circuit breaker is open" in str(exc)
    else:
        raise AssertionError("expected live execution to be blocked while breaker is open")

    reopened = service.get_state(now=started_at + timedelta(seconds=70))
    assert reopened.is_open is False
    assert reopened.consecutive_failures == 0
    assert reopened.resume_at is None


def test_circuit_breaker_success_resets_failure_counter() -> None:
    service = ExecutionCircuitBreakerService(
        path=make_path("circuit-breaker-reset"),
        enabled=True,
        failure_threshold=3,
        cooldown_seconds=60,
    )
    started_at = datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc)

    service.record_failure(
        trade_id="cb-reset-1",
        reason="temporary exchange failure",
        occurred_at=started_at,
    )
    state = service.record_success(
        trade_id="cb-reset-1",
        occurred_at=started_at + timedelta(seconds=2),
    )

    assert state.is_open is False
    assert state.consecutive_failures == 0
    assert state.last_reason is None
