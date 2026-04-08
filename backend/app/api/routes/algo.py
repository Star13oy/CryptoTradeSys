from fastapi import APIRouter, Depends, HTTPException, Request

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
    ExecutionCircuitBreakerService,
    ExecutionCircuitBreakerState,
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
from app.compensation import (
    CompensationExecutionSummary,
    CompensationPlanListResponse,
    CompensationService,
    CompensationWorker,
    CompensationWorkerSnapshot,
)
from app.hedge import (
    HedgeAutoRebalanceExecutionRequest,
    HedgeManagerService,
    HedgeOverview,
    HedgeRebalanceWorker,
    HedgeRebalanceWorkerSnapshot,
    HedgeRebalanceExecutionRequest,
    HedgeRebalancePlan,
)
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
    ReconciliationWorker,
    ReconciliationWorkerSnapshot,
)
from app.recovery import RecoveryExecutionSummary, RecoveryPlanListResponse, RecoveryService
from app.recovery import RecoveryWorker, RecoveryWorkerSnapshot
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
    circuit_breaker: ExecutionCircuitBreakerService = Depends(lambda: get_execution_circuit_breaker_service()),
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
        circuit_breaker=circuit_breaker,
        live_execution_enabled=settings.live_execution_enabled,
        live_symbol_allowlist=allowlist,
        max_live_notional=settings.max_live_notional,
    )


def get_execution_circuit_breaker_service() -> ExecutionCircuitBreakerService:
    settings = get_settings()
    return ExecutionCircuitBreakerService(
        path=settings.execution_circuit_breaker_state_path,
        enabled=settings.live_circuit_breaker_enabled,
        failure_threshold=settings.live_circuit_breaker_failure_threshold,
        cooldown_seconds=settings.live_circuit_breaker_cooldown_seconds,
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
    settings = get_settings()
    from app.reconciliation import ExchangeOrderReportStore

    return HedgeManagerService(
        ledger_service,
        audit_service,
        report_store=ExchangeOrderReportStore(settings.exchange_order_report_path),
    )


def build_hedge_rebalance_worker() -> HedgeRebalanceWorker:
    settings = get_settings()
    ledger_service = TradeLedgerService(TradeLedgerStore(settings.trade_ledger_path))
    audit_service = AuditEventService(AuditEventStore(settings.audit_event_path))
    from app.reconciliation import ExchangeOrderReportStore

    hedge_service = HedgeManagerService(
        ledger_service,
        audit_service,
        report_store=ExchangeOrderReportStore(settings.exchange_order_report_path),
    )
    allowlist = {
        symbol.strip().upper()
        for symbol in settings.live_symbol_allowlist.split(",")
        if symbol.strip()
    }
    live_adapter = None
    if settings.binance_api_key and settings.binance_api_secret:
        live_adapter = BinanceLiveExecutionAdapter(BinanceTradingClient())
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=live_adapter,
        circuit_breaker=get_execution_circuit_breaker_service(),
        live_execution_enabled=settings.live_execution_enabled,
        live_symbol_allowlist=allowlist,
        max_live_notional=settings.max_live_notional,
    )
    return HedgeRebalanceWorker(
        hedge_service,
        orchestrator=orchestrator,
        enabled=settings.hedge_rebalance_worker_enabled,
        interval_seconds=settings.hedge_rebalance_worker_interval_seconds,
        limit=settings.hedge_rebalance_worker_limit,
        exposure_limit_bps=settings.hedge_rebalance_worker_exposure_limit_bps,
    )


def get_hedge_rebalance_worker(request: Request) -> HedgeRebalanceWorker:
    worker = getattr(request.app.state, "hedge_rebalance_worker", None)
    if worker is None:
        worker = build_hedge_rebalance_worker()
        request.app.state.hedge_rebalance_worker = worker
    return worker


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


