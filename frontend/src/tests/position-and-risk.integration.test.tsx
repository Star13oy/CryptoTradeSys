import { screen, waitFor } from "@testing-library/react";

import { PositionMonitorPage } from "../pages/position-monitor/page";
import { RiskCenterPage } from "../pages/risk-center/page";
import { renderWithProviders } from "./render-with-providers";

test("position monitor page loads hedge overview and rebalance plan", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/v1/safety")) {
      return { ok: true, json: async () => ({ frozen: false, new_positions_allowed: true, reduce_only_trades: [], paused_trades: [], updated_at: "2026-04-05T12:00:00Z" }) } as Response;
    }
    if (url.includes("/api/v1/algo/hedge/overview")) {
      return {
        ok: true,
        json: async () => ({
          generated_at: "2026-04-05T12:00:00Z",
          exposure_limit_bps: 50,
          active_trade_count: 1,
          healthy_count: 0,
          monitoring_count: 0,
          rebalance_required_count: 1,
          recovery_required_count: 0,
          items: [
            {
              trade_id: "pos-1",
              mode: "live",
              symbol: "BTCUSDT",
              status: "hedged",
              health: "rebalance_required",
              opened_at: "2026-04-05T12:00:00Z",
              spot_notional: 15000,
              perp_notional: 14880,
              net_exposure: 120,
              exposure_bps: 80,
              latest_event_type: "execution.completed",
              latest_event_summary: "Hedge open completed",
              latest_event_severity: "info",
            },
          ],
        }),
      } as Response;
    }

    return {
      ok: true,
      json: async () => ({
        trade_id: "pos-1",
        symbol: "BTCUSDT",
        status: "hedged",
        health: "rebalance_required",
        exposure_limit_bps: 50,
        net_exposure: 120,
        exposure_bps: 80,
        recommended_action: "increase_perp_hedge",
        suggested_perp_notional_delta: 120,
        estimated_post_rebalance_exposure_bps: 0,
        notes: "Increase perp hedge to neutralize exposure.",
      }),
    } as Response;
  }) as typeof fetch;

  renderWithProviders(<PositionMonitorPage />);

  expect(screen.getByText("正在同步持仓监控数据")).toBeTruthy();

  await waitFor(() => expect(screen.getByText("BTC/USDT")).toBeTruthy());
  await waitFor(() => expect(screen.getAllByText("increase_perp_hedge").length).toBeGreaterThan(0));
});

test("risk center page loads execution summary and renders incident rows", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        generated_at: "2026-04-05T12:00:00Z",
        status_counts: [
          { status: "hedged", count: 2 },
          { status: "recovery_pending", count: 1 },
        ],
        recovery_queue: [
          {
            trade_id: "risk-1",
            mode: "live",
            symbol: "ETHUSDT",
            status: "recovery_pending",
            opened_at: "2026-04-05T12:00:00Z",
            net_exposure: 60,
            spot_notional: 10000,
            perp_notional: 9940,
            latest_event_type: "execution.recovery.required",
            latest_event_summary: "Recovery required after live open issue on ETHUSDT",
            latest_event_severity: "warning",
          },
        ],
        recent_incidents: [
          {
            event_id: "incident-1",
            event_type: "execution.recovery.required",
            severity: "warning",
            occurred_at: "2026-04-05T12:05:00Z",
            summary: "Recovery required after live open issue on ETHUSDT",
            trade_id: "risk-1",
          },
        ],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<RiskCenterPage />);

  expect(screen.getByText("正在同步执行风险摘要")).toBeTruthy();

  await waitFor(() => expect(screen.getByText("GUARDED")).toBeTruthy());
  await waitFor(() => expect(screen.getByText("execution.recovery.required")).toBeTruthy());
});
