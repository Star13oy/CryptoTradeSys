from app.opportunity.scorer import score_snapshot
from app.schemas.market import MarketSnapshot


def make_snapshot(
    *,
    symbol: str = "BTCUSDT",
    funding_rate: float,
    perp_bid: float = 60005,
    perp_ask: float = 60007,
    spot_bid: float = 59999,
    spot_ask: float = 60001,
    perp_mid: float = 60000,
    spot_mid: float = 60000,
    perp_spread_bps: float = 0.4,
    spot_spread_bps: float = 0.3,
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        funding_rate=funding_rate,
        perp_bid=perp_bid,
        perp_ask=perp_ask,
        spot_bid=spot_bid,
        spot_ask=spot_ask,
        perp_mid=perp_mid,
        spot_mid=spot_mid,
        perp_spread_bps=perp_spread_bps,
        spot_spread_bps=spot_spread_bps,
    )


def test_score_snapshot_marks_high_quality_opportunity_normal() -> None:
    snapshot = make_snapshot(funding_rate=0.0008, perp_mid=60006, spot_mid=60000)

    scored = score_snapshot(snapshot)

    assert scored.risk_tag == "normal"
    assert scored.gross_edge_bps == 8.0
    assert scored.trading_cost_bps == 1.5
    assert round(scored.annualized_funding_rate_pct, 2) == 87.6
    assert scored.basis_bps > 0
    assert scored.score > 0
    assert scored.score_breakdown.carry_component > scored.score_breakdown.cost_penalty
    assert scored.perp_bid == 60005
    assert scored.perp_ask == 60007
    assert scored.spot_bid == 59999
    assert scored.spot_ask == 60001


def test_score_snapshot_penalizes_large_basis_and_marks_guarded() -> None:
    normal = score_snapshot(make_snapshot(symbol="BTCUSDT", funding_rate=0.0008, perp_mid=60006, spot_mid=60000))
    guarded = score_snapshot(make_snapshot(symbol="ETHUSDT", funding_rate=0.0008, perp_mid=60500, spot_mid=60000))

    assert guarded.risk_tag == "guarded"
    assert guarded.basis_bps > normal.basis_bps
    assert guarded.score_breakdown.basis_penalty > normal.score_breakdown.basis_penalty
    assert guarded.score < normal.score


def test_score_snapshot_marks_negative_net_edge_as_thin_edge() -> None:
    snapshot = make_snapshot(funding_rate=0.00003, perp_spread_bps=0.8, spot_spread_bps=0.7)

    scored = score_snapshot(snapshot)

    assert scored.net_edge_bps < 0
    assert scored.risk_tag == "thin-edge"
    assert scored.score == 0


def test_score_snapshot_projects_edge_over_holding_window() -> None:
    snapshot = make_snapshot(funding_rate=0.00012, perp_mid=60003, spot_mid=60000)

    scored = score_snapshot(snapshot)

    assert scored.net_edge_bps < 0
    assert scored.projected_net_edge_bps > 0
    assert scored.expected_hold_periods >= 4
    assert scored.payback_periods > 1
    assert scored.risk_tag == "guarded"
    assert scored.score > 0
