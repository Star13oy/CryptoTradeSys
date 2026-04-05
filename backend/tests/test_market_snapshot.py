from app.market_data.service import build_market_snapshot


def test_build_market_snapshot_merges_rows() -> None:
    funding_rows = [{"symbol": "BTCUSDT", "fundingRate": "0.0002"}]
    perp_rows = [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}]
    spot_rows = [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}]

    snapshots = build_market_snapshot(funding_rows, perp_rows, spot_rows)

    assert len(snapshots) == 1
    assert snapshots[0].symbol == "BTCUSDT"
    assert snapshots[0].funding_rate == 0.0002


def test_build_market_snapshot_accepts_last_funding_rate_field() -> None:
    funding_rows = [{"symbol": "BTCUSDT", "lastFundingRate": "0.0003"}]
    perp_rows = [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}]
    spot_rows = [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}]

    snapshots = build_market_snapshot(funding_rows, perp_rows, spot_rows)

    assert len(snapshots) == 1
    assert snapshots[0].funding_rate == 0.0003


def test_build_market_snapshot_skips_zero_price_rows() -> None:
    funding_rows = [{"symbol": "BTCUSDT", "lastFundingRate": "0.0003"}]
    perp_rows = [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}]
    spot_rows = [{"symbol": "BTCUSDT", "bidPrice": "0.00000000", "askPrice": "0.00000000"}]

    snapshots = build_market_snapshot(funding_rows, perp_rows, spot_rows)

    assert snapshots == []
