from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.backtest.dataset_store import BacktestDataset, BacktestDatasetStore
from app.backtest.engine import BacktestPeriod
from app.schemas.market import MarketSnapshot


def make_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-backtest-datasets.json"


def make_dataset(*, dataset_id: str = "funding-apr-01") -> BacktestDataset:
    return BacktestDataset(
        dataset_id=dataset_id,
        title="Funding Replay 2026-04-01",
        source="manual_import",
        periods=[
            BacktestPeriod(
                observed_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
                snapshots=[
                    MarketSnapshot(
                        symbol="BTCUSDT",
                        funding_rate=0.0008,
                        perp_mid=60006,
                        spot_mid=60000,
                        perp_spread_bps=0.4,
                        spot_spread_bps=0.3,
                    )
                ],
            ),
            BacktestPeriod(
                observed_at=datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc),
                snapshots=[
                    MarketSnapshot(
                        symbol="SOLUSDT",
                        funding_rate=0.0007,
                        perp_mid=180.12,
                        spot_mid=180,
                        perp_spread_bps=0.4,
                        spot_spread_bps=0.3,
                    )
                ],
            ),
        ],
    )


def test_backtest_dataset_store_upserts_and_lists_summaries() -> None:
    store = BacktestDatasetStore(make_path())

    stored = store.save_dataset(make_dataset())

    assert stored.dataset_id == "funding-apr-01"
    assert len(store.list_datasets()) == 1
    summary = store.list_summaries()[0]
    assert summary.dataset_id == "funding-apr-01"
    assert summary.period_count == 2


def test_backtest_dataset_store_loads_by_dataset_id() -> None:
    store = BacktestDatasetStore(make_path())
    store.save_dataset(make_dataset())
    store.save_dataset(make_dataset(dataset_id="funding-apr-02"))

    loaded = store.get_dataset("funding-apr-02")

    assert loaded is not None
    assert loaded.dataset_id == "funding-apr-02"
    assert loaded.periods[-1].snapshots[0].symbol == "SOLUSDT"
