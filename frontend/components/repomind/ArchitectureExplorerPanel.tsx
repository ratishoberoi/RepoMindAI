"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, Database, GitBranch, Network, Route, Sparkles } from "lucide-react";
import { Badge, Button, EmptyState, LoadingInline, Panel } from "./ui";
import { Heatmap } from "./visuals";
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
