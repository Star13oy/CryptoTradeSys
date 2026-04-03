import { render, screen } from "@testing-library/react";

import { OpportunityScanPage } from "../pages/opportunity-scan/page";

test("scan page renders the Chinese title", () => {
  render(<OpportunityScanPage />);
  expect(screen.getByText("机会扫描页")).toBeTruthy();
});
