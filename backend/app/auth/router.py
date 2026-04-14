from fastapi import APIRouter, Depends

from .schemas import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .service import AuthService
from .middleware import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Service singleton
_service: AuthService | None = None

def _get_service() -> AuthService:
    global _service
    if _service is None:
        _service = AuthService()
    return _service

@router.post("/register", response_model=UserResponse)
async def register(body: RegisterRequest):
    svc = _get_service()
    return svc.register(body.username, body.password)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    svc = _get_service()
    token, user = svc.login(body.username, body.password)
    return TokenResponse(access_token=token, username=user.username, role=user.role)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@router.put("/password")
async def change_password(body: ChangePasswordRequest, current_user: UserResponse = Depends(get_current_user)):
    svc = _get_service()
    svc.change_password(current_user.id, body.old_password, body.new_password)
    return {"detail": "password changed"}
