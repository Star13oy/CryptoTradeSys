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
        perp_mid = (float(perp["bidPrice"]) + float(perp["askPrice"])) / 2
        spot_mid = (float(spot["bidPrice"]) + float(spot["askPrice"])) / 2

        snapshots.append(
            MarketSnapshot(
                symbol=symbol,
                funding_rate=float(funding["fundingRate"]),
                perp_mid=perp_mid,
                spot_mid=spot_mid,
                perp_spread_bps=((float(perp["askPrice"]) - float(perp["bidPrice"])) / perp_mid) * 10000,
                spot_spread_bps=((float(spot["askPrice"]) - float(spot["bidPrice"])) / spot_mid) * 10000,
            )
        )

    return snapshots
