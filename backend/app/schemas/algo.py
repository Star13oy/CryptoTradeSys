from pydantic import BaseModel, Field

from app.backtest import BacktestConfig, BacktestDatasetSummary, BacktestPeriod


class BacktestRunRequest(BaseModel):
    periods: list[BacktestPeriod] = Field(default_factory=list)
    config: BacktestConfig = Field(default_factory=BacktestConfig)


class BacktestDatasetListResponse(BaseModel):
    datasets: list[BacktestDatasetSummary] = Field(default_factory=list)


class BacktestDatasetImportResponse(BaseModel):
    dataset: BacktestDatasetSummary


class BacktestRunFromDatasetRequest(BaseModel):
    dataset_id: str
    config: BacktestConfig = Field(default_factory=BacktestConfig)
    limit_recent_periods: int | None = Field(default=None, ge=1)
