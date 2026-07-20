import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RequirementBadge } from "../components/RequirementBadge";

test("does not expose internal requirement links in the public demo UI", () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <RequirementBadge id="2.3" />
    </MemoryRouter>
  );

  expect(screen.queryByRole("link", { name: /需求/ })).not.toBeInTheDocument();
});
