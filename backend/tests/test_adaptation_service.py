from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from app.adaptation.service import AdaptationService
from app.adaptation.store import TuningStateStore
from app.schemas.adaptation import LearningTradeSample, TradeJournalRecord, TuningApplyRequest
from app.schemas.market import MarketSnapshot


def make_samples() -> list[LearningTradeSample]:
    return [
        LearningTradeSample(
            symbol="BTCUSDT",
            score=95,
            risk_tag="guarded",
            net_edge_bps=-0.4,
            projected_net_edge_bps=2.6,
            basis_bps=6.8,
            realized_pnl_bps=-1.8,
            max_drawdown_bps=9.5,
            hold_periods=9,
        ),
        LearningTradeSample(
            symbol="ETHUSDT",
            score=82,
            risk_tag="guarded",
            net_edge_bps=-0.2,
            projected_net_edge_bps=2.2,
            basis_bps=7.4,
            realized_pnl_bps=-0.6,
            max_drawdown_bps=7.2,
            hold_periods=8,
        ),
        LearningTradeSample(
            symbol="SOLUSDT",
            score=76,
            risk_tag="normal",
            net_edge_bps=0.2,
            projected_net_edge_bps=2.8,
            basis_bps=4.4,
            realized_pnl_bps=0.1,
            max_drawdown_bps=5.1,
            hold_periods=7,
        ),
    ]


def make_snapshot(symbol: str, funding_rate: float) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        funding_rate=funding_rate,
        perp_mid=60000,
        spot_mid=60000,
        perp_spread_bps=0.4,
        spot_spread_bps=0.3,
    )


def build_service(state_path: Path) -> AdaptationService:
    return AdaptationService(TuningStateStore(state_path))


def make_state_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}.json"


def test_adaptation_service_generates_four_packages_and_stability_first_auto_pick() -> None:
    service = build_service(make_state_path())

    recommendation = service.recommend(make_samples())

    assert recommendation.metrics.trade_count == 3
    assert len(recommendation.packages) == 4
    assert recommendation.recommended_package_id == "auto"
    auto_package = next(pkg for pkg in recommendation.packages if pkg.package_id == "auto")
    assert auto_package.recommended is True
    assert auto_package.derived_from == "conservative"
    assert auto_package.config.risk.min_allow_score > recommendation.current_state.config.risk.min_allow_score


def test_adaptation_service_apply_persists_confirmed_package_and_affects_runtime_components() -> None:
    state_path = make_state_path()
    service = build_service(state_path)
    recommendation = service.recommend(make_samples())
    auto_package = next(pkg for pkg in recommendation.packages if pkg.package_id == "auto")

    applied_state = service.apply(TuningApplyRequest(package=auto_package, confirmed=True))
    reloaded_service = build_service(state_path)
    runtime = reloaded_service.build_runtime_components()
    rows = runtime.strategy_registry.get_default().score_snapshots([make_snapshot("BTCUSDT", 0.0002)])

    assert applied_state.active_package_id == "auto"
    assert reloaded_service.get_state().active_package_id == "auto"
    assert rows[0].expected_hold_periods == applied_state.config.score.expected_hold_periods


def test_adaptation_service_extracts_learning_samples_from_trade_journal() -> None:
    service = build_service(make_state_path())
    records = [
        TradeJournalRecord(
            trade_id="trade-1",
            symbol="BTCUSDT",
            opened_at=datetime(2026, 4, 4, 8, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc),
            score=91,
            risk_tag="guarded",
            net_edge_bps=-0.3,
            projected_net_edge_bps=2.5,
            basis_bps=5.4,
            realized_pnl_bps=1.4,
            max_drawdown_bps=4.1,
            hold_periods=7,
        ),
        TradeJournalRecord(
            trade_id="trade-2",
            symbol="ETHUSDT",
            opened_at=datetime(2026, 4, 4, 9, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 4, 13, 0, tzinfo=timezone.utc),
            score=89,
            risk_tag="normal",
            net_edge_bps=0.1,
            projected_net_edge_bps=2.2,
            basis_bps=4.4,
            realized_pnl_bps=0.9,
            max_drawdown_bps=3.2,
            hold_periods=6,
        ),
    ]

    samples = service.extract_from_trade_journal(records, symbol="BTCUSDT")

    assert len(samples) == 1
    assert samples[0].trade_id == "trade-1"
    assert samples[0].symbol == "BTCUSDT"
