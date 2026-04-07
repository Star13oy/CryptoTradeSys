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
