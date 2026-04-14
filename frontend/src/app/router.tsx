import { createBrowserRouter, redirect } from "react-router-dom";

import { AuditLogCenterPage } from "../pages/audit-log-center/page";
import { BacktestLabPage } from "../pages/backtest-lab/page";
import { DashboardPage } from "../pages/dashboard/page";
import { ModelWorkbenchPage } from "../pages/model-workbench/page";
import { OpportunityScanPage } from "../pages/opportunity-scan/page";
import { PositionMonitorPage } from "../pages/position-monitor/page";
import { RiskCenterPage } from "../pages/risk-center/page";
import { LoginPage } from "../pages/login/page";
import { SettingsPage } from "../pages/settings/page";
import { TradingPage } from "../pages/trading/page";

function authLoader() {
  if (!localStorage.getItem("auth_token")) {
    return redirect("/login");
  }
  return null;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/", element: <DashboardPage />, loader: authLoader },
  { path: "/scan", element: <OpportunityScanPage />, loader: authLoader },
  { path: "/positions", element: <PositionMonitorPage />, loader: authLoader },
  { path: "/risk", element: <RiskCenterPage />, loader: authLoader },
  { path: "/backtest", element: <BacktestLabPage />, loader: authLoader },
  { path: "/models", element: <ModelWorkbenchPage />, loader: authLoader },
  { path: "/audit", element: <AuditLogCenterPage />, loader: authLoader },
  { path: "/settings", element: <SettingsPage />, loader: authLoader },
  { path: "/trade", element: <TradingPage />, loader: authLoader },
]);
