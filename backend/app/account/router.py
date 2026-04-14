from fastapi import APIRouter, Depends, Request

from app.exchange.binance_trading import BinanceTradingClient

from .schemas import AccountBalanceSnapshot, AccountSummary, PositionInfo
from .service import AccountService

router = APIRouter(prefix="/api/v1/account", tags=["account"])

def _get_account_service(request: Request) -> AccountService:
    svc = getattr(request.app.state, "account_service", None)
    if svc is None:
        trading_client = getattr(request.app.state, "binance_trading_client", None)
        if trading_client is None:
            try:
                trading_client = BinanceTradingClient()
                request.app.state.binance_trading_client = trading_client
            except Exception:
                pass
        svc = AccountService(trading_client=trading_client)
        request.app.state.account_service = svc
    return svc

@router.get("/balance", response_model=AccountBalanceSnapshot)
async def get_balance(service: AccountService = Depends(_get_account_service)):
    return service.get_balance()

@router.get("/positions", response_model=list[PositionInfo])
async def get_positions(symbol: str | None = None, service: AccountService = Depends(_get_account_service)):
    return service.get_positions(symbol)

@router.get("/summary", response_model=AccountSummary)
async def get_summary(service: AccountService = Depends(_get_account_service)):
    return service.get_summary()
