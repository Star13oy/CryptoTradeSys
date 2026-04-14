import { apiClient } from "../shared/api/client";

// Clear localStorage to ensure no auth token interferes with tests
beforeEach(() => {
  localStorage.clear();
});

test("api client requests hedge overview with exposure_limit_bps", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ items: [] }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getHedgeOverview({ exposure_limit_bps: 75 });

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/overview?exposure_limit_bps=75", { headers: {} });
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

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-plan/trade%2Fa%20b?exposure_limit_bps=60", { headers: {} });
});

test("api client requests hedge rebalance worker status", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ enabled: false }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getHedgeRebalanceWorker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/worker", { headers: {} });
});

test("api client posts hedge rebalance worker run", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ running: true }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.runHedgeRebalanceWorker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/worker/run", { headers: {}, method: "POST" });
});

test("api client posts single trade hedge rebalance execution", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ trade_id: "trade-1" }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.runHedgeRebalanceAuto("trade-1");

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-auto/trade-1", { headers: {}, method: "POST" });
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

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/execution/summary?limit_incidents=8", { headers: {} });
});

test("api client requests reconciliation candidates", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ candidates: [] }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getReconciliationCandidates();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/reconciliation/candidates", { headers: {} });
});

test("api client requests compensation plans", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ plans: [] }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getCompensationPlans({ only_actionable: true, exposure_limit_bps: 75 });

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/compensation/plans?only_actionable=true&exposure_limit_bps=75", { headers: {} });
});

test("api client requests compensation worker status", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ enabled: false }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.getCompensationWorker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/compensation/worker", { headers: {} });
});

test("api client posts compensation worker run", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ running: true }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.runCompensationWorker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/compensation/worker/run", { headers: {}, method: "POST" });
});

test("api client posts recovery worker run", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ running: true }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.runRecoveryWorker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/recovery/worker/run", { headers: {}, method: "POST" });
});

test("api client posts reconciliation worker run", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ running: true }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.runReconciliationWorker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/reconciliation/worker/run", { headers: {}, method: "POST" });
});

test("api client posts execution circuit breaker reset", async () => {
  const fetchMock = vi.fn(async () =>
    ({
      ok: true,
      json: async () => ({ is_open: false }),
    }) as Response
  );
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  await apiClient.resetExecutionCircuitBreaker();

  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/execution/circuit-breaker/reset", { headers: {}, method: "POST" });
});
