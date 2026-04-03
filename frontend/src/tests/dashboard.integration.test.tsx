import { render, screen, waitFor } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";

test("dashboard page renders a fetched opportunity row", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        account_health: { mode: "paper", exchange: "binance", risk_state: "guarded" },
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
    }) as Response) as typeof fetch;

  render(<DashboardPage />);

  await waitFor(() => expect(screen.getByText("XRPUSDT")).toBeTruthy());
});
