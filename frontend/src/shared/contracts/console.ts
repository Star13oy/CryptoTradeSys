export type OpportunityScore = {
  symbol: string;
  funding_rate: number;
  net_edge_bps: number;
  score: number;
  risk_tag: string;
  perp_bid: number;
  perp_ask: number;
  spot_bid: number;
  spot_ask: number;
  perp_mid: number;
  spot_mid: number;
  perp_spread_bps: number;
  spot_spread_bps: number;
  gross_edge_bps: number;
  trading_cost_bps: number;
  annualized_funding_rate_pct: number;
  basis_bps: number;
  projected_net_edge_bps: number;
  payback_periods: number;
  expected_hold_periods: number;
};

export type AccountHealthSummary = {
  mode: string;
  exchange: string;
  risk_state: string;
};

export type ScanFilters = {
  limit: number;
  positive_funding_only: boolean;
  min_net_edge_bps: number | null;
};

export type MarketDataStatus = {
  spot_source: string;
  perp_source: string;
  degraded: boolean;
  requested_symbols: number;
  quoted_symbols: number;
};

export type DashboardSummary = {
  generated_at: string;
  account_health: AccountHealthSummary;
  market_status: MarketDataStatus;
  top_opportunities: OpportunityScore[];
  paper_positions: Array<Record<string, unknown>>;
};

export type ScanOpportunitiesResponse = {
  generated_at: string;
  applied_filters: ScanFilters;
  market_status: MarketDataStatus;
  total_matches: number;
  rows: OpportunityScore[];
};

export type HedgeHealth = "healthy" | "monitoring" | "rebalance_required" | "recovery_required";

export type RebalanceAction =
  | "none"
  | "monitor_only"
  | "recover_trade"
  | "increase_perp_hedge"
  | "reduce_perp_hedge";

export type HedgeOverviewItem = {
  trade_id: string;
  mode: "paper" | "live";
  symbol: string;
  status: string;
  health: HedgeHealth;
  opened_at: string;
  spot_notional: number;
  perp_notional: number;
  net_exposure: number;
  exposure_bps: number;
  latest_event_type: string | null;
  latest_event_summary: string | null;
  latest_event_severity: string | null;
};

export type HedgeOverviewResponse = {
  generated_at: string;
  exposure_limit_bps: number;
  active_trade_count: number;
  healthy_count: number;
  monitoring_count: number;
  rebalance_required_count: number;
  recovery_required_count: number;
  items: HedgeOverviewItem[];
};

export type HedgeRebalancePlan = {
  trade_id: string;
  symbol: string;
  status: string;
  health: HedgeHealth;
  exposure_limit_bps: number;
  net_exposure: number;
  exposure_bps: number;
  recommended_action: RebalanceAction;
  suggested_perp_notional_delta: number;
  estimated_post_rebalance_exposure_bps: number;
  notes: string;
};

export type HedgeRebalanceAutoResponse = {
  trade_id: string;
  executed: boolean;
};

export type HedgeRebalanceWorkerStatus = {
  enabled: boolean;
  configured: boolean;
  running: boolean;
  interval_seconds: number;
  limit: number;
  exposure_limit_bps: number;
  total_runs: number;
  total_failed_runs: number;
  total_executed_rebalances: number;
  last_attempted_count: number;
  last_executed_count: number;
  last_skipped_count: number;
  last_failed_count: number;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
};

export type ReconciliationSuggestedAction = "none" | "inspect_exchange" | "resume_open" | "resume_close";

export type ReconciliationCandidate = {
  trade_id: string;
  symbol: string;
  local_status: string;
  expected_order_ids: string[];
  reported_order_ids: string[];
  missing_order_ids: string[];
  exchange_statuses: string[];
  latest_event_at: string | null;
  latest_report_at: string | null;
  suggested_action: ReconciliationSuggestedAction;
  needs_attention: boolean;
};

