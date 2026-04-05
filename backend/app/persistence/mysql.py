from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Iterator

from app.core.settings import Settings, get_settings

_DATABASE_READY: set[tuple[str, int, str]] = set()
_TABLES_READY: set[tuple[str, int, str, str]] = set()
_SCHEMA_LOCK = RLock()


def mysql_storage_enabled(settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()
    return active_settings.storage_backend == "mysql"


class MySQLPersistence:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @contextmanager
    def cursor(self) -> Iterator[Any]:
        self._ensure_database()
        driver = self._load_driver()
        connection = driver.connect(
            host=self._settings.mysql_host,
            port=self._settings.mysql_port,
            user=self._settings.mysql_user,
            password=self._settings.mysql_password,
            database=self._settings.mysql_database,
            charset=self._settings.mysql_charset,
            autocommit=True,
            cursorclass=driver.cursors.DictCursor,
        )
        try:
            with connection.cursor() as cursor:
                yield cursor
        finally:
            connection.close()

    def ensure_table(self, table_name: str, ddl: str) -> None:
        table_key = (
            self._settings.mysql_host,
            self._settings.mysql_port,
            self._settings.mysql_database,
            table_name,
        )
        if table_key in _TABLES_READY:
            return
        with _SCHEMA_LOCK:
            if table_key in _TABLES_READY:
                return
            with self.cursor() as cursor:
                cursor.execute(ddl)
            _TABLES_READY.add(table_key)

    def fetch_json_rows(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self.cursor() as cursor:
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
        decoded: list[dict[str, Any]] = []
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode("utf-8")
            if isinstance(payload, str):
                payload = json.loads(payload)
            decoded.append(payload)
        return decoded

    def execute(self, statement: str, params: tuple[Any, ...] | None = None) -> None:
        with self.cursor() as cursor:
            cursor.execute(statement, params or ())

    def executemany(self, statement: str, params: list[tuple[Any, ...]]) -> None:
        if not params:
            return
        with self.cursor() as cursor:
            cursor.executemany(statement, params)

    def replace_rows(
        self,
        *,
        table_name: str,
        insert_sql: str,
        params: list[tuple[Any, ...]],
    ) -> None:
        with self.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table_name}")
            if params:
                cursor.executemany(insert_sql, params)

    def serialize(self, payload: Any) -> str:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump(mode="json")
        return json.dumps(payload, ensure_ascii=False)

    def to_mysql_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def _ensure_database(self) -> None:
        db_key = (
            self._settings.mysql_host,
            self._settings.mysql_port,
            self._settings.mysql_database,
        )
        if db_key in _DATABASE_READY:
            return
        with _SCHEMA_LOCK:
            if db_key in _DATABASE_READY:
                return
            driver = self._load_driver()
            connection = driver.connect(
                host=self._settings.mysql_host,
                port=self._settings.mysql_port,
                user=self._settings.mysql_user,
                password=self._settings.mysql_password,
                charset=self._settings.mysql_charset,
                autocommit=True,
            )
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{self._settings.mysql_database}` "
                        f"CHARACTER SET {self._settings.mysql_charset}"
                    )
            finally:
                connection.close()
            _DATABASE_READY.add(db_key)

    def _load_driver(self) -> Any:
        try:
            import pymysql
        except ImportError as exc:  # pragma: no cover - exercised in runtime smoke, not unit tests
            raise RuntimeError(
                "MySQL storage backend requires PyMySQL. Install backend dependencies before enabling storage_backend=mysql."
            ) from exc
        return pymysql
