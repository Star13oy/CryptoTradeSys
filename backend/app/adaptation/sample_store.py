from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.core.settings import get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled
from app.schemas.adaptation import LearningTradeSample

_TABLE_NAME = "learning_samples"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    row_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_id VARCHAR(191) NULL,
    symbol VARCHAR(64) NOT NULL,
    closed_at DATETIME(6) NULL,
    score DOUBLE NOT NULL,
    risk_tag VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    KEY idx_learning_samples_trade_id (trade_id),
    KEY idx_learning_samples_symbol_closed_at (symbol, closed_at)
)
"""


class LearningSampleStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._settings = get_settings()
        self._path = Path(path or self._settings.learning_sample_path)
        self._mysql = MySQLPersistence(self._settings)

    def load(self) -> list[LearningTradeSample]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            payloads = self._mysql.fetch_json_rows(f"SELECT payload FROM {_TABLE_NAME} ORDER BY row_id")
            return [LearningTradeSample.model_validate(item) for item in payloads]
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [LearningTradeSample.model_validate(item) for item in payload]

    def save(
        self,
        samples: list[LearningTradeSample],
        mode: Literal["append", "replace"] = "append",
    ) -> list[LearningTradeSample]:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            persisted = list(samples) if mode == "replace" else [*self.load(), *samples]
            params = [
                (
                    sample.trade_id,
                    sample.symbol,
                    self._mysql.to_mysql_datetime(sample.closed_at),
                    sample.score,
                    sample.risk_tag,
                    self._mysql.serialize(sample),
                )
                for sample in persisted
            ]
            self._mysql.replace_rows(
                table_name=_TABLE_NAME,
                insert_sql=(
                    f"""
                    INSERT INTO {_TABLE_NAME} (trade_id, symbol, closed_at, score, risk_tag, payload)
                    VALUES (%s, %s, %s, %s, %s, CAST(%s AS JSON))
                    """
                ),
                params=params,
            )
            return persisted
        persisted = list(samples) if mode == "replace" else [*self.load(), *samples]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([sample.model_dump(mode="json") for sample in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted
