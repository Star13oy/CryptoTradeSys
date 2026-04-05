import { apiClient } from "../shared/api/client";

test("api client requests hedge overview with exposure_limit_bps", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ items: [] }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getHedgeOverview({ exposure_limit_bps: 75 });

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/overview?exposure_limit_bps=75");
});

test("api client requests rebalance plan with encoded trade_id", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ trade_id: "trade/a b" }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getHedgeRebalancePlan("trade/a b", { exposure_limit_bps: 60 });

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-plan/trade%2Fa%20b?exposure_limit_bps=60");
});

test("api client requests execution summary with incident limit", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ status_counts: [] }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getExecutionSummary({ limit_incidents: 8 });

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/execution/summary?limit_incidents=8");
});
