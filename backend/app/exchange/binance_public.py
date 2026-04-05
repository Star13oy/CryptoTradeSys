import httpx

from app.core.settings import get_settings


class BinancePublicClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.perp_base = settings.binance_perp_base_url
        self.spot_base = settings.binance_spot_base_url

    async def fetch_funding_rates(self) -> list[dict]:
        return await self._get_json(f"{self.perp_base}/fapi/v1/premiumIndex")

    async def fetch_perp_book_tickers(self) -> list[dict]:
        return await self._get_json(f"{self.perp_base}/fapi/v1/ticker/bookTicker")

    async def fetch_spot_book_tickers(self) -> list[dict]:
        return await self._get_json(f"{self.spot_base}/api/v3/ticker/bookTicker")

    async def fetch_perp_depth_snapshot(self, symbol: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.perp_base}/fapi/v1/depth", params={"symbol": symbol, "limit": 5})
            response.raise_for_status()
            return response.json()

    async def fetch_spot_depth_snapshot(self, symbol: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.spot_base}/api/v3/depth", params={"symbol": symbol, "limit": 5})
            response.raise_for_status()
            return response.json()

    async def _get_json(self, url: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
