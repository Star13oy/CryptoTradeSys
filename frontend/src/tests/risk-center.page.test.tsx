import { screen, waitFor } from "@testing-library/react";

import { RiskCenterPage } from "../pages/risk-center/page";
import { renderWithProviders } from "./render-with-providers";

test("risk center page loads execution summary", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (!url.startsWith("/api/v1/algo/execution/summary")) {
      return {
        ok: false,
        status: 404,
        json: async () => ({}),
      } as Response;
    }

    return {
      ok: true,
      json: async () => ({
        generated_at: "2026-04-05T12:00:00Z",
        status_counts: [
          { status: "hedged", count: 3 },
          { status: "failed", count: 2 },
          { status: "recovery_pending", count: 1 },
        ],
        recovery_queue: [
          {
            trade_id: "recover-1",
            mode: "live",
            symbol: "ETHUSDT",
            status: "recovery_pending",
            opened_at: "2026-04-05T11:20:00Z",
            net_exposure: 120,
            spot_notional: 10000,
            perp_notional: 9880,
            latest_event_type: "execution.recovery.required",
            latest_event_summary: "Need manual recovery",
            latest_event_severity: "error",
          },
        ],
        recent_incidents: [
          {
            event_id: "evt-1",
            event_type: "execution.recovery.required",
            severity: "error",
            occurred_at: "2026-04-05T11:21:00Z",
            summary: "Recovery required",
            trade_id: "recover-1",
          },
          {
            event_id: "evt-2",
            event_type: "execution.slippage.warn",
            severity: "warning",
            occurred_at: "2026-04-05T11:19:00Z",
            summary: "Slippage warning",
            trade_id: "recover-2",
          },
        ],
      }),
    } as Response;
  });
  (globalThis as { fetch: typeof fetch }).fetch = fetchMock as typeof fetch;

  renderWithProviders(<RiskCenterPage />);

  await waitFor(() => expect(screen.getByText("GUARDED")).toBeTruthy());
  expect(screen.getByText("Recovery required")).toBeTruthy();
  expect(screen.getByText("execution.recovery.required")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/execution/summary?limit_incidents=6");
});
