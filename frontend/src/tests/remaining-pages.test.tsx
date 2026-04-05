import { screen } from "@testing-library/react";

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
  renderWithProviders(<BacktestLabPage />);

  expect(screen.getByText("回测实验室")).toBeTruthy();
  expect(screen.getByText("策略配置")).toBeTruthy();
  expect(screen.getByText("历史回测记录")).toBeTruthy();
});

test("model workbench page renders stitch anchors", () => {
  renderWithProviders(<ModelWorkbenchPage />);

  expect(screen.getByText("模型工作台")).toBeTruthy();
  expect(screen.getByText("模型库 (Library)")).toBeTruthy();
  expect(screen.getByText("部署清单 (Checklist)")).toBeTruthy();
});

test("audit log center page renders stitch anchors", () => {
  renderWithProviders(<AuditLogCenterPage />);

  expect(screen.getByText("审计与日志中心")).toBeTruthy();
  expect(screen.getByText("近期核心事件链路")).toBeTruthy();
  expect(screen.getByText("详细审计日志")).toBeTruthy();
});
