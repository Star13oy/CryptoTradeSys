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

type HedgeOverviewParams = {
  exposure_limit_bps?: number;
};

type HedgeRebalancePlanParams = {
  exposure_limit_bps?: number;
};

type ExecutionSummaryParams = {
  limit_incidents?: number;
};

export const apiClient = {
  getHedgeOverview: <T>(params?: HedgeOverviewParams) => apiGet<T>("/api/v1/algo/hedge/overview", params),
  getHedgeRebalancePlan: <T>(tradeId: string, params?: HedgeRebalancePlanParams) =>
    apiGet<T>(`/api/v1/algo/hedge/rebalance-plan/${encodeURIComponent(tradeId)}`, params),
  getExecutionSummary: <T>(params?: ExecutionSummaryParams) => apiGet<T>("/api/v1/algo/execution/summary", params),
};
