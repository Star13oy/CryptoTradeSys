import { fireEvent, screen, waitFor } from "@testing-library/react";

import { RiskCenterPage } from "../pages/risk-center/page";
import { renderWithProviders } from "./render-with-providers";

test("risk center page loads execution summary", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/safety/state") {
      return {
        ok: true,
        json: async () => ({
          frozen: false,
          new_positions_allowed: true,
          reduce_only_trades: [],
          paused_trades: [],
          updated_at: "2026-04-05T12:00:00Z",
        }),
      } as Response;
    }
    if (url === "/api/v1/algo/compensation/worker/run") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: true,
          interval_seconds: 45,
          limit: 2,
          exposure_limit_bps: 35,
          total_runs: 4,
          total_failed_runs: 0,
          total_executed_actions: 3,
          last_attempted_count: 1,
          last_executed_count: 1,
          last_skipped_count: 0,
          last_failed_count: 0,
          last_success_at: "2026-04-05T11:30:00Z",
          last_error: null,
        }),
      } as Response;
    }

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

    if (url === "/api/v1/algo/execution/circuit-breaker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          is_open: true,
          failure_threshold: 2,
          cooldown_seconds: 300,
          consecutive_failures: 2,
          last_failure_at: "2026-04-05T11:25:00Z",
          opened_at: "2026-04-05T11:25:00Z",
          resume_at: "2026-04-05T11:30:00Z",
          last_reason: "live perp leg failed",
          last_trade_id: "recover-1",
          updated_at: "2026-04-05T11:25:00Z",
        }),
      } as Response;
    }

    if (url === "/api/v1/algo/recovery/worker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: false,
          interval_seconds: 30,
          limit: 3,
          total_runs: 7,
          total_failed_runs: 1,
          total_executed_recoveries: 4,
          last_attempted_count: 1,
          last_executed_count: 1,
          last_skipped_count: 0,
          last_success_at: "2026-04-05T11:28:00Z",
          last_error: null,
        }),
      } as Response;
    }

    if (url === "/api/v1/algo/compensation/worker") {
      return {
        ok: true,
        json: async () => ({
          enabled: true,
          configured: true,
          running: false,
          interval_seconds: 45,
          limit: 2,
          exposure_limit_bps: 35,
          total_runs: 3,
          total_failed_runs: 0,
          total_executed_actions: 2,
          last_attempted_count: 1,
          last_executed_count: 1,
          last_skipped_count: 0,
          last_failed_count: 0,
          last_success_at: "2026-04-05T11:29:00Z",
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

    if (url.startsWith("/api/v1/algo/compensation/plans")) {
      return {
        ok: true,
        json: async () => ({
          plans: [
            {
              trade_id: "comp-1",
              symbol: "BTCUSDT",
              mode: "live",
              local_status: "hedged",
              recommended_action: "sync_exchange_reports",
              priority: "critical",
              actionable: true,
              reason: "missing exchange reports",
              details: { missing_order_ids: ["perp-1"] },
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
  expect(screen.getAllByText("Live Execution Circuit Breaker").length).toBeGreaterThan(0);
  expect(screen.getByText("OPEN")).toBeTruthy();
  expect(screen.getAllByText("Recovery Worker").length).toBeGreaterThan(0);
  expect(screen.getAllByText("IDLE").length).toBeGreaterThan(0);
  await waitFor(() => expect(screen.getByText("recon-1")).toBeTruthy());
  expect(screen.getAllByText("BTCUSDT").length).toBeGreaterThan(0);
  expect(screen.getByText("spot-1, perp-2")).toBeTruthy();
  expect(screen.getByText("inspect_exchange")).toBeTruthy();
  expect(screen.getByText("是")).toBeTruthy();
  expect(screen.getByText("执行补偿计划")).toBeTruthy();
  expect(screen.getByText("comp-1")).toBeTruthy();
  expect(screen.getByText("sync_exchange_reports")).toBeTruthy();
  expect(screen.getByText("critical")).toBeTruthy();
  expect(screen.getByText("missing exchange reports")).toBeTruthy();
  expect(screen.getByText("自动对账 Worker")).toBeTruthy();
  expect(screen.getByText("RUNNING")).toBeTruthy();
  expect(screen.getByText("累计同步 8 条回报")).toBeTruthy();
  expect(screen.getAllByText("Compensation Worker").length).toBeGreaterThan(0);
  expect(screen.getByText(/累计执行 2 个动作/)).toBeTruthy();
  expect(screen.getByText(/连续失败 2/)).toBeTruthy();
  expect(screen.getByText(/累计恢复 4 笔/)).toBeTruthy();

  // Check that all expected endpoints were called (order may vary with React Query)
  const calledUrls = fetchMock.mock.calls.map((call: unknown[]) => String(call[0]));
  expect(calledUrls).toContain("/api/v1/safety/state");
  expect(calledUrls).toContain("/api/v1/algo/execution/summary?limit_incidents=6");
  expect(calledUrls).toContain("/api/v1/algo/reconciliation/candidates");
  expect(calledUrls).toContain("/api/v1/algo/reconciliation/worker");
  expect(calledUrls).toContain("/api/v1/algo/execution/circuit-breaker");
  expect(calledUrls).toContain("/api/v1/algo/recovery/worker");
  expect(calledUrls).toContain("/api/v1/algo/compensation/worker");
  expect(calledUrls).toContain("/api/v1/algo/compensation/plans?only_actionable=true&exposure_limit_bps=50");

  fireEvent.click(screen.getByText("运行补偿"));
  await waitFor(() => {
    const postCalls = fetchMock.mock.calls.filter((call: unknown[]) => {
      const url = String(call[0]);
      const opts = call[1] as Record<string, unknown> | undefined;
      return url === "/api/v1/algo/compensation/worker/run" && opts?.method === "POST";
    });
    expect(postCalls.length).toBeGreaterThan(0);
  });
});
