from fastapi import APIRouter

from app.market_data.service import build_market_snapshot
from app.opportunity.scorer import score_snapshot


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary() -> dict:
    snapshots = build_market_snapshot(
        [{"symbol": "BTCUSDT", "fundingRate": "0.0002"}],
        [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}],
        [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}],
    )
    scores = [score_snapshot(snapshot).model_dump() for snapshot in snapshots]
    return {
        "account_health": {"mode": "paper", "exchange": "binance", "risk_state": "normal"},
        "top_opportunities": scores,
        "paper_positions": [],
    }
