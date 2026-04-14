from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from urllib.parse import urlencode

import httpx

from app.core.settings import get_settings


class BinanceTradingClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        spot_base_url: str | None = None,
        perp_base_url: str | None = None,
        client: httpx.Client | None = None,
        timestamp_provider: Callable[[], int] | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.binance_api_key
        self._api_secret = api_secret or settings.binance_api_secret
        self._spot_base_url = spot_base_url or settings.binance_spot_base_url
        self._perp_base_url = perp_base_url or settings.binance_perp_base_url
        self._client = client or httpx.Client(timeout=10)
        self._timestamp_provider = timestamp_provider or (lambda: int(time.time() * 1000))

    def place_spot_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quote_order_qty: float | None = None,
        quantity: float | None = None,
        recv_window: int | None = None,
        new_client_order_id: str | None = None,
    ) -> dict:
        payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
        }
        if quote_order_qty is not None:
            payload["quoteOrderQty"] = self._stringify(quote_order_qty)
        if quantity is not None:
            payload["quantity"] = self._stringify(quantity)
        if recv_window is not None:
            payload["recvWindow"] = str(recv_window)
        if new_client_order_id is not None:
            payload["newClientOrderId"] = new_client_order_id
        return self._signed_post(f"{self._spot_base_url}/api/v3/order", payload)

    def place_perp_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool = False,
        recv_window: int | None = None,
        new_client_order_id: str | None = None,
    ) -> dict:
        payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": self._stringify(quantity),
            "reduceOnly": "true" if reduce_only else "false",
        }
        if recv_window is not None:
            payload["recvWindow"] = str(recv_window)
        if new_client_order_id is not None:
            payload["newClientOrderId"] = new_client_order_id
        return self._signed_post(f"{self._perp_base_url}/fapi/v1/order", payload)

    def get_spot_order(
        self,
        *,
        symbol: str,
        order_id: str | None = None,
        orig_client_order_id: str | None = None,
        recv_window: int | None = None,
    ) -> dict:
        payload = {"symbol": symbol}
        if order_id is not None:
            payload["orderId"] = str(order_id)
        if orig_client_order_id is not None:
            payload["origClientOrderId"] = orig_client_order_id
        if recv_window is not None:
            payload["recvWindow"] = str(recv_window)
        return self._signed_get(f"{self._spot_base_url}/api/v3/order", payload)

    def get_perp_order(
        self,
        *,
        symbol: str,
        order_id: str | None = None,
        orig_client_order_id: str | None = None,
        recv_window: int | None = None,
    ) -> dict:
        payload = {"symbol": symbol}
        if order_id is not None:
            payload["orderId"] = str(order_id)
        if orig_client_order_id is not None:
            payload["origClientOrderId"] = orig_client_order_id
        if recv_window is not None:
            payload["recvWindow"] = str(recv_window)
        return self._signed_get(f"{self._perp_base_url}/fapi/v1/order", payload)

    def get_account_balance(self, *, recv_window: int | None = None) -> list[dict]:
        """GET /fapi/v3/balance — returns futures account balances."""
        payload: dict[str, str] = {}
        if recv_window is not None:
            payload["recvWindow"] = str(recv_window)
        return self._signed_get(f"{self._perp_base_url}/fapi/v3/balance", payload)

    def get_position_info(self, symbol: str | None = None, *, recv_window: int | None = None) -> list[dict]:
        """GET /fapi/v2/positionRisk — returns position risk information."""
        payload: dict[str, str] = {}
        if symbol is not None:
            payload["symbol"] = symbol
        if recv_window is not None:
            payload["recvWindow"] = str(recv_window)
        return self._signed_get(f"{self._perp_base_url}/fapi/v2/positionRisk", payload)

    def _signed_post(self, url: str, payload: dict[str, str]) -> dict:
        if not self._api_key or not self._api_secret:
            raise ValueError("binance api credentials are not configured")
        request_payload = {
            **payload,
            "timestamp": str(self._timestamp_provider()),
        }
        query = urlencode(request_payload)
        signature = hmac.new(self._api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        body = urlencode({**request_payload, "signature": signature})
        response = self._client.post(
            url,
            content=body,
            headers={
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        return response.json()

    def _signed_get(self, url: str, payload: dict[str, str]) -> dict:
        if not self._api_key or not self._api_secret:
            raise ValueError("binance api credentials are not configured")
        request_payload = {
            **payload,
            "timestamp": str(self._timestamp_provider()),
        }
        query = urlencode(request_payload)
        signature = hmac.new(self._api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        response = self._client.get(
            url,
            params={**request_payload, "signature": signature},
            headers={
                "X-MBX-APIKEY": self._api_key,
            },
        )
        response.raise_for_status()
        return response.json()

    def _stringify(self, value: float) -> str:
        return f"{value:g}"
