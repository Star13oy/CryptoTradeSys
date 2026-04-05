from app.backtest.engine import BacktestConfig, BacktestEngine, BacktestPeriod
from app.schemas.market import MarketSnapshot


def make_snapshot(
    *,
    symbol: str,
    funding_rate: float,
    perp_mid: float = 60000,
    spot_mid: float = 60000,
    perp_spread_bps: float = 0.4,
    spot_spread_bps: float = 0.3,
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        funding_rate=funding_rate,
        perp_mid=perp_mid,
        spot_mid=spot_mid,
        perp_spread_bps=perp_spread_bps,
        spot_spread_bps=spot_spread_bps,
    )


def test_backtest_engine_replays_periods_and_accumulates_estimated_pnl() -> None:
    engine = BacktestEngine()
    periods = [
        BacktestPeriod(
            snapshots=[
                make_snapshot(symbol="BTCUSDT", funding_rate=0.0008, perp_mid=60006, spot_mid=60000),
                make_snapshot(symbol="ETHUSDT", funding_rate=0.0002),
            ]
        ),
        BacktestPeriod(
            snapshots=[
                make_snapshot(symbol="SOLUSDT", funding_rate=0.0007, perp_mid=180.12, spot_mid=180),
            ]
        ),
    ]

    result = engine.run(periods, BacktestConfig(notional_per_trade=10000, min_score=50, top_k=1))

    assert result.periods_processed == 2
    assert result.candidates_seen == 3
    assert result.selected_trades == 2
    assert result.estimated_total_pnl > 0
    assert result.average_score > 50
    assert [trade.symbol for trade in result.trades] == ["BTCUSDT", "SOLUSDT"]


def test_backtest_engine_filters_out_blocked_or_low_score_candidates() -> None:
    engine = BacktestEngine()
    periods = [
        BacktestPeriod(
            snapshots=[
                make_snapshot(symbol="BTCUSDT", funding_rate=0.00003, perp_spread_bps=0.8, spot_spread_bps=0.7),
                make_snapshot(symbol="ETHUSDT", funding_rate=0.0003),
            ]
        )
    ]

    result = engine.run(periods, BacktestConfig(notional_per_trade=10000, min_score=80, top_k=2))

    assert result.periods_processed == 1
    assert result.candidates_seen == 2
    assert result.selected_trades == 0
    assert result.estimated_total_pnl == 0
    assert result.trades == []


def test_backtest_engine_can_include_reviewed_candidates_when_enabled() -> None:
    engine = BacktestEngine()
    periods = [
        BacktestPeriod(
            snapshots=[
                make_snapshot(symbol="BTCUSDT", funding_rate=0.00012, perp_mid=60003, spot_mid=60000),
            ]
        )
    ]

    result = engine.run(
        periods,
        BacktestConfig(
            notional_per_trade=10000,
            min_score=10,
            top_k=1,
            accept_reviewed=True,
        ),
    )

    assert result.selected_trades == 1
    assert result.trades[0].risk_decision == "review"
    assert result.estimated_total_pnl > 0
