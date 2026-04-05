import { fireEvent, screen, waitFor } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";
import { renderWithProviders } from "./render-with-providers";

test("scan page refetches with typed filters when the operator changes the control bar", async () => {
  const calls: string[] = [];

  (globalThis as { fetch: typeof fetch }).fetch = (async (input) => {
    calls.push(String(input));

    return {
      ok: true,
      json: async () => ({
        generated_at: "2026-04-03T12:00:00Z",
        applied_filters: {
          limit: 25,
          positive_funding_only: true,
          min_net_edge_bps: calls.length > 1 ? 2 : null,
        },
        market_status: {
          spot_source: "bookTicker",
          perp_source: "bookTicker",
          degraded: false,
          requested_symbols: 12,
          quoted_symbols: 12,
        },
        total_matches: 1,
        rows: [
          {
            symbol: "ETHUSDT",
            score: 21,
            risk_tag: "normal",
            net_edge_bps: 2.1,
            funding_rate: 0.0004,
          },
        ],
      }),
    } as Response;
  }) as typeof fetch;

  renderWithProviders(<OpportunityScanPage />);

  await waitFor(() =>
    expect(calls[0]).toContain("/api/v1/scan/opportunities?limit=25&positive_funding_only=true")
  );

  fireEvent.change(screen.getByLabelText("收益阈值 (Annualized)"), {
    target: { value: "apy-20" },
  });

  await waitFor(() =>
    expect(
      calls.some(
        (call) =>
          call.includes("positive_funding_only=true") &&
          call.includes("min_net_edge_bps=2")
      )
    ).toBe(true)
  );
});
