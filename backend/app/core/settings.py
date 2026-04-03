from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FUNDING_ARB_", env_file=".env", extra="ignore")

    app_mode: str = "paper"
    exchange_name: str = "binance"
    binance_perp_base_url: str = "https://fapi.binance.com"
    binance_spot_base_url: str = "https://api.binance.com"
    scan_limit: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()
