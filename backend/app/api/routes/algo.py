from fastapi import APIRouter, Depends, HTTPException

from app.adaptation.service import AdaptationService
from app.audit import (
    AuditEventImportRequest,
    AuditEventImportResponse,
    AuditEventListResponse,
    AuditEventService,
    AuditEventStore,
)
from app.execution import (
    BinanceLiveExecutionAdapter,
    ExecutionConsoleSnapshot,
    ExecutionIntentRequest,
    ExecutionRecoveryRequest,
    ExecutionReadService,
    ExecutionOrchestrator,
    ExecutionResult,
)
from app.backtest import (
    BacktestDataset,
    BacktestDatasetService,
    BacktestDatasetStore,
    BacktestEngine,
    BacktestResult,
)
from app.exchange.binance_trading import BinanceTradingClient
from app.core.settings import get_settings
from app.hedge import HedgeManagerService, HedgeOverview, HedgeRebalancePlan
from app.journal import TradeJournalService
from app.journal.schemas import (
    TradeJournalImportRequest,
    TradeJournalImportResponse,
    TradeJournalListResponse,
)
from app.journal.store import TradeJournalStore
from app.ledger import (
    TradeLedgerImportRequest,
    TradeLedgerImportResponse,
    TradeLedgerListResponse,
    TradeLedgerService,
    TradeLedgerStore,
)
from app.persistence.migration import JsonToMySQLBackfillService
from app.persistence.migration_schemas import PersistenceBackfillSummary
from app.risk import OpportunityRiskPolicy, RiskDecision
from app.reconciliation import (
    ReconciliationCandidateListResponse,
    ExchangeOrderReportImportRequest,
    ExchangeOrderReportImportResponse,
    ExchangeOrderReportListResponse,
    ReconciliationService,
    ReconciliationSummary,
)
from app.schemas.adaptation import (
    AdaptationPackageEvaluationRequest,
    AdaptationPackageEvaluationResponse,
    AdaptationRecommendationRequest,
    AdaptationRecommendationResponse,
    JournalSampleExtractionRequest,
    LearningSampleImportRequest,
    LearningSampleImportResponse,
    LearningSampleListResponse,
    TuningApplyRequest,
    TuningState,
)
from app.schemas.algo import BacktestRunRequest
from app.schemas.algo import (
    BacktestDatasetImportResponse,
    BacktestDatasetListResponse,
    BacktestRunFromDatasetRequest,
)
from app.schemas.market import OpportunityScore


router = APIRouter(prefix="/api/v1/algo", tags=["algo"])


def get_adaptation_service() -> AdaptationService:
    return AdaptationService()


def get_trade_journal_service() -> TradeJournalService:
    settings = get_settings()
    return TradeJournalService(TradeJournalStore(settings.trade_journal_path))


def get_backtest_dataset_service() -> BacktestDatasetService:
    settings = get_settings()
    return BacktestDatasetService(BacktestDatasetStore(settings.backtest_dataset_path))


def get_trade_ledger_service() -> TradeLedgerService:
    settings = get_settings()
    return TradeLedgerService(TradeLedgerStore(settings.trade_ledger_path))


def get_audit_event_service() -> AuditEventService:
    settings = get_settings()
    return AuditEventService(AuditEventStore(settings.audit_event_path))


def get_execution_orchestrator(
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> ExecutionOrchestrator:
    settings = get_settings()
    live_adapter = None
    if settings.binance_api_key and settings.binance_api_secret:
        live_adapter = BinanceLiveExecutionAdapter(BinanceTradingClient())
    allowlist = {
        symbol.strip().upper()
        for symbol in settings.live_symbol_allowlist.split(",")
        if symbol.strip()
    }
    return ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=live_adapter,
        live_execution_enabled=settings.live_execution_enabled,
        live_symbol_allowlist=allowlist,
        max_live_notional=settings.max_live_notional,
    )


