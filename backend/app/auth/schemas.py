from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str  # "admin" | "trader"
    created_at: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)
