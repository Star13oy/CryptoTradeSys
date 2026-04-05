from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.settings import get_settings

from .engine import BacktestPeriod


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
        settings = get_settings()
        self._path = Path(path or settings.backtest_dataset_path)

    def list_datasets(self) -> list[BacktestDataset]:
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
