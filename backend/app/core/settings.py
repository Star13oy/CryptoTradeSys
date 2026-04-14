from functools import lru_cache
from typing import Literal

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
    live_circuit_breaker_enabled: bool = True
    live_circuit_breaker_failure_threshold: int = 2
    live_circuit_breaker_cooldown_seconds: float = 300.0
    reconciliation_worker_enabled: bool = False
    reconciliation_worker_interval_seconds: float = 30.0
    reconciliation_worker_limit: int = 5
    recovery_worker_enabled: bool = False
    recovery_worker_interval_seconds: float = 30.0
    recovery_worker_limit: int = 3
    compensation_worker_enabled: bool = False
    compensation_worker_interval_seconds: float = 30.0
    compensation_worker_limit: int = 3
    compensation_worker_exposure_limit_bps: float = 50.0
    hedge_rebalance_worker_enabled: bool = False
    hedge_rebalance_worker_interval_seconds: float = 30.0
    hedge_rebalance_worker_limit: int = 3
    hedge_rebalance_worker_exposure_limit_bps: float = 50.0
    holding_monitor_enabled: bool = False
    holding_monitor_interval_seconds: float = 60.0
    holding_monitor_max_hold_periods: float = 72.0
    scheduler_enabled: bool = False
    scheduler_interval_seconds: float = 60.0
    scheduler_max_open_positions: int = 3
    scheduler_max_total_notional: float = 25000.0
    scan_limit: int = 25
    storage_backend: Literal["json", "mysql"] = "json"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root"
    mysql_database: str = "crypto_funding_arb"
    mysql_charset: str = "utf8mb4"
    tuning_state_path: str = "backend/runtime/tuning-state.json"
    learning_sample_path: str = "backend/runtime/learning-samples.json"
    trade_journal_path: str = "backend/runtime/trade-journal.json"
    backtest_dataset_path: str = "backend/runtime/backtest-datasets.json"
    trade_ledger_path: str = "backend/runtime/trade-ledger.json"
    audit_event_path: str = "backend/runtime/audit-events.json"
    exchange_order_report_path: str = "backend/runtime/exchange-order-reports.json"
    execution_circuit_breaker_state_path: str = "backend/runtime/execution-circuit-breaker.json"
    users_path: str = "backend/runtime/users.json"
    credentials_path: str = "backend/runtime/credentials.json"
    jwt_secret: str = "change-me-in-production"
    encryption_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
