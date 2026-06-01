"use client";

import { Building2, Layers3, Network, Radar, ShieldAlert } from "lucide-react";
import type { PortfolioIntelligence } from "./types";
import { Badge, Button, EmptyState, MetricCard, Panel, ScoreBar, SeverityBadge } from "./ui";
import { asScore, compactNumber } from "./utils";
import { Heatmap, RadarChart, RiskMatrix } from "./visuals";

export function PortfolioPanel({
  data,
  busy,
  onRefresh
}: {
  data: PortfolioIntelligence | null;
  busy: boolean;
  onRefresh: () => void;
}) {
  if (!data) {
    return (
      <Panel title="Portfolio Intelligence" eyebrow="Cross-repository operating system" action={<Button onClick={onRefresh} disabled={busy}>{busy ? "Loading" : "Generate"}</Button>}>
        <EmptyState title="No portfolio snapshot yet" text="Generate a cross-repository view to expose shared risks, dependency concentration, and portfolio-level investment priorities." />
      </Panel>
    );
  }
  const sharedDependencies = normalizeDependencies(data) as Array<Record<string, unknown>>;
  const risks = [...(data.risk_concentration ?? []), ...(data.top_risks ?? [])];
  const insights = (data.strategic_insights?.length
    ? data.strategic_insights
    : (data.recommendations ?? []).map((item, index) => ({ title: `Portfolio move ${index + 1}`, description: item, severity: index === 0 ? "high" : "medium" }))) as Array<Record<string, unknown>>;
  const repositoryCount = data.total_repositories ?? data.repository_count ?? data.repositories?.length ?? 0;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Portfolio Score" value={asScore(data.portfolio_score)} score={asScore(data.portfolio_score)} detail="Aggregate repo health" icon={<Building2 size={18} />} />
        <MetricCard label="Repositories" value={compactNumber(repositoryCount)} detail="Analyzed assets" icon={<Layers3 size={18} />} />
        <MetricCard label="Shared Risks" value={compactNumber(risks.length)} detail="Repeated exposure patterns" icon={<ShieldAlert size={18} />} />
        <MetricCard label="Dependency Clusters" value={compactNumber(sharedDependencies.length)} detail="Concentration map" icon={<Network size={18} />} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <Panel title="Cross-Repo Insights" eyebrow="Board-ready signals" action={<Button variant="secondary" onClick={onRefresh} disabled={busy}>Refresh</Button>}>
          <div className="space-y-3">
            {insights.length ? insights.slice(0, 7).map((insight, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{String(insight.title ?? insight.name ?? "Strategic insight")}</p>
                  <SeverityBadge severity={String(insight.severity ?? insight.risk ?? "info")} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{String(insight.description ?? insight.message ?? insight.recommendation ?? "")}</p>
              </div>
            )) : <EmptyState title="No strategic insights" text="Insights appear after more repositories have complete analysis artifacts." />}
          </div>
        </Panel>

        <Panel title="Dependency Concentration" eyebrow="Operational fragility">
          <div className="space-y-4">
            {sharedDependencies.slice(0, 8).map((dependency, index) => {
              const repoCount = Number(dependency.repository_count ?? dependency.count ?? 0);
              return (
                <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">{String(dependency.name ?? dependency.dependency ?? "dependency")}</p>
                      <p className="mt-1 text-xs text-slate-500">{repoCount || "Multiple"} repositories</p>
                    </div>
                    <Badge className="border-cyan-300/25 bg-cyan-300/10 text-cyan-100">{String(dependency.ecosystem ?? dependency.kind ?? "package")}</Badge>
                  </div>
                  <div className="mt-3"><ScoreBar label="Concentration" value={Math.min(100, repoCount * 18)} /></div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.8fr_0.8fr_1.4fr]">
        <Panel title="Portfolio Radar" eyebrow="Operating profile">
          <RadarChart axes={[
            { label: "Health", value: asScore(data.portfolio_score) },
            { label: "Risk", value: Math.max(0, 100 - risks.length * 12) },
            { label: "Deps", value: Math.max(0, 100 - sharedDependencies.length * 8) },
            { label: "Scale", value: Math.min(100, Number(repositoryCount ?? 0) * 18) },
            { label: "Signal", value: Math.min(100, insights.length * 20) }
          ]} />
        </Panel>
        <Panel title="Portfolio Heatmap" eyebrow="Concentration density">
          <Heatmap values={[...sharedDependencies.map((item, index) => ({ label: String(item.name ?? item.dependency ?? index), value: 35 + ((index * 17) % 65) })), ...risks.map((item, index) => ({ label: String(item.title ?? item.name ?? index), value: 70 + ((index * 7) % 30) }))]} />
        </Panel>
        <Panel title="Shared Risk Register" eyebrow="Where one fix helps multiple repos">
          <RiskMatrix items={risks.map((risk, index) => ({ label: String(risk.title ?? risk.name ?? `Risk ${index}`), severity: String(risk.severity ?? "medium"), likelihood: Math.min(5, 2 + (index % 4)) }))} />
        </Panel>
      </div>

      <Panel title="Shared Risk Details" eyebrow="Prioritized remediation portfolio">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {risks.slice(0, 9).map((risk, index) => (
            <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
              <Radar className="h-5 w-5 text-amber-200" />
              <p className="mt-3 text-sm font-semibold text-white">{String(risk.title ?? risk.name ?? risk.risk ?? "Shared exposure")}</p>
              <p className="mt-2 text-sm leading-5 text-slate-400">{String(risk.description ?? risk.message ?? risk.path ?? risk.file ?? risk.repo ?? "")}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function normalizeDependencies(data: PortfolioIntelligence) {
  const shared = data.shared_dependencies ?? [];
  if (shared.length) return shared;
  const frameworks = entries(data.frameworks).map(([name, count]) => ({ name, repository_count: count, ecosystem: "framework" }));
  const languages = entries(data.languages).map(([name, count]) => ({ name, repository_count: count, ecosystem: "language" }));
  const domains = (data.shared_domains ?? []).map((item) => ({ name: item.name ?? item.domain ?? "domain", repository_count: item.repository_count ?? item.count ?? 1, ecosystem: "domain" }));
  return [...frameworks, ...languages, ...domains];
}

function entries(value: unknown): Array<[string, number]> {
  if (Array.isArray(value)) return value.map((item) => [String(item[0]), Number(item[1] ?? 0)]);
  return Object.entries((value ?? {}) as Record<string, number>).map(([key, count]) => [key, Number(count)]);
}
