from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.core.settings import get_settings

from .schemas import CompletedTradeRecord


class TradeJournalStore:
    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        self._path = Path(path or settings.trade_journal_path)

    def list(self) -> list[CompletedTradeRecord]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [CompletedTradeRecord.model_validate(item) for item in payload]

    def save(
        self,
        records: list[CompletedTradeRecord],
        mode: Literal["append", "replace"] = "append",
    ) -> list[CompletedTradeRecord]:
        persisted = list(records) if mode == "replace" else [*self.list(), *records]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([record.model_dump(mode="json") for record in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted

    def append(self, records: list[CompletedTradeRecord]) -> list[CompletedTradeRecord]:
        return self.save(records, mode="append")

    def replace(self, records: list[CompletedTradeRecord]) -> list[CompletedTradeRecord]:
        return self.save(records, mode="replace")
