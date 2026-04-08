from __future__ import annotations

import httpx

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

        spot_client_order_id = f"{request.trade_id}-spot-open"
        perp_client_order_id = f"{request.trade_id}-perp-open"
        spot = self._submit_with_safe_retry(
            submit=lambda: self._trading_client.place_spot_market_order(
                symbol=request.symbol,
                side="BUY",
                quote_order_qty=request.spot_notional,
                new_client_order_id=spot_client_order_id,
            ),
            lookup=lambda: self._trading_client.get_spot_order(
                symbol=request.symbol,
                orig_client_order_id=spot_client_order_id,
            ),
        )
        perp = self._submit_with_safe_retry(
            submit=lambda: self._trading_client.place_perp_market_order(
                symbol=request.symbol,
                side="SELL",
                quantity=request.perp_quantity,
                reduce_only=False,
                new_client_order_id=perp_client_order_id,
            ),
            lookup=lambda: self._trading_client.get_perp_order(
                symbol=request.symbol,
                orig_client_order_id=perp_client_order_id,
            ),
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

        spot_client_order_id = f"{request.trade_id}-spot-close"
        perp_client_order_id = f"{request.trade_id}-perp-close"
        spot = self._submit_with_safe_retry(
            submit=lambda: self._trading_client.place_spot_market_order(
                symbol=request.symbol,
                side="SELL",
                quantity=request.spot_quantity,
                new_client_order_id=spot_client_order_id,
            ),
            lookup=lambda: self._trading_client.get_spot_order(
                symbol=request.symbol,
                orig_client_order_id=spot_client_order_id,
            ),
        )
        perp = self._submit_with_safe_retry(
            submit=lambda: self._trading_client.place_perp_market_order(
                symbol=request.symbol,
                side="BUY",
                quantity=request.perp_quantity,
                reduce_only=True,
                new_client_order_id=perp_client_order_id,
            ),
            lookup=lambda: self._trading_client.get_perp_order(
                symbol=request.symbol,
                orig_client_order_id=perp_client_order_id,
            ),
        )
        return [
            ExecutionLegReport(leg="spot", status=self._normalize_status(spot), payload=spot),
            ExecutionLegReport(leg="perp", status=self._normalize_status(perp), payload=perp),
        ]

    def rebalance_perp(
        self,
        *,
        trade_id: str,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool,
    ) -> ExecutionLegReport:
        if quantity <= 0:
            raise ValueError("live rebalance_hedge requires positive perp quantity")

        client_order_id = f"{trade_id}-perp-rebalance"
        perp = self._submit_with_safe_retry(
            submit=lambda: self._trading_client.place_perp_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                reduce_only=reduce_only,
                new_client_order_id=client_order_id,
            ),
            lookup=lambda: self._trading_client.get_perp_order(
                symbol=symbol,
                orig_client_order_id=client_order_id,
            ),
        )
        return ExecutionLegReport(leg="perp", status=self._normalize_status(perp), payload=perp)

    def _submit_with_safe_retry(
        self,
        *,
        submit,
        lookup,
    ) -> dict:
        try:
            return submit()
        except httpx.HTTPError as original_exc:
            try:
                return lookup()
            except httpx.HTTPStatusError as lookup_exc:
                if self._is_order_not_found(lookup_exc):
                    return submit()
                raise original_exc from lookup_exc
            except httpx.HTTPError as lookup_exc:
                raise original_exc from lookup_exc

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

    def _is_order_not_found(self, exc: httpx.HTTPStatusError) -> bool:
        response = exc.response
        if response.status_code == 404:
            return True
        try:
            payload = response.json()
        except ValueError:
            return False
        code = payload.get("code")
        return code in {-2013, "-2013"}