export type ReconciliationCandidateListResponse = {
  candidates: ReconciliationCandidate[];
};

export type ReconciliationWorkerStatus = {
  enabled: boolean;
  configured: boolean;
  running: boolean;
  interval_seconds: number;
  limit: number;
  total_runs: number;
  total_failed_runs: number;
  total_imported_reports: number;
  last_imported_report_count: number;
  last_synced_trade_count: number;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
};

export type RecoveryWorkerStatus = {
  enabled: boolean;
  configured: boolean;
  running: boolean;
  interval_seconds: number;
  limit: number;
  total_runs: number;
  total_failed_runs: number;
  total_executed_recoveries: number;
  last_attempted_count: number;
  last_executed_count: number;
  last_skipped_count: number;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
};

export type ExecutionCircuitBreakerStatus = {
  enabled: boolean;
  is_open: boolean;
  failure_threshold: number;
  cooldown_seconds: number;
  consecutive_failures: number;
  last_failure_at: string | null;
  opened_at: string | null;
  resume_at: string | null;
  last_reason: string | null;
  last_trade_id: string | null;
  updated_at: string;
};

export type CompensationAction =
  | "none"
  | "sync_exchange_reports"
  | "resume_open"
  | "resume_close"
  | "rebalance_hedge"
  | "manual_review"
  | "flatten_spot"
  | "flatten_perp";

export type CompensationPriority = "low" | "medium" | "high" | "critical";

export type CompensationPlan = {
  trade_id: string;
  symbol: string;
  mode: "paper" | "live";
  local_status: string;
  recommended_action: CompensationAction;
  priority: CompensationPriority;
  actionable: boolean;
  reason: string;
  details: Record<string, unknown>;
};

export type CompensationPlanListResponse = {
  generated_at: string;
  plans: CompensationPlan[];
};

export type CompensationWorkerStatus = {
  enabled: boolean;
  configured: boolean;
  running: boolean;
  interval_seconds: number;
  limit: number;
  exposure_limit_bps: number;
  total_runs: number;
  total_failed_runs: number;
  total_executed_actions: number;
  last_attempted_count: number;
  last_executed_count: number;
  last_skipped_count: number;
  last_failed_count: number;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
};

export type ExecutionStatusCount = {
  status: string;
  count: number;
};

export type ExecutionRecoveryQueueItem = {
  trade_id: string;
  mode: "paper" | "live";
  symbol: string;
  status: string;
  opened_at: string;
  net_exposure: number;
  spot_notional: number;
  perp_notional: number;
  latest_event_type: string | null;
  latest_event_summary: string | null;
  latest_event_severity: string | null;
};

export type ExecutionIncident = {
  event_id: string;
  event_type: string;
  severity: string;
  occurred_at: string;
  summary: string;
  trade_id: string | null;
};

export type ExecutionSummaryResponse = {
  generated_at: string;
  status_counts: ExecutionStatusCount[];
  recovery_queue: ExecutionRecoveryQueueItem[];
  recent_incidents: ExecutionIncident[];
};

// --- Backtest ---

export type BacktestConfig = {
  notional_per_trade: number;
  min_score: number;
  min_net_edge_bps: number;
  top_k: number;
  accept_reviewed: boolean;
  strategy_id?: string | null;
};

export type BacktestTrade = {
  period_index: number;
  observed_at: string | null;
  symbol: string;
  funding_rate: number;
  score: number;
  net_edge_bps: number;
  projected_net_edge_bps: number;
  estimated_pnl: number;
  risk_tag: string;
  risk_decision: string;
  position_fraction: number;
  reasons: string[];
};

export type BacktestResult = {
  periods_processed: number;
  candidates_seen: number;
  selected_trades: number;
  estimated_total_pnl: number;
  average_score: number;
  average_net_edge_bps: number;
  average_projected_edge_bps: number;
  trades: BacktestTrade[];
};

