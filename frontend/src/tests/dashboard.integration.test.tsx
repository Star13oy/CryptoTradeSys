import { screen, waitFor } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";
import { renderWithProviders } from "./render-with-providers";

test("dashboard page shows loading state before rendering a fetched opportunity row", async () => {
  let resolveFetch: ((value: Response) => void) | undefined;

  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    })) as typeof fetch;

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

  await waitFor(() => expect(screen.getByText("XRPUSDT")).toBeTruthy());
});
