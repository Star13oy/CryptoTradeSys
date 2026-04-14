from __future__ import annotations
from fastapi import APIRouter, Depends, Request

from app.auth.middleware import get_current_user
from app.auth.schemas import UserResponse
from app.market_data.service import build_market_snapshot
from app.schemas.market import MarketSnapshot

from .schemas import ManualOrderRequest, OrderPreview, OrderResult, SymbolInfo
from .service import TradingService

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])

_service: TradingService | None = None

def _get_service() -> TradingService:
    global _service
    if _service is None:
        _service = TradingService()
    return _service

def _get_snapshot_for_symbol(symbol: str) -> MarketSnapshot | None:
    """Try to get a snapshot for a symbol. Returns None if unavailable."""
    try:
        from app.exchange.binance_public import BinancePublicClient
        import asyncio
        async def _fetch():
            client = BinancePublicClient()
            funding = await client.fetch_funding_rates()
            perp = await client.fetch_perp_book_tickers()
            spot = await client.fetch_spot_book_tickers()
            return build_market_snapshot(funding, perp, spot)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None  # Can't fetch async in sync context during request
        snapshots = loop.run_until_complete(_fetch())
        return next((s for s in snapshots if s.symbol == symbol), None)
    except Exception:
        return None

@router.get("/symbols", response_model=list[SymbolInfo])
async def get_symbols():
    return _get_service().get_symbols()

@router.post("/preview", response_model=OrderPreview)
async def preview_order(body: ManualOrderRequest, current_user: UserResponse = Depends(get_current_user)):
    snapshot = _get_snapshot_for_symbol(body.symbol)
    return _get_service().preview(body, snapshot)

@router.post("/execute", response_model=OrderResult)
async def execute_order(body: ManualOrderRequest, request: Request, current_user: UserResponse = Depends(get_current_user)):
    orchestrator = getattr(request.app.state, "execution_orchestrator", None)
    if orchestrator is None:
        # Fallback: create a basic orchestrator
        from app.execution import ExecutionOrchestrator
        orchestrator = ExecutionOrchestrator()
    return _get_service().execute(body, orchestrator=orchestrator)
