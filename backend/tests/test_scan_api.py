from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.console.read_service import get_console_read_service
from app.main import app
from app.schemas.console import MarketDataStatus, ScanFilters, ScanOpportunitiesResponse
from app.schemas.market import OpportunityScore


class StubConsoleReadService:
    def __init__(self) -> None:
        self.received_filters: ScanFilters | None = None

    async def get_scan_opportunities(self, filters: ScanFilters) -> ScanOpportunitiesResponse:
        self.received_filters = filters
        return ScanOpportunitiesResponse(
            generated_at=datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc),
            applied_filters=filters,
            market_status=MarketDataStatus(
                spot_source="bookTicker",
                perp_source="bookTicker",
                degraded=False,
                requested_symbols=12,
                quoted_symbols=12,
            ),
            total_matches=1,
            rows=[
                OpportunityScore(
                    symbol="ETHUSDT",
                    funding_rate=0.0004,
                    net_edge_bps=2.1,
                    score=21,
                    risk_tag="normal",
                )
            ]
        )


def test_scan_returns_ranked_rows_and_applies_query_filters() -> None:
    stub_service = StubConsoleReadService()
    app.dependency_overrides[get_console_read_service] = lambda: stub_service
    client = TestClient(app)

    try:
        response = client.get(
            "/api/v1/scan/opportunities",
            params={
                "limit": 10,
                "positive_funding_only": "false",
                "min_net_edge_bps": 1.0,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert stub_service.received_filters is not None
    assert stub_service.received_filters.limit == 10
    assert stub_service.received_filters.positive_funding_only is False
    assert stub_service.received_filters.min_net_edge_bps == 1.0
    assert payload["applied_filters"]["limit"] == 10
    assert payload["market_status"]["degraded"] is False
    assert payload["total_matches"] == 1
    assert payload["rows"][0]["symbol"] == "ETHUSDT"
