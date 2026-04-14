from __future__ import annotations
import base64
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import get_settings

from .schemas import ApiKeySummary

class CredentialsService:
    def __init__(self, file_path: str | None = None) -> None:
        settings = get_settings()
        self._file_path = Path(file_path or settings.credentials_path)
        self._key = settings.encryption_key or "default-encryption-key"

    def _xor_cipher(self, text: str) -> str:
        """Simple XOR cipher with key stretching via SHA256."""
        key_hash = hashlib.sha256(self._key.encode()).digest()
        text_bytes = text.encode()
        cipher_bytes = bytes(b ^ key_hash[i % len(key_hash)] for i, b in enumerate(text_bytes))
        return base64.b64encode(cipher_bytes).decode()

    def _xor_decipher(self, encoded: str) -> str:
        """Reverse XOR cipher."""
        key_hash = hashlib.sha256(self._key.encode()).digest()
        cipher_bytes = base64.b64decode(encoded)
        text_bytes = bytes(b ^ key_hash[i % len(key_hash)] for i, b in enumerate(cipher_bytes))
        return text_bytes.decode()

    def _read_all(self) -> dict[str, list[dict]]:
        if not self._file_path.exists():
            return {}
        with open(self._file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_all(self, data: dict[str, list[dict]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_user_keys(self, user_id: str) -> list[dict]:
        data = self._read_all()
        return data.get(user_id, [])

    def list_keys(self, user_id: str) -> list[ApiKeySummary]:
        keys = self._get_user_keys(user_id)
        result = []
        for k in keys:
            preview = k.get("api_key", "")[:4] + "****"
            result.append(ApiKeySummary(
                id=k["id"], label=k["label"], exchange=k["exchange"],
                api_key_preview=preview, created_at=k["created_at"],
                is_active=k.get("is_active", False),
            ))
        return result

    def add_key(self, user_id: str, label: str, exchange: str, api_key: str, api_secret: str) -> ApiKeySummary:
        data = self._read_all()
        if user_id not in data:
            data[user_id] = []
        entry = {
            "id": str(uuid.uuid4()),
            "label": label,
            "exchange": exchange,
            "api_key": api_key,
            "api_secret_enc": self._xor_cipher(api_secret),
            "is_active": len(data[user_id]) == 0,  # First key is auto-active
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data[user_id].append(entry)
        self._write_all(data)
        return ApiKeySummary(
            id=entry["id"], label=entry["label"], exchange=entry["exchange"],
            api_key_preview=api_key[:4] + "****", created_at=entry["created_at"],
            is_active=entry["is_active"],
        )

    def delete_key(self, user_id: str, key_id: str) -> None:
        data = self._read_all()
        if user_id not in data:
            raise ValueError("key not found")
        data[user_id] = [k for k in data[user_id] if k["id"] != key_id]
        self._write_all(data)

    def activate_key(self, user_id: str, key_id: str) -> None:
        data = self._read_all()
        if user_id not in data:
            raise ValueError("key not found")
        for k in data[user_id]:
            k["is_active"] = k["id"] == key_id
        self._write_all(data)

    def get_active_credentials(self, user_id: str) -> tuple[str, str] | None:
        """Returns (api_key, api_secret) for the active key, or None."""
        keys = self._get_user_keys(user_id)
        active = next((k for k in keys if k.get("is_active")), None)
        if active is None:
            return None
        api_secret = self._xor_decipher(active["api_secret_enc"])
        return (active["api_key"], api_secret)

    def get_active_key_summary(self, user_id: str) -> ApiKeySummary | None:
        keys = self._get_user_keys(user_id)
        active = next((k for k in keys if k.get("is_active")), None)
        if active is None:
            return None
        return ApiKeySummary(
            id=active["id"], label=active["label"], exchange=active["exchange"],
            api_key_preview=active["api_key"][:4] + "****",
            created_at=active["created_at"], is_active=True,
        )
