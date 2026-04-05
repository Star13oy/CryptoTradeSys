import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import app
from app.persistence.migration import JsonToMySQLBackfillService
from app.schemas.adaptation import TuningState


pytestmark = pytest.mark.skipif(
    os.getenv("FUNDING_ARB_RUN_MYSQL_TESTS") != "1",
    reason="set FUNDING_ARB_RUN_MYSQL_TESTS=1 to run MySQL integration tests",
)


@pytest.fixture()
def mysql_backfill_api_settings(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    database = f"crypto_funding_arb_test_{uuid4().hex[:10]}"
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    tuning_path = base / f"{uuid4().hex}-api-tuning.json"
    tuning_path.write_text(
        json.dumps(
            TuningState(active_package_id="api-balanced", active_package_title="API 平衡方案").model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FUNDING_ARB_STORAGE_BACKEND", "mysql")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_PORT", "3306")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_USER", "root")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_PASSWORD", "root")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_DATABASE", database)
    monkeypatch.setenv("FUNDING_ARB_TUNING_STATE_PATH", str(tuning_path))
    get_settings.cache_clear()
    yield {"tuning_path": str(tuning_path)}
    get_settings.cache_clear()


def test_persistence_backfill_api_runs_and_returns_summary(mysql_backfill_api_settings: dict[str, str]) -> None:
    client = TestClient(app)

    response = client.post("/api/v1/algo/persistence/backfill-json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "mysql"
    assert payload["sections"]["tuning_state"]["imported"] == 1
