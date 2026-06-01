"use client";

import { useState } from "react";
import { AlertOctagon, GitCompareArrows, GitPullRequest, ShieldAlert, Target } from "lucide-react";
import type { Repository } from "@/lib/api";
import type { DriftResult, PrRiskResult } from "./types";
import { splitChangedFiles } from "./utils";
import { Badge, Button, EmptyState, MetricCard, Panel, ScoreBar, SeverityBadge } from "./ui";
import { Heatmap, RiskMatrix, ScoreOrb } from "./visuals";

export function RiskAndDriftCenter({
  repositories,
  activeRepo,
  prResult,
  driftResult,
  busy,
  onPrRisk,
  onDrift
}: {
  repositories: Repository[];
  activeRepo: Repository | null;
  prResult: PrRiskResult | null;
  driftResult: DriftResult | null;
  busy: boolean;
  onPrRisk: (files: string[]) => void;
  onDrift: (baselineId: string) => void;
}) {
  const [files, setFiles] = useState("backend/repomind/main.py\nfrontend/components/RepoMindDashboard.tsx");
  const [baseline, setBaseline] = useState("");
  const completeRepos = repositories.filter((repo) => repo.status === "complete" && repo.id !== activeRepo?.id);

  return (
    <div className="space-y-5">
      <section className="rounded-3xl border border-amber-300/15 bg-[linear-gradient(135deg,rgba(251,191,36,0.14),rgba(255,255,255,0.04)_42%,rgba(251,113,133,0.09))] p-5 shadow-panel">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-200/80">Change intelligence</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">PR risk and architecture drift command center</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">Turn changed files and baseline comparisons into review priority, blast radius, test strategy, and drift narrative.</p>
          </div>
          <div className="grid grid-cols-3 gap-3 xl:w-[520px]">
            <MetricMini label="PR score" value={prResult?.risk_score ?? "--"} />
            <MetricMini label="Drift" value={driftResult?.drift_score ?? "--"} />
            <MetricMini label="Changed" value={splitChangedFiles(files).length} />
          </div>
        </div>
      </section>
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="PR Risk Center" eyebrow="Pre-merge blast radius" action={<Button onClick={() => onPrRisk(splitChangedFiles(files))} disabled={!activeRepo || busy}>Analyze PR</Button>}>
          <textarea
            className="min-h-40 w-full resize-y rounded-xl border border-white/10 bg-black/20 p-3 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45"
            value={files}
            onChange={(event) => setFiles(event.target.value)}
            placeholder="One changed file per line"
          />
          {prResult ? <PrRiskResultView result={prResult} /> : <div className="mt-4"><EmptyState title="No PR risk run" text="Paste changed files to estimate affected domains, review intensity, and test strategy." /></div>}
        </Panel>

        <Panel title="Architecture Drift Center" eyebrow="Baseline comparison" action={<Button onClick={() => baseline && onDrift(baseline)} disabled={!baseline || !activeRepo || busy}>Compare</Button>}>
          <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Baseline repository</label>
          <select className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none focus:border-cyan-300/45" value={baseline} onChange={(event) => setBaseline(event.target.value)}>
            <option value="">Select complete baseline</option>
            {completeRepos.map((repo) => <option key={repo.id} value={repo.id}>{repo.name}</option>)}
          </select>
          {driftResult ? <DriftResultView result={driftResult} /> : <div className="mt-4"><EmptyState title="No drift comparison" text="Compare against a prior analysis or sibling repo to identify architecture change and operational drift." /></div>}
        </Panel>
      </div>
    </div>
  );
}

function PrRiskResultView({ result }: { result: PrRiskResult }) {
  const score = Number(result.risk_score ?? 0);
  return (
    <div className="mt-5 space-y-4">
      <div className="grid gap-3 md:grid-cols-[170px_1fr]">
        <div className="rounded-2xl border border-amber-300/20 bg-amber-300/[0.08] p-3">
          <ScoreOrb label="PR Risk" score={100 - score} size="medium" sublabel={result.risk_level ?? "risk"} />
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <MetricCard label="Files" value={result.changed_files?.length ?? 0} detail="Changed paths analyzed" icon={<GitPullRequest size={18} />} />
          <MetricCard label="Domains" value={result.impacted_domains?.length ?? 0} detail="Potential blast radius" icon={<Target size={18} />} />
          <MetricCard label="Findings" value={result.findings?.length ?? 0} detail="Review exceptions" icon={<AlertOctagon size={18} />} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="PR Risk Matrix" eyebrow="Impact x likelihood">
          <RiskMatrix items={(result.findings ?? []).map((finding, index) => ({ label: finding.title ?? finding.file ?? `Finding ${index}`, severity: finding.severity, likelihood: Math.min(5, 2 + (index % 4)) }))} />
        </Panel>
        <Panel title="Change Heatmap" eyebrow="Changed-file concentration">
          <Heatmap values={(result.changed_files ?? []).map((file, index) => ({ label: file, value: 40 + ((index * 23) % 60) }))} />
        </Panel>
      </div>
      <Panel title="Review Plan">
        <div className="space-y-2">
          {(result.review_plan ?? []).map((item, index) => <ChecklistItem key={index} text={item} />)}
          {(result.test_strategy ?? []).map((item, index) => <ChecklistItem key={`test-${index}`} text={item} tone="test" />)}
        </div>
      </Panel>
      <div className="grid gap-3 md:grid-cols-2">
        {(result.findings ?? []).slice(0, 6).map((finding, index) => (
          <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold text-white">{finding.title ?? finding.message ?? "Risk finding"}</p>
              <SeverityBadge severity={finding.severity} />
            </div>
            <p className="mt-2 text-xs text-slate-500">{finding.file}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DriftResultView({ result }: { result: DriftResult }) {
  const score = Number(result.drift_score ?? 0);
  return (
    <div className="mt-5 space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Drift score" value={score} score={100 - score} detail={result.drift_level ?? "Architecture movement"} icon={<GitCompareArrows size={18} />} />
        <MetricCard label="Added domains" value={result.added_domains?.length ?? 0} detail="New responsibilities" />
        <MetricCard label="Removed domains" value={result.removed_domains?.length ?? 0} detail="Potential regressions" />
      </div>
      <ScoreBar label="Architecture stability" value={100 - score} />
      <div className="grid gap-3 md:grid-cols-2">
        {(result.findings ?? []).slice(0, 6).map((finding, index) => (
          <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
            <ShieldAlert className="h-5 w-5 text-amber-200" />
            <p className="mt-3 text-sm font-semibold text-white">{finding.title ?? finding.message ?? "Drift finding"}</p>
            <p className="mt-2 text-sm leading-5 text-slate-400">{finding.recommendation ?? finding.evidence ?? ""}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricMini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function ChecklistItem({ text, tone = "review" }: { text: string; tone?: "review" | "test" }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.035] p-3">
      <Badge className={tone === "test" ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100" : "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"}>{tone}</Badge>
      <p className="text-sm leading-5 text-slate-300">{text}</p>
    </div>
  );
}
