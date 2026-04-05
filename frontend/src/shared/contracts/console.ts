export type OpportunityScore = {
  symbol: string;
  funding_rate: number;
  net_edge_bps: number;
  score: number;
  risk_tag: string;
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
