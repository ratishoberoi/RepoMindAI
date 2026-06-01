"use client";

import { Activity, Brain, GitPullRequest, Network, ShieldCheck, Sparkles } from "lucide-react";
import type { RepositorySummary } from "./types";
import { asScore, compactNumber, executiveScore, evidenceFiles, riskLevel, topFindings } from "./utils";
import { Badge, EmptyState, MetricCard, Panel, ScoreBar, SeverityBadge, Timeline } from "./ui";

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

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Repo Health" value={overall} score={overall} detail={`${riskLevel(overall)} delivery posture`} icon={<Sparkles size={18} />} />
        <MetricCard label="Security" value={asScore(scores.security)} score={asScore(scores.security)} detail={`${findings.length} priority findings surfaced`} icon={<ShieldCheck size={18} />} />
        <MetricCard label="Architecture" value={asScore(scores.production_readiness ?? scores.architecture)} score={asScore(scores.production_readiness ?? scores.architecture)} detail="Runtime and boundary confidence" icon={<Network size={18} />} />
        <MetricCard label="AI Readiness" value={asScore(scores.ai_readiness ?? scores.maintainability)} score={asScore(scores.ai_readiness ?? scores.maintainability)} detail="Context quality for agentic workflows" icon={<Brain size={18} />} />
        <MetricCard label="Risk Level" value={riskLevel(overall)} score={overall} detail="Investor-ready snapshot" icon={<Activity size={18} />} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Executive Command Center" eyebrow="Operational picture">
          <div className="grid gap-4 md:grid-cols-3">
            <InsightStat label="Files analyzed" value={compactNumber(stats.files ?? summary.files?.length)} />
            <InsightStat label="Knowledge entities" value={compactNumber(graphMetrics.entities)} />
            <InsightStat label="Security findings" value={compactNumber(summary.security?.findings?.length)} />
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <ScoreBar label="Maintainability" value={asScore(scores.maintainability)} />
            <ScoreBar label="Production readiness" value={asScore(scores.production_readiness)} />
            <ScoreBar label="CTO score" value={asScore(scores.cto)} />
            <ScoreBar label="Security confidence" value={asScore(scores.security)} />
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <button onClick={() => onNavigate("knowledge")} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-left transition hover:border-cyan-300/30 hover:bg-cyan-300/10">
              <Network className="h-5 w-5 text-cyan-200" />
              <p className="mt-3 text-sm font-semibold text-white">Open Knowledge Graph</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Explore domains, hotspots, and evidence paths.</p>
            </button>
            <button onClick={() => onNavigate("pr-risk")} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-left transition hover:border-amber-300/30 hover:bg-amber-300/10">
              <GitPullRequest className="h-5 w-5 text-amber-200" />
              <p className="mt-3 text-sm font-semibold text-white">Assess PR Risk</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Map changed files to blast radius and tests.</p>
            </button>
            <button onClick={() => onNavigate("diligence")} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-left transition hover:border-emerald-300/30 hover:bg-emerald-300/10">
              <Sparkles className="h-5 w-5 text-emerald-200" />
              <p className="mt-3 text-sm font-semibold text-white">Due Diligence</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Package investor, CTO, and security narratives.</p>
            </button>
          </div>
        </Panel>

        <Panel title="Risk Matrix" eyebrow="Highest leverage findings">
          {findings.length ? (
            <div className="space-y-3">
              {findings.map((finding, index) => (
                <div key={`${finding.file}-${finding.title}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-white">{finding.title ?? finding.message ?? "Repository finding"}</p>
                    <SeverityBadge severity={finding.severity} />
                  </div>
                  <p className="mt-2 truncate text-xs text-slate-500">{finding.file ?? "Evidence unavailable"}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No priority risks" text="Security and debt findings will appear here after analysis." />
          )}
        </Panel>
      </div>

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
