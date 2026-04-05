from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.schemas.market import MarketSnapshot, OpportunityScore


class Strategy(ABC):
    _strategy_id: str
    _name: str

    @abstractmethod
    def score_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> list[OpportunityScore]:
        raise NotImplementedError

    def rank_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> list[OpportunityScore]:
        return self.score_snapshots(snapshots)

    @property
    def strategy_id(self) -> str:
        return type(self)._strategy_id

    @property
    def name(self) -> str:
        return type(self)._name
