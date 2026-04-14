from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel

class ApiKeySet(BaseModel):
    label: str
    exchange: str = "binance"
    api_key: str
    api_secret: str

class ApiKeySummary(BaseModel):
    id: str
    label: str
    exchange: str
    api_key_preview: str
    created_at: str
    is_active: bool
