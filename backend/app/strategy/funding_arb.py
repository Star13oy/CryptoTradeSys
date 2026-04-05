from __future__ import annotations

from typing import Sequence

from app.opportunity import scorer
from app.opportunity.scorer import ScoreConfig
from app.schemas.market import MarketSnapshot, OpportunityScore

from .base import Strategy


class FundingArbStrategy(Strategy):
    _strategy_id = "funding-arb"
    _name = "Funding Arbitrage"

    def __init__(self, score_config: ScoreConfig | None = None) -> None:
        self._score_config = score_config

    def score_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> list[OpportunityScore]:
        ranked = [scorer.score_snapshot(snapshot, config=self._score_config) for snapshot in snapshots]
        return sorted(ranked, key=lambda row: row.score, reverse=True)
