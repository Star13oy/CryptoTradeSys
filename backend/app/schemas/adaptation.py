from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from typing import Literal

from app.backtest import BacktestConfig
from app.backtest import BacktestPeriod
from app.opportunity.scorer import ScoreConfig
from app.risk.policy import RiskPolicyConfig


class ScoreConfigSnapshot(BaseModel):
    taker_fee_bps: float = 0.4
    funding_periods_per_day: int = 3
    expected_hold_periods: int = 6
    basis_soft_limit_bps: float = 2.0
    basis_guarded_bps: float = 8.0
    payback_guarded_periods: float = 1.0
    trading_cost_guarded_bps: float = 3.0
    carry_weight: float = 20.0
    annualized_weight: float = 0.15
    cost_soft_limit_bps: float = 1.5
    cost_penalty_weight: float = 1.0
    basis_penalty_weight: float = 1.5

    @classmethod
    def from_domain(cls, config: ScoreConfig) -> "ScoreConfigSnapshot":
        return cls(**config.__dict__)

    def to_domain(self) -> ScoreConfig:
        return ScoreConfig(**self.model_dump())


class RiskConfigSnapshot(BaseModel):
    min_allow_score: float = 100.0
    min_review_score: float = 10.0
    min_allow_net_edge_bps: float = 4.0
    min_allow_projected_edge_bps: float = 2.0
    max_allow_basis_bps: float = 7.0
    max_review_basis_bps: float = 100.0
    max_allow_trading_cost_bps: float = 3.0
    max_allow_payback_periods: float = 1.0

    @classmethod
    def from_domain(cls, config: RiskPolicyConfig) -> "RiskConfigSnapshot":
        return cls(**config.__dict__)

    def to_domain(self) -> RiskPolicyConfig:
        return RiskPolicyConfig(**self.model_dump())


def _default_score_snapshot() -> ScoreConfigSnapshot:
    return ScoreConfigSnapshot.from_domain(ScoreConfig())


def _default_risk_snapshot() -> RiskConfigSnapshot:
    return RiskConfigSnapshot.from_domain(RiskPolicyConfig())


class TuningConfig(BaseModel):
    score: ScoreConfigSnapshot = Field(default_factory=_default_score_snapshot)
    risk: RiskConfigSnapshot = Field(default_factory=_default_risk_snapshot)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)


class LearningTradeSample(BaseModel):
    trade_id: str | None = None
    symbol: str
    closed_at: datetime | None = None
    score: float
    risk_tag: str
    net_edge_bps: float = 0.0
    projected_net_edge_bps: float = 0.0
    basis_bps: float = 0.0
    realized_pnl_bps: float
    max_drawdown_bps: float = 0.0
    hold_periods: float = 1.0


class TradeJournalRecord(BaseModel):
    trade_id: str
    symbol: str
    opened_at: datetime
    closed_at: datetime
    score: float
    risk_tag: str
    net_edge_bps: float
    projected_net_edge_bps: float = 0.0
    basis_bps: float = 0.0
    realized_pnl_bps: float
    max_drawdown_bps: float = 0.0
    hold_periods: float = 1.0


class AdaptationMetrics(BaseModel):
    trade_count: int = 0
    win_rate: float = 0.0
    avg_realized_pnl_bps: float = 0.0
    avg_projected_edge_bps: float = 0.0
    avg_projection_shortfall_bps: float = 0.0
    max_drawdown_p95_bps: float = 0.0
    slow_payback_rate: float = 0.0


class TuningPackage(BaseModel):
    package_id: str
    title: str
    summary: str
    objective: str = "stability-first"
    recommended: bool = False
    derived_from: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    config: TuningConfig


class TuningState(BaseModel):
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_package_id: str = "balanced"
    active_package_title: str = "平衡方案"
    config: TuningConfig = Field(default_factory=TuningConfig)


class AdaptationRecommendationRequest(BaseModel):
    samples: list[LearningTradeSample] = Field(default_factory=list)


class AdaptationRecommendationResponse(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: AdaptationMetrics
    current_state: TuningState
    recommended_package_id: str
    packages: list[TuningPackage] = Field(default_factory=list)


class AdaptationPackageEvaluationRequest(BaseModel):
    dataset_id: str
    limit_recent_periods: int | None = Field(default=None, ge=1)


class PackageBacktestEvaluation(BaseModel):
    package_id: str
    title: str
    recommended: bool = False
    estimated_total_pnl: float = 0.0
    selected_trades: int = 0
    average_score: float = 0.0
    average_projected_edge_bps: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)


class AdaptationPackageEvaluationResponse(BaseModel):
    dataset_id: str
    metrics: AdaptationMetrics
    recommended_package_id: str
    evaluations: list[PackageBacktestEvaluation] = Field(default_factory=list)


class TuningApplyRequest(BaseModel):
    package: TuningPackage
    confirmed: bool = False


class LearningSampleImportRequest(BaseModel):
    samples: list[LearningTradeSample] = Field(default_factory=list)
    mode: Literal["append", "replace"] = "append"


class JournalSampleExtractionRequest(BaseModel):
    mode: Literal["append", "replace"] = "append"
    symbol: str | None = None
    limit: int | None = Field(default=None, ge=1)


class LearningSampleListResponse(BaseModel):
    samples: list[LearningTradeSample] = Field(default_factory=list)


class LearningSampleImportResponse(BaseModel):
    imported_samples: int
    total_samples: int
