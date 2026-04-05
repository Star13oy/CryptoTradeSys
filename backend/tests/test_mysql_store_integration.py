import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.adaptation.store import TuningStateStore
from app.backtest.dataset_store import BacktestDataset, BacktestDatasetStore
from app.backtest.engine import BacktestPeriod
from app.core.settings import get_settings
from app.ledger.schemas import TradeLedgerRecord
from app.ledger.store import TradeLedgerStore
from app.schemas.adaptation import TuningState
from app.schemas.market import MarketSnapshot


pytestmark = pytest.mark.skipif(
    os.getenv("FUNDING_ARB_RUN_MYSQL_TESTS") != "1",
    reason="set FUNDING_ARB_RUN_MYSQL_TESTS=1 to run MySQL integration tests",
)


@pytest.fixture()
def mysql_settings(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    database = f"crypto_funding_arb_test_{uuid4().hex[:10]}"
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    tuning_path = base / f"{uuid4().hex}-tuning.json"
    ledger_path = base / f"{uuid4().hex}-ledger.json"
    dataset_path = base / f"{uuid4().hex}-datasets.json"
    monkeypatch.setenv("FUNDING_ARB_STORAGE_BACKEND", "mysql")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_PORT", "3306")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_USER", "root")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_PASSWORD", "root")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_DATABASE", database)
    monkeypatch.setenv("FUNDING_ARB_TUNING_STATE_PATH", str(tuning_path))
    monkeypatch.setenv("FUNDING_ARB_TRADE_LEDGER_PATH", str(ledger_path))
    monkeypatch.setenv("FUNDING_ARB_BACKTEST_DATASET_PATH", str(dataset_path))
    get_settings.cache_clear()
    yield {
        "database": database,
        "tuning_path": str(tuning_path),
        "ledger_path": str(ledger_path),
        "dataset_path": str(dataset_path),
    }
    get_settings.cache_clear()


def make_ledger_records() -> list[TradeLedgerRecord]:
    return [
        TradeLedgerRecord(
            trade_id="mysql-ledger-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            status="hedged",
            opened_at=datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
            spot_notional=15000,
            perp_notional=14990,
            realized_pnl=0.0,
            notes="mysql-test",
        )
    ]


def make_dataset() -> BacktestDataset:
    return BacktestDataset(
        dataset_id="mysql-funding-apr-01",
        title="MySQL Funding Replay",
        periods=[
            BacktestPeriod(
                observed_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
                snapshots=[
                    MarketSnapshot(
                        symbol="BTCUSDT",
                        funding_rate=0.0008,
                        perp_mid=60010,
                        spot_mid=60000,
                        perp_spread_bps=0.5,
                        spot_spread_bps=0.4,
                    )
                ],
            )
        ],
    )


def test_tuning_state_store_round_trips_with_mysql(mysql_settings: dict[str, str]) -> None:
    store = TuningStateStore()

    initial = store.load()
    saved = store.save(TuningState(active_package_id="mysql-balanced", active_package_title="MySQL 平衡方案"))

    assert initial.active_package_id == "balanced"
    assert saved.active_package_id == "mysql-balanced"
    assert TuningStateStore().load().active_package_title == "MySQL 平衡方案"
    assert not Path(mysql_settings["tuning_path"]).exists()


def test_trade_ledger_store_persists_records_with_mysql(mysql_settings: dict[str, str]) -> None:
    store = TradeLedgerStore()

    persisted = store.save(make_ledger_records(), mode="append")

    assert len(persisted) == 1
    reloaded = TradeLedgerStore().list()
    assert len(reloaded) == 1
    assert reloaded[0].trade_id == "mysql-ledger-1"
    assert not Path(mysql_settings["ledger_path"]).exists()


def test_backtest_dataset_store_upserts_and_loads_with_mysql(mysql_settings: dict[str, str]) -> None:
    store = BacktestDatasetStore()

    stored = store.save_dataset(make_dataset())

    assert stored.dataset_id == "mysql-funding-apr-01"
    assert store.list_summaries()[0].dataset_id == "mysql-funding-apr-01"
    loaded = BacktestDatasetStore().get_dataset("mysql-funding-apr-01")
    assert loaded is not None
    assert loaded.periods[0].snapshots[0].symbol == "BTCUSDT"
    assert not Path(mysql_settings["dataset_path"]).exists()
