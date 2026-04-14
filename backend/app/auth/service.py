from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
import jwt

from app.core.settings import get_settings

from .schemas import UserResponse

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

class AuthService:
    def __init__(self, file_path: str | None = None) -> None:
        settings = get_settings()
        self._file_path = Path(file_path or settings.users_path)
        self._jwt_secret = settings.jwt_secret
        self._ensure_default_admin()

    def _read_users(self) -> list[dict]:
        if not self._file_path.exists():
            return []
        with open(self._file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_users(self, users: list[dict]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

    def _ensure_default_admin(self) -> None:
        users = self._read_users()
        if not any(u.get("username") == "admin" for u in users):
            hashed = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
            users.append({
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password_hash": hashed,
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            self._write_users(users)

    def register(self, username: str, password: str) -> UserResponse:
        users = self._read_users()
        if any(u.get("username") == username for u in users):
            raise ValueError(f"username '{username}' already exists")
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "password_hash": hashed,
            "role": "trader",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        users.append(user)
        self._write_users(users)
        return UserResponse(id=user["id"], username=user["username"], role=user["role"], created_at=user["created_at"])

    def login(self, username: str, password: str) -> tuple[str, UserResponse]:
        users = self._read_users()
        user = next((u for u in users if u.get("username") == username), None)
        if user is None or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise ValueError("invalid username or password")
        token = jwt.encode(
            {"sub": user["id"], "username": user["username"], "role": user["role"], "exp": datetime.now(timezone.utc).timestamp() + JWT_EXPIRATION_HOURS * 3600},
            self._jwt_secret,
            algorithm=JWT_ALGORITHM,
        )
        return token, UserResponse(id=user["id"], username=user["username"], role=user["role"], created_at=user["created_at"])

    def verify_token(self, token: str) -> UserResponse:
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise ValueError("token expired")
        except jwt.InvalidTokenError:
            raise ValueError("invalid token")
        user_id = payload.get("sub")
        users = self._read_users()
        user = next((u for u in users if u.get("id") == user_id), None)
        if user is None:
            raise ValueError("user not found")
        return UserResponse(id=user["id"], username=user["username"], role=user["role"], created_at=user["created_at"])

    def change_password(self, user_id: str, old_password: str, new_password: str) -> None:
        users = self._read_users()
        user = next((u for u in users if u.get("id") == user_id), None)
        if user is None:
            raise ValueError("user not found")
        if not bcrypt.checkpw(old_password.encode(), user["password_hash"].encode()):
            raise ValueError("old password is incorrect")
        user["password_hash"] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self._write_users(users)
