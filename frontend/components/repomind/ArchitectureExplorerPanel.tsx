"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Database, GitBranch, Network, Route, ShieldAlert } from "lucide-react";
import { Badge, Button, EmptyState, LoadingInline, Panel, ScoreBar, Timeline } from "./ui";
import { Heatmap, RiskMatrix } from "./visuals";
import type { ArchitectureExplorerResult } from "./types";

export function ArchitectureExplorerPanel({
  data,
  busy,
  onGenerate
}: {
  data: ArchitectureExplorerResult | null;
  busy: boolean;
  onGenerate: () => void;
}) {
  const [activeFlowId, setActiveFlowId] = useState<string | null>(null);
  const flows = (data?.request_flows ?? []).filter((flow) => Array.isArray(flow.steps) && flow.steps.length);
  const activeFlow = flows.find((flow) => flow.id === activeFlowId) ?? flows[0];
  const dependencyFlows = data?.dependency_flows ?? [];
  const onboarding = data?.onboarding_markdown ?? "";
  const review = data?.architecture_review ?? {};
  const architectFindings = data?.ai_architect_review ?? [];
  const serviceExplorer = data?.service_dependency_explorer;
  const blastRadius = data?.blast_radius_explorer ?? [];
  const ownership = data?.ownership_explorer;
  const impact = data?.impact_explorer ?? [];
  const architectureTimeline = data?.architecture_timeline ?? [];
  const heat = useMemo(
    () =>
      flows.map((flow) => ({
        label: String(flow.label ?? flow.id ?? "flow"),
        value: flow.confidence === "high" ? 88 : flow.confidence === "medium" ? 58 : 24
      })),
    [flows]
  );

  if (!data && !busy) {
    return (
      <EmptyState
        title="Generate architecture explorer"
        text="Trace request flows, dependency paths, sequence diagrams, and onboarding docs from analyzed repository evidence."
        action={<Button onClick={onGenerate}>Generate Explorer</Button>}
      />
    );
  }

  return (
    <div className="grid gap-4">
      <Panel
        className="overflow-hidden"
        title="Architecture Explorer"
        eyebrow="request flow intelligence"
        action={<Button variant="secondary" onClick={onGenerate}>{busy ? <LoadingInline label="Tracing" /> : "Refresh"}</Button>}
      >
        <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-cyan-300/20 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_34%),linear-gradient(135deg,rgba(15,23,42,0.95),rgba(2,6,23,0.85))] p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-200/80">System behavior map</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">{String(data?.repository?.name ?? "Repository")}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">{data?.narratives?.executive ?? "No executive narrative generated yet."}</p>
              </div>
              <Badge className="border-emerald-300/25 bg-emerald-500/10 text-emerald-100">{flows.length} traced flows</Badge>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-4">
              <Signal icon={<Route size={16} />} label="Entry points" value={data?.entry_points?.length ?? 0} />
              <Signal icon={<Network size={16} />} label="Services" value={data?.services?.length ?? 0} />
              <Signal icon={<Database size={16} />} label="Models" value={data?.models?.length ?? 0} />
              <Signal icon={<GitBranch size={16} />} label="Dependency paths" value={dependencyFlows.length} />
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <Heatmap label="Flow confidence heatmap" values={heat} />
            <p className="mt-4 text-sm leading-6 text-slate-400">{data?.narratives?.engineering ?? "Engineering trace narrative unavailable."}</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Panel title="Detected Flows" eyebrow="click to inspect">
          <div className="space-y-2">
            {flows.map((flow) => (
              <button
                key={String(flow.id)}
                onClick={() => setActiveFlowId(String(flow.id))}
                className={`w-full rounded-xl border p-3 text-left transition ${activeFlow?.id === flow.id ? "border-cyan-300/30 bg-cyan-400/10" : "border-white/10 bg-white/[0.035] hover:bg-white/[0.06]"}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-white">{String(flow.label ?? flow.id)}</span>
                  <Badge className={flow.confidence === "high" ? "border-emerald-300/25 bg-emerald-500/10 text-emerald-100" : "border-amber-300/25 bg-amber-500/10 text-amber-100"}>{String(flow.confidence ?? "low")}</Badge>
                </div>
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">{String(flow.summary ?? "")}</p>
              </button>
            ))}
            {!flows.length ? <EmptyState title="No named flows detected" text="The analyzed repository did not expose routes or services matching known flow patterns." /> : null}
          </div>
        </Panel>

        <Panel title={String(activeFlow?.label ?? "Sequence Diagram")} eyebrow="frontend -> api -> services -> database">
          {activeFlow ? (
            <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
              <MermaidDiagram chart={String(activeFlow.sequence_diagram ?? "")} />
              <div className="space-y-3">
                {(activeFlow.steps as Array<Record<string, unknown>>).map((step, index) => (
                  <div key={`${String(step.component)}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                    <div className="flex items-center gap-2">
                      <Badge>{String(step.layer)}</Badge>
                      {index < (activeFlow.steps as unknown[]).length - 1 ? <ArrowRight size={14} className="text-slate-500" /> : null}
                    </div>
                    <p className="mt-2 text-sm font-medium text-white">{String(step.component)}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">{String(step.detail)}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState title="No flow selected" text="Generate architecture explorer data to inspect sequence diagrams." />
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Dependency Flow Explorer" eyebrow="click-expand ready paths">
          <div className="space-y-3">
            {dependencyFlows.slice(0, 8).map((flow, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{String(flow.source)}</p>
                  <Badge>{String(flow.length ?? 0)} hops</Badge>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {((flow.path as string[]) ?? []).map((item, itemIndex) => (
                    <span key={`${item}-${itemIndex}`} className="inline-flex items-center gap-2 text-xs text-slate-300">
                      <span className="rounded-lg border border-white/10 bg-black/20 px-2 py-1">{item}</span>
                      {itemIndex < ((flow.path as string[]) ?? []).length - 1 ? <ArrowRight size={12} className="text-slate-600" /> : null}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Auto-generated ONBOARDING.md" eyebrow="developer ramp">
          <div className="max-h-[460px] overflow-auto rounded-xl border border-white/10 bg-black/25 p-4 font-mono text-xs leading-5 text-slate-300">
            {onboarding ? onboarding : "Generate architecture explorer to create onboarding documentation."}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Service Dependency Explorer" eyebrow="service nodes, dependency edges, evidence-backed risk">
          <p className="mb-4 text-sm leading-6 text-slate-400">{serviceExplorer?.summary ?? "No service dependency explorer payload was returned."}</p>
          <div className="grid gap-3 md:grid-cols-3">
            <Signal icon={<Network size={16} />} label="Service nodes" value={serviceExplorer?.nodes?.length ?? 0} />
            <Signal icon={<GitBranch size={16} />} label="Dependency edges" value={serviceExplorer?.edges?.length ?? 0} />
            <Signal icon={<ShieldAlert size={16} />} label="High risk" value={serviceExplorer?.high_risk_services?.length ?? 0} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {(serviceExplorer?.high_risk_services ?? []).slice(0, 8).map((node, index) => (
              <div key={`${String(node.id)}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">{String(node.id)}</p>
                    <p className="mt-1 text-xs text-slate-500">{String(node.layer)} / {String(node.domain)}</p>
                  </div>
                  <Badge className="border-amber-300/25 bg-amber-500/10 text-amber-100">{String(node.risk_score ?? 0)}</Badge>
                </div>
                <div className="mt-3"><ScoreBar label="Service risk" value={Number(node.risk_score ?? 0)} /></div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Architecture Timeline" eyebrow="time-machine signal">
          <Timeline
            items={architectureTimeline.slice(-8).map((item, index) => ({
              title: `${String(item.date ?? `Event ${index + 1}`)} - risk ${String(item.risk ?? item.architecture ?? "--")}`,
              text: String(item.evidence ?? item.label ?? "Architecture evolution evidence.")
            }))}
          />
          {!architectureTimeline.length ? <EmptyState title="No timeline evidence" text="No git-derived architecture timeline is available for this repository." /> : null}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel title="Blast Radius Explorer" eyebrow="upstream, downstream, affected domains">
          <RiskMatrix items={blastRadius.map((item, index) => ({ label: String(item.source ?? `Node ${index}`), severity: Number(item.risk_score ?? 0) > 70 ? "high" : "medium", impact: Math.min(5, Number(item.affected_files ?? 1)), likelihood: Math.min(5, 2 + (index % 4)) }))} />
          <div className="mt-4 space-y-3">
            {blastRadius.slice(0, 5).map((item, index) => (
              <div key={`${String(item.source)}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 truncate text-sm font-semibold text-white">{String(item.source)}</p>
                  <Badge>{String(item.affected_files ?? 0)} files</Badge>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-400">{((item.affected_domains as string[] | undefined) ?? []).join(" | ")}</p>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Ownership Explorer" eyebrow="domain owners and orphan risk">
          <p className="mb-4 text-sm leading-6 text-slate-400">{ownership?.summary ?? "No ownership mapping returned."}</p>
          <div className="space-y-3">
            {(ownership?.domains ?? []).slice(0, 8).map((domain, index) => (
              <div key={`${String(domain.domain)}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{String(domain.domain)}</p>
                    <p className="mt-1 text-xs text-slate-500">{String(domain.owner)}</p>
                  </div>
                  <Badge className="border-cyan-300/25 bg-cyan-500/10 text-cyan-100">BF {String(domain.bus_factor ?? "--")}</Badge>
                </div>
                <div className="mt-3"><ScoreBar label="Ownership risk" value={Number(domain.risk_score ?? 0)} /></div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Impact Explorer" eyebrow="business and engineering impact">
          <div className="space-y-3">
            {impact.slice(0, 8).map((item, index) => (
              <div key={`${String(item.file)}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 truncate text-sm font-semibold text-white">{String(item.file)}</p>
                  <Badge className="border-rose-300/25 bg-rose-500/10 text-rose-100">{String(item.risk_score ?? 0)}</Badge>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-400">{String(item.business_impact ?? "")}</p>
                <p className="mt-2 text-xs leading-5 text-cyan-100">{String(item.recommended_action ?? "")}</p>
              </div>
            ))}
            {!impact.length ? <EmptyState title="No impact findings" text="No high-risk service impact signals were detected." /> : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Architecture Review" eyebrow="strengths, weaknesses, coupling, scalability, modularity">
          <div className="grid gap-3 md:grid-cols-2">
            <ReviewMetric label="Architecture score" value={Number(review.score ?? 0)} />
            <ReviewMetric label="Coupling" value={Number((review.coupling_analysis as any)?.score ?? 0)} />
            <ReviewMetric label="Scalability" value={Number((review.scalability_analysis as any)?.score ?? 0)} />
            <ReviewMetric label="Modularity" value={Number((review.modularity_analysis as any)?.score ?? 0)} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <ReviewList title="Strengths" items={(review.strengths as string[]) ?? []} tone="emerald" />
            <ReviewList title="Weaknesses" items={(review.weaknesses as string[]) ?? []} tone="amber" />
            <ReviewList title="Current Risks" items={((review.current_risks as Array<Record<string, unknown>>) ?? []).map((item) => `${String(item.risk)} - ${String(item.evidence)}`)} tone="rose" />
            <ReviewList title="Refactoring Opportunities" items={(review.refactoring_opportunities as string[]) ?? []} tone="cyan" />
          </div>
        </Panel>
        <Panel title="AI Architect Review" eyebrow="risk, impact, recommendation, affected files">
          <div className="space-y-3">
            {architectFindings.map((finding, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{String(finding.risk ?? "Architecture risk")}</p>
                  <Badge className={String(finding.severity) === "high" ? "border-rose-300/25 bg-rose-500/10 text-rose-100" : "border-amber-300/25 bg-amber-500/10 text-amber-100"}>{String(finding.severity ?? "medium")}</Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{String(finding.impact ?? "")}</p>
                <p className="mt-2 text-sm leading-6 text-cyan-100">{String(finding.recommendation ?? "")}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {((finding.affected_files as string[]) ?? []).map((file) => <Badge key={file} className="border-white/10 bg-black/20 text-slate-300">{file}</Badge>)}
                </div>
              </div>
            ))}
            {!architectFindings.length ? <EmptyState title="No architect findings" text="No high-confidence architecture review issues were detected." /> : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Signal({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="flex items-center justify-between text-slate-400">
        <span className="text-[11px] uppercase tracking-[0.14em]">{label}</span>
        <span className="text-cyan-200">{icon}</span>
      </div>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function ReviewMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{Math.round(value)}</p>
    </div>
  );
}

function ReviewList({ title, items, tone }: { title: string; items: string[]; tone: "emerald" | "amber" | "rose" | "cyan" }) {
  const toneClass = {
    emerald: "border-emerald-300/20 bg-emerald-300/[0.07] text-emerald-50",
    amber: "border-amber-300/20 bg-amber-300/[0.07] text-amber-50",
    rose: "border-rose-300/20 bg-rose-300/[0.07] text-rose-50",
    cyan: "border-cyan-300/20 bg-cyan-300/[0.07] text-cyan-50"
  }[tone];
  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"><AlertTriangle size={13} />{title}</p>
      <div className="space-y-2">
        {(items.length ? items : ["No high-confidence signal detected."]).slice(0, 5).map((item, index) => (
          <div key={index} className={`rounded-xl border p-3 text-sm leading-5 ${toneClass}`}>{item}</div>
        ))}
      </div>
    </div>
  );
}

function MermaidDiagram({ chart }: { chart: string }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function render() {
      setError("");
      setSvg("");
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "dark" });
        const result = await mermaid.render(`architecture-flow-${Math.random().toString(36).slice(2)}`, chart);
        if (mounted) setSvg(result.svg);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Diagram failed to render.");
      }
    }
    if (chart) render();
    return () => {
      mounted = false;
    };
  }, [chart]);

  if (error) return <div className="rounded-xl border border-amber-300/25 bg-amber-500/10 p-4 text-sm text-amber-100">{error}</div>;
  if (!svg) return <div className="grid min-h-[360px] place-items-center rounded-xl border border-white/10 bg-black/20"><LoadingInline label="Rendering sequence diagram" /></div>;
  return (
    <div className="min-h-[360px] overflow-auto rounded-xl border border-white/10 bg-black/20 p-4">
      <div className="min-w-[620px]" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  );
}
