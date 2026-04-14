from __future__ import annotations
from datetime import datetime, timezone

from app.exchange.binance_trading import BinanceTradingClient

from .schemas import AccountBalanceSnapshot, AccountSummary, AssetBalance, PositionInfo

class AccountService:
    def __init__(self, trading_client: BinanceTradingClient | None = None) -> None:
        self._client = trading_client

    def get_balance(self) -> AccountBalanceSnapshot:
        if self._client is None:
            raise ValueError("trading client not configured")
        raw_balances = self._client.get_account_balance()
        usdt = next((b for b in raw_balances if b.get("asset") == "USDT"), None)
        now = datetime.now(timezone.utc)
        if usdt is None:
            return AccountBalanceSnapshot(
                assets=[AssetBalance(asset="USDT", balance=0.0, available=0.0)],
                fetched_at=now,
            )
        balance = float(usdt.get("balance", 0))
        available = float(usdt.get("availableBalance", 0))
        pnl = float(usdt.get("crossUnPnl", 0))
        in_positions = balance - available
        return AccountBalanceSnapshot(
            total_usdt_equity=balance,
            available_usdt=available,
            usdt_in_positions=abs(in_positions),
            unrealized_pnl=pnl,
            assets=[AssetBalance(asset="USDT", balance=balance, available=available, cross_unrealized_pnl=pnl)],
            fetched_at=now,
        )

    def get_positions(self, symbol: str | None = None) -> list[PositionInfo]:
        if self._client is None:
            raise ValueError("trading client not configured")
        raw = self._client.get_position_info(symbol)
        positions = []
        for p in raw:
            amt = float(p.get("positionAmt", 0))
            if abs(amt) < 1e-10:
                continue  # skip zero positions
            positions.append(PositionInfo(
                symbol=p.get("symbol", ""),
                position_side=p.get("positionSide", "BOTH"),
                position_amt=amt,
                unrealized_pnl=float(p.get("unRealizedProfit", 0)),
                liquidation_price=float(p["liquidationPrice"]) if p.get("liquidationPrice") else None,
                mark_price=float(p.get("markPrice", 0)),
                entry_price=float(p.get("entryPrice", 0)),
                leverage=int(p.get("leverage", 1)),
            ))
        return positions

    def get_summary(self) -> AccountSummary:
        now = datetime.now(timezone.utc)
        try:
            balance = self.get_balance()
        except Exception:
            balance = None
        try:
            positions = self.get_positions()
        except Exception:
            positions = []
        return AccountSummary(
            balance=balance,
            positions=positions,
            active_position_count=len(positions),
            fetched_at=now,
        )