def get_execution_read_service(
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> ExecutionReadService:
    return ExecutionReadService(ledger_service, audit_service)


def get_hedge_manager_service(
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> HedgeManagerService:
    return HedgeManagerService(ledger_service, audit_service)


def get_reconciliation_service(
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> ReconciliationService:
    settings = get_settings()
    from app.reconciliation import ExchangeOrderReportStore

    return ReconciliationService(
        ExchangeOrderReportStore(settings.exchange_order_report_path),
        ledger_service,
        audit_service,
    )


def get_persistence_backfill_service() -> JsonToMySQLBackfillService:
    return JsonToMySQLBackfillService()


@router.post("/risk/evaluate", response_model=RiskDecision)
async def evaluate_risk(
    opportunity: OpportunityScore,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> RiskDecision:
    return adaptation_service.build_runtime_components().risk_policy.evaluate(opportunity)


@router.post("/backtest/run", response_model=BacktestResult)
async def run_backtest(
    request: BacktestRunRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> BacktestResult:
    runtime = adaptation_service.build_runtime_components()
    effective_config = runtime.backtest_config.model_copy(update=request.config.model_dump(exclude_unset=True))
    return BacktestEngine(
        strategy_registry=runtime.strategy_registry,
        risk_policy=runtime.risk_policy,
    ).run(request.periods, effective_config)


@router.get("/backtest/datasets", response_model=BacktestDatasetListResponse)
async def list_backtest_datasets(
    dataset_service: BacktestDatasetService = Depends(get_backtest_dataset_service),
) -> BacktestDatasetListResponse:
    return BacktestDatasetListResponse(datasets=dataset_service.list_summaries())


@router.post("/backtest/datasets/import", response_model=BacktestDatasetImportResponse)
async def import_backtest_dataset(
    request: BacktestDataset,
    dataset_service: BacktestDatasetService = Depends(get_backtest_dataset_service),
) -> BacktestDatasetImportResponse:
    return BacktestDatasetImportResponse(dataset=dataset_service.import_dataset(request))


@router.post("/backtest/run-from-dataset", response_model=BacktestResult)
async def run_backtest_from_dataset(
    request: BacktestRunFromDatasetRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
    dataset_service: BacktestDatasetService = Depends(get_backtest_dataset_service),
) -> BacktestResult:
    periods = dataset_service.get_periods(
        request.dataset_id,
        limit_recent_periods=request.limit_recent_periods,
    )
    if periods is None:
        raise HTTPException(status_code=404, detail=f"backtest dataset '{request.dataset_id}' not found")
    runtime = adaptation_service.build_runtime_components()
    effective_config = runtime.backtest_config.model_copy(update=request.config.model_dump(exclude_unset=True))
    return BacktestEngine(
        strategy_registry=runtime.strategy_registry,
        risk_policy=runtime.risk_policy,
    ).run(periods, effective_config)


@router.get("/adaptation/state", response_model=TuningState)
async def get_adaptation_state(
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> TuningState:
    return adaptation_service.get_state()


@router.post("/adaptation/recommend", response_model=AdaptationRecommendationResponse)
async def recommend_adaptation(
    request: AdaptationRecommendationRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> AdaptationRecommendationResponse:
    if not request.samples:
        return adaptation_service.recommend_from_store()
    return adaptation_service.recommend(request.samples)


@router.post("/adaptation/evaluate-packages", response_model=AdaptationPackageEvaluationResponse)
async def evaluate_adaptation_packages(
    request: AdaptationPackageEvaluationRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
    dataset_service: BacktestDatasetService = Depends(get_backtest_dataset_service),
) -> AdaptationPackageEvaluationResponse:
    periods = dataset_service.get_periods(
        request.dataset_id,
        limit_recent_periods=request.limit_recent_periods,
    )
    if periods is None:
        raise HTTPException(status_code=404, detail=f"backtest dataset '{request.dataset_id}' not found")
    return adaptation_service.evaluate_packages_against_periods(request.dataset_id, periods)


@router.post("/adaptation/apply", response_model=TuningState)
async def apply_adaptation(
    request: TuningApplyRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> TuningState:
    try:
        return adaptation_service.apply(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/adaptation/samples", response_model=LearningSampleListResponse)
async def list_adaptation_samples(
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> LearningSampleListResponse:
    return LearningSampleListResponse(samples=adaptation_service.get_samples())


@router.post("/adaptation/samples/import", response_model=LearningSampleImportResponse)
async def import_adaptation_samples(
    request: LearningSampleImportRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
) -> LearningSampleImportResponse:
    persisted = adaptation_service.import_samples(request.samples, mode=request.mode)
    return LearningSampleImportResponse(
        imported_samples=len(request.samples),
        total_samples=len(persisted),
    )


@router.get("/journal/trades", response_model=TradeJournalListResponse)
async def list_trade_journal_records(
    journal_service: TradeJournalService = Depends(get_trade_journal_service),
) -> TradeJournalListResponse:
    return TradeJournalListResponse(trades=journal_service.list_records())


@router.post("/journal/trades/import", response_model=TradeJournalImportResponse)
async def import_trade_journal_records(
    request: TradeJournalImportRequest,
    journal_service: TradeJournalService = Depends(get_trade_journal_service),
) -> TradeJournalImportResponse:
    persisted = journal_service.import_records(request.trades, mode=request.mode)
    return TradeJournalImportResponse(
        imported_trades=len(request.trades),
        total_trades=len(persisted),
    )


@router.post("/adaptation/samples/extract-from-journal", response_model=LearningSampleImportResponse)
async def extract_adaptation_samples_from_journal(
    request: JournalSampleExtractionRequest,
    adaptation_service: AdaptationService = Depends(get_adaptation_service),
    journal_service: TradeJournalService = Depends(get_trade_journal_service),
) -> LearningSampleImportResponse:
    samples = journal_service.extract_learning_samples(
        symbol=request.symbol,
        limit=request.limit,
    )
    persisted = adaptation_service.import_samples(samples, mode=request.mode)
    return LearningSampleImportResponse(
        imported_samples=len(samples),
        total_samples=len(persisted),
    )


@router.get("/ledger/trades", response_model=TradeLedgerListResponse)
async def list_trade_ledger_records(
    mode: str | None = None,
    status: str | None = None,
    symbol: str | None = None,
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
) -> TradeLedgerListResponse:
    return TradeLedgerListResponse(
        trades=ledger_service.list_records(mode=mode, status=status, symbol=symbol),
    )


@router.post("/ledger/trades/import", response_model=TradeLedgerImportResponse)
async def import_trade_ledger_records(
    request: TradeLedgerImportRequest,
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
) -> TradeLedgerImportResponse:
    persisted = ledger_service.import_records(request.trades, mode=request.mode)
    return TradeLedgerImportResponse(
        imported_trades=len(request.trades),
        total_trades=len(persisted),
    )


@router.get("/audit/events", response_model=AuditEventListResponse)
async def list_audit_events(
    severity: str | None = None,
    source: str | None = None,
    limit: int | None = None,
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> AuditEventListResponse:
    return AuditEventListResponse(
        events=audit_service.list_events(severity=severity, source=source, limit=limit),
    )


@router.post("/audit/events/import", response_model=AuditEventImportResponse)
async def import_audit_events(
    request: AuditEventImportRequest,
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> AuditEventImportResponse:
    persisted = audit_service.import_events(request.events, mode=request.mode)
    return AuditEventImportResponse(
        imported_events=len(request.events),
        total_events=len(persisted),
    )


@router.post("/execution/execute", response_model=ExecutionResult)
async def execute_intent(
    request: ExecutionIntentRequest,
    orchestrator: ExecutionOrchestrator = Depends(get_execution_orchestrator),
) -> ExecutionResult:
    try:
        return orchestrator.execute(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/execution/recover", response_model=ExecutionResult)
async def recover_execution(
    request: ExecutionRecoveryRequest,
    orchestrator: ExecutionOrchestrator = Depends(get_execution_orchestrator),
) -> ExecutionResult:
    try:
        return orchestrator.recover(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/execution/summary", response_model=ExecutionConsoleSnapshot)
async def get_execution_summary(
    limit_incidents: int = 5,
    read_service: ExecutionReadService = Depends(get_execution_read_service),
) -> ExecutionConsoleSnapshot:
    return read_service.snapshot(limit_incidents=limit_incidents)


@router.get("/hedge/overview", response_model=HedgeOverview)
async def get_hedge_overview(
    exposure_limit_bps: float = 50.0,
    hedge_service: HedgeManagerService = Depends(get_hedge_manager_service),
) -> HedgeOverview:
    return hedge_service.overview(exposure_limit_bps=exposure_limit_bps)


@router.get("/hedge/rebalance-plan/{trade_id}", response_model=HedgeRebalancePlan)
async def get_hedge_rebalance_plan(
    trade_id: str,
    exposure_limit_bps: float = 50.0,
    hedge_service: HedgeManagerService = Depends(get_hedge_manager_service),
) -> HedgeRebalancePlan:
    try:
        return hedge_service.build_rebalance_plan(trade_id, exposure_limit_bps=exposure_limit_bps)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reconciliation/reports", response_model=ExchangeOrderReportListResponse)
async def list_reconciliation_reports(
    symbol: str | None = None,
    order_id: str | None = None,
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ExchangeOrderReportListResponse:
    return ExchangeOrderReportListResponse(
        reports=reconciliation_service.list_reports(symbol=symbol, order_id=order_id),
    )


@router.post("/reconciliation/reports/import", response_model=ExchangeOrderReportImportResponse)
async def import_reconciliation_reports(
    request: ExchangeOrderReportImportRequest,
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ExchangeOrderReportImportResponse:
    persisted = reconciliation_service.import_reports(request.reports, mode=request.mode)
    return ExchangeOrderReportImportResponse(
        imported_reports=len(request.reports),
        total_reports=len(persisted),
    )


@router.post("/reconciliation/sync/{trade_id}", response_model=ExchangeOrderReportImportResponse)
async def sync_reconciliation_reports(
    trade_id: str,
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ExchangeOrderReportImportResponse:
    try:
        persisted = reconciliation_service.sync_reports_for_trade(trade_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExchangeOrderReportImportResponse(
        imported_reports=len(persisted),
        total_reports=len(persisted),
    )


@router.post("/reconciliation/sync", response_model=ExchangeOrderReportImportResponse)
async def sync_attention_reconciliation_reports(
    limit: int | None = None,
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ExchangeOrderReportImportResponse:
    persisted = reconciliation_service.sync_attention_candidates(limit=limit)
    return ExchangeOrderReportImportResponse(
        imported_reports=len(persisted),
        total_reports=len(persisted),
    )


@router.get("/reconciliation/summary", response_model=ReconciliationSummary)
async def get_reconciliation_summary(
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationSummary:
    return reconciliation_service.build_summary()


@router.get("/reconciliation/candidates", response_model=ReconciliationCandidateListResponse)
async def list_reconciliation_candidates(
    symbol: str | None = None,
    only_attention: bool = False,
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationCandidateListResponse:
    return ReconciliationCandidateListResponse(
        candidates=reconciliation_service.list_candidates(symbol=symbol, only_attention=only_attention),
    )


@router.post("/persistence/backfill-json", response_model=PersistenceBackfillSummary)
async def backfill_json_to_mysql(
    backfill_service: JsonToMySQLBackfillService = Depends(get_persistence_backfill_service),
) -> PersistenceBackfillSummary:
    try:
        return backfill_service.run()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
