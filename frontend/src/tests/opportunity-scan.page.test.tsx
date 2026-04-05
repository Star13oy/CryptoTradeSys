import { screen, waitFor } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";
import { renderWithProviders } from "./render-with-providers";

test("scan page renders the Chinese title", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        generated_at: "2026-04-03T12:00:00Z",
        applied_filters: {
          limit: 25,
          positive_funding_only: true,
          min_net_edge_bps: null,
        },
        market_status: {
          spot_source: "depth",
          perp_source: "bookTicker",
          degraded: true,
          requested_symbols: 8,
          quoted_symbols: 8,
        },
        total_matches: 0,
        rows: [],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<OpportunityScanPage />);
  expect(screen.getByText("QUANT_ADMIN")).toBeTruthy();
  expect(screen.getByText("机会扫描器 (Scanner)")).toBeTruthy();
  expect(screen.getByText("交易对搜索")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("BTC/USDT 套利分析")).toBeTruthy());
});
