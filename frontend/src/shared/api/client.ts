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
  const response = await fetch(`${path}${buildQueryString(params)}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string): Promise<T> {
  const response = await fetch(path, { method: "POST" });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

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
};
