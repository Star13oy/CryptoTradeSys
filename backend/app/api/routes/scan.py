from fastapi import APIRouter

from app.market_data.service import build_market_snapshot
from app.opportunity.scorer import score_snapshot


router = APIRouter(prefix="/api/v1/scan", tags=["scan"])


@router.get("/opportunities")
async def get_scan() -> dict:
    snapshots = build_market_snapshot(
        [{"symbol": "BTCUSDT", "fundingRate": "0.0002"}],
        [{"symbol": "BTCUSDT", "bidPrice": "60000", "askPrice": "60001"}],
        [{"symbol": "BTCUSDT", "bidPrice": "59995", "askPrice": "59996"}],
    )
    return {"rows": [score_snapshot(snapshot).model_dump() for snapshot in snapshots]}
