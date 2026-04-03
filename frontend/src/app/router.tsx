import { createBrowserRouter } from "react-router-dom";

import { DashboardPage } from "../pages/dashboard/page";
import { OpportunityScanPage } from "../pages/opportunity-scan/page";

export const router = createBrowserRouter([
  { path: "/", element: <DashboardPage /> },
  { path: "/scan", element: <OpportunityScanPage /> },
]);
