import { render, screen, waitFor } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";

test("scan page renders fetched rows", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        rows: [{ symbol: "ADAUSDT", score: 7, risk_tag: "normal", net_edge_bps: 0.72 }],
      }),
    }) as Response) as typeof fetch;

  render(<OpportunityScanPage />);

  await waitFor(() => expect(screen.getByText("ADAUSDT")).toBeTruthy());
});
