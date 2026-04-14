from __future__ import annotations
import uuid
from datetime import datetime, timezone

from app.execution.schemas import ExecutionIntentRequest
from app.opportunity.scorer import score_snapshot, ScoreConfig
from app.risk.policy import OpportunityRiskPolicy
from app.schemas.market import MarketSnapshot

from .schemas import ManualOrderRequest, OrderPreview, OrderResult, SymbolInfo

class TradingService:
    def __init__(self) -> None:
        self._risk_policy = OpportunityRiskPolicy()

    def preview(
        self,
        request: ManualOrderRequest,
        snapshot: MarketSnapshot | None = None,
    ) -> OrderPreview:
        fees = request.notional * 0.0004 * 2  # 0.04% taker fee x 2 legs
        net_edge_bps = 0.0
        risk_decision = "allow"
        if snapshot is not None:
            score = score_snapshot(snapshot)
            try:
                decision = self._risk_policy.evaluate(score)
                risk_decision = decision.decision
            except Exception:
                pass
            net_edge_bps = score.net_edge_bps
            return OrderPreview(
                symbol=request.symbol,
                side=request.side,
                notional=request.notional,
                spot_price=snapshot.spot_mid,
                perp_price=snapshot.perp_mid,
                funding_rate=snapshot.funding_rate,
                estimated_fees_usd=fees,
                estimated_net_edge_bps=net_edge_bps,
                risk_decision=risk_decision,
            )
        return OrderPreview(
            symbol=request.symbol,
            side=request.side,
            notional=request.notional,
            estimated_fees_usd=fees,
        )

    def execute(self, request: ManualOrderRequest, *, orchestrator) -> OrderResult:
        trade_id = f"manual-{uuid.uuid4().hex[:8]}"
        spot_side = "BUY" if request.side == "long" else "SELL"
        perp_side = "SELL" if request.side == "long" else "BUY"
        now = datetime.now(timezone.utc).isoformat()

        req = ExecutionIntentRequest(
            trade_id=trade_id,
            mode=request.mode,
            strategy_id="manual-trade",
            symbol=request.symbol,
            action="open_hedge",
            spot_notional=request.notional,
            perp_notional=request.notional,
        )
        result = orchestrator.execute(req)

        return OrderResult(
            trade_id=trade_id,
            status=result.status,
            spot_filled=request.notional,
            perp_filled=request.notional,
            executed_at=now,
        )

    def get_symbols(self) -> list[SymbolInfo]:
        """Return common symbols for trading."""
        common = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"]
        return [SymbolInfo(symbol=s) for s in common]
