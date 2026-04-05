from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.settings import get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled

from .engine import BacktestPeriod

_TABLE_NAME = "backtest_datasets"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    dataset_id VARCHAR(191) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(128) NOT NULL,
    imported_at DATETIME(6) NOT NULL,
    payload JSON NOT NULL,
    KEY idx_backtest_datasets_imported_at (imported_at)
)
"""


class BacktestDataset(BaseModel):
    dataset_id: str
    title: str
    source: str = "manual_import"
    description: str | None = None
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    periods: list[BacktestPeriod] = Field(default_factory=list)


class BacktestDatasetSummary(BaseModel):
    dataset_id: str
    title: str
    source: str
    period_count: int
    snapshot_count: int
    observed_from: datetime | None = None
    observed_to: datetime | None = None
    imported_at: datetime

    @classmethod
    def from_dataset(cls, dataset: BacktestDataset) -> "BacktestDatasetSummary":
        observed = [period.observed_at for period in dataset.periods if period.observed_at is not None]
        snapshot_count = sum(len(period.snapshots) for period in dataset.periods)
        return cls(
            dataset_id=dataset.dataset_id,
            title=dataset.title,
            source=dataset.source,
            period_count=len(dataset.periods),
            snapshot_count=snapshot_count,
            observed_from=min(observed) if observed else None,
            observed_to=max(observed) if observed else None,
            imported_at=dataset.imported_at.astimezone(timezone.utc),
        )


class BacktestDatasetStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._settings = get_settings()
        self._path = Path(path or self._settings.backtest_dataset_path)
        self._mysql = MySQLPersistence(self._settings)

    def list_datasets(self) -> list[BacktestDataset]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            payloads = self._mysql.fetch_json_rows(
                f"SELECT payload FROM {_TABLE_NAME} ORDER BY imported_at, dataset_id"
            )
            return [BacktestDataset.model_validate(item) for item in payloads]
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [BacktestDataset.model_validate(item) for item in payload]

    def list_summaries(self) -> list[BacktestDatasetSummary]:
        return [BacktestDatasetSummary.from_dataset(dataset) for dataset in self.list_datasets()]

    def get_dataset(self, dataset_id: str) -> BacktestDataset | None:
        for dataset in self.list_datasets():
            if dataset.dataset_id == dataset_id:
                return dataset
        return None

    def save_dataset(self, dataset: BacktestDataset) -> BacktestDataset:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            self._mysql.execute(
                f"""
                REPLACE INTO {_TABLE_NAME} (dataset_id, title, source, imported_at, payload)
                VALUES (%s, %s, %s, %s, CAST(%s AS JSON))
                """,
                (
                    dataset.dataset_id,
                    dataset.title,
                    dataset.source,
                    self._mysql.to_mysql_datetime(dataset.imported_at),
                    self._mysql.serialize(dataset),
                ),
            )
            return dataset
        datasets = self.list_datasets()
        replaced = False
        for index, existing in enumerate(datasets):
            if existing.dataset_id == dataset.dataset_id:
                datasets[index] = dataset
                replaced = True
                break
        if not replaced:
            datasets.append(dataset)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([item.model_dump(mode="json") for item in datasets], indent=2),
            encoding="utf-8",
        )
        return dataset
