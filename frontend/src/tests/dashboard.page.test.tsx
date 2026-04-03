import { render, screen } from "@testing-library/react";

import { DashboardPage } from "../pages/dashboard/page";

test("dashboard page renders the Chinese title", () => {
  render(<DashboardPage />);
  expect(screen.getByText("总览指挥台")).toBeTruthy();
});
