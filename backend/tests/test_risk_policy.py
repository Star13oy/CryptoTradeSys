from app.opportunity.scorer import score_snapshot
from app.risk.policy import OpportunityRiskPolicy
from app.schemas.market import MarketSnapshot


def make_snapshot(
    *,
    symbol: str = "BTCUSDT",
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


def test_risk_policy_allows_high_quality_opportunity() -> None:
    score = score_snapshot(make_snapshot(funding_rate=0.0008, perp_mid=60006, spot_mid=60000))

    decision = OpportunityRiskPolicy().evaluate(score)

    assert decision.decision == "allow"
    assert decision.reasons == []
    assert decision.max_position_fraction == 1.0
    assert decision.confidence > 0.7


def test_risk_policy_reviews_guarded_opportunity() -> None:
    score = score_snapshot(make_snapshot(funding_rate=0.0008, perp_mid=60500, spot_mid=60000))

    decision = OpportunityRiskPolicy().evaluate(score)

    assert decision.decision == "review"
    assert "basis_wide" in decision.reasons
    assert decision.max_position_fraction < 1.0


def test_risk_policy_blocks_negative_edge_opportunity() -> None:
    score = score_snapshot(make_snapshot(funding_rate=0.00003, perp_spread_bps=0.8, spot_spread_bps=0.7))

    decision = OpportunityRiskPolicy().evaluate(score)

    assert decision.decision == "block"
    assert "negative_edge" in decision.reasons
    assert decision.max_position_fraction == 0.0


def test_risk_policy_reviews_slow_payback_opportunity() -> None:
    score = score_snapshot(make_snapshot(funding_rate=0.00012, perp_mid=60003, spot_mid=60000))

    decision = OpportunityRiskPolicy().evaluate(score)

    assert decision.decision == "review"
    assert "slow_payback" in decision.reasons
    assert decision.max_position_fraction > 0
