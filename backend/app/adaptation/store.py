from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import get_settings
from app.persistence import MySQLPersistence, mysql_storage_enabled
from app.schemas.adaptation import TuningState

_TABLE_NAME = "tuning_state"
_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
    state_key VARCHAR(64) PRIMARY KEY,
    updated_at DATETIME(6) NOT NULL,
    payload JSON NOT NULL
)
"""


class TuningStateStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._settings = get_settings()
        self._path = Path(path or self._settings.tuning_state_path)
        self._mysql = MySQLPersistence(self._settings)

    def load(self) -> TuningState:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            rows = self._mysql.fetch_json_rows(
                f"SELECT payload FROM {_TABLE_NAME} WHERE state_key = %s LIMIT 1",
                ("active",),
            )
            if not rows:
                return TuningState()
            return TuningState.model_validate(rows[0])
        if not self._path.exists():
            return TuningState()
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return TuningState.model_validate(payload)

    def save(self, state: TuningState) -> TuningState:
        if mysql_storage_enabled(self._settings):
            self._mysql.ensure_table(_TABLE_NAME, _CREATE_TABLE_SQL)
            self._mysql.execute(
                f"""
                REPLACE INTO {_TABLE_NAME} (state_key, updated_at, payload)
                VALUES (%s, %s, CAST(%s AS JSON))
                """,
                (
                    "active",
                    self._mysql.to_mysql_datetime(state.updated_at),
                    self._mysql.serialize(state),
                ),
            )
            return state
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state
