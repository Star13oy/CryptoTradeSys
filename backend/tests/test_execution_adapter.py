import httpx

from app.execution import BinanceLiveExecutionAdapter, ExecutionIntentRequest


def _not_found_error(url: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", url)
    response = httpx.Response(404, request=request, json={"code": -2013, "msg": "Order does not exist."})
    return httpx.HTTPStatusError("not found", request=request, response=response)


def test_live_adapter_recovers_spot_order_after_transport_error_by_query() -> None:
    class StubTradingClient:
        def __init__(self) -> None:
            self.spot_place_calls = 0
            self.spot_query_calls = 0

        def place_spot_market_order(self, **kwargs):
            self.spot_place_calls += 1
            raise httpx.ConnectError("network reset")

        def get_spot_order(self, **kwargs):
            self.spot_query_calls += 1
            return {"symbol": "BTCUSDT", "status": "FILLED", "orderId": 101, "clientOrderId": kwargs["orig_client_order_id"]}

        def place_perp_market_order(self, **kwargs):
            return {"symbol": "BTCUSDT", "status": "FILLED", "orderId": 202}

        def get_perp_order(self, **kwargs):
            raise AssertionError("perp query should not be called")

    adapter = BinanceLiveExecutionAdapter(StubTradingClient())

    reports = adapter.open_hedge(
        ExecutionIntentRequest(
            trade_id="retry-open-1",
            mode="live",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            action="open_hedge",
            spot_notional=10000,
            perp_notional=9980,
            perp_quantity=0.2,
        )
    )

    assert reports[0].leg == "spot"
    assert reports[0].status == "filled"
    assert reports[0].payload["orderId"] == 101
    assert reports[1].leg == "perp"
    assert reports[1].status == "filled"


def test_live_adapter_retries_spot_order_once_when_query_confirms_not_found() -> None:
    class StubTradingClient:
        def __init__(self) -> None:
            self.spot_place_calls = 0
            self.spot_query_calls = 0

        def place_spot_market_order(self, **kwargs):
            self.spot_place_calls += 1
            if self.spot_place_calls == 1:
                raise httpx.ConnectError("temporary connection error")
            return {"symbol": "BTCUSDT", "status": "FILLED", "orderId": 303}

        def get_spot_order(self, **kwargs):
            self.spot_query_calls += 1
            raise _not_found_error("https://api.binance.com/api/v3/order")

        def place_perp_market_order(self, **kwargs):
            return {"symbol": "BTCUSDT", "status": "FILLED", "orderId": 404}

        def get_perp_order(self, **kwargs):
            raise AssertionError("perp query should not be called")

    client = StubTradingClient()
    adapter = BinanceLiveExecutionAdapter(client)

    reports = adapter.open_hedge(
        ExecutionIntentRequest(
            trade_id="retry-open-2",
            mode="live",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            action="open_hedge",
            spot_notional=10000,
            perp_notional=9980,
            perp_quantity=0.2,
        )
    )

    assert client.spot_place_calls == 2
    assert client.spot_query_calls == 1
    assert reports[0].status == "filled"
    assert reports[0].payload["orderId"] == 303


def test_live_adapter_recovers_perp_close_order_after_transport_error_by_query() -> None:
    class StubTradingClient:
        def place_spot_market_order(self, **kwargs):
            return {"symbol": "BTCUSDT", "status": "FILLED", "orderId": 505}

        def get_spot_order(self, **kwargs):
            raise AssertionError("spot query should not be called")

        def place_perp_market_order(self, **kwargs):
            raise httpx.ConnectError("timeout")

        def get_perp_order(self, **kwargs):
            return {"symbol": "BTCUSDT", "status": "FILLED", "orderId": 606, "clientOrderId": kwargs["orig_client_order_id"]}

    adapter = BinanceLiveExecutionAdapter(StubTradingClient())

    reports = adapter.close_hedge(
        ExecutionIntentRequest(
            trade_id="retry-close-1",
            mode="live",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            action="close_hedge",
            spot_quantity=0.2,
            perp_quantity=0.2,
        )
    )

    assert reports[0].status == "filled"
    assert reports[1].status == "filled"
    assert reports[1].payload["orderId"] == 606


def test_live_adapter_rebalances_perp_with_safe_retry() -> None:
    class StubTradingClient:
        def __init__(self) -> None:
            self.place_calls = 0
            self.query_calls = 0

        def place_perp_market_order(self, **kwargs):
            self.place_calls += 1
            raise httpx.ConnectError("timeout")

        def get_perp_order(self, **kwargs):
            self.query_calls += 1
            return {
                "symbol": "BTCUSDT",
                "status": "FILLED",
                "orderId": 707,
                "clientOrderId": kwargs["orig_client_order_id"],
            }

    adapter = BinanceLiveExecutionAdapter(StubTradingClient())

    report = adapter.rebalance_perp(
        trade_id="rebalance-1",
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.02,
        reduce_only=False,
    )

    assert report.leg == "perp"
    assert report.status == "filled"
    assert report.payload["orderId"] == 707