export type BacktestDatasetSummary = {
  dataset_id: string;
  title: string;
  source: string;
  description: string | null;
  imported_at: string;
  period_count: number;
  snapshot_count: number;
  observed_from: string | null;
  observed_to: string | null;
};

export type BacktestDatasetListResponse = {
  datasets: BacktestDatasetSummary[];
};

// --- Adaptation (Model Workbench) ---

export type ScoreConfigSnapshot = {
  taker_fee_bps: number;
  funding_periods_per_day: number;
  expected_hold_periods: number;
  basis_soft_limit_bps: number;
  basis_guarded_bps: number;
  payback_guarded_periods: number;
  trading_cost_guarded_bps: number;
  carry_weight: number;
  annualized_weight: number;
  cost_soft_limit_bps: number;
  cost_penalty_weight: number;
  basis_penalty_weight: number;
};

export type RiskConfigSnapshot = {
  min_allow_score: number;
  min_review_score: number;
  min_allow_net_edge_bps: number;
  min_allow_projected_edge_bps: number;
  max_allow_basis_bps: number;
  max_review_basis_bps: number;
  max_allow_trading_cost_bps: number;
  max_allow_payback_periods: number;
};

export type TuningConfig = {
  score: ScoreConfigSnapshot;
  risk: RiskConfigSnapshot;
  backtest: BacktestConfig;
};

export type TuningState = {
  updated_at: string;
  active_package_id: string;
  active_package_title: string;
  config: TuningConfig;
};

export type LearningTradeSample = {
  trade_id: string | null;
  symbol: string;
  closed_at: string | null;
  score: number;
  risk_tag: string;
  net_edge_bps: number;
  projected_net_edge_bps: number;
  basis_bps: number;
  realized_pnl_bps: number;
  max_drawdown_bps: number;
  hold_periods: number;
};

export type AdaptationMetrics = {
  trade_count: number;
  win_rate: number;
  avg_realized_pnl_bps: number;
  avg_projected_edge_bps: number;
  avg_projection_shortfall_bps: number;
  max_drawdown_p95_bps: number;
  slow_payback_rate: number;
};

export type TuningPackage = {
  package_id: string;
  title: string;
  summary: string;
  objective: string;
  recommended: boolean;
  derived_from: string | null;
  reason_codes: string[];
  config: TuningConfig;
};

export type AdaptationRecommendationResponse = {
  generated_at: string;
  metrics: AdaptationMetrics;
  current_state: TuningState;
  recommended_package_id: string;
  packages: TuningPackage[];
};

export type PackageBacktestEvaluation = {
  package_id: string;
  title: string;
  recommended: boolean;
  estimated_total_pnl: number;
  selected_trades: number;
  average_score: number;
  average_projected_edge_bps: number;
  reason_codes: string[];
};

export type AdaptationPackageEvaluationResponse = {
  dataset_id: string;
  metrics: AdaptationMetrics;
  recommended_package_id: string;
  evaluations: PackageBacktestEvaluation[];
};

export type LearningSampleListResponse = {
  samples: LearningTradeSample[];
};

export type LearningSampleImportResponse = {
  imported_samples: number;
  total_samples: number;
};

// --- Audit ---

export type AuditEventRecord = {
  event_id: string;
  event_type: string;
  severity: "debug" | "info" | "warning" | "error" | "critical";
  source: string;
  occurred_at: string;
  summary: string;
  payload: Record<string, unknown>;
  tags: string[];
};

export type AuditEventListResponse = {
  events: AuditEventRecord[];
};

export type AuditEventImportResponse = {
  imported_events: number;
  total_events: number;
};

// --- Safety ---

export type SafetyStateSnapshot = {
  frozen: boolean;
  new_positions_allowed: boolean;
  reduce_only_trades: string[];
  paused_trades: string[];
  updated_at: string;
};

export type EmergencyCloseResult = {
  closed_count: number;
  failed_count: number;
  skipped_count: number;
  results: Array<Record<string, unknown>>;
};

