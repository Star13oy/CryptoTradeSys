import { screen, waitFor } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";
import { renderWithProviders } from "./render-with-providers";

test("dashboard page renders the Chinese title", async () => {
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
        top_opportunities: [
          {
            symbol: "BTCUSDT",
            funding_rate: 0.0002,
            net_edge_bps: 1.84,
            score: 12.5,
            risk_tag: "normal",
            gross_edge_bps: 2.0,
            trading_cost_bps: 0.16,
            annualized_funding_rate_pct: 21.9,
            basis_bps: 1.17,
            projected_net_edge_bps: 11.84,
            payback_periods: 0.8,
            expected_hold_periods: 6,
            spot_bid: 59998,
            spot_ask: 60000,
            spot_mid: 59999,
            perp_bid: 60004,
            perp_ask: 60006,
            perp_mid: 60005,
            perp_spread_bps: 0.33,
            spot_spread_bps: 0.33,
          },
        ],
        paper_positions: [],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<DashboardPage />);
  expect(screen.getByText("QUANT_ADMIN")).toBeTruthy();
  expect(screen.getByText("OBSIDIAN LEDGER")).toBeTruthy();
  expect(screen.getByText("机会扫描器 (实时)")).toBeTruthy();
  expect(screen.getByText("风险状态中心")).toBeTruthy();
  expect(screen.getByText("实时行情脉冲")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("59998.00 / 60000.00")).toBeTruthy());
  expect(screen.getAllByText("BTCUSDT").length).toBeGreaterThan(0);
  expect(screen.getByText("59998.00 / 60000.00")).toBeTruthy();
  expect(screen.getByText("60004.00 / 60006.00")).toBeTruthy();
});
