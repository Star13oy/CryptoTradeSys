from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import get_settings

from .schemas import LedgerWriteMode, TradeLedgerRecord

_DEFAULT_LEDGER_PATH = "backend/runtime/trade-ledger.json"


class TradeLedgerStore:
    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        configured = getattr(settings, "trade_ledger_path", _DEFAULT_LEDGER_PATH)
        self._path = Path(path or configured)

    def list(self) -> list[TradeLedgerRecord]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [TradeLedgerRecord.model_validate(item) for item in payload]

    def save(
        self,
        records: list[TradeLedgerRecord],
        mode: LedgerWriteMode = "append",
    ) -> list[TradeLedgerRecord]:
        persisted = list(records) if mode == "replace" else [*self.list(), *records]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([record.model_dump(mode="json") for record in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted

    def append(self, records: list[TradeLedgerRecord]) -> list[TradeLedgerRecord]:
        return self.save(records, mode="append")

    def replace(self, records: list[TradeLedgerRecord]) -> list[TradeLedgerRecord]:
        return self.save(records, mode="replace")
