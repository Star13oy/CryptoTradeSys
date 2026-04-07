from dataclasses import dataclass

from app.schemas.market import MarketSnapshot, OpportunityScore, ScoreBreakdown


@dataclass(frozen=True)
class ScoreConfig:
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


def _compute_basis_bps(snapshot: MarketSnapshot) -> float:
    if snapshot.spot_mid <= 0:
        return 0.0
    return round(abs((snapshot.perp_mid - snapshot.spot_mid) / snapshot.spot_mid) * 10000, 4)


def score_snapshot(
    snapshot: MarketSnapshot,
    taker_fee_bps: float = 0.4,
    config: ScoreConfig | None = None,
) -> OpportunityScore:
    active_config = config or ScoreConfig(taker_fee_bps=taker_fee_bps)
    gross_edge_bps = round(snapshot.funding_rate * 10000, 4)
    trading_cost_bps = round(
        (active_config.taker_fee_bps * 2) + snapshot.perp_spread_bps + snapshot.spot_spread_bps,
        4,
    )
    net_edge_bps = round(gross_edge_bps - trading_cost_bps, 4)
    annualized_funding_rate_pct = round(
        snapshot.funding_rate * active_config.funding_periods_per_day * 365 * 100,
        4,
    )
    basis_bps = _compute_basis_bps(snapshot)
    projected_net_edge_bps = round(
        (gross_edge_bps * active_config.expected_hold_periods) - trading_cost_bps,
        4,
    )
    payback_periods = round(trading_cost_bps / gross_edge_bps, 4) if gross_edge_bps > 0 else 0.0
    basis_penalty_bps = round(max(basis_bps - active_config.basis_soft_limit_bps, 0), 4)

    carry_component = round(max(projected_net_edge_bps, 0) * active_config.carry_weight, 4)
    annualized_component = round(
        max(annualized_funding_rate_pct, 0) * active_config.annualized_weight,
        4,
    )
    cost_penalty = round(
        max(trading_cost_bps - active_config.cost_soft_limit_bps, 0) * active_config.cost_penalty_weight,
        4,
    )
    basis_penalty = round(basis_penalty_bps * active_config.basis_penalty_weight, 4)
    base_edge_score = round(carry_component + annualized_component, 4)
    score = round(max(base_edge_score - cost_penalty - basis_penalty, 0), 4)

    if gross_edge_bps <= 0 or projected_net_edge_bps <= 0:
        risk_tag = "thin-edge"
    elif (
        net_edge_bps <= 0
        or payback_periods > active_config.payback_guarded_periods
        or basis_bps >= active_config.basis_guarded_bps
        or trading_cost_bps >= active_config.trading_cost_guarded_bps
    ):
        risk_tag = "guarded"
    else:
        risk_tag = "normal"

    return OpportunityScore(
        symbol=snapshot.symbol,
        funding_rate=snapshot.funding_rate,
        net_edge_bps=net_edge_bps,
        score=score,
        risk_tag=risk_tag,
        perp_bid=snapshot.perp_bid,
        perp_ask=snapshot.perp_ask,
        spot_bid=snapshot.spot_bid,
        spot_ask=snapshot.spot_ask,
        perp_mid=snapshot.perp_mid,
        spot_mid=snapshot.spot_mid,
        perp_spread_bps=snapshot.perp_spread_bps,
        spot_spread_bps=snapshot.spot_spread_bps,
        gross_edge_bps=gross_edge_bps,
        trading_cost_bps=trading_cost_bps,
        annualized_funding_rate_pct=annualized_funding_rate_pct,
        basis_bps=basis_bps,
        projected_net_edge_bps=projected_net_edge_bps,
        payback_periods=payback_periods,
        expected_hold_periods=active_config.expected_hold_periods,
        score_breakdown=ScoreBreakdown(
            carry_component=carry_component,
            annualized_component=annualized_component,
            cost_penalty=cost_penalty,
            basis_penalty=basis_penalty,
            projected_edge_bps=projected_net_edge_bps,
            base_edge_score=base_edge_score,
            basis_penalty_score=basis_penalty,
            basis_penalty_bps=basis_penalty_bps,
            final_score=score,
        ),
    )