def build_reconciliation_worker() -> ReconciliationWorker:
    settings = get_settings()
    ledger_service = TradeLedgerService(TradeLedgerStore(settings.trade_ledger_path))
    audit_service = AuditEventService(AuditEventStore(settings.audit_event_path))
    from app.reconciliation import ExchangeOrderReportStore

    reconciliation_service = ReconciliationService(
        ExchangeOrderReportStore(settings.exchange_order_report_path),
        ledger_service,
        audit_service,
    )
    trading_client = None
    if settings.binance_api_key and settings.binance_api_secret:
        trading_client = BinanceTradingClient()
    return ReconciliationWorker(
        reconciliation_service,
        trading_client=trading_client,
        enabled=settings.reconciliation_worker_enabled,
        interval_seconds=settings.reconciliation_worker_interval_seconds,
        limit=settings.reconciliation_worker_limit,
    )


def build_recovery_worker() -> RecoveryWorker:
    settings = get_settings()
    ledger_service = TradeLedgerService(TradeLedgerStore(settings.trade_ledger_path))
    audit_service = AuditEventService(AuditEventStore(settings.audit_event_path))
    from app.reconciliation import ExchangeOrderReportStore

    reconciliation_service = ReconciliationService(
        ExchangeOrderReportStore(settings.exchange_order_report_path),
        ledger_service,
        audit_service,
    )
    recovery_service = RecoveryService(ledger_service, audit_service, reconciliation_service)
    allowlist = {
        symbol.strip().upper()
        for symbol in settings.live_symbol_allowlist.split(",")
        if symbol.strip()
    }
    live_adapter = None
    if settings.binance_api_key and settings.binance_api_secret:
        live_adapter = BinanceLiveExecutionAdapter(BinanceTradingClient())
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=live_adapter,
        live_execution_enabled=settings.live_execution_enabled,
        live_symbol_allowlist=allowlist,
        max_live_notional=settings.max_live_notional,
    )
    return RecoveryWorker(
        recovery_service,
        orchestrator=orchestrator,
        enabled=settings.recovery_worker_enabled,
        interval_seconds=settings.recovery_worker_interval_seconds,
        limit=settings.recovery_worker_limit,
    )


def get_reconciliation_worker(request: Request) -> ReconciliationWorker:
    worker = getattr(request.app.state, "reconciliation_worker", None)
    if worker is None:
        worker = build_reconciliation_worker()
        request.app.state.reconciliation_worker = worker
    return worker


def get_recovery_worker(request: Request) -> RecoveryWorker:
    worker = getattr(request.app.state, "recovery_worker", None)
    if worker is None:
        worker = build_recovery_worker()
        request.app.state.recovery_worker = worker
    return worker


