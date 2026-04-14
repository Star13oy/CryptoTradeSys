type QueryValue = string | number | boolean | null | undefined;

function buildQueryString(params: Record<string, QueryValue> | undefined): string {
  if (!params) {
    return "";
  }

  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }
    searchParams.set(key, String(value));
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export async function apiGet<T>(path: string, params?: Record<string, QueryValue>): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers: Record<string, string> = {};
  if (token) { headers["Authorization"] = `Bearer ${token}`; }
  const response = await fetch(`${path}${buildQueryString(params)}`, { headers });
  if (!response.ok) { throw new Error(`Request failed: ${response.status}`); }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const init: RequestInit = { method: "POST", headers: {} };
  if (token) { (init.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`; }
  if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const response = await fetch(path, init);
  if (!response.ok) { throw new Error(`Request failed: ${response.status}`); }
  return response.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const init: RequestInit = { method: "PUT", headers: {} };
  if (token) { (init.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`; }
  if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const response = await fetch(path, init);
  if (!response.ok) { throw new Error(`Request failed: ${response.status}`); }
  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const init: RequestInit = { method: "DELETE", headers: {} };
  if (token) { (init.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`; }
  const response = await fetch(path, init);
  if (!response.ok) { throw new Error(`Request failed: ${response.status}`); }
  return response.json() as Promise<T>;
}

type HedgeOverviewParams = {
  exposure_limit_bps?: number;
};

type HedgeRebalancePlanParams = {
  exposure_limit_bps?: number;
};

type ExecutionSummaryParams = {
  limit_incidents?: number;
};

type ReconciliationCandidatesParams = {
  symbol?: string;
  only_attention?: boolean;
};

type CompensationPlansParams = {
  symbol?: string;
  only_actionable?: boolean;
  exposure_limit_bps?: number;
};

type AuditEventsParams = {
  severity?: string;
  source?: string;
  limit?: number;
};

type BacktestRunFromDatasetBody = {
  dataset_id: string;
  config: Record<string, unknown>;
  limit_recent_periods?: number;
};

type AdaptationEvaluateBody = {
  dataset_id: string;
  limit_recent_periods?: number;
};

type AdaptationApplyBody = {
  package: Record<string, unknown>;
  confirmed: boolean;
};

type ExtractSamplesBody = {
  mode: "append" | "replace";
  symbol?: string;
  limit?: number;
};

type SafetyActionBody = {
  trade_id?: string;
  reason?: string;
};

export const apiClient = {
  getHedgeOverview: <T>(params?: HedgeOverviewParams) => apiGet<T>("/api/v1/algo/hedge/overview", params),
  getHedgeRebalancePlan: <T>(tradeId: string, params?: HedgeRebalancePlanParams) =>
    apiGet<T>(`/api/v1/algo/hedge/rebalance-plan/${encodeURIComponent(tradeId)}`, params),
  runHedgeRebalanceAuto: <T>(tradeId: string) =>
    apiPost<T>(`/api/v1/algo/hedge/rebalance-auto/${encodeURIComponent(tradeId)}`),
  getHedgeRebalanceWorker: <T>() => apiGet<T>("/api/v1/algo/hedge/worker"),
  runHedgeRebalanceWorker: <T>() => apiPost<T>("/api/v1/algo/hedge/worker/run"),
  getExecutionSummary: <T>(params?: ExecutionSummaryParams) => apiGet<T>("/api/v1/algo/execution/summary", params),
  getExecutionCircuitBreaker: <T>() => apiGet<T>("/api/v1/algo/execution/circuit-breaker"),
  getReconciliationCandidates: <T>(params?: ReconciliationCandidatesParams) =>
    apiGet<T>("/api/v1/algo/reconciliation/candidates", params),
  getReconciliationWorker: <T>() => apiGet<T>("/api/v1/algo/reconciliation/worker"),
  runReconciliationWorker: <T>() => apiPost<T>("/api/v1/algo/reconciliation/worker/run"),
  getRecoveryWorker: <T>() => apiGet<T>("/api/v1/algo/recovery/worker"),
  runRecoveryWorker: <T>() => apiPost<T>("/api/v1/algo/recovery/worker/run"),
  getCompensationPlans: <T>(params?: CompensationPlansParams) =>
    apiGet<T>("/api/v1/algo/compensation/plans", params),
  getCompensationWorker: <T>() => apiGet<T>("/api/v1/algo/compensation/worker"),
  runCompensationWorker: <T>() => apiPost<T>("/api/v1/algo/compensation/worker/run"),
  resetExecutionCircuitBreaker: <T>() => apiPost<T>("/api/v1/algo/execution/circuit-breaker/reset"),

  // --- Backtest ---
  getBacktestDatasets: <T>() => apiGet<T>("/api/v1/algo/backtest/datasets"),
  runBacktestFromDataset: <T>(body: BacktestRunFromDatasetBody) =>
    apiPost<T>("/api/v1/algo/backtest/run-from-dataset", body),

  // --- Adaptation (Model Workbench) ---
  getAdaptationState: <T>() => apiGet<T>("/api/v1/algo/adaptation/state"),
  recommendAdaptation: <T>() => apiPost<T>("/api/v1/algo/adaptation/recommend"),
  evaluateAdaptationPackages: <T>(body: AdaptationEvaluateBody) =>
    apiPost<T>("/api/v1/algo/adaptation/evaluate-packages", body),
  applyAdaptation: <T>(body: AdaptationApplyBody) =>
    apiPost<T>("/api/v1/algo/adaptation/apply", body),
  getAdaptationSamples: <T>() => apiGet<T>("/api/v1/algo/adaptation/samples"),
  extractSamplesFromJournal: <T>(body: ExtractSamplesBody) =>
    apiPost<T>("/api/v1/algo/adaptation/samples/extract-from-journal", body),

  // --- Audit ---
  getAuditEvents: <T>(params?: AuditEventsParams) =>
    apiGet<T>("/api/v1/algo/audit/events", params),

  // --- Safety ---
  getSafetyState: <T>() => apiGet<T>("/api/v1/safety/state"),
  freezeAll: <T>(body?: SafetyActionBody) => apiPost<T>("/api/v1/safety/freeze", body),
  unfreezeAll: <T>(body?: SafetyActionBody) => apiPost<T>("/api/v1/safety/unfreeze", body),
  stopNewPositions: <T>(body?: SafetyActionBody) => apiPost<T>("/api/v1/safety/stop-new-positions", body),
  resumeNewPositions: <T>(body?: SafetyActionBody) => apiPost<T>("/api/v1/safety/resume-new-positions", body),
  setReduceOnly: <T>(body: SafetyActionBody) => apiPost<T>("/api/v1/safety/reduce-only", body),
  clearReduceOnly: <T>(body: SafetyActionBody) => apiPost<T>("/api/v1/safety/reduce-only/clear", body),
  pauseTrade: <T>(body: SafetyActionBody) => apiPost<T>("/api/v1/safety/pause", body),
  unpauseTrade: <T>(body: SafetyActionBody) => apiPost<T>("/api/v1/safety/unpause", body),
  emergencyCloseAll: <T>() => apiPost<T>("/api/v1/safety/emergency-close-all"),
  panicSell: <T>(body: SafetyActionBody) => apiPost<T>("/api/v1/safety/panic-sell", body),

  // --- Account ---
  getAccountSummary: <T>() => apiGet<T>("/api/v1/account/summary"),
  getAccountBalance: <T>() => apiGet<T>("/api/v1/account/balance"),
  getAccountPositions: <T>(params?: { symbol?: string }) => apiGet<T>("/api/v1/account/positions", params),

  // --- Scheduler ---
  getSchedulerState: <T>() => apiGet<T>("/api/v1/scheduler/state"),
  runSchedulerOnce: <T>() => apiPost<T>("/api/v1/scheduler/run"),

  // --- Monitor ---
  getMonitorState: <T>() => apiGet<T>("/api/v1/monitor/state"),
  runMonitorOnce: <T>() => apiPost<T>("/api/v1/monitor/run"),

  // --- Auth ---
  login: <T>(body: { username: string; password: string }) => apiPost<T>("/api/v1/auth/login", body),
  register: <T>(body: { username: string; password: string }) => apiPost<T>("/api/v1/auth/register", body),
  getMe: <T>() => apiGet<T>("/api/v1/auth/me"),
  changePassword: <T>(body: { old_password: string; new_password: string }) => apiPut<T>("/api/v1/auth/password", body),

  // --- Credentials ---
  listCredentials: <T>() => apiGet<T>("/api/v1/credentials"),
  addCredential: <T>(body: { label: string; exchange: string; api_key: string; api_secret: string }) => apiPost<T>("/api/v1/credentials", body),
  deleteCredential: <T>(keyId: string) => apiDelete<T>(`/api/v1/credentials/${encodeURIComponent(keyId)}`),
  activateCredential: <T>(keyId: string) => apiPost<T>(`/api/v1/credentials/${encodeURIComponent(keyId)}/activate`),
  getActiveCredential: <T>() => apiGet<T>("/api/v1/credentials/active"),

  // --- Trading ---
  getTradingSymbols: <T>() => apiGet<T>("/api/v1/trading/symbols"),
  previewOrder: <T>(body: { symbol: string; side: string; notional: number; mode: string }) => apiPost<T>("/api/v1/trading/preview", body),
  executeOrder: <T>(body: { symbol: string; side: string; notional: number; mode: string }) => apiPost<T>("/api/v1/trading/execute", body),
};
