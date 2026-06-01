"use client";

import { Building2, Layers3, Network, Radar, ShieldAlert } from "lucide-react";
import type { PortfolioIntelligence } from "./types";
import { Badge, Button, EmptyState, MetricCard, Panel, ScoreBar, SeverityBadge } from "./ui";
import { asScore, compactNumber } from "./utils";

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
  const sharedDependencies = data.shared_dependencies ?? [];
  const risks = data.risk_concentration ?? [];
  const insights = data.strategic_insights ?? [];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Portfolio Score" value={asScore(data.portfolio_score)} score={asScore(data.portfolio_score)} detail="Aggregate repo health" icon={<Building2 size={18} />} />
        <MetricCard label="Repositories" value={compactNumber(data.total_repositories)} detail="Analyzed assets" icon={<Layers3 size={18} />} />
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

      <Panel title="Shared Risk Register" eyebrow="Where one fix helps multiple repos">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {risks.slice(0, 9).map((risk, index) => (
            <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
              <Radar className="h-5 w-5 text-amber-200" />
              <p className="mt-3 text-sm font-semibold text-white">{String(risk.title ?? risk.name ?? "Shared exposure")}</p>
              <p className="mt-2 text-sm leading-5 text-slate-400">{String(risk.description ?? risk.message ?? risk.file ?? "")}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
