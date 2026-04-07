import { screen, waitFor } from "@testing-library/react";

import { RiskCenterPage } from "../pages/risk-center/page";
import { renderWithProviders } from "./render-with-providers";

test("risk center page loads execution summary", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/algo/reconciliation/worker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: true,
          interval_seconds: 30,
          limit: 5,
          total_runs: 4,
          total_failed_runs: 1,
          total_imported_reports: 8,
          last_imported_report_count: 2,
          last_synced_trade_count: 1,
          last_success_at: "2026-04-05T11:22:00Z",
          last_error: null,
        }),
      } as Response;
    }

    if (url.startsWith("/api/v1/algo/reconciliation/candidates")) {
      return {
        ok: true,
        json: async () => ({
          candidates: [
            {
              trade_id: "recon-1",
              symbol: "BTCUSDT",
              missing_order_ids: ["spot-1", "perp-2"],
              suggested_action: "inspect_exchange",
              needs_attention: true,
            },
          ],
        }),
      } as Response;
    }

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
  await waitFor(() => expect(screen.getByText("recon-1")).toBeTruthy());
  expect(screen.getByText("BTCUSDT")).toBeTruthy();
  expect(screen.getByText("spot-1, perp-2")).toBeTruthy();
  expect(screen.getByText("inspect_exchange")).toBeTruthy();
  expect(screen.getByText("是")).toBeTruthy();
  expect(screen.getByText("自动对账 Worker")).toBeTruthy();
  expect(screen.getByText("RUNNING")).toBeTruthy();
  expect(screen.getByText("累计同步 8 条回报")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/execution/summary?limit_incidents=6");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/reconciliation/candidates");
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/algo/reconciliation/worker");
});
