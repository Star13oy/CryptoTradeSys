from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled

from .schemas import LedgerWriteMode, TradeLedgerRecord

_DEFAULT_LEDGER_PATH = "backend/runtime/trade-ledger.json"
_TABLE_NAME = "trade_ledger"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    row_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_id VARCHAR(191) NOT NULL,
    mode VARCHAR(16) NOT NULL,
    strategy_id VARCHAR(191) NOT NULL,
    symbol VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    opened_at DATETIME(6) NOT NULL,
    closed_at DATETIME(6) NULL,
    payload JSON NOT NULL,
    KEY idx_trade_ledger_trade_id (trade_id),
    KEY idx_trade_ledger_symbol_status (symbol, status),
    KEY idx_trade_ledger_mode_status (mode, status)
)
"""


class TradeLedgerStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._settings = get_settings()
        configured = getattr(self._settings, "trade_ledger_path", _DEFAULT_LEDGER_PATH)
        self._path = Path(path or configured)
        self._mysql = MySQLPersistence(self._settings)

    def list(self) -> list[TradeLedgerRecord]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            payloads = self._mysql.fetch_json_rows(f"SELECT payload FROM {_TABLE_NAME} ORDER BY row_id")
            return [TradeLedgerRecord.model_validate(item) for item in payloads]
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [TradeLedgerRecord.model_validate(item) for item in payload]

    def save(
        self,
        records: list[TradeLedgerRecord],
        mode: LedgerWriteMode = "append",
    ) -> list[TradeLedgerRecord]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            persisted = list(records) if mode == "replace" else [*self.list(), *records]
            params = [
                (
                    record.trade_id,
                    record.mode,
                    record.strategy_id,
                    record.symbol,
                    record.status,
                    self._mysql.to_mysql_datetime(record.opened_at),
                    self._mysql.to_mysql_datetime(record.closed_at),
                    self._mysql.serialize(record),
                )
                for record in persisted
            ]
            self._mysql.replace_rows(
                table_name=_TABLE_NAME,
                insert_sql=(
                    f"""
                    INSERT INTO {_TABLE_NAME}
                    (trade_id, mode, strategy_id, symbol, status, opened_at, closed_at, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSON))
                    """
                ),
                params=params,
            )
            return persisted
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
