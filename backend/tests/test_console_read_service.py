import asyncio
from datetime import datetime, timezone

from app.console.read_service import ConsoleReadService
from app.schemas.console import ScanFilters


class StubBinancePublicClient:
    async def fetch_funding_rates(self) -> list[dict]:
        return [
            {"symbol": "BTCUSDT", "fundingRate": "0.0002"},
            {"symbol": "ETHUSDT", "fundingRate": "0.0004"},
            {"symbol": "XRPUSDT", "fundingRate": "0.0001"},
        ]

    async def fetch_perp_book_tickers(self) -> list[dict]:
        return [
            {"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60002"},
            {"symbol": "ETHUSDT", "bidPrice": "3200", "askPrice": "3200.1"},
            {"symbol": "XRPUSDT", "bidPrice": "0.55", "askPrice": "0.552"},
        ]

    async def fetch_spot_book_tickers(self) -> list[dict]:
        return [
            {"symbol": "BTCUSDT", "bidPrice": "59998", "askPrice": "60000"},
            {"symbol": "ETHUSDT", "bidPrice": "3199.95", "askPrice": "3200"},
            {"symbol": "XRPUSDT", "bidPrice": "0.549", "askPrice": "0.553"},
        ]


class FallbackBinancePublicClient(StubBinancePublicClient):
    async def fetch_perp_book_tickers(self) -> list[dict]:
        raise RuntimeError("bookTicker unavailable")

    async def fetch_spot_book_tickers(self) -> list[dict]:
        raise RuntimeError("spot bookTicker unavailable")

    async def fetch_perp_depth_snapshot(self, symbol: str) -> dict:
        depth_map = {
            "BTCUSDT": {"bids": [["60000", "1.0"]], "asks": [["60002", "1.0"]]},
            "ETHUSDT": {"bids": [["3200", "1.0"]], "asks": [["3200.1", "1.0"]]},
            "XRPUSDT": {"bids": [["0.55", "1.0"]], "asks": [["0.552", "1.0"]]},
        }
        return depth_map[symbol]

    async def fetch_spot_depth_snapshot(self, symbol: str) -> dict:
        depth_map = {
            "BTCUSDT": {"bids": [["59998", "1.0"]], "asks": [["60000", "1.0"]]},
            "ETHUSDT": {"bids": [["3199.95", "1.0"]], "asks": [["3200", "1.0"]]},
            "XRPUSDT": {"bids": [["0.549", "1.0"]], "asks": [["0.553", "1.0"]]},
        }
        return depth_map[symbol]


class PartialCoverageBinancePublicClient(StubBinancePublicClient):
    async def fetch_funding_rates(self) -> list[dict]:
        return [
            {"symbol": "BTCUSDT", "fundingRate": "0.0002"},
            {"symbol": "ALTUSDT", "fundingRate": "0.0004"},
        ]

    async def fetch_perp_book_tickers(self) -> list[dict]:
        return [
            {"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60002"},
            {"symbol": "ALTUSDT", "bidPrice": "10", "askPrice": "10.01"},
        ]

    async def fetch_spot_book_tickers(self) -> list[dict]:
        return [
            {"symbol": "BTCUSDT", "bidPrice": "59998", "askPrice": "60000"},
        ]


def test_console_read_service_ranks_realistic_opportunities() -> None:
    service = ConsoleReadService(client=StubBinancePublicClient(), scan_limit=2)

    summary = asyncio.run(service.get_dashboard_summary())

    assert summary.account_health.exchange == "binance"
    assert len(summary.top_opportunities) == 2
    assert summary.top_opportunities[0].symbol == "ETHUSDT"
    assert summary.top_opportunities[0].score >= summary.top_opportunities[1].score


def test_console_read_service_falls_back_to_depth_when_bookticker_fails() -> None:
    service = ConsoleReadService(client=FallbackBinancePublicClient(), scan_limit=2)

    summary = asyncio.run(service.get_dashboard_summary())

    assert summary.market_status.degraded is True
    assert summary.market_status.spot_source == "depth"
    assert summary.market_status.perp_source == "depth"
    assert summary.market_status.requested_symbols == 2
    assert summary.market_status.quoted_symbols == 2
    assert len(summary.top_opportunities) == 2
    assert summary.top_opportunities[0].symbol == "ETHUSDT"


def test_console_read_service_applies_filters_and_metadata() -> None:
    fixed_now = datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc)
    service = ConsoleReadService(
        client=StubBinancePublicClient(),
        scan_limit=5,
        now_provider=lambda: fixed_now,
    )

    scan = asyncio.run(
        service.get_scan_opportunities(
            ScanFilters(limit=1, positive_funding_only=True, min_net_edge_bps=1.0)
        )
    )

    assert scan.generated_at == fixed_now
    assert scan.applied_filters.limit == 1
    assert scan.applied_filters.positive_funding_only is True
    assert scan.applied_filters.min_net_edge_bps == 1.0
    assert scan.total_matches == 1
    assert scan.market_status.degraded is False
    assert scan.market_status.spot_source == "bookTicker"
    assert scan.market_status.perp_source == "bookTicker"
    assert scan.market_status.requested_symbols == 3
    assert scan.market_status.quoted_symbols == 3
    assert [row.symbol for row in scan.rows] == ["ETHUSDT"]


def test_console_read_service_tracks_partial_coverage_without_marking_primary_reads_degraded() -> None:
    service = ConsoleReadService(client=PartialCoverageBinancePublicClient(), scan_limit=5)

    scan = asyncio.run(service.get_scan_opportunities())

    assert scan.market_status.degraded is False
    assert scan.market_status.spot_source == "bookTicker"
    assert scan.market_status.perp_source == "bookTicker"
    assert scan.market_status.requested_symbols == 2
    assert scan.market_status.quoted_symbols == 1
