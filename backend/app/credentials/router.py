from fastapi import APIRouter, Depends

from app.auth.middleware import get_current_user
from app.auth.schemas import UserResponse

from .schemas import ApiKeySet, ApiKeySummary
from .service import CredentialsService

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])

_service: CredentialsService | None = None

def _get_service() -> CredentialsService:
    global _service
    if _service is None:
        _service = CredentialsService()
    return _service

@router.get("", response_model=list[ApiKeySummary])
async def list_keys(current_user: UserResponse = Depends(get_current_user)):
    return _get_service().list_keys(current_user.id)

@router.post("", response_model=ApiKeySummary)
async def add_key(body: ApiKeySet, current_user: UserResponse = Depends(get_current_user)):
    return _get_service().add_key(current_user.id, body.label, body.exchange, body.api_key, body.api_secret)

@router.delete("/{key_id}")
async def delete_key(key_id: str, current_user: UserResponse = Depends(get_current_user)):
    _get_service().delete_key(current_user.id, key_id)
    return {"detail": "deleted"}

@router.post("/{key_id}/activate", response_model=ApiKeySummary)
async def activate_key(key_id: str, current_user: UserResponse = Depends(get_current_user)):
    svc = _get_service()
    svc.activate_key(current_user.id, key_id)
    summary = svc.get_active_key_summary(current_user.id)
    return summary

@router.get("/active", response_model=ApiKeySummary | None)
async def get_active(current_user: UserResponse = Depends(get_current_user)):
    return _get_service().get_active_key_summary(current_user.id)
