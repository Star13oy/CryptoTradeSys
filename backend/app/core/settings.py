from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FUNDING_ARB_", env_file=".env", extra="ignore")

    app_mode: str = "paper"
    exchange_name: str = "binance"
    binance_perp_base_url: str = "https://fapi.binance.com"
    binance_spot_base_url: str = "https://api.binance.com"
    binance_api_key: str = ""
    binance_api_secret: str = ""
    live_execution_enabled: bool = False
    live_symbol_allowlist: str = "BTCUSDT,ETHUSDT,SOLUSDT"
    max_live_notional: float = 25000
    scan_limit: int = 25
    tuning_state_path: str = "backend/runtime/tuning-state.json"
    learning_sample_path: str = "backend/runtime/learning-samples.json"
    trade_journal_path: str = "backend/runtime/trade-journal.json"
    backtest_dataset_path: str = "backend/runtime/backtest-datasets.json"
    trade_ledger_path: str = "backend/runtime/trade-ledger.json"
    audit_event_path: str = "backend/runtime/audit-events.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
