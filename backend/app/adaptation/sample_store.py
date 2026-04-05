from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from app.core.settings import get_settings
from app.schemas.adaptation import LearningTradeSample


class LearningSampleStore:
    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        self._path = Path(path or settings.learning_sample_path)

    def load(self) -> list[LearningTradeSample]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [LearningTradeSample.model_validate(item) for item in payload]

    def save(
        self,
        samples: list[LearningTradeSample],
        mode: Literal["append", "replace"] = "append",
    ) -> list[LearningTradeSample]:
        persisted = list(samples) if mode == "replace" else [*self.load(), *samples]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([sample.model_dump(mode="json") for sample in persisted], indent=2),
            encoding="utf-8",
        )
        return persisted
