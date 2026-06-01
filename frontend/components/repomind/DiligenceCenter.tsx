"use client";

import { useState } from "react";
import { BriefcaseBusiness, Building, ShieldCheck } from "lucide-react";
import type { DiligenceResult } from "./types";
import { asScore } from "./utils";
import { Badge, Button, EmptyState, MetricCard, Panel, SeverityBadge, Timeline } from "./ui";
import { InsightTicker, RiskMatrix, ScoreOrb } from "./visuals";

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
  const normalized = normalizeDiligence(data);
  const summary = view === "investor" ? normalized.investor : view === "security" ? normalized.security : normalized.cto;

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-3xl border border-emerald-300/15 bg-[linear-gradient(135deg,rgba(52,211,153,0.14),rgba(255,255,255,0.045)_42%,rgba(56,189,248,0.08))] shadow-panel">
        <div className="grid gap-0 xl:grid-cols-[300px_1fr]">
          <div className="grid place-items-center border-b border-white/10 bg-black/20 p-5 xl:border-b-0 xl:border-r">
            <ScoreOrb label="Investment" score={asScore(normalized.score)} size="medium" sublabel={normalized.readiness} />
          </div>
          <div className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-200/80">Investor-grade diligence</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">CTO Due-Diligence Center</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">A board-ready view of technical strengths, risks, remediation path, and acquisition readiness.</p>
              </div>
              <Button onClick={onGenerate} disabled={busy}>{busy ? "Generating" : "Generate packet"}</Button>
            </div>
            {data ? (
              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <MetricCard label="Strengths" value={normalized.strengths.length} detail="Defensible proof points" />
                <MetricCard label="Risks" value={normalized.risks.length} detail="Board-level exceptions" />
                <MetricCard label="Recommendations" value={normalized.recommendations.length} detail="Execution path" />
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <Panel title="Diligence Memo" eyebrow="Persona-specific narrative">
        {!data ? (
          <EmptyState title="No diligence packet" text="Generate investor, CTO, and security narratives from repository evidence, graph signals, and risk findings." />
        ) : (
          <div className="space-y-5">
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
        <div className="grid gap-5 xl:grid-cols-3">
          <Panel title="Executive Insights" eyebrow="Diligence takeaways">
            <InsightTicker
              insights={[
                { label: "Readiness", severity: asScore(normalized.score) < 65 ? "high" : "low", text: `Investment readiness is ${asScore(normalized.score)}/100 with ${normalized.risks.length} unresolved risks.` },
                { label: "Narrative", severity: "info", text: "Investor, CTO, and security views are separated so each stakeholder sees the right proof points." },
                { label: "Action", severity: "medium", text: "Recommendations are organized into an execution timeline for follow-up diligence." }
              ]}
            />
          </Panel>
          <Panel title="Diligence Risk Matrix" eyebrow="Negotiation focus">
            <RiskMatrix items={normalized.risks.map((risk, index) => ({ label: risk.title ?? risk.message ?? `Risk ${index}`, severity: risk.severity, likelihood: Math.min(5, 2 + (index % 4)) }))} />
          </Panel>
          <Panel title="Investment Strengths" eyebrow="Evidence-backed positives">
            <div className="space-y-3">
              {normalized.strengths.map((strength, index) => (
                <div key={index} className="rounded-xl border border-emerald-300/15 bg-emerald-300/[0.08] p-4 text-sm leading-6 text-emerald-50">{strength}</div>
              ))}
            </div>
          </Panel>
          <Panel title="Risk Exceptions" eyebrow="Negotiation and remediation focus" className="xl:col-span-2">
            <div className="space-y-3">
              {normalized.risks.slice(0, 6).map((risk, index) => (
                <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-white">{risk.title ?? risk.message ?? "Diligence risk"}</p>
                    <SeverityBadge severity={risk.severity} />
                  </div>
                  <p className="mt-2 text-sm leading-5 text-slate-400">{String((risk as any).recommendation ?? risk.evidence ?? risk.file ?? "")}</p>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Recommendation Timeline" eyebrow="What the acquirer or CTO does next" className="xl:col-span-2">
            <Timeline
              items={normalized.recommendations.slice(0, 5).map((item, index) => ({
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

function normalizeDiligence(data: DiligenceResult | null) {
  const risks = [
    ...(data?.risks ?? []),
    ...(data?.top_risks ?? []).map((risk) => ({
      title: String(risk.risk ?? risk.title ?? "Diligence risk"),
      message: String(risk.risk ?? risk.message ?? ""),
      severity: String(risk.severity ?? "medium"),
      evidence: String(risk.evidence ?? ""),
      file: String(risk.evidence ?? "").split(":")[0]
    }))
  ];
  const score = data?.score ?? data?.scorecard?.cto ?? data?.scorecard?.production_readiness ?? 0;
  const readiness = data?.investment_readiness ?? "readiness";
  const recommendation = data?.recommendation ? [data.recommendation] : [];
  const gaps = data?.enterprise_gaps ?? [];
  const recommendations = [...recommendation, ...gaps, ...(data?.recommendations ?? [])];
  const executive = data?.executive_summary ?? "Generate a diligence packet to populate this memo.";
  return {
    score,
    readiness,
    strengths: data?.strengths ?? [],
    risks,
    recommendations: recommendations.length ? recommendations : ["Prioritize risks, validate deployment controls, and repeat analysis after remediation."],
    investor: data?.investor_summary ?? `${executive}\n\nInvestment readiness: ${readiness}. Recommendation: ${data?.recommendation ?? "review with technical leadership"}.`,
    cto: data?.cto_summary ?? `${executive}\n\nCritical evidence: ${(data?.critical_evidence ?? []).join(", ") || "not provided"}.`,
    security: data?.security_summary ?? `${executive}\n\nTop risk count: ${risks.length}. ${gaps.length ? `Enterprise gaps: ${gaps.join(" ")}` : ""}`,
  };
}
