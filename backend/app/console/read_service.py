import asyncio
from collections.abc import Callable
from datetime import datetime, timezone

from app.adaptation.service import AdaptationService
from app.core.settings import get_settings
from app.exchange.binance_public import BinancePublicClient
from app.market_data.service import build_market_snapshot
from app.schemas.console import (
    AccountHealthSummary,
    DashboardSummary,
    MarketDataStatus,
    ScanFilters,
    ScanOpportunitiesResponse,
)
from app.strategy import StrategyRegistry, build_default_registry


class ConsoleReadService:
    def __init__(
        self,
        client: BinancePublicClient | None = None,
        scan_limit: int | None = None,
        now_provider: Callable[[], datetime] | None = None,
        strategy_registry: StrategyRegistry | None = None,
        strategy_id: str | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client or BinancePublicClient()
        self._scan_limit = scan_limit or settings.scan_limit
        self._app_mode = settings.app_mode
        self._exchange_name = settings.exchange_name
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._strategy_registry = strategy_registry or build_default_registry()
        self._strategy_id = strategy_id

    async def get_dashboard_summary(self) -> DashboardSummary:
        opportunities = await self.get_scan_opportunities(ScanFilters(limit=min(5, self._scan_limit)))
        return DashboardSummary(
            generated_at=opportunities.generated_at,
            account_health=AccountHealthSummary(
                mode=self._app_mode,
                exchange=self._exchange_name,
                risk_state="normal",
            ),
            market_status=opportunities.market_status,
            top_opportunities=opportunities.rows,
            paper_positions=[],
        )

    async def get_scan_opportunities(self, filters: ScanFilters | None = None) -> ScanOpportunitiesResponse:
        effective_filters = self._normalize_filters(filters)
        funding_rows = await self._client.fetch_funding_rates()
        filtered_funding_rows = self._filter_funding_rows(funding_rows, effective_filters)
        spot_rows, spot_source = await self._fetch_spot_rows(filtered_funding_rows)
        perp_rows, perp_source = await self._fetch_perp_rows(filtered_funding_rows)

        snapshots = build_market_snapshot(filtered_funding_rows, perp_rows, spot_rows)
        strategy = self._resolve_strategy()
        scored_rows = strategy.score_snapshots(snapshots)
        if effective_filters.min_net_edge_bps is not None:
            scored_rows = [
                row for row in scored_rows if row.net_edge_bps >= effective_filters.min_net_edge_bps
            ]
        requested_symbols = len(filtered_funding_rows)
        if spot_source != "bookTicker" or perp_source != "bookTicker":
            requested_symbols = min(requested_symbols, self._scan_limit)

        return ScanOpportunitiesResponse(
            generated_at=self._now_provider(),
            applied_filters=effective_filters,
            market_status=MarketDataStatus(
                spot_source=spot_source,
                perp_source=perp_source,
                degraded=spot_source != "bookTicker" or perp_source != "bookTicker",
                requested_symbols=requested_symbols,
                quoted_symbols=len(snapshots),
            ),
            total_matches=len(scored_rows),
            rows=scored_rows[: effective_filters.limit],
        )

    def _normalize_filters(self, filters: ScanFilters | None) -> ScanFilters:
        requested = filters or ScanFilters(limit=self._scan_limit)
        return ScanFilters(
            limit=min(requested.limit, self._scan_limit),
            positive_funding_only=requested.positive_funding_only,
            min_net_edge_bps=requested.min_net_edge_bps,
        )

    def _filter_funding_rows(self, funding_rows: list[dict], filters: ScanFilters) -> list[dict]:
        if not filters.positive_funding_only:
            return funding_rows

        filtered_rows: list[dict] = []
        for row in funding_rows:
            funding_rate = row.get("fundingRate", row.get("lastFundingRate"))
            if funding_rate is None:
                continue
            if float(funding_rate) > 0:
                filtered_rows.append(row)
        return filtered_rows

    async def _fetch_perp_rows(self, funding_rows: list[dict]) -> tuple[list[dict], str]:
        try:
            return await self._client.fetch_perp_book_tickers(), "bookTicker"
        except Exception:
            symbols = [row["symbol"] for row in funding_rows[: self._scan_limit]]
            depth_snapshots = await asyncio.gather(
                *(self._client.fetch_perp_depth_snapshot(symbol) for symbol in symbols)
            )
            return (
                [
                    {
                        "symbol": symbol,
                        "bidPrice": depth["bids"][0][0],
                        "askPrice": depth["asks"][0][0],
                    }
                    for symbol, depth in zip(symbols, depth_snapshots, strict=False)
                    if depth.get("bids") and depth.get("asks")
                ],
                "depth",
            )

    def _resolve_strategy(self):
        if self._strategy_id:
            return self._strategy_registry.get(self._strategy_id)
        return self._strategy_registry.get_default()

    async def _fetch_spot_rows(self, funding_rows: list[dict]) -> tuple[list[dict], str]:
        try:
            return await self._client.fetch_spot_book_tickers(), "bookTicker"
        except Exception:
            symbols = [row["symbol"] for row in funding_rows[: self._scan_limit]]
            depth_snapshots = await asyncio.gather(
                *(self._client.fetch_spot_depth_snapshot(symbol) for symbol in symbols)
            )
            return (
                [
                    {
                        "symbol": symbol,
                        "bidPrice": depth["bids"][0][0],
                        "askPrice": depth["asks"][0][0],
                    }
                    for symbol, depth in zip(symbols, depth_snapshots, strict=False)
                    if depth.get("bids") and depth.get("asks")
                ],
                "depth",
            )


def get_console_read_service() -> ConsoleReadService:
    runtime = AdaptationService().build_runtime_components()
    return ConsoleReadService(strategy_registry=runtime.strategy_registry)
