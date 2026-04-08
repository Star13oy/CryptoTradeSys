import { fireEvent, screen, waitFor } from "@testing-library/react";

import { PositionMonitorPage } from "../pages/position-monitor/page";
import { renderWithProviders } from "./render-with-providers";

test("position monitor page loads hedge overview and rebalance plan", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.startsWith("/api/v1/algo/hedge/overview")) {
      return {
        ok: true,
        json: async () => ({
          generated_at: "2026-04-05T12:00:00Z",
          exposure_limit_bps: 50,
          active_trade_count: 1,
          healthy_count: 0,
          monitoring_count: 0,
          rebalance_required_count: 1,
          recovery_required_count: 0,
          items: [
            {
              trade_id: "trade-1",
              mode: "live",
              symbol: "BTCUSDT",
              status: "hedged",
              health: "rebalance_required",
              opened_at: "2026-04-05T11:00:00Z",
              spot_notional: 10000,
              perp_notional: 9800,
              net_exposure: 200,
              exposure_bps: 200,
              latest_event_type: "execution.recovery.required",
              latest_event_summary: "Exposure drift detected",
              latest_event_severity: "warning",
            },
          ],
        }),
      } as Response;
    }

    if (url.startsWith("/api/v1/algo/hedge/rebalance-plan/trade-1")) {
      return {
        ok: true,
        json: async () => ({
          trade_id: "trade-1",
          symbol: "BTCUSDT",
          status: "hedged",
          health: "rebalance_required",
          exposure_limit_bps: 50,
          net_exposure: 200,
          exposure_bps: 200,
          recommended_action: "increase_perp_hedge",
          suggested_perp_notional_delta: 200,
          estimated_post_rebalance_exposure_bps: 0,
          notes: "Rebalance now",
        }),
      } as Response;
    }

    if (url === "/api/v1/algo/hedge/worker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: false,
          interval_seconds: 30,
          limit: 3,
          exposure_limit_bps: 50,
          total_runs: 5,
          total_failed_runs: 1,
          total_executed_rebalances: 4,
          last_attempted_count: 2,
          last_executed_count: 1,
          last_skipped_count: 1,
          last_failed_count: 0,
          last_success_at: "2026-04-08T12:05:00Z",
          last_error: null,
        }),
      } as Response;
    }

    if (url === "/api/v1/algo/hedge/worker/run") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: true,
          interval_seconds: 30,
          limit: 3,
          exposure_limit_bps: 50,
          total_runs: 6,
          total_failed_runs: 1,
          total_executed_rebalances: 5,
          last_attempted_count: 1,
          last_executed_count: 1,
          last_skipped_count: 0,
          last_failed_count: 0,
          last_success_at: "2026-04-08T12:06:00Z",
          last_error: null,
        }),
      } as Response;
    }

    return {
      ok: false,
      status: 404,
      json: async () => ({}),
    } as Response;
  });
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  renderWithProviders(<PositionMonitorPage />);

  await waitFor(() => expect(screen.getByText("BTC/USDT")).toBeTruthy());
  await waitFor(() => expect(screen.getAllByText("increase_perp_hedge").length).toBeGreaterThan(0));
  expect(screen.getAllByText("Auto Hedge Rebalance").length).toBeGreaterThan(0);
  expect(screen.getByText(/累计执行 4 次/)).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/overview?exposure_limit_bps=50");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-plan/trade-1?exposure_limit_bps=50");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/worker");

  fireEvent.click(screen.getByText("运行再平衡"));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/worker/run", { method: "POST" }));
});

