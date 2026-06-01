import { describe, expect, it } from "vitest";
import { buildTree, shortName } from "./tree";
import { reports, tabs } from "./constants";

describe("dashboard tree utilities", () => {
  it("builds a nested file tree from repository paths", () => {
    const tree = buildTree([
      { relative_path: "backend/repomind/main.py" },
      { relative_path: "frontend/app/page.tsx" }
    ]);

    expect(tree.children.backend.children.repomind.children["main.py"].file).toBe(true);
    expect(tree.children.frontend.children.app.children["page.tsx"].file).toBe(true);
  });

  it("keeps compact names stable for graph labels", () => {
    expect(shortName("backend/repomind/main.py::route")).toBe("repomind/main.py");
  });

  it("exposes enterprise report and navigation entries", () => {
    expect(reports).toContain("SECURITY.sarif");
    expect(reports).toContain("EXECUTIVE_SUMMARY.html");
    expect(tabs).toContain("Architecture");
  });
});
