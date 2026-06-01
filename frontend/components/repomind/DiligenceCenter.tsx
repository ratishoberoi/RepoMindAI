"use client";

import { useState } from "react";
import { BriefcaseBusiness, Building, ClipboardCheck, ShieldCheck } from "lucide-react";
import type { DiligenceResult } from "./types";
import { asScore } from "./utils";
import { Badge, Button, EmptyState, MetricCard, Panel, SeverityBadge, Timeline } from "./ui";

const views = [
  { id: "investor", label: "Investor", icon: Building },
  { id: "cto", label: "CTO", icon: BriefcaseBusiness },
  { id: "security", label: "Security", icon: ShieldCheck }
];

export function DiligenceCenter({
  data,
  busy,
  onGenerate
}: {
  data: DiligenceResult | null;
  busy: boolean;
  onGenerate: () => void;
}) {
  const [view, setView] = useState("investor");
  const summary = view === "investor" ? data?.investor_summary : view === "security" ? data?.security_summary : data?.cto_summary;

  return (
    <div className="space-y-5">
      <Panel title="CTO Due-Diligence Center" eyebrow="Executive-ready decision packet" action={<Button onClick={onGenerate} disabled={busy}>{busy ? "Generating" : "Generate packet"}</Button>}>
        {!data ? (
          <EmptyState title="No diligence packet" text="Generate investor, CTO, and security narratives from repository evidence, graph signals, and risk findings." />
        ) : (
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <MetricCard label="Diligence Score" value={asScore(data.score)} score={asScore(data.score)} detail="Funding-readiness signal" icon={<ClipboardCheck size={18} />} />
              <MetricCard label="Strengths" value={data.strengths?.length ?? 0} detail="Defensible proof points" />
              <MetricCard label="Risks" value={data.risks?.length ?? 0} detail="Board-level exceptions" />
            </div>
            <div className="flex flex-wrap gap-2">
              {views.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setView(item.id)}
                    className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition ${
                      view === item.id ? "border-white/25 bg-white text-slate-950" : "border-white/10 bg-white/[0.05] text-slate-300 hover:bg-white/[0.09]"
                    }`}
                  >
                    <Icon size={15} />
                    {item.label}
                  </button>
                );
              })}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-200/75">{view} memo</p>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-300">{summary ?? "No narrative returned for this persona."}</p>
            </div>
          </div>
        )}
      </Panel>

      {data ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <Panel title="Investment Strengths" eyebrow="Evidence-backed positives">
            <div className="space-y-3">
              {(data.strengths ?? []).map((strength, index) => (
                <div key={index} className="rounded-xl border border-emerald-300/15 bg-emerald-300/[0.08] p-4 text-sm leading-6 text-emerald-50">{strength}</div>
              ))}
            </div>
          </Panel>
          <Panel title="Risk Exceptions" eyebrow="Negotiation and remediation focus">
            <div className="space-y-3">
              {(data.risks ?? []).slice(0, 6).map((risk, index) => (
                <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-white">{risk.title ?? risk.message ?? "Diligence risk"}</p>
                    <SeverityBadge severity={risk.severity} />
                  </div>
                  <p className="mt-2 text-sm leading-5 text-slate-400">{risk.recommendation ?? risk.evidence ?? risk.file ?? ""}</p>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Recommendation Timeline" eyebrow="What the acquirer or CTO does next" className="xl:col-span-2">
            <Timeline
              items={(data.recommendations ?? ["Prioritize risks, validate deployment controls, and repeat analysis after remediation."]).slice(0, 5).map((item, index) => ({
                title: index === 0 ? "Immediate" : index < 3 ? "Near term" : "Strategic",
                text: item
              }))}
            />
          </Panel>
        </div>
      ) : null}
    </div>
  );
}
