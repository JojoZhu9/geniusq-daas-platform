import { expect, test } from "vitest";
import css from "../styles.css?raw";

test("keeps the sidebar model mode visible within the viewport", () => {
  expect(css).toContain(".sidebar { position: sticky;");
  expect(css).toContain("height: calc(100vh - 54px);");
  expect(css).toContain("top: 54px;");
});

test("keeps the top navigation visible while scrolling", () => {
  expect(css).toContain(".topbar {\n  position: sticky;");
  expect(css).toContain("top: 0;");
  expect(css).toContain("z-index: 20;");
});
