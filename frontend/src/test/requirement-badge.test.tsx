import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RequirementBadge } from "../components/RequirementBadge";

test("links a feature to its canonical requirement row", () => {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <RequirementBadge id="2.3" />
    </MemoryRouter>
  );

  expect(screen.getByRole("link", { name: "需求 2.3" })).toHaveAttribute(
    "href",
    "/requirements?id=2.3"
  );
});