export type SafetyActionRequest = {
  trade_id?: string;
  reason?: string;
};

// --- Account ---

export type AssetBalance = {
  asset: string;
  balance: number;
  available: number;
  cross_unrealized_pnl: number;
};

export type PositionInfo = {
  symbol: string;
  position_side: string;
  position_amt: number;
  unrealized_pnl: number;
  liquidation_price: number | null;
  mark_price: number;
  entry_price: number;
  leverage: number;
};

export type AccountBalanceSnapshot = {
  total_usdt_equity: number;
  available_usdt: number;
  usdt_in_positions: number;
  unrealized_pnl: number;
  assets: AssetBalance[];
  fetched_at: string;
};

export type AccountSummary = {
  balance: AccountBalanceSnapshot | null;
  positions: PositionInfo[];
  active_position_count: number;
  fetched_at: string;
};

// --- Scheduler ---

export type SchedulerCycleAction = {
  action: "open_hedge" | "close_hedge";
  symbol: string;
  trade_id: string;
  score: number;
  risk_decision: string;
  reason: string;
};

export type SchedulerCycleResult = {
  cycle_started_at: string;
  cycle_finished_at: string;
  snapshots_evaluated: number;
  positions_evaluated: number;
  actions_generated: number;
  actions_executed: number;
  actions_skipped: number;
  actions_failed: number;
  actions: SchedulerCycleAction[];
};

export type SchedulerWorkerSnapshot = {
  enabled: boolean;
  configured: boolean;
  running: boolean;
  interval_seconds: number;
  max_open_positions: number;
  max_total_notional: number;
  total_cycles: number;
  total_failed_cycles: number;
  total_actions_executed: number;
  last_cycle_result: SchedulerCycleResult | null;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
};

// --- Monitor ---

export type HoldingAlert = {
  trade_id: string;
  symbol: string;
  alert_type: string;
  severity: "warning" | "critical";
  detail: string;
  entry_funding_rate: number;
  current_funding_rate: number;
  hold_periods: number;
  max_hold_periods: number;
};

export type HoldingMonitorResult = {
  evaluated_count: number;
  alert_count: number;
  close_executed: number;
  close_skipped: number;
  close_failed: number;
  actions: Array<{
    trade_id: string;
    symbol: string;
    action: "close_hedge" | "monitor";
    alert: HoldingAlert | null;
    outcome: "executed" | "skipped" | "failed";
    reason: string | null;
  }>;
  cycle_started_at: string;
  cycle_finished_at: string;
};

export type HoldingMonitorWorkerSnapshot = {
  enabled: boolean;
  configured: boolean;
  running: boolean;
  interval_seconds: number;
  max_hold_periods: number;
  total_cycles: number;
  total_failed_cycles: number;
  total_closes_executed: number;
  last_cycle_result: HoldingMonitorResult | null;
  last_started_at: string | null;
  last_finished_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
};

// --- Auth ---
export type LoginRequest = { username: string; password: string };
export type RegisterRequest = { username: string; password: string };
export type TokenResponse = { access_token: string; token_type: string; username: string; role: string };
export type UserResponse = { id: string; username: string; role: string; created_at: string };

// --- Credentials ---
export type ApiKeySet = { label: string; exchange: string; api_key: string; api_secret: string };
export type ApiKeySummary = { id: string; label: string; exchange: string; api_key_preview: string; created_at: string; is_active: boolean };

// --- Trading ---
export type ManualOrderRequest = { symbol: string; side: string; notional: number; mode: string };
export type OrderPreview = { symbol: string; side: string; notional: number; spot_price: number; perp_price: number; funding_rate: number; estimated_fees_usd: number; estimated_net_edge_bps: number; risk_decision: string };
export type OrderResult = { trade_id: string; status: string; spot_filled: number; perp_filled: number; executed_at: string };
export type SymbolInfo = { symbol: string; funding_rate: number; mark_price: number };
