from __future__ import annotations

from .schemas import LedgerWriteMode, TradeLedgerRecord, TradeMode, TradeStatus
from .store import TradeLedgerStore


class TradeLedgerService:
    def __init__(self, store: TradeLedgerStore | None = None) -> None:
        self._store = store or TradeLedgerStore()

    def list_records(
        self,
        *,
        mode: TradeMode | None = None,
        status: TradeStatus | None = None,
        strategy_id: str | None = None,
        symbol: str | None = None,
    ) -> list[TradeLedgerRecord]:
        records = self._store.list()
        if mode is not None:
            records = [record for record in records if record.mode == mode]
        if status is not None:
            records = [record for record in records if record.status == status]
        if strategy_id is not None:
            records = [record for record in records if record.strategy_id == strategy_id]
        if symbol is not None:
            records = [record for record in records if record.symbol == symbol]
        return records

    def import_records(
        self,
        records: list[TradeLedgerRecord],
        mode: LedgerWriteMode = "append",
    ) -> list[TradeLedgerRecord]:
        return self._store.save(records, mode=mode)

    def get_record(self, trade_id: str) -> TradeLedgerRecord | None:
        for record in self._store.list():
            if record.trade_id == trade_id:
                return record
        return None

    def save_record(self, record: TradeLedgerRecord) -> TradeLedgerRecord:
        records = self._store.list()
        replaced = False
        for index, existing in enumerate(records):
            if existing.trade_id == record.trade_id:
                records[index] = record
                replaced = True
                break
        if not replaced:
            records.append(record)
        self._store.save(records, mode="replace")
        return record
