from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.console.read_service import get_console_read_service
from app.main import app
from app.schemas.console import AccountHealthSummary, DashboardSummary, MarketDataStatus
from app.schemas.market import OpportunityScore


class StubConsoleReadService:
    async def get_dashboard_summary(self) -> DashboardSummary:
        return DashboardSummary(
            generated_at=datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc),
            account_health=AccountHealthSummary(mode="paper", exchange="binance", risk_state="normal"),
            market_status=MarketDataStatus(
                spot_source="bookTicker",
                perp_source="bookTicker",
                degraded=False,
                requested_symbols=12,
                quoted_symbols=12,
            ),
            top_opportunities=[
                OpportunityScore(
                    symbol="BTCUSDT",
                    funding_rate=0.0002,
                    net_edge_bps=0.7,
                    score=7,
                    risk_tag="normal",
                )
            ],
            paper_positions=[],
        )


def test_dashboard_summary_contains_ranked_opportunities() -> None:
    app.dependency_overrides[get_console_read_service] = lambda: StubConsoleReadService()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/dashboard/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_at"].startswith("2026-04-03T12:00:00")
    assert payload["market_status"]["spot_source"] == "bookTicker"
    assert len(payload["top_opportunities"]) >= 1
    assert payload["top_opportunities"][0]["symbol"] == "BTCUSDT"
