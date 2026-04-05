from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import get_settings

from .schemas import ExchangeOrderReport, ExchangeReportWriteMode


class ExchangeOrderReportStore:
    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        self._path = Path(path or settings.exchange_order_report_path)

    def list(self) -> list[ExchangeOrderReport]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [ExchangeOrderReport.model_validate(item) for item in payload]

    def save(
        self,
        reports: list[ExchangeOrderReport],
        mode: ExchangeReportWriteMode = "append",
    ) -> list[ExchangeOrderReport]:
        persisted = list(reports) if mode == "replace" else [*self.list(), *reports]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([report.model_dump(mode="json") for report in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted
