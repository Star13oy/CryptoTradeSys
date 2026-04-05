import { screen } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";
import { renderWithProviders } from "./render-with-providers";

test("dashboard page renders the Chinese title", () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        generated_at: "2026-04-03T12:00:00Z",
        account_health: { mode: "paper", exchange: "binance", risk_state: "normal" },
        market_status: {
          spot_source: "bookTicker",
          perp_source: "bookTicker",
          degraded: false,
          requested_symbols: 12,
          quoted_symbols: 12,
        },
        top_opportunities: [],
        paper_positions: [],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<DashboardPage />);
  expect(screen.getByText("QUANT_ADMIN")).toBeTruthy();
  expect(screen.getByText("OBSIDIAN LEDGER")).toBeTruthy();
  expect(screen.getByText("机会扫描器 (实时)")).toBeTruthy();
  expect(screen.getByText("风险状态中心")).toBeTruthy();
});
