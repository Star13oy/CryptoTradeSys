from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled

from .schemas import ExchangeOrderReport, ExchangeReportWriteMode

_TABLE_NAME = "exchange_order_reports"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    row_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(191) NOT NULL,
    venue VARCHAR(64) NOT NULL,
    order_id VARCHAR(191) NOT NULL,
    trade_id VARCHAR(191) NULL,
    symbol VARCHAR(64) NOT NULL,
    leg VARCHAR(16) NOT NULL,
    status VARCHAR(64) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    payload JSON NOT NULL,
    KEY idx_exchange_order_reports_report_id (report_id),
    KEY idx_exchange_order_reports_order_id (order_id),
    KEY idx_exchange_order_reports_trade_id (trade_id),
    KEY idx_exchange_order_reports_symbol_updated_at (symbol, updated_at)
)
"""


class ExchangeOrderReportStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._settings = get_settings()
        self._path = Path(path or self._settings.exchange_order_report_path)
        self._mysql = MySQLPersistence(self._settings)

    def list(self) -> list[ExchangeOrderReport]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            payloads = self._mysql.fetch_json_rows(f"SELECT payload FROM {_TABLE_NAME} ORDER BY row_id")
            return [ExchangeOrderReport.model_validate(item) for item in payloads]
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [ExchangeOrderReport.model_validate(item) for item in payload]

    def save(
        self,
        reports: list[ExchangeOrderReport],
        mode: ExchangeReportWriteMode = "append",
    ) -> list[ExchangeOrderReport]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            persisted = list(reports) if mode == "replace" else [*self.list(), *reports]
            params = [
                (
                    report.report_id,
                    report.venue,
                    report.order_id,
                    report.trade_id,
                    report.symbol,
                    report.leg,
                    report.status,
                    self._mysql.to_mysql_datetime(report.updated_at),
                    self._mysql.serialize(report),
                )
                for report in persisted
            ]
            self._mysql.replace_rows(
                table_name=_TABLE_NAME,
                insert_sql=(
                    f"""
                    INSERT INTO {_TABLE_NAME}
                    (report_id, venue, order_id, trade_id, symbol, leg, status, updated_at, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSON))
                    """
                ),
                params=params,
            )
            return persisted
        persisted = list(reports) if mode == "replace" else [*self.list(), *reports]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([report.model_dump(mode="json") for report in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted
