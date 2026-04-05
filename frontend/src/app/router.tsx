import { createBrowserRouter } from "react-router-dom";

import { AuditLogCenterPage } from "../pages/audit-log-center/page";
import { BacktestLabPage } from "../pages/backtest-lab/page";
import { DashboardPage } from "../pages/dashboard/page";
import { ModelWorkbenchPage } from "../pages/model-workbench/page";
import { OpportunityScanPage } from "../pages/opportunity-scan/page";
import { PositionMonitorPage } from "../pages/position-monitor/page";
import { RiskCenterPage } from "../pages/risk-center/page";

export const router = createBrowserRouter([
  { path: "/", element: <DashboardPage /> },
  { path: "/scan", element: <OpportunityScanPage /> },
  { path: "/positions", element: <PositionMonitorPage /> },
  { path: "/risk", element: <RiskCenterPage /> },
  { path: "/backtest", element: <BacktestLabPage /> },
  { path: "/models", element: <ModelWorkbenchPage /> },
  { path: "/audit", element: <AuditLogCenterPage /> },
]);
