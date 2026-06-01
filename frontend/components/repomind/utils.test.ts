import { describe, expect, it } from "vitest";
import { asScore, citationLineRange, executiveScore, reportSections, riskLevel, splitChangedFiles } from "./utils";

describe("premium dashboard utilities", () => {
  it("normalizes scores and risk labels", () => {
    expect(asScore(144)).toBe(100);
    expect(asScore(-12)).toBe(0);
    expect(riskLevel(88)).toBe("Low");
    expect(riskLevel(61)).toBe("Elevated");
  });

  it("computes executive score from repository score signals", () => {
    expect(executiveScore({ scores: { security: 80, maintainability: 70, production_readiness: 90, cto: 60 } })).toBe(75);
  });

  it("parses markdown into executive report sections", () => {
    const sections = reportSections("# CTO Review\nStrong.\n## Risks\nOne issue.");
    expect(sections).toEqual([
      { title: "CTO Review", body: "Strong." },
      { title: "Risks", body: "One issue." }
    ]);
  });

  it("parses changed files and citation ranges", () => {
    expect(splitChangedFiles("a.ts\n b.py, c.go ")).toEqual(["a.ts", "b.py", "c.go"]);
    expect(citationLineRange({ start_line: 10, end_line: 12 })).toBe(":10-12");
    expect(citationLineRange({ start_line: 7 })).toBe(":7");
  });
});
