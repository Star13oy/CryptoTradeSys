from __future__ import annotations

import json
from pathlib import Path

from app.core.settings import get_settings
from app.schemas.adaptation import TuningState


class TuningStateStore:
    def __init__(self, path: str | Path | None = None) -> None:
        settings = get_settings()
        self._path = Path(path or settings.tuning_state_path)

    def load(self) -> TuningState:
        if not self._path.exists():
            return TuningState()
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return TuningState.model_validate(payload)

    def save(self, state: TuningState) -> TuningState:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state
