from fastapi import APIRouter, Depends

from app.console.read_service import ConsoleReadService, get_console_read_service
from app.schemas.console import DashboardSummary


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    read_service: ConsoleReadService = Depends(get_console_read_service),
) -> DashboardSummary:
    return await read_service.get_dashboard_summary()
