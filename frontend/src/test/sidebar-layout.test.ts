import { expect, test } from "vitest";
import css from "../styles.css?raw";

test("keeps the sidebar model mode visible within the viewport", () => {
  expect(css).toContain(".sidebar { position: fixed;");
  expect(css).toContain("top: 54px;");
  expect(css).toContain("bottom: 0;");
  expect(css).toContain("width: 212px;");
});

test("keeps the top navigation visible while scrolling", () => {
  expect(css).toContain(".topbar {\n  position: fixed;");
  expect(css).toContain("top: 0;");
  expect(css).toContain("left: 0;");
  expect(css).toContain("right: 0;");
  expect(css).toContain("z-index: 40;");
});

test("offsets the main content for fixed chrome", () => {
  expect(css).toContain(".platform-body {");
  expect(css).toContain("padding-top: 54px;");
  expect(css).toContain("grid-template-columns: 212px minmax(0, 1fr);");
  expect(css).toContain(".page-canvas { grid-column: 2;");
});
