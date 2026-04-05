from app.schemas.market import MarketSnapshot
from app.strategy.funding_arb import FundingArbStrategy
from app.strategy.registry import StrategyRegistry


def make_snapshot(symbol: str, funding_rate: float) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        funding_rate=funding_rate,
        perp_mid=60000,
        spot_mid=60000,
        perp_spread_bps=0.4,
        spot_spread_bps=0.3,
    )


def test_funding_arb_strategy_ranks_snapshots_by_score_desc() -> None:
    strategy = FundingArbStrategy()

    rows = strategy.score_snapshots(
        [
            make_snapshot("BTCUSDT", 0.0002),
            make_snapshot("ETHUSDT", 0.0005),
        ]
    )

    assert [row.symbol for row in rows] == ["ETHUSDT", "BTCUSDT"]
    assert rows[0].score >= rows[1].score


def test_strategy_registry_registers_fetches_and_returns_default_strategy() -> None:
    strategy = FundingArbStrategy()
    registry = StrategyRegistry(default_strategy_id=strategy.strategy_id)

    registry.register(strategy)

    assert registry.get(strategy.strategy_id) is strategy
    assert registry.get_default() is strategy


def test_strategy_registry_rejects_duplicate_strategy_ids() -> None:
    registry = StrategyRegistry(default_strategy_id="funding-arb")

    registry.register(FundingArbStrategy())

    try:
        registry.register(FundingArbStrategy())
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("expected duplicate strategy registration to fail")
