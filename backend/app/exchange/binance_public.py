import httpx

from app.core.settings import get_settings


class BinancePublicClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.perp_base = settings.binance_perp_base_url
        self.spot_base = settings.binance_spot_base_url

    async def fetch_funding_rates(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.perp_base}/fapi/v1/premiumIndex")
            response.raise_for_status()
            return response.json()
