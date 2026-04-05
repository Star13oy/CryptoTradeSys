from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.market import OpportunityScore


class RiskDecision(BaseModel):
    decision: Literal["allow", "review", "block"]
    reasons: list[str] = Field(default_factory=list)
    max_position_fraction: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


@dataclass(frozen=True)
class RiskPolicyConfig:
    min_allow_score: float = 100.0
    min_review_score: float = 10.0
    min_allow_net_edge_bps: float = 4.0
    min_allow_projected_edge_bps: float = 2.0
    max_allow_basis_bps: float = 7.0
    max_review_basis_bps: float = 100.0
    max_allow_trading_cost_bps: float = 3.0
    max_allow_payback_periods: float = 1.0


class OpportunityRiskPolicy:
    def __init__(self, config: RiskPolicyConfig | None = None) -> None:
        self._config = config or RiskPolicyConfig()

    def evaluate(self, score: OpportunityScore) -> RiskDecision:
        projected_edge_bps = score.projected_net_edge_bps or score.net_edge_bps
        payback_periods = score.payback_periods

        if projected_edge_bps <= 0 or score.score <= 0 or score.gross_edge_bps <= 0:
            return RiskDecision(
                decision="block",
                reasons=["negative_edge"],
                max_position_fraction=0.0,
                confidence=0.05,
            )

        if score.basis_bps > self._config.max_review_basis_bps:
            return RiskDecision(
                decision="block",
                reasons=["basis_extreme"],
                max_position_fraction=0.0,
                confidence=0.1,
            )

        reasons: list[str] = []
        if score.risk_tag == "guarded" or score.basis_bps > self._config.max_allow_basis_bps:
            reasons.append("basis_wide")
        if score.trading_cost_bps > self._config.max_allow_trading_cost_bps:
            reasons.append("elevated_cost")
        if score.score < self._config.min_allow_score:
            reasons.append("low_score")
        if payback_periods > self._config.max_allow_payback_periods or score.net_edge_bps <= 0:
            reasons.append("slow_payback")
        if projected_edge_bps < self._config.min_allow_projected_edge_bps:
            reasons.append("low_edge")
        elif score.net_edge_bps < self._config.min_allow_net_edge_bps:
            reasons.append("low_edge")

        if reasons:
            if score.score < self._config.min_review_score:
                return RiskDecision(
                    decision="block",
                    reasons=sorted(set(reasons)),
                    max_position_fraction=0.0,
                    confidence=0.2,
                )
            return RiskDecision(
                decision="review",
                reasons=sorted(set(reasons)),
                max_position_fraction=0.35,
                confidence=min(max(score.score / 200, 0.35), 0.75),
            )

        return RiskDecision(
            decision="allow",
            reasons=[],
            max_position_fraction=1.0,
            confidence=min(max(score.score / 160, 0.55), 1.0),
        )