test("position monitor page enables single trade rebalance for recommended hedge increase", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.startsWith("/api/v1/algo/hedge/overview")) {
      return {
        ok: true,
        json: async () => ({
          generated_at: "2026-04-05T12:00:00Z",
          exposure_limit_bps: 50,
          active_trade_count: 1,
          healthy_count: 0,
          monitoring_count: 0,
          rebalance_required_count: 1,
          recovery_required_count: 0,
          items: [
            {
              trade_id: "trade-1",
              mode: "live",
              symbol: "BTCUSDT",
              status: "hedged",
              health: "rebalance_required",
              opened_at: "2026-04-05T11:00:00Z",
              spot_notional: 10000,
              perp_notional: 9800,
              net_exposure: 200,
              exposure_bps: 200,
              latest_event_type: "execution.recovery.required",
              latest_event_summary: "Exposure drift detected",
              latest_event_severity: "warning",
            },
          ],
        }),
      } as Response;
    }

    if (url.startsWith("/api/v1/algo/hedge/rebalance-plan/trade-1")) {
      return {
        ok: true,
        json: async () => ({
          trade_id: "trade-1",
          symbol: "BTCUSDT",
          status: "hedged",
          health: "rebalance_required",
          exposure_limit_bps: 50,
          net_exposure: 200,
          exposure_bps: 200,
          recommended_action: "increase_perp_hedge",
          suggested_perp_notional_delta: 200,
          estimated_post_rebalance_exposure_bps: 0,
          notes: "Rebalance now",
        }),
      } as Response;
    }

    if (url === "/api/v1/algo/hedge/rebalance-auto/trade-1" && init?.method === "POST") {
      return {
        ok: true,
        json: async () => ({ trade_id: "trade-1", executed: true }),
      } as Response;
    }

    if (url === "/api/v1/algo/hedge/worker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: false,
          interval_seconds: 30,
          limit: 3,
          exposure_limit_bps: 50,
          total_runs: 5,
          total_failed_runs: 1,
          total_executed_rebalances: 4,
          last_attempted_count: 2,
          last_executed_count: 1,
          last_skipped_count: 1,
          last_failed_count: 0,
          last_success_at: "2026-04-08T12:05:00Z",
          last_error: null,
        }),
      } as Response;
    }

    return {
      ok: false,
      status: 404,
      json: async () => ({}),
    } as Response;
  });
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  renderWithProviders(<PositionMonitorPage />);

  await waitFor(() => expect(screen.getByText("BTC/USDT")).toBeTruthy());
  await waitFor(() => expect(screen.getAllByText("increase_perp_hedge").length).toBeGreaterThan(0));
  const enabledButton = screen.getByRole("button", { name: "执行再平衡" });
  expect((enabledButton as HTMLButtonElement).disabled).toBe(false);

  fireEvent.click(screen.getByRole("button", { name: "执行再平衡" }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-auto/trade-1", { method: "POST" }));
});

test("position monitor page disables single trade rebalance when action is not supported", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.startsWith("/api/v1/algo/hedge/overview")) {
      return {
        ok: true,
        json: async () => ({
          generated_at: "2026-04-05T12:00:00Z",
          exposure_limit_bps: 50,
          active_trade_count: 1,
          healthy_count: 1,
          monitoring_count: 0,
          rebalance_required_count: 0,
          recovery_required_count: 0,
          items: [
            {
              trade_id: "trade-2",
              mode: "live",
              symbol: "ETHUSDT",
              status: "hedged",
              health: "healthy",
              opened_at: "2026-04-05T11:00:00Z",
              spot_notional: 10000,
              perp_notional: 10010,
              net_exposure: -10,
              exposure_bps: 10,
              latest_event_type: null,
              latest_event_summary: null,
              latest_event_severity: null,
            },
          ],
        }),
      } as Response;
    }

    if (url.startsWith("/api/v1/algo/hedge/rebalance-plan/trade-2")) {
      return {
        ok: true,
        json: async () => ({
          trade_id: "trade-2",
          symbol: "ETHUSDT",
          status: "hedged",
          health: "healthy",
          exposure_limit_bps: 50,
          net_exposure: -10,
          exposure_bps: 10,
          recommended_action: "monitor_only",
          suggested_perp_notional_delta: 0,
          estimated_post_rebalance_exposure_bps: 10,
          notes: "No manual execution available",
        }),
      } as Response;
    }

    if (url === "/api/v1/algo/hedge/worker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: false,
          interval_seconds: 30,
          limit: 3,
          exposure_limit_bps: 50,
          total_runs: 5,
          total_failed_runs: 1,
          total_executed_rebalances: 4,
          last_attempted_count: 2,
          last_executed_count: 1,
          last_skipped_count: 1,
          last_failed_count: 0,
          last_success_at: "2026-04-08T12:05:00Z",
          last_error: null,
        }),
      } as Response;
    }

    return {
      ok: false,
      status: 404,
      json: async () => ({}),
    } as Response;
  });
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  renderWithProviders(<PositionMonitorPage />);

  await waitFor(() => expect(screen.getByText("ETH/USDT")).toBeTruthy());

  const disabledButton = screen.getByRole("button", { name: "执行再平衡" });
  expect((disabledButton as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(disabledButton);
  expect(fetchMock).not.toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-auto/trade-2", expect.anything());
});
