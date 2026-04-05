from __future__ import annotations

from typing import Iterable

from app.opportunity.scorer import ScoreConfig

from .base import Strategy
from .funding_arb import FundingArbStrategy


class StrategyRegistry:
    def __init__(
        self,
        strategies: Iterable[Strategy] | None = None,
        default_strategy_id: str | None = None,
    ) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._default_strategy_id: str | None = default_strategy_id

        if strategies is not None:
            for strategy in strategies:
                self.register(strategy)

    def register(self, strategy: Strategy) -> None:
        strategy_id = strategy.strategy_id
        if strategy_id in self._strategies:
            raise ValueError(f"Strategy '{strategy_id}' is already registered")

        self._strategies[strategy_id] = strategy
        if self._default_strategy_id is None:
            self._default_strategy_id = strategy_id

    def get(self, strategy_id: str) -> Strategy:
        try:
            return self._strategies[strategy_id]
        except KeyError as exc:
            raise KeyError(f"Unknown strategy '{strategy_id}'") from exc

    def get_default(self) -> Strategy:
        if self._default_strategy_id is None:
            raise KeyError("No strategies have been registered")
        return self.get(self._default_strategy_id)

    def get_default_strategy(self) -> Strategy:
        return self.get_default()


def build_default_registry(score_config: ScoreConfig | None = None) -> StrategyRegistry:
    strategy = FundingArbStrategy(score_config=score_config)
    return StrategyRegistry(
        strategies=[strategy],
        default_strategy_id=strategy.strategy_id,
    )
