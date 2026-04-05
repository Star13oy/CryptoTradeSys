from __future__ import annotations

from app.adaptation.extractor import LearningSampleExtractor
from app.schemas.adaptation import LearningTradeSample

from .schemas import CompletedTradeRecord
from .store import TradeJournalStore


class TradeJournalService:
    def __init__(self, store: TradeJournalStore | None = None) -> None:
        self._store = store or TradeJournalStore()
        self._extractor = LearningSampleExtractor()

    def list_records(self) -> list[CompletedTradeRecord]:
        return self._store.list()

    def import_records(
        self,
        records: list[CompletedTradeRecord],
        mode: str = "append",
    ) -> list[CompletedTradeRecord]:
        return self._store.save(records, mode=mode)

    def extract_learning_samples(
        self,
        *,
        symbol: str | None = None,
        limit: int | None = None,
    ) -> list[LearningTradeSample]:
        return self._extractor.extract(
            self._store.list(),
            symbol=symbol,
            limit=limit,
        )
