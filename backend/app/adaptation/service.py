from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.backtest import BacktestConfig, BacktestEngine, BacktestPeriod
from app.risk import OpportunityRiskPolicy
from app.schemas.adaptation import (
    AdaptationMetrics,
    AdaptationPackageEvaluationResponse,
    AdaptationRecommendationResponse,
    LearningTradeSample,
    PackageBacktestEvaluation,
    TradeJournalRecord,
    TuningApplyRequest,
    TuningConfig,
    TuningPackage,
    TuningState,
)
from app.strategy import StrategyRegistry, build_default_registry

from .extractor import TradeJournalExtractor
from .sample_store import LearningSampleStore
from .store import TuningStateStore


@dataclass(frozen=True)
class RuntimeComponents:
    strategy_registry: StrategyRegistry
    risk_policy: OpportunityRiskPolicy
    backtest_config: BacktestConfig


class AdaptationService:
    def __init__(
        self,
        store: TuningStateStore | None = None,
        sample_store: LearningSampleStore | None = None,
        sample_store_path: str | Path | None = None,
    ) -> None:
        self._store = store or TuningStateStore()
        self._sample_store = sample_store or LearningSampleStore(sample_store_path)
        self._extractor = TradeJournalExtractor()

    def get_state(self) -> TuningState:
        return self._store.load()

    def build_runtime_components(self) -> RuntimeComponents:
        state = self.get_state()
        return self.build_runtime_components_from_config(state.config)

    def build_runtime_components_from_config(self, config: TuningConfig) -> RuntimeComponents:
        return RuntimeComponents(
            strategy_registry=build_default_registry(score_config=config.score.to_domain()),
            risk_policy=OpportunityRiskPolicy(config.risk.to_domain()),
            backtest_config=config.backtest,
        )

    def recommend(self, samples: list[LearningTradeSample]) -> AdaptationRecommendationResponse:
        current_state = self.get_state()
        metrics = self._compute_metrics(samples)
        conservative = self._build_conservative_package(current_state.config, metrics)
        balanced = self._build_balanced_package(current_state.config, metrics)
        aggressive = self._build_aggressive_package(current_state.config, metrics)
        auto_target, reason_codes = self._select_auto_target(metrics)
        target_package = {
            "conservative": conservative,
            "balanced": balanced,
            "aggressive": aggressive,
        }[auto_target]
        auto = TuningPackage(
            package_id="auto",
            title="系统自动推荐",
            summary=self._build_auto_summary(auto_target, metrics),
            recommended=True,
            derived_from=auto_target,
            reason_codes=reason_codes,
            config=target_package.config,
        )
        return AdaptationRecommendationResponse(
            generated_at=datetime.now(timezone.utc),
            metrics=metrics,
            current_state=current_state,
            recommended_package_id="auto",
            packages=[conservative, balanced, aggressive, auto],
        )

    def recommend_from_store(self) -> AdaptationRecommendationResponse:
        return self.recommend(self.get_samples())

    def apply(self, request: TuningApplyRequest) -> TuningState:
        if not request.confirmed:
            raise ValueError("manual confirmation is required before applying a tuning package")
        state = TuningState(
            updated_at=datetime.now(timezone.utc),
            active_package_id=request.package.package_id,
            active_package_title=request.package.title,
            config=request.package.config,
        )
        return self._store.save(state)

    def get_samples(self) -> list[LearningTradeSample]:
        return self._sample_store.load()

    def import_samples(
        self,
        samples: list[LearningTradeSample],
        mode: str = "append",
    ) -> list[LearningTradeSample]:
        return self._sample_store.save(samples, mode=mode)

    def extract_from_trade_journal(
        self,
        records: list[TradeJournalRecord],
        *,
        symbol: str | None = None,
        recent_n: int | None = None,
    ) -> list[LearningTradeSample]:
        return self._extractor.extract(records, symbol=symbol, recent_n=recent_n)

    def evaluate_packages_against_periods(
        self,
        dataset_id: str,
        periods: list[BacktestPeriod],
        *,
        samples: list[LearningTradeSample] | None = None,
    ) -> AdaptationPackageEvaluationResponse:
        recommendation = self.recommend(self.get_samples() if samples is None else samples)
        evaluations: list[PackageBacktestEvaluation] = []

        for package in recommendation.packages:
            runtime = self.build_runtime_components_from_config(package.config)
            result = BacktestEngine(
                strategy_registry=runtime.strategy_registry,
                risk_policy=runtime.risk_policy,
            ).run(periods, package.config.backtest)
            evaluations.append(
                PackageBacktestEvaluation(
                    package_id=package.package_id,
                    title=package.title,
                    recommended=package.package_id == recommendation.recommended_package_id,
                    estimated_total_pnl=result.estimated_total_pnl,
                    selected_trades=result.selected_trades,
                    average_score=result.average_score,
                    average_projected_edge_bps=result.average_projected_edge_bps,
                    reason_codes=package.reason_codes,
                )
            )

        return AdaptationPackageEvaluationResponse(
            dataset_id=dataset_id,
            metrics=recommendation.metrics,
            recommended_package_id=recommendation.recommended_package_id,
            evaluations=evaluations,
        )

    def _compute_metrics(self, samples: list[LearningTradeSample]) -> AdaptationMetrics:
        if not samples:
            return AdaptationMetrics()

        trade_count = len(samples)
        wins = sum(1 for sample in samples if sample.realized_pnl_bps > 0)
        drawdowns = sorted(sample.max_drawdown_bps for sample in samples)
        p95_index = max(int((len(drawdowns) - 1) * 0.95), 0)
        avg_realized = round(sum(sample.realized_pnl_bps for sample in samples) / trade_count, 4)
        avg_projected = round(sum(sample.projected_net_edge_bps for sample in samples) / trade_count, 4)
        avg_shortfall = round(
            sum(sample.projected_net_edge_bps - sample.realized_pnl_bps for sample in samples) / trade_count,
            4,
        )
        slow_payback_rate = round(
            sum(1 for sample in samples if sample.hold_periods >= 7) / trade_count,
            4,
        )
        return AdaptationMetrics(
            trade_count=trade_count,
            win_rate=round(wins / trade_count, 4),
            avg_realized_pnl_bps=avg_realized,
            avg_projected_edge_bps=avg_projected,
            avg_projection_shortfall_bps=avg_shortfall,
            max_drawdown_p95_bps=round(drawdowns[p95_index], 4),
            slow_payback_rate=slow_payback_rate,
        )

    def _build_conservative_package(self, current: TuningConfig, metrics: AdaptationMetrics) -> TuningPackage:
        config = TuningConfig(
            score=current.score.model_copy(
                update={
                    "expected_hold_periods": min(current.score.expected_hold_periods + 2, 12),
                    "basis_guarded_bps": max(current.score.basis_guarded_bps - 1.0, 4.0),
                    "payback_guarded_periods": max(current.score.payback_guarded_periods - 0.25, 0.5),
                    "cost_penalty_weight": current.score.cost_penalty_weight + 0.25,
                    "basis_penalty_weight": current.score.basis_penalty_weight + 0.25,
                }
            ),
            risk=current.risk.model_copy(
                update={
                    "min_allow_score": current.risk.min_allow_score + 15,
                    "min_review_score": current.risk.min_review_score + 5,
                    "max_allow_basis_bps": max(current.risk.max_allow_basis_bps - 1.0, 4.0),
                    "max_allow_payback_periods": max(current.risk.max_allow_payback_periods - 0.2, 0.6),
                }
            ),
            backtest=current.backtest.model_copy(
                update={
                    "min_score": current.backtest.min_score + 10,
                    "accept_reviewed": False,
                }
            ),
        )
        return TuningPackage(
            package_id="conservative",
            title="保守方案",
            summary=(
                "优先压低误判和回撤，抬高准入门槛，缩小 basis 与慢回本机会的放行范围。"
            ),
            reason_codes=self._stability_reason_codes(metrics),
            config=config,
        )

    def _build_balanced_package(self, current: TuningConfig, metrics: AdaptationMetrics) -> TuningPackage:
        config = TuningConfig(
            score=current.score.model_copy(
                update={
                    "expected_hold_periods": max(current.score.expected_hold_periods, 6),
                }
            ),
            risk=current.risk.model_copy(),
            backtest=current.backtest.model_copy(),
        )
        return TuningPackage(
            package_id="balanced",
            title="平衡方案",
            summary="保持当前风险收益折中，只做轻微稳定化，不明显放宽也不明显收紧。",
            reason_codes=["stability_first_default"],
            config=config,
        )

    def _build_aggressive_package(self, current: TuningConfig, metrics: AdaptationMetrics) -> TuningPackage:
        config = TuningConfig(
            score=current.score.model_copy(
                update={
                    "expected_hold_periods": max(current.score.expected_hold_periods - 1, 4),
                    "basis_guarded_bps": current.score.basis_guarded_bps + 1.0,
                    "payback_guarded_periods": current.score.payback_guarded_periods + 0.25,
                }
            ),
            risk=current.risk.model_copy(
                update={
                    "min_allow_score": max(current.risk.min_allow_score - 15, 50),
                    "max_allow_basis_bps": current.risk.max_allow_basis_bps + 1.0,
                    "max_allow_payback_periods": current.risk.max_allow_payback_periods + 0.2,
                }
            ),
            backtest=current.backtest.model_copy(
                update={
                    "min_score": max(current.backtest.min_score - 10, 0),
                    "accept_reviewed": True,
                    "top_k": min(current.backtest.top_k + 1, 3),
                }
            ),
        )
        return TuningPackage(
            package_id="aggressive",
            title="进取方案",
            summary="扩大机会覆盖面，提高出手机会与资金利用率，但波动和误判容忍度也会更高。",
            reason_codes=["throughput_bias"],
            config=config,
        )

    def _select_auto_target(self, metrics: AdaptationMetrics) -> tuple[str, list[str]]:
        reason_codes = self._stability_reason_codes(metrics)
        if metrics.trade_count < 5:
            reason_codes.append("sample_too_small")
        if reason_codes:
            return "conservative", reason_codes
        return "balanced", ["stability_first_default"]

    def _stability_reason_codes(self, metrics: AdaptationMetrics) -> list[str]:
        reason_codes: list[str] = []
        if metrics.win_rate < 0.55:
            reason_codes.append("win_rate_weak")
        if metrics.avg_realized_pnl_bps < 0.25:
            reason_codes.append("realized_edge_weak")
        if metrics.avg_projection_shortfall_bps > 2.0:
            reason_codes.append("projection_shortfall_high")
        if metrics.max_drawdown_p95_bps > 6.0:
            reason_codes.append("drawdown_high")
        if metrics.slow_payback_rate > 0.4:
            reason_codes.append("payback_slow")
        return reason_codes

    def _build_auto_summary(self, auto_target: str, metrics: AdaptationMetrics) -> str:
        if auto_target == "conservative":
            return (
                "系统检测到近期稳定性偏弱，自动推荐更稳的参数组合。"
                f" 当前胜率 {metrics.win_rate:.2f}，慢回本占比 {metrics.slow_payback_rate:.2f}。"
            )
        return "系统认为当前更适合维持平衡配置，先稳住收益波动，再观察更多样本。"
