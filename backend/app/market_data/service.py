from app.schemas.market import MarketSnapshot


def build_market_snapshot(funding_rows: list[dict], perp_rows: list[dict], spot_rows: list[dict]) -> list[MarketSnapshot]:
    perp_map = {row["symbol"]: row for row in perp_rows}
    spot_map = {row["symbol"]: row for row in spot_rows}
    snapshots: list[MarketSnapshot] = []

    for funding in funding_rows:
        symbol = funding["symbol"]
        if symbol not in perp_map or symbol not in spot_map:
            continue

        perp = perp_map[symbol]
        spot = spot_map[symbol]
        funding_rate = funding.get("fundingRate", funding.get("lastFundingRate"))
        if funding_rate is None:
            continue
        perp_bid = float(perp["bidPrice"])
        perp_ask = float(perp["askPrice"])
        spot_bid = float(spot["bidPrice"])
        spot_ask = float(spot["askPrice"])
        if min(perp_bid, perp_ask, spot_bid, spot_ask) <= 0:
            continue

        perp_mid = (perp_bid + perp_ask) / 2
        spot_mid = (spot_bid + spot_ask) / 2

        snapshots.append(
            MarketSnapshot(
                symbol=symbol,
                funding_rate=float(funding_rate),
                perp_mid=perp_mid,
                spot_mid=spot_mid,
                perp_spread_bps=((perp_ask - perp_bid) / perp_mid) * 10000,
                spot_spread_bps=((spot_ask - spot_bid) / spot_mid) * 10000,
            )
        )

    return snapshots
