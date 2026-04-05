from fastapi import APIRouter, Depends, Query

from app.console.read_service import ConsoleReadService, get_console_read_service
from app.schemas.console import ScanFilters, ScanOpportunitiesResponse


router = APIRouter(prefix="/api/v1/scan", tags=["scan"])


@router.get("/opportunities", response_model=ScanOpportunitiesResponse)
async def get_scan(
    limit: int = Query(default=25, ge=1, le=100),
    positive_funding_only: bool = Query(default=True),
    min_net_edge_bps: float | None = Query(default=None, ge=0),
    read_service: ConsoleReadService = Depends(get_console_read_service),
) -> ScanOpportunitiesResponse:
    filters = ScanFilters(
        limit=limit,
        positive_funding_only=positive_funding_only,
        min_net_edge_bps=min_net_edge_bps,
    )
    return await read_service.get_scan_opportunities(filters)
