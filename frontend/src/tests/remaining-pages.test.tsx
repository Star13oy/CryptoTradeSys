import { screen, waitFor } from "@testing-library/react";

import { AuditLogCenterPage } from "../pages/audit-log-center/page";
import { BacktestLabPage } from "../pages/backtest-lab/page";
import { ModelWorkbenchPage } from "../pages/model-workbench/page";
import { PositionMonitorPage } from "../pages/position-monitor/page";
import { RiskCenterPage } from "../pages/risk-center/page";
import { renderWithProviders } from "./render-with-providers";

test("position monitor page renders stitch anchors", () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
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
            trade_id: "test-position-1",
            mode: "live",
            symbol: "BTCUSDT",
            status: "hedged",
            health: "rebalance_required",
            opened_at: "2026-04-05T12:00:00Z",
            spot_notional: 15000,
            perp_notional: 14880,
            net_exposure: 120,
            exposure_bps: 80,
            latest_event_type: null,
            latest_event_summary: null,
            latest_event_severity: null,
          },
        ],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<PositionMonitorPage />);

  expect(screen.getByText("持仓监控")).toBeTruthy();
  expect(screen.getByText("净暴露敞口")).toBeTruthy();
  expect(screen.getByText("实时风险热图")).toBeTruthy();
});

test("risk center page renders stitch anchors", () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        generated_at: "2026-04-05T12:00:00Z",
        status_counts: [
          { status: "hedged", count: 2 },
          { status: "recovery_pending", count: 1 },
        ],
        recovery_queue: [],
        recent_incidents: [],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<RiskCenterPage />);

  expect(screen.getByText("风控中心")).toBeTruthy();
  expect(screen.getByText("风险阈值动态配置")).toBeTruthy();
  expect(screen.getByText("实时风险规则与告警")).toBeTruthy();
});

test("backtest lab page renders stitch anchors", () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({ datasets: [] }),
    }) as Response) as typeof fetch;

  renderWithProviders(<BacktestLabPage />);

  expect(screen.getByText("回测实验室")).toBeTruthy();
  expect(screen.getByText("策略配置")).toBeTruthy();
  expect(screen.getByText("历史回测记录")).toBeTruthy();
});

test("model workbench page renders stitch anchors", () => {
  let callIndex = 0;
  (globalThis as { fetch: typeof fetch }).fetch = (async () => {
    callIndex++;
    const responses: Record<number, unknown> = {
      1: { updated_at: "2026-04-05T12:00:00Z", active_package_id: "conservative", active_package_title: "保守方案", config: { score: { taker_fee_bps: 0.4, funding_periods_per_day: 3, expected_hold_periods: 6, basis_soft_limit_bps: 2.0, basis_guarded_bps: 8.0, payback_guarded_periods: 1.0, trading_cost_guarded_bps: 3.0, carry_weight: 20.0, annualized_weight: 0.15, cost_soft_limit_bps: 1.5, cost_penalty_weight: 1.0, basis_penalty_weight: 1.5 }, risk: { min_allow_score: 100, min_review_score: 10, min_allow_net_edge_bps: 4.0, min_allow_projected_edge_bps: 2.0, max_allow_basis_bps: 7.0, max_review_basis_bps: 100, max_allow_trading_cost_bps: 3.0, max_allow_payback_periods: 1.0 }, backtest: { notional_per_trade: 1000, min_score: 0, min_net_edge_bps: 0, top_k: 1, accept_reviewed: false } } },
      2: { generated_at: "2026-04-05T12:00:00Z", metrics: { trade_count: 0, win_rate: 0, avg_realized_pnl_bps: 0, avg_projected_edge_bps: 0, avg_projection_shortfall_bps: 0, max_drawdown_p95_bps: 0, slow_payback_rate: 0 }, current_state: {}, recommended_package_id: "conservative", packages: [{ package_id: "conservative", title: "保守方案", summary: "低风险", objective: "稳健", recommended: true, derived_from: null, reason_codes: [], config: {} }] },
      3: { samples: [] },
    };
    return { ok: true, json: async () => responses[callIndex] ?? {} } as Response;
  }) as typeof fetch;

  renderWithProviders(<ModelWorkbenchPage />);

  expect(screen.getByText("模型工作台")).toBeTruthy();
  expect(screen.getByText("模型库 (Library)")).toBeTruthy();
  expect(screen.getByText("部署清单 (Checklist)")).toBeTruthy();
});

test("audit log center page renders stitch anchors", async () => {
  (globalThis as { fetch: typeof fetch }).fetch = (async () =>
    ({
      ok: true,
      json: async () => ({
        events: [
          { event_id: "evt-1", event_type: "订单执行", severity: "info", source: "execution", occurred_at: "2026-04-05T12:45:01Z", summary: "BTC/USDT 限价买入 $64,210.50", payload: {}, tags: [] },
          { event_id: "evt-2", event_type: "风控扫描", severity: "warning", source: "risk", occurred_at: "2026-04-05T12:45:02Z", summary: "订单滑点率 0.12% - 安全", payload: {}, tags: [] },
        ],
      }),
    }) as Response) as typeof fetch;

  renderWithProviders(<AuditLogCenterPage />);

  expect(screen.getByText("审计与日志中心")).toBeTruthy();
  await waitFor(() => {
    expect(screen.getByText("近期核心事件链路")).toBeTruthy();
    expect(screen.getByText("详细审计日志")).toBeTruthy();
  });
});
