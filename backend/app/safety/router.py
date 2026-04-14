from fastapi import APIRouter, Depends, Request
from .schemas import SafetyStateSnapshot, EmergencyCloseResult, SafetyActionRequest
from .service import SafetyService

router = APIRouter(prefix="/api/v1/safety", tags=["safety"])

def _get_safety_service(request: Request) -> SafetyService:
    svc = getattr(request.app.state, "safety_service", None)
    if svc is None:
        svc = SafetyService()
        request.app.state.safety_service = svc
    return svc

@router.get("/state", response_model=SafetyStateSnapshot)
async def get_safety_state(safety: SafetyService = Depends(_get_safety_service)):
    return safety.get_state()

@router.post("/freeze", response_model=SafetyStateSnapshot)
async def freeze_all(body: SafetyActionRequest = SafetyActionRequest(), safety: SafetyService = Depends(_get_safety_service)):
    return safety.freeze_all(reason=body.reason)

@router.post("/unfreeze", response_model=SafetyStateSnapshot)
async def unfreeze_all(body: SafetyActionRequest = SafetyActionRequest(), safety: SafetyService = Depends(_get_safety_service)):
    return safety.unfreeze_all(reason=body.reason)

@router.post("/stop-new-positions", response_model=SafetyStateSnapshot)
async def stop_new_positions(body: SafetyActionRequest = SafetyActionRequest(), safety: SafetyService = Depends(_get_safety_service)):
    return safety.stop_new_positions(reason=body.reason)

@router.post("/resume-new-positions", response_model=SafetyStateSnapshot)
async def resume_new_positions(body: SafetyActionRequest = SafetyActionRequest(), safety: SafetyService = Depends(_get_safety_service)):
    return safety.resume_new_positions(reason=body.reason)

@router.post("/reduce-only", response_model=SafetyStateSnapshot)
async def set_reduce_only(body: SafetyActionRequest, safety: SafetyService = Depends(_get_safety_service)):
    if not body.trade_id:
        raise ValueError("trade_id is required")
    return safety.set_reduce_only(body.trade_id, reason=body.reason)

@router.post("/reduce-only/clear", response_model=SafetyStateSnapshot)
async def unset_reduce_only(body: SafetyActionRequest, safety: SafetyService = Depends(_get_safety_service)):
    if not body.trade_id:
        raise ValueError("trade_id is required")
    return safety.unset_reduce_only(body.trade_id, reason=body.reason)

@router.post("/pause", response_model=SafetyStateSnapshot)
async def pause_trade(body: SafetyActionRequest, safety: SafetyService = Depends(_get_safety_service)):
    if not body.trade_id:
        raise ValueError("trade_id is required")
    return safety.pause_trade(body.trade_id, reason=body.reason)

@router.post("/unpause", response_model=SafetyStateSnapshot)
async def unpause_trade(body: SafetyActionRequest, safety: SafetyService = Depends(_get_safety_service)):
    if not body.trade_id:
        raise ValueError("trade_id is required")
    return safety.unpause_trade(body.trade_id, reason=body.reason)

@router.post("/emergency-close-all", response_model=EmergencyCloseResult)
async def emergency_close_all(request: Request, safety: SafetyService = Depends(_get_safety_service)):
    from app.ledger import TradeLedgerService
    from app.execution import ExecutionOrchestrator
    orchestrator = getattr(request.app.state, "execution_orchestrator", None)
    if orchestrator is None:
        raise ValueError("execution orchestrator not available")
    ledger = TradeLedgerService()
    return safety.emergency_close_all(orchestrator=orchestrator, ledger_service=ledger)

@router.post("/panic-sell", response_model=EmergencyCloseResult)
async def panic_sell(body: SafetyActionRequest, request: Request, safety: SafetyService = Depends(_get_safety_service)):
    if not body.trade_id:
        raise ValueError("trade_id is required")
    from app.ledger import TradeLedgerService
    orchestrator = getattr(request.app.state, "execution_orchestrator", None)
    if orchestrator is None:
        raise ValueError("execution orchestrator not available")
    ledger = TradeLedgerService()
    return safety.panic_sell(body.trade_id, orchestrator=orchestrator, ledger_service=ledger)
