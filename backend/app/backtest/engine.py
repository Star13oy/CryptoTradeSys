from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, Field

from app.risk import OpportunityRiskPolicy, RiskDecision
from app.schemas.market import MarketSnapshot, OpportunityScore
from app.strategy import StrategyRegistry, build_default_registry


class BacktestPeriod(BaseModel):
    observed_at: datetime | None = None
    snapshots: list[MarketSnapshot] = Field(default_factory=list)


class BacktestConfig(BaseModel):
    notional_per_trade: float = Field(default=1000.0, gt=0.0)
    min_score: float = Field(default=0.0, ge=0.0)
    min_net_edge_bps: float = Field(default=0.0)
    top_k: int = Field(default=1, ge=1, le=20)
    accept_reviewed: bool = False
    strategy_id: str | None = None


class BacktestTrade(BaseModel):
    period_index: int
    observed_at: datetime | None = None
    symbol: str
    funding_rate: float
    score: float
    net_edge_bps: float
    projected_net_edge_bps: float = 0.0
    estimated_pnl: float
    risk_tag: str
    risk_decision: str
    position_fraction: float
    reasons: list[str] = Field(default_factory=list)


class BacktestResult(BaseModel):
    periods_processed: int
    candidates_seen: int = 0
    selected_trades: int = 0
    estimated_total_pnl: float = 0.0
    average_score: float = 0.0
    average_net_edge_bps: float = 0.0
    average_projected_edge_bps: float = 0.0
    trades: list[BacktestTrade] = Field(default_factory=list)


class BacktestEngine:
    def __init__(
        self,
        *,
        strategy_registry: StrategyRegistry | None = None,
        risk_policy: OpportunityRiskPolicy | None = None,
    ) -> None:
        self._strategy_registry = strategy_registry or build_default_registry()
        self._risk_policy = risk_policy or OpportunityRiskPolicy()

    def run(
        self,
        periods: Sequence[BacktestPeriod],
        config: BacktestConfig | None = None,
    ) -> BacktestResult:
        active_config = config or BacktestConfig()
        strategy = self._resolve_strategy(active_config.strategy_id)
        selected_trades: list[BacktestTrade] = []
        candidates_seen = 0

        for period_index, period in enumerate(periods):
            ranked_rows = strategy.score_snapshots(period.snapshots)
            candidates_seen += len(ranked_rows)
            period_selected = 0

            for row in ranked_rows:
                decision = self._risk_policy.evaluate(row)
                if not self._passes_filters(row, decision, active_config):
                    continue
                selected_trades.append(self._to_trade(period_index, period.observed_at, row, decision, active_config))
                period_selected += 1
                if period_selected >= active_config.top_k:
                    break

        estimated_pnl = round(sum(trade.estimated_pnl for trade in selected_trades), 4)
        average_score = self._average([trade.score for trade in selected_trades])
        average_net_edge_bps = self._average([trade.net_edge_bps for trade in selected_trades])
        average_projected_edge_bps = self._average([trade.projected_net_edge_bps for trade in selected_trades])

        return BacktestResult(
            periods_processed=len(periods),
            candidates_seen=candidates_seen,
            selected_trades=len(selected_trades),
            estimated_total_pnl=estimated_pnl,
            average_score=average_score,
            average_net_edge_bps=average_net_edge_bps,
            average_projected_edge_bps=average_projected_edge_bps,
            trades=selected_trades,
        )

    def _passes_filters(
        self,
        score: OpportunityScore,
        decision: RiskDecision,
        config: BacktestConfig,
    ) -> bool:
        projected_edge_bps = score.projected_net_edge_bps or score.net_edge_bps
        if score.score < config.min_score or projected_edge_bps < config.min_net_edge_bps:
            return False
        if decision.decision == "block":
            return False
        if decision.decision == "review" and not config.accept_reviewed:
            return False
        return True

    def _to_trade(
        self,
        period_index: int,
        observed_at: datetime | None,
        score: OpportunityScore,
        decision: RiskDecision,
        config: BacktestConfig,
    ) -> BacktestTrade:
        notional = config.notional_per_trade * decision.max_position_fraction
        projected_edge_bps = score.projected_net_edge_bps or score.net_edge_bps
        estimated_pnl = round((notional * projected_edge_bps) / 10000, 4)
        return BacktestTrade(
            period_index=period_index,
            observed_at=observed_at,
            symbol=score.symbol,
            funding_rate=score.funding_rate,
            score=score.score,
            net_edge_bps=score.net_edge_bps,
            projected_net_edge_bps=projected_edge_bps,
            estimated_pnl=estimated_pnl,
            risk_tag=score.risk_tag,
            risk_decision=decision.decision,
            position_fraction=decision.max_position_fraction,
            reasons=decision.reasons,
        )

    def _resolve_strategy(self, strategy_id: str | None):
        if strategy_id:
            return self._strategy_registry.get(strategy_id)
        return self._strategy_registry.get_default()

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)
