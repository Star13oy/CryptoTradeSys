import hashlib
import hmac
from urllib.parse import parse_qs

import httpx

from app.exchange.binance_trading import BinanceTradingClient


def test_binance_trading_client_signs_spot_order_requests() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        captured["api_key"] = request.headers["X-MBX-APIKEY"]
        return httpx.Response(200, json={"symbol": "BTCUSDT", "status": "FILLED", "orderId": 123})

    client = BinanceTradingClient(
        api_key="test-key",
        api_secret="test-secret",
        spot_base_url="https://api.binance.com",
        perp_base_url="https://fapi.binance.com",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        timestamp_provider=lambda: 1700000000000,
    )

    response = client.place_spot_market_order(
        symbol="BTCUSDT",
        side="BUY",
        quote_order_qty=100,
        recv_window=5000,
        new_client_order_id="spot-open-1",
    )

    assert response["status"] == "FILLED"
    assert captured["api_key"] == "test-key"
    body = parse_qs(captured["body"])
    assert body["symbol"] == ["BTCUSDT"]
    assert body["side"] == ["BUY"]
    assert body["type"] == ["MARKET"]
    assert body["quoteOrderQty"] == ["100"]
    assert body["recvWindow"] == ["5000"]
    assert body["newClientOrderId"] == ["spot-open-1"]
    assert body["timestamp"] == ["1700000000000"]
    expected_query = (
        "symbol=BTCUSDT&side=BUY&type=MARKET&quoteOrderQty=100&recvWindow=5000&newClientOrderId=spot-open-1&timestamp=1700000000000"
    )
    expected_signature = hmac.new(
        b"test-secret",
        expected_query.encode(),
        hashlib.sha256,
    ).hexdigest()
    assert body["signature"] == [expected_signature]


def test_binance_trading_client_signs_perp_order_requests() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        captured["api_key"] = request.headers["X-MBX-APIKEY"]
        return httpx.Response(200, json={"symbol": "BTCUSDT", "status": "PARTIALLY_FILLED", "orderId": 456})

    client = BinanceTradingClient(
        api_key="test-key",
        api_secret="test-secret",
        spot_base_url="https://api.binance.com",
        perp_base_url="https://fapi.binance.com",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        timestamp_provider=lambda: 1700000001000,
    )

    response = client.place_perp_market_order(
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.25,
        reduce_only=True,
        recv_window=7000,
        new_client_order_id="perp-close-1",
    )

    assert response["status"] == "PARTIALLY_FILLED"
    assert captured["api_key"] == "test-key"
    body = parse_qs(captured["body"])
    assert body["symbol"] == ["BTCUSDT"]
    assert body["side"] == ["SELL"]
    assert body["type"] == ["MARKET"]
    assert body["quantity"] == ["0.25"]
    assert body["reduceOnly"] == ["true"]
    assert body["recvWindow"] == ["7000"]
    assert body["newClientOrderId"] == ["perp-close-1"]
    assert body["timestamp"] == ["1700000001000"]
