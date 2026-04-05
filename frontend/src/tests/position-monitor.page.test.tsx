import { screen, waitFor } from "@testing-library/react";

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
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/overview?exposure_limit_bps=50");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/hedge/rebalance-plan/trade-1?exposure_limit_bps=50");
});
