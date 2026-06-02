"use client";

import { Activity, GitCommitHorizontal, GitCompareArrows, ShieldAlert, Workflow } from "lucide-react";
import type { RepositoryEvolution } from "./types";
import { Badge, Button, EmptyState, MetricCard, Panel, ScoreBar, Timeline } from "./ui";
import { Heatmap, RadarChart, RiskMatrix } from "./visuals";
import { asScore, compactNumber } from "./utils";

export function RepositoryEvolutionPanel({
  data,
  busy,
  onGenerate
}: {
  data: RepositoryEvolution | null;
  busy: boolean;
  onGenerate: () => void;
}) {
  if (!data && !busy) {
    return (
      <EmptyState
        title="Generate repository time machine"
        text="Build architecture, dependency, security, complexity, and risk evolution from git history and current analysis evidence."
        action={<Button onClick={onGenerate}>Generate Time Machine</Button>}
      />
    );
  }

  const snapshot = data?.current_snapshot ?? {};
  const risk = data?.risk_evolution ?? [];
  const architecture = data?.architectural_drift_over_time ?? [];
  const security = data?.security_evolution ?? [];
  const complexity = data?.complexity_evolution ?? [];
  const hotFiles = data?.hot_files ?? [];
  const coupling = data?.change_coupling ?? [];
  const limitations = data?.limitations ?? [];

  return (
    <div className="grid gap-4">
      <Panel
        className="overflow-hidden"
        title="Repository Time Machine"
        eyebrow="architecture, dependency, risk, security, complexity evolution"
        action={<Button variant="secondary" onClick={onGenerate}>{busy ? "Generating" : "Refresh"}</Button>}
      >
        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-2xl border border-cyan-300/20 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_34%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(2,6,23,0.84))] p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-200/80">Evolution intelligence</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">{String(data?.repository?.name ?? "Repository")}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">{data?.summary ?? "Evolution summary unavailable."}</p>
              </div>
              <Badge className={data?.history_available ? "border-emerald-300/25 bg-emerald-500/10 text-emerald-100" : "border-amber-300/25 bg-amber-500/10 text-amber-100"}>
                {data?.history_available ? "git history" : "snapshot only"}
              </Badge>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-4">
              <MetricCard label="Commits" value={compactNumber(data?.commit_count_analyzed ?? 0)} detail="Analyzed history window" icon={<GitCommitHorizontal size={18} />} />
              <MetricCard label="Risk" value={asScore(Number(snapshot.risk_score ?? 0))} score={100 - asScore(Number(snapshot.risk_score ?? 0))} detail="Current risk pressure" icon={<ShieldAlert size={18} />} />
              <MetricCard label="Hotspots" value={compactNumber(snapshot.architecture_hotspots)} detail="Current architecture hotspots" icon={<Workflow size={18} />} />
              <MetricCard label="Couplings" value={compactNumber(coupling.length)} detail="Cross-domain co-change pairs" icon={<GitCompareArrows size={18} />} />
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <RadarChart axes={[
              { label: "Risk", value: Number(snapshot.risk_score ?? 0) },
              { label: "Security", value: Number(snapshot.security_risk ?? 0) },
              { label: "Architecture", value: Number(snapshot.architecture_risk ?? 0) },
              { label: "Complexity", value: Number(snapshot.complexity_risk ?? 0) },
              { label: "Dependency", value: Number(snapshot.dependency_risk ?? 0) }
            ]} />
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Panel title="Evolution Timeline" eyebrow="git-derived change pressure">
          <Timeline
            items={risk.slice(-10).map((item) => ({
              title: `${String(item.date)} - risk ${asScore(Number(item.value ?? 0))}`,
              text: String(item.evidence ?? item.label ?? "Repository evolution signal.")
            }))}
          />
          {!risk.length ? <EmptyState title="No timeline evidence" text="No git history or current snapshot evolution evidence was returned." /> : null}
        </Panel>
        <Panel title="Risk Heatmap" eyebrow="recent evolution signals">
          <Heatmap
            values={[
              ...architecture.slice(-10).map((item) => ({ label: `Architecture ${String(item.date)}`, value: Number(item.value ?? 0) })),
              ...security.slice(-10).map((item) => ({ label: `Security ${String(item.date)}`, value: Number(item.value ?? 0) })),
              ...complexity.slice(-10).map((item) => ({ label: `Complexity ${String(item.date)}`, value: Number(item.value ?? 0) }))
            ]}
          />
          <div className="mt-5 space-y-3">
            <ScoreBar label="Architecture risk" value={Number(snapshot.architecture_risk ?? 0)} />
            <ScoreBar label="Security risk" value={Number(snapshot.security_risk ?? 0)} />
            <ScoreBar label="Complexity risk" value={Number(snapshot.complexity_risk ?? 0)} />
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Hot Files" eyebrow="change frequency x architecture/security risk">
          <div className="space-y-3">
            {hotFiles.slice(0, 10).map((file, index) => (
              <div key={`${String(file.file)}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">{String(file.file)}</p>
                    <p className="mt-1 text-xs text-slate-500">{String(file.domain ?? "domain")} / {String(file.layer ?? "layer")}</p>
                  </div>
                  <Badge className="border-amber-300/25 bg-amber-500/10 text-amber-100">{asScore(Number(file.risk_score ?? 0))}</Badge>
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <ScoreBar label={`${String(file.touches ?? 0)} touches`} value={Math.min(100, Number(file.touches ?? 0) * 12)} />
                  <ScoreBar label={`${String(file.churn ?? 0)} churn`} value={Math.min(100, Number(file.churn ?? 0) / 10)} />
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-400">{((file.evidence as string[] | undefined) ?? []).join(" | ")}</p>
              </div>
            ))}
            {!hotFiles.length ? <EmptyState title="No hot files" text="No file-level evolution evidence was returned." /> : null}
          </div>
        </Panel>
        <Panel title="Change Coupling" eyebrow="files that evolve together">
          <RiskMatrix
            items={coupling.slice(0, 12).map((item, index) => ({
              label: `${String(item.source)} -> ${String(item.target)}`,
              severity: Number(item.co_changes ?? 0) >= 4 ? "high" : "medium",
              likelihood: Math.min(5, Number(item.co_changes ?? 1)),
              impact: Math.min(5, 2 + (index % 4))
            }))}
          />
          <div className="mt-4 space-y-2">
            {coupling.slice(0, 8).map((item, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-black/20 p-3">
                <p className="text-sm font-medium text-white">{String(item.source)}</p>
                <p className="mt-1 text-xs text-slate-500">co-changes with</p>
                <p className="mt-1 text-sm text-cyan-100">{String(item.target)}</p>
                <p className="mt-2 text-xs leading-5 text-slate-400">{String(item.evidence ?? "")}</p>
              </div>
            ))}
            {!coupling.length ? <p className="text-sm leading-6 text-slate-400">No cross-domain co-change pairs were detected in available git history.</p> : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Evidence" eyebrow="why this view is trustworthy">
          <div className="space-y-3">
            {(data?.evidence ?? []).map((item, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{String(item.type ?? "evidence")}</p>
                  <Badge>{String(item.source ?? "analysis")}</Badge>
                </div>
                <pre className="mt-3 max-h-36 overflow-auto rounded-lg bg-black/20 p-3 text-xs leading-5 text-slate-400">{JSON.stringify(item.facts ?? {}, null, 2)}</pre>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Limitations" eyebrow="explicit trust boundary">
          <div className="space-y-2">
            {limitations.map((item, index) => (
              <div key={index} className="flex items-start gap-3 rounded-xl border border-amber-300/20 bg-amber-500/[0.08] p-3 text-sm leading-5 text-amber-50">
                <Activity className="mt-0.5 h-4 w-4 shrink-0" />
                {item}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
