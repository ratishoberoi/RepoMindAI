import type { Citation, Finding, KnowledgeGraph, RepositorySummary, Severity } from "./types";

export function asScore(value: unknown, fallback = 0) {
  const score = typeof value === "number" && Number.isFinite(value) ? value : fallback;
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function executiveScore(summary: RepositorySummary | null | undefined) {
  const scores = summary?.scores ?? {};
  const values = [
    scores.cto,
    scores.security,
    scores.maintainability,
    scores.production_readiness,
    scores.ai_readiness
  ].filter((value): value is number => typeof value === "number");
  if (!values.length) return 0;
  return asScore(values.reduce((total, score) => total + score, 0) / values.length);
}

export function riskLevel(score: number) {
  if (score >= 85) return "Low";
  if (score >= 70) return "Guarded";
  if (score >= 50) return "Elevated";
  return "Critical";
}

export function scoreTone(score: number) {
  if (score >= 85) return "text-emerald-300 border-emerald-400/25 bg-emerald-400/10";
  if (score >= 70) return "text-cyan-200 border-cyan-400/25 bg-cyan-400/10";
  if (score >= 50) return "text-amber-200 border-amber-400/25 bg-amber-400/10";
  return "text-rose-200 border-rose-400/25 bg-rose-400/10";
}

export function severityTone(severity?: string) {
  const normalized = (severity ?? "info").toLowerCase() as Severity;
  if (normalized === "critical") return "text-rose-100 border-rose-400/40 bg-rose-500/15";
  if (normalized === "high") return "text-orange-100 border-orange-400/35 bg-orange-500/15";
  if (normalized === "medium") return "text-amber-100 border-amber-400/35 bg-amber-500/15";
  if (normalized === "low") return "text-emerald-100 border-emerald-400/30 bg-emerald-500/[0.12]";
  return "text-slate-200 border-white/10 bg-white/[0.04]";
}

export function compactNumber(value: unknown) {
  const number = typeof value === "number" && Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("en", { notation: number > 9999 ? "compact" : "standard" }).format(number);
}

export function topFindings(summary: RepositorySummary | null | undefined, limit = 5): Finding[] {
  const findings = [
    ...(summary?.security?.findings ?? []),
    ...(summary?.technical_debt?.findings ?? [])
  ];
  const rank: Record<string, number> = { critical: 5, high: 4, medium: 3, low: 2, info: 1 };
  return findings
    .sort((left, right) => (rank[(right.severity ?? "info").toLowerCase()] ?? 0) - (rank[(left.severity ?? "info").toLowerCase()] ?? 0))
    .slice(0, limit);
}

export function reportSections(markdown: string) {
  if (!markdown.trim()) return [];
  const sections: Array<{ title: string; body: string }> = [];
  let current = { title: "Executive Summary", body: "" };
  for (const line of markdown.split("\n")) {
    const heading = line.match(/^#{1,3}\s+(.+)/);
    if (heading) {
      if (current.body.trim()) sections.push({ ...current, body: current.body.trim() });
      current = { title: heading[1].trim(), body: "" };
    } else {
      current.body += `${line}\n`;
    }
  }
  if (current.body.trim()) sections.push({ ...current, body: current.body.trim() });
  return sections.slice(0, 12);
}

export function splitChangedFiles(input: string) {
  return input
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function citationPath(citation: Citation) {
  return citation.file ?? citation.path ?? "repository evidence";
}

export function citationLineRange(citation: Citation) {
  if (!citation.start_line) return "";
  return citation.end_line && citation.end_line !== citation.start_line
    ? `:${citation.start_line}-${citation.end_line}`
    : `:${citation.start_line}`;
}

export function domainCards(graph: KnowledgeGraph | undefined) {
  const domains = graph?.domains ?? [];
  const hotspots = graph?.hotspots ?? [];
  if (domains.length) return domains.slice(0, 8);
  return hotspots.slice(0, 8);
}

export function evidenceFiles(summary: RepositorySummary | null | undefined, limit = 8) {
  const paths = new Set<string>();
  for (const finding of topFindings(summary, limit)) {
    if (finding.file) paths.add(finding.file);
  }
  for (const route of summary?.architecture?.routes ?? []) {
    const file = String(route.file ?? route.path ?? "");
    if (file) paths.add(file);
  }
  for (const file of summary?.files ?? []) {
    if (file.relative_path && paths.size < limit) paths.add(file.relative_path);
  }
  return Array.from(paths).slice(0, limit);
}
