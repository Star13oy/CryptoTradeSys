from __future__ import annotations

from .dataset_store import BacktestDataset, BacktestDatasetStore, BacktestDatasetSummary
from .engine import BacktestPeriod


class BacktestDatasetService:
    def __init__(self, store: BacktestDatasetStore | None = None) -> None:
        self._store = store or BacktestDatasetStore()

    def list_summaries(self) -> list[BacktestDatasetSummary]:
        return self._store.list_summaries()

    def import_dataset(self, dataset: BacktestDataset) -> BacktestDatasetSummary:
        stored = self._store.save_dataset(dataset)
        return BacktestDatasetSummary.from_dataset(stored)

    def get_periods(
        self,
        dataset_id: str,
        *,
        limit_recent_periods: int | None = None,
    ) -> list[BacktestPeriod] | None:
        dataset = self._store.get_dataset(dataset_id)
        if dataset is None:
            return None
        periods = dataset.periods
        if limit_recent_periods is not None:
            return periods[-limit_recent_periods:]
        return periods
