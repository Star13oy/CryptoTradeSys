import { screen, waitFor } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";
import { renderWithProviders } from "./render-with-providers";

test("scan page renders an explicit error state when the request fails", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: false,
      status: 503,
    }) as Response) as typeof fetch;

  renderWithProviders(<OpportunityScanPage />);

  await waitFor(() => expect(screen.getByText("扫描服务暂时不可用")).toBeTruthy());
});
