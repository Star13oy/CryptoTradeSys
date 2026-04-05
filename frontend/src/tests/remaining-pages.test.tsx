import { screen } from "@testing-library/react";

import { AuditLogCenterPage } from "../pages/audit-log-center/page";
import { BacktestLabPage } from "../pages/backtest-lab/page";
import { ModelWorkbenchPage } from "../pages/model-workbench/page";
import { PositionMonitorPage } from "../pages/position-monitor/page";
import { RiskCenterPage } from "../pages/risk-center/page";
import { renderWithProviders } from "./render-with-providers";

test("position monitor page renders stitch anchors", () => {
  renderWithProviders(<PositionMonitorPage />);

  expect(screen.getByText("持仓监控")).toBeTruthy();
  expect(screen.getByText("未实现收益 (uPnL)")).toBeTruthy();
  expect(screen.getByText("实时风险热图")).toBeTruthy();
});

test("risk center page renders stitch anchors", () => {
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
