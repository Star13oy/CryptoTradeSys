from __future__ import annotations

from app.exchange.binance_trading import BinanceTradingClient

from .schemas import ExecutionIntentRequest, ExecutionLegReport


class BinanceLiveExecutionAdapter:
    def __init__(self, trading_client: BinanceTradingClient | None = None) -> None:
        self._trading_client = trading_client or BinanceTradingClient()

    def open_hedge(self, request: ExecutionIntentRequest) -> list[ExecutionLegReport]:
        if request.perp_quantity is None or request.perp_quantity <= 0:
            raise ValueError("live open_hedge requires perp_quantity")
        if request.spot_notional <= 0:
            raise ValueError("live open_hedge requires spot_notional")

        spot = self._trading_client.place_spot_market_order(
            symbol=request.symbol,
            side="BUY",
            quote_order_qty=request.spot_notional,
            new_client_order_id=f"{request.trade_id}-spot-open",
        )
        perp = self._trading_client.place_perp_market_order(
            symbol=request.symbol,
            side="SELL",
            quantity=request.perp_quantity,
            reduce_only=False,
            new_client_order_id=f"{request.trade_id}-perp-open",
        )
        return [
            ExecutionLegReport(leg="spot", status=self._normalize_status(spot), payload=spot),
            ExecutionLegReport(leg="perp", status=self._normalize_status(perp), payload=perp),
        ]

    def close_hedge(self, request: ExecutionIntentRequest, existing=None) -> list[ExecutionLegReport]:
        if request.spot_quantity is None or request.spot_quantity <= 0:
            raise ValueError("live close_hedge requires spot_quantity")
        if request.perp_quantity is None or request.perp_quantity <= 0:
            raise ValueError("live close_hedge requires perp_quantity")

        spot = self._trading_client.place_spot_market_order(
            symbol=request.symbol,
            side="SELL",
            quantity=request.spot_quantity,
            new_client_order_id=f"{request.trade_id}-spot-close",
        )
        perp = self._trading_client.place_perp_market_order(
            symbol=request.symbol,
            side="BUY",
            quantity=request.perp_quantity,
            reduce_only=True,
            new_client_order_id=f"{request.trade_id}-perp-close",
        )
        return [
            ExecutionLegReport(leg="spot", status=self._normalize_status(spot), payload=spot),
            ExecutionLegReport(leg="perp", status=self._normalize_status(perp), payload=perp),
        ]

    def _normalize_status(self, payload: dict) -> str:
        status = str(payload.get("status", "submitted")).lower()
        if status == "filled":
            return "filled"
        if status == "partially_filled":
            return "partial"
        if status in {"new"}:
            return "submitted"
        if status in {"rejected", "expired", "canceled"}:
            return "failed"
        return "submitted"
