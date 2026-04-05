from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel

from app.adaptation.sample_store import LearningSampleStore
from app.adaptation.store import TuningStateStore
from app.audit.schemas import AuditEventRecord
from app.audit.store import AuditEventStore
from app.backtest.dataset_store import BacktestDataset, BacktestDatasetStore
from app.core.settings import get_settings
from app.journal.schemas import CompletedTradeRecord
from app.journal.store import TradeJournalStore
from app.ledger.schemas import TradeLedgerRecord
from app.ledger.store import TradeLedgerStore
from app.persistence.mysql import mysql_storage_enabled
from app.reconciliation.schemas import ExchangeOrderReport
from app.reconciliation.store import ExchangeOrderReportStore
from app.schemas.adaptation import LearningTradeSample, TuningState

from .migration_schemas import BackfillSectionResult, PersistenceBackfillSummary

TModel = TypeVar("TModel", bound=BaseModel)


class JsonToMySQLBackfillService:
    def __init__(self) -> None:
        self._settings = get_settings()
        if not mysql_storage_enabled(self._settings):
            raise ValueError("JSON backfill requires FUNDING_ARB_STORAGE_BACKEND=mysql")

        self._tuning_store = TuningStateStore()
        self._sample_store = LearningSampleStore()
        self._journal_store = TradeJournalStore()
        self._dataset_store = BacktestDatasetStore()
        self._ledger_store = TradeLedgerStore()
        self._audit_store = AuditEventStore()
        self._report_store = ExchangeOrderReportStore()

    def run(self) -> PersistenceBackfillSummary:
        return PersistenceBackfillSummary(
            backend=self._settings.storage_backend,
            sections={
                "tuning_state": self._backfill_single(
                    source_path=self._settings.tuning_state_path,
                    model=TuningState,
                    current_loader=self._tuning_store.load,
                    current_saver=self._tuning_store.save,
                ),
                "learning_samples": self._backfill_many(
                    source_path=self._settings.learning_sample_path,
                    model=LearningTradeSample,
                    current_loader=self._sample_store.load,
                    current_saver=lambda items: self._sample_store.save(items, mode="append"),
                ),
                "trade_journal": self._backfill_many(
                    source_path=self._settings.trade_journal_path,
                    model=CompletedTradeRecord,
                    current_loader=self._journal_store.list,
                    current_saver=lambda items: self._journal_store.save(items, mode="append"),
                ),
                "backtest_datasets": self._backfill_many(
                    source_path=self._settings.backtest_dataset_path,
                    model=BacktestDataset,
                    current_loader=self._dataset_store.list_datasets,
                    current_saver=self._save_datasets,
                ),
                "trade_ledger": self._backfill_many(
                    source_path=self._settings.trade_ledger_path,
                    model=TradeLedgerRecord,
                    current_loader=self._ledger_store.list,
                    current_saver=lambda items: self._ledger_store.save(items, mode="append"),
                ),
                "audit_events": self._backfill_many(
                    source_path=self._settings.audit_event_path,
                    model=AuditEventRecord,
                    current_loader=self._audit_store.list,
                    current_saver=lambda items: self._audit_store.save(items, mode="append"),
                ),
                "exchange_order_reports": self._backfill_many(
                    source_path=self._settings.exchange_order_report_path,
                    model=ExchangeOrderReport,
                    current_loader=self._report_store.list,
                    current_saver=lambda items: self._report_store.save(items, mode="append"),
                ),
            },
        )

    def _save_datasets(self, items: list[BacktestDataset]) -> None:
        for item in items:
            self._dataset_store.save_dataset(item)
    def _backfill_single(
        self,
        *,
        source_path: str,
        model: type[TModel],
        current_loader: Callable[[], TModel],
        current_saver: Callable[[TModel], TModel],
    ) -> BackfillSectionResult:
        path = Path(source_path)
        result = BackfillSectionResult(source_path=str(path))
        if not path.exists():
            return result
        result.found = True
        result.source_records = 1
        source = model.model_validate(json.loads(path.read_text(encoding="utf-8")))
        current = current_loader()
        if self._canonical(current) == self._canonical(source):
            result.skipped = 1
            return result
        current_saver(source)
        result.imported = 1
        return result

    def _backfill_many(
        self,
        *,
        source_path: str,
        model: type[TModel],
        current_loader: Callable[[], list[TModel]],
        current_saver: Callable[[list[TModel]], None],
    ) -> BackfillSectionResult:
        path = Path(source_path)
        result = BackfillSectionResult(source_path=str(path))
        if not path.exists():
            return result
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_items = [model.model_validate(item) for item in payload]
        result.found = True
        result.source_records = len(source_items)
        existing = {self._canonical(item) for item in current_loader()}
        to_import: list[TModel] = []
        for item in source_items:
            normalized = self._canonical(item)
            if normalized in existing:
                result.skipped += 1
                continue
            existing.add(normalized)
            to_import.append(item)
        if to_import:
            current_saver(to_import)
            result.imported = len(to_import)
        return result

    def _canonical(self, item: BaseModel) -> str:
        return json.dumps(item.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