def get_recovery_service(
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
    audit_service: AuditEventService = Depends(get_audit_event_service),
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> RecoveryService:
    return RecoveryService(ledger_service, audit_service, reconciliation_service)


def get_persistence_backfill_service() -> JsonToMySQLBackfillService:
    return JsonToMySQLBackfillService()


def get_compensation_service(
    ledger_service: TradeLedgerService = Depends(get_trade_ledger_service),
    audit_service: AuditEventService = Depends(get_audit_event_service),
) -> CompensationService:
    settings = get_settings()
    from app.reconciliation import ExchangeOrderReportStore

    return CompensationService(
        ledger_service=ledger_service,
        audit_service=audit_service,
        report_store=ExchangeOrderReportStore(settings.exchange_order_report_path),
    )


def build_compensation_worker() -> CompensationWorker:
    settings = get_settings()
    ledger_service = TradeLedgerService(TradeLedgerStore(settings.trade_ledger_path))
    audit_service = AuditEventService(AuditEventStore(settings.audit_event_path))
    from app.reconciliation import ExchangeOrderReportStore

    compensation_service = CompensationService(
        ledger_service=ledger_service,
        audit_service=audit_service,
        report_store=ExchangeOrderReportStore(settings.exchange_order_report_path),
    )
    allowlist = {
        symbol.strip().upper()
        for symbol in settings.live_symbol_allowlist.split(",")
        if symbol.strip()
    }
    live_adapter = None
    if settings.binance_api_key and settings.binance_api_secret:
        live_adapter = BinanceLiveExecutionAdapter(BinanceTradingClient())
    orchestrator = ExecutionOrchestrator(
        ledger_service,
        audit_service,
        live_adapter=live_adapter,
        circuit_breaker=get_execution_circuit_breaker_service(),
        live_execution_enabled=settings.live_execution_enabled,
        live_symbol_allowlist=allowlist,
        max_live_notional=settings.max_live_notional,
    )
    return CompensationWorker(
        compensation_service,
        orchestrator=orchestrator,
        enabled=settings.compensation_worker_enabled,
        interval_seconds=settings.compensation_worker_interval_seconds,
        limit=settings.compensation_worker_limit,
        exposure_limit_bps=settings.compensation_worker_exposure_limit_bps,
    )


def get_compensation_worker(request: Request) -> CompensationWorker:
    worker = getattr(request.app.state, "compensation_worker", None)
    if worker is None:
        worker = build_compensation_worker()
        request.app.state.compensation_worker = worker
    return worker


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


@router.get("/execution/circuit-breaker", response_model=ExecutionCircuitBreakerState)
async def get_execution_circuit_breaker_status(
    circuit_breaker: ExecutionCircuitBreakerService = Depends(get_execution_circuit_breaker_service),
) -> ExecutionCircuitBreakerState:
    return circuit_breaker.get_state()


@router.post("/execution/circuit-breaker/reset", response_model=ExecutionCircuitBreakerState)
async def reset_execution_circuit_breaker(
    circuit_breaker: ExecutionCircuitBreakerService = Depends(get_execution_circuit_breaker_service),
) -> ExecutionCircuitBreakerState:
    return circuit_breaker.manual_reset()


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


@router.post("/hedge/rebalance/{trade_id}", response_model=ExecutionResult)
async def execute_hedge_rebalance(
    trade_id: str,
    request: HedgeRebalanceExecutionRequest,
    hedge_service: HedgeManagerService = Depends(get_hedge_manager_service),
    orchestrator: ExecutionOrchestrator = Depends(get_execution_orchestrator),
) -> ExecutionResult:
    try:
        plan = hedge_service.build_rebalance_plan(trade_id, exposure_limit_bps=request.exposure_limit_bps)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if (
        plan.recommended_action not in {"increase_perp_hedge", "reduce_perp_hedge"}
        or plan.suggested_perp_notional_delta == 0
    ):
        raise HTTPException(
            status_code=400,
            detail=f"trade '{trade_id}' does not currently require hedge rebalance",
        )

    try:
        return orchestrator.rebalance_hedge(
            trade_id=trade_id,
            perp_notional_delta=plan.suggested_perp_notional_delta,
            perp_quantity=request.perp_quantity,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/hedge/rebalance-auto/{trade_id}", response_model=ExecutionResult)
async def execute_hedge_rebalance_auto(
    trade_id: str,
    request: HedgeAutoRebalanceExecutionRequest | None = None,
    hedge_service: HedgeManagerService = Depends(get_hedge_manager_service),
    orchestrator: ExecutionOrchestrator = Depends(get_execution_orchestrator),
) -> ExecutionResult:
    payload = request or HedgeAutoRebalanceExecutionRequest()
    try:
        return hedge_service.execute_rebalance_plan(
            trade_id,
            orchestrator=orchestrator,
            exposure_limit_bps=payload.exposure_limit_bps,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/hedge/worker", response_model=HedgeRebalanceWorkerSnapshot)
async def get_hedge_rebalance_worker_status(
    worker: HedgeRebalanceWorker = Depends(get_hedge_rebalance_worker),
) -> HedgeRebalanceWorkerSnapshot:
    return worker.snapshot()


@router.post("/hedge/worker/run", response_model=HedgeRebalanceWorkerSnapshot)
async def run_hedge_rebalance_worker_once(
    worker: HedgeRebalanceWorker = Depends(get_hedge_rebalance_worker),
) -> HedgeRebalanceWorkerSnapshot:
    try:
        return await worker.run_once()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/reconciliation/worker", response_model=ReconciliationWorkerSnapshot)
async def get_reconciliation_worker_status(
    worker: ReconciliationWorker = Depends(get_reconciliation_worker),
) -> ReconciliationWorkerSnapshot:
    return worker.snapshot()


@router.post("/reconciliation/worker/run", response_model=ReconciliationWorkerSnapshot)
async def run_reconciliation_worker_once(
    worker: ReconciliationWorker = Depends(get_reconciliation_worker),
) -> ReconciliationWorkerSnapshot:
    try:
        return await worker.run_once()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recovery/plans", response_model=RecoveryPlanListResponse)
async def list_recovery_plans(
    symbol: str | None = None,
    only_actionable: bool = False,
    recovery_service: RecoveryService = Depends(get_recovery_service),
) -> RecoveryPlanListResponse:
    return RecoveryPlanListResponse(
        plans=recovery_service.list_plans(symbol=symbol, only_actionable=only_actionable),
    )


@router.post("/recovery/execute-auto", response_model=RecoveryExecutionSummary)
async def execute_recovery_plans(
    limit: int | None = None,
    symbol: str | None = None,
    recovery_service: RecoveryService = Depends(get_recovery_service),
    orchestrator: ExecutionOrchestrator = Depends(get_execution_orchestrator),
) -> RecoveryExecutionSummary:
    if symbol is None:
        return recovery_service.execute_actionable_plans(
            orchestrator=orchestrator,
            limit=limit,
        )
    return recovery_service.execute_actionable_plans(
        orchestrator=orchestrator,
        limit=limit,
        symbol=symbol,
    )


@router.get("/recovery/worker", response_model=RecoveryWorkerSnapshot)
async def get_recovery_worker_status(
    worker: RecoveryWorker = Depends(get_recovery_worker),
) -> RecoveryWorkerSnapshot:
    return worker.snapshot()


@router.post("/recovery/worker/run", response_model=RecoveryWorkerSnapshot)
async def run_recovery_worker_once(
    worker: RecoveryWorker = Depends(get_recovery_worker),
) -> RecoveryWorkerSnapshot:
    try:
        return await worker.run_once()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/compensation/plans", response_model=CompensationPlanListResponse)
async def list_compensation_plans(
    symbol: str | None = None,
    only_actionable: bool = False,
    exposure_limit_bps: float = 50.0,
    compensation_service: CompensationService = Depends(get_compensation_service),
) -> CompensationPlanListResponse:
    return CompensationPlanListResponse(
        plans=compensation_service.list_plans(
            symbol=symbol,
            only_actionable=only_actionable,
            exposure_limit_bps=exposure_limit_bps,
        )
    )


@router.post("/compensation/execute", response_model=CompensationExecutionSummary)
async def execute_compensation_actions(
    symbol: str | None = None,
    limit: int | None = None,
    exposure_limit_bps: float = 50.0,
    compensation_service: CompensationService = Depends(get_compensation_service),
    orchestrator: ExecutionOrchestrator = Depends(get_execution_orchestrator),
) -> CompensationExecutionSummary:
    return compensation_service.execute_safe_actions(
        orchestrator=orchestrator,
        symbol=symbol,
        limit=limit,
        exposure_limit_bps=exposure_limit_bps,
    )


@router.get("/compensation/worker", response_model=CompensationWorkerSnapshot)
async def get_compensation_worker_status(
    worker: CompensationWorker = Depends(get_compensation_worker),
) -> CompensationWorkerSnapshot:
    return worker.snapshot()


@router.post("/compensation/worker/run", response_model=CompensationWorkerSnapshot)
async def run_compensation_worker_once(
    worker: CompensationWorker = Depends(get_compensation_worker),
) -> CompensationWorkerSnapshot:
    try:
        return await worker.run_once()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
