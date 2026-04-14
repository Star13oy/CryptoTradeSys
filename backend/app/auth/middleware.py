from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .service import AuthService
from .schemas import UserResponse

security = HTTPBearer()

_auth_service: AuthService | None = None

def set_auth_service(service: AuthService) -> None:
    global _auth_service
    _auth_service = service

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    if _auth_service is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="auth service not initialized")
    try:
        return _auth_service.verify_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
