import { screen, waitFor } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";
import { renderWithProviders } from "./render-with-providers";

test("dashboard page shows loading state before rendering a fetched opportunity row", async () => {
  let resolveFetch: ((value: Response) => void) | undefined;

  (globalThis as { fetch: typeof fetch }).fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    // Account and safety endpoints return immediately
    if (url.includes("/api/v1/account")) {
      return { ok: true, json: async () => ({ balance: null, positions: [], active_position_count: 0, fetched_at: "2026-04-03T12:00:00Z" }) } as Response;
    }
    if (url.includes("/api/v1/safety")) {
      return { ok: true, json: async () => ({ frozen: false, new_positions_allowed: true, reduce_only_trades: [], paused_trades: [], updated_at: "2026-04-03T12:00:00Z" }) } as Response;
    }
    // Dashboard summary waits for manual resolve
    return new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
  }) as typeof fetch;

  renderWithProviders(<DashboardPage />);

  expect(screen.getByText("正在刷新指挥台数据")).toBeTruthy();

  resolveFetch?.({
    ok: true,
    json: async () => ({
      generated_at: "2026-04-03T12:00:00Z",
      account_health: { mode: "paper", exchange: "binance", risk_state: "guarded" },
      market_status: {
        spot_source: "bookTicker",
        perp_source: "depth",
        degraded: true,
        requested_symbols: 12,
        quoted_symbols: 10,
      },
      top_opportunities: [
        {
          symbol: "XRPUSDT",
          net_edge_bps: 0.7,
          score: 7,
          risk_tag: "normal",
          funding_rate: 0.0002,
        },
      ],
      paper_positions: [],
    }),
  } as Response);

  await waitFor(() => expect(screen.getAllByText("XRPUSDT").length).toBeGreaterThan(0));
});
