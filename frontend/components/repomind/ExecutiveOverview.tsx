"use client";

import { Activity, GitPullRequest, Landmark, Network, ShieldCheck, Sparkles, Wrench } from "lucide-react";
import type { RepositorySummary } from "./types";
import { asScore, compactNumber, executiveScore, evidenceFiles, riskLevel, topFindings } from "./utils";
import { Badge, EmptyState, Panel, ScoreBar, SeverityBadge, Timeline } from "./ui";
import { ExecutiveSignalCard, Heatmap, InsightTicker, RadarChart, RiskMatrix, ScoreOrb } from "./visuals";
import { ScoreEvidencePanel } from "./ScoreEvidencePanel";

export function ExecutiveOverview({ summary, onNavigate }: { summary: RepositorySummary | null; onNavigate: (view: string) => void }) {
  if (!summary) {
    return <EmptyState title="No intelligence generated" text="Import and analyze a repository to unlock executive, product, security, and architecture views." />;
  }
  const scores = summary.scores ?? {};
  const overall = executiveScore(summary);
  const findings = topFindings(summary, 4);
  const stats = summary.statistics ?? {};
  const graphMetrics = summary.knowledge_graph?.metrics ?? {};
  const files = evidenceFiles(summary, 6);
  const debtCount = summary.technical_debt?.findings?.length ?? 0;
  const securityCount = summary.security?.findings?.length ?? 0;
  const axes = [
    { label: "Security", value: asScore(scores.security) },
    { label: "Arch", value: asScore(scores.production_readiness ?? scores.architecture) },
    { label: "Debt", value: Math.max(0, 100 - debtCount * 6) },
    { label: "AI", value: asScore(scores.ai_readiness ?? scores.maintainability) },
    { label: "Invest", value: asScore(scores.cto) }
  ];
  const heat = [
    ...findings.map((finding, index) => ({ label: finding.title ?? finding.file ?? `Finding ${index + 1}`, value: (finding.severity ?? "").toLowerCase() === "critical" ? 92 : (finding.severity ?? "").toLowerCase() === "high" ? 76 : 48, severity: finding.severity })),
    ...files.map((file, index) => ({ label: file, value: 28 + ((index * 19) % 58) }))
  ];

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.1),rgba(255,255,255,0.035)_48%,rgba(56,189,248,0.08))] shadow-panel">
        <div className="grid gap-0 xl:grid-cols-[280px_1fr] 2xl:grid-cols-[320px_1fr_300px]">
          <div className="grid place-items-center border-b border-white/10 bg-black/20 p-5 xl:border-b-0 xl:border-r">
            <ScoreOrb label="Repo Health" score={overall} sublabel={`${riskLevel(overall)} risk posture`} />
          </div>
          <div className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/80">30-second executive readout</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">Repository intelligence cockpit</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
                  Security posture, architecture health, technical debt, and investment readiness compressed into one board-ready operating picture.
                </p>
              </div>
              <Badge className="border-emerald-300/25 bg-emerald-300/10 text-emerald-100">Investor demo mode</Badge>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
              <ExecutiveSignalCard label="Security Posture" value={asScore(scores.security)} detail={`${securityCount} findings mapped to impact`} icon={ShieldCheck} delta={asScore(scores.security) > 75 ? "up" : "down"} />
              <ExecutiveSignalCard label="Architecture Health" value={asScore(scores.production_readiness ?? scores.architecture)} detail="Boundary, runtime, and scaling confidence" icon={Network} delta="stable" />
              <ExecutiveSignalCard label="Technical Debt" value={debtCount} detail="Debt signals requiring triage" icon={Wrench} delta={debtCount > 8 ? "down" : "stable"} />
              <ExecutiveSignalCard label="Investment Readiness" value={asScore(scores.cto)} detail="Diligence and acquisition confidence" icon={Landmark} delta={asScore(scores.cto) > 70 ? "up" : "stable"} />
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
              <InsightStat label="Files analyzed" value={compactNumber(stats.files ?? summary.files?.length)} />
              <InsightStat label="Graph entities" value={compactNumber(graphMetrics.entities)} />
              <InsightStat label="Routes" value={compactNumber(summary.architecture?.routes?.length)} />
              <InsightStat label="Data models" value={compactNumber(summary.architecture?.data_models?.length)} />
            </div>
          </div>
          <div className="border-t border-white/10 bg-black/20 p-5 xl:col-span-2 2xl:col-span-1 2xl:border-l 2xl:border-t-0">
            <RadarChart axes={axes} />
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button onClick={() => onNavigate("knowledge")} className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 p-3 text-left text-sm font-semibold text-cyan-50 hover:bg-cyan-300/15"><Network className="mb-2 h-4 w-4" />Graph</button>
              <button onClick={() => onNavigate("pr-risk")} className="rounded-xl border border-amber-300/20 bg-amber-300/10 p-3 text-left text-sm font-semibold text-amber-50 hover:bg-amber-300/15"><GitPullRequest className="mb-2 h-4 w-4" />PR Risk</button>
              <button onClick={() => onNavigate("diligence")} className="rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3 text-left text-sm font-semibold text-emerald-50 hover:bg-emerald-300/15"><Sparkles className="mb-2 h-4 w-4" />Diligence</button>
              <button onClick={() => onNavigate("reports")} className="rounded-xl border border-white/10 bg-white/[0.04] p-3 text-left text-sm font-semibold text-slate-100 hover:bg-white/[0.07]"><Activity className="mb-2 h-4 w-4" />Reports</button>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-5 2xl:grid-cols-[0.85fr_1.15fr_0.9fr]">
        <Panel title="Executive Insights" eyebrow="What matters now">
          <InsightTicker
            insights={[
              { label: "Posture", severity: asScore(scores.security) < 60 ? "high" : "info", text: `${riskLevel(overall)} repository posture with ${securityCount} security findings and ${debtCount} technical debt signals.` },
              { label: "Architecture", severity: asScore(scores.production_readiness) < 65 ? "medium" : "info", text: "Architecture health is weighted by production readiness, routes, data models, and graph density." },
              { label: "Investment", severity: asScore(scores.cto) < 65 ? "high" : "low", text: "Investment readiness reflects CTO score, evidence quality, and remediation clarity." }
            ]}
          />
        </Panel>
        <Panel title="Risk Matrix" eyebrow="Impact x likelihood">
          <RiskMatrix items={findings.map((finding, index) => ({ label: finding.title ?? finding.file ?? `Finding ${index}`, severity: finding.severity, likelihood: Math.min(5, 2 + (index % 4)) }))} />
        </Panel>
        <Panel title="Repository Heatmap" eyebrow="Risk and evidence density">
          <Heatmap values={heat} />
        </Panel>
      </div>

      <ScoreEvidencePanel evidence={summary.score_evidence} />

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Evidence Docket" eyebrow="Files worth opening first">
          <div className="grid gap-2">
            {files.map((file) => <Badge key={file} className="justify-start border-white/10 bg-white/[0.035] text-slate-300">{file}</Badge>)}
          </div>
        </Panel>
        <Panel title="Recommendation Timeline" eyebrow="Execution sequence">
          <Timeline
            items={[
              { title: "0-7 days", text: "Resolve critical security findings and verify production configuration." },
              { title: "2-4 weeks", text: "Stabilize architecture boundaries, dependency ownership, and test coverage." },
              { title: "Quarter", text: "Track architectural drift, multi-repo concentration, and recurring CTO score movement." }
            ]}
          />
        </Panel>
      </div>
    </div>
  );
}

function InsightStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}
