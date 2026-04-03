from app.schemas.market import MarketSnapshot, OpportunityScore


def score_snapshot(snapshot: MarketSnapshot, taker_fee_bps: float = 0.4) -> OpportunityScore:
    gross_edge_bps = snapshot.funding_rate * 10000
    trading_cost_bps = (taker_fee_bps * 2) + snapshot.perp_spread_bps + snapshot.spot_spread_bps
    net_edge_bps = gross_edge_bps - trading_cost_bps
    risk_tag = "normal" if net_edge_bps > 0 else "thin-edge"
    score = max(net_edge_bps, 0) * 10
    return OpportunityScore(
        symbol=snapshot.symbol,
        funding_rate=snapshot.funding_rate,
        net_edge_bps=net_edge_bps,
        score=score,
        risk_tag=risk_tag,
    )
