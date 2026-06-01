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
  onPrRisk: (files: string[], prUrl: string, repository: string, prNumber?: number) => void;
  onDrift: (baselineId: string, compareType: string, baselineRef: string, targetRef: string) => void;
}) {
  const [files, setFiles] = useState("backend/repomind/main.py\nfrontend/components/RepoMindDashboard.tsx");
  const [prUrl, setPrUrl] = useState("");
  const [githubRepository, setGithubRepository] = useState("");
  const [prNumber, setPrNumber] = useState("");
  const [baseline, setBaseline] = useState("");
  const [compareType, setCompareType] = useState("repository");
  const [baselineRef, setBaselineRef] = useState("");
  const [targetRef, setTargetRef] = useState("");
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
        <Panel title="PR Risk Center" eyebrow="Pre-merge blast radius" action={<Button onClick={() => onPrRisk(splitChangedFiles(files), prUrl, githubRepository, prNumber ? Number(prNumber) : undefined)} disabled={!activeRepo || busy || (!splitChangedFiles(files).length && !prUrl.trim() && !(githubRepository.trim() && prNumber.trim()))}>Analyze PR</Button>}>
          <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">PR URL</label>
          <input
            className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45"
            value={prUrl}
            onChange={(event) => setPrUrl(event.target.value)}
            placeholder="https://github.com/org/repo/pull/123"
          />
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_150px]">
            <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              GitHub repository
              <input
                className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45"
                value={githubRepository}
                onChange={(event) => setGithubRepository(event.target.value)}
                placeholder="owner/repo"
              />
            </label>
            <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              PR number
              <input
                className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45"
                value={prNumber}
                onChange={(event) => setPrNumber(event.target.value.replace(/\D/g, ""))}
                placeholder="123"
              />
            </label>
          </div>
          <label className="mt-4 block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Changed files</label>
          <textarea
            className="mt-2 min-h-40 w-full resize-y rounded-xl border border-white/10 bg-black/20 p-3 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45"
            value={files}
            onChange={(event) => setFiles(event.target.value)}
            placeholder="One changed file per line"
          />
          {prResult ? <PrRiskResultView result={prResult} /> : <div className="mt-4"><EmptyState title="No PR risk run" text="Paste a PR URL or changed files to estimate affected domains, review intensity, deployment risk, and test strategy." /></div>}
        </Panel>

        <Panel title="Architecture Drift Center" eyebrow="commit, branch, release, repository" action={<Button onClick={() => baseline && onDrift(baseline, compareType, baselineRef, targetRef)} disabled={!baseline || !activeRepo || busy}>Compare</Button>}>
          <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Baseline repository</label>
          <select className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none focus:border-cyan-300/45" value={baseline} onChange={(event) => setBaseline(event.target.value)}>
            <option value="">Select complete baseline</option>
            {completeRepos.map((repo) => <option key={repo.id} value={repo.id}>{repo.name}</option>)}
          </select>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              Compare
              <select className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none focus:border-cyan-300/45" value={compareType} onChange={(event) => setCompareType(event.target.value)}>
                {["repository", "commit", "branch", "release"].map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              Baseline ref
              <input className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45" value={baselineRef} onChange={(event) => setBaselineRef(event.target.value)} placeholder="main, v1.0, sha" />
            </label>
            <label className="block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              Target ref
              <input className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-300/45" value={targetRef} onChange={(event) => setTargetRef(event.target.value)} placeholder="feature, v2.0, sha" />
            </label>
          </div>
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
          <MetricCard label="Deploy Risk" value={String(result.deployment_risk?.level ?? "--")} detail={`Score ${String(result.deployment_risk?.score ?? "--")}`} icon={<AlertOctagon size={18} />} />
        </div>
      </div>
      {result.summary ? <div className="rounded-xl border border-amber-300/20 bg-amber-300/[0.08] p-4 text-sm leading-6 text-amber-50">{result.summary}</div> : null}
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
          {((result.review_plan ?? result.required_review) ?? []).map((item, index) => <ChecklistItem key={index} text={item} />)}
          {((result.recommended_tests ?? result.test_strategy) ?? []).map((item, index) => <ChecklistItem key={`test-${index}`} text={item} tone="test" />)}
        </div>
      </Panel>
      <Panel title="PR Review Packet" eyebrow="Release gate and deployment risk">
        <div className="grid gap-3 md:grid-cols-3">
          <PacketItem label="Release gate" value={String(result.release_gate_recommendation ?? result.pr_review_packet?.release_gate ?? "standard review")} />
          <PacketItem label="Blast radius" value={`${String(result.blast_radius?.domain_count ?? 0)} domains`} />
          <PacketItem label="Source" value={String(result.changed_files_source ?? "manual")} />
        </div>
      </Panel>
      <div className="grid gap-4 md:grid-cols-3">
        <Panel title="Review Complexity" eyebrow="GitHub + diff evidence">
          <MetricCard label="Complexity" value={String(result.review_complexity?.level ?? "--")} score={100 - Number(result.review_complexity?.score ?? 0)} detail={`${String(result.review_complexity?.line_delta ?? 0)} changed lines`} />
        </Panel>
        <Panel title="Regression Probability" eyebrow={String(result.regression_probability?.confidence ?? "unknown")}>
          <MetricCard label="Probability" value={String(result.regression_probability?.level ?? "--")} score={100 - Number(result.regression_probability?.score ?? 0)} detail={(result.regression_probability?.evidence as string[] | undefined)?.join(" | ") ?? "Evidence unavailable"} />
        </Panel>
        <Panel title="GitHub Evidence" eyebrow={String(result.github_pr?.available ? "connected" : "not connected")}>
          <div className="space-y-2 text-sm text-slate-300">
            <PacketItem label="Repository" value={String(result.repository || result.github_pr?.repository || "--")} />
            <PacketItem label="Checks" value={`${((result.github_pr?.checks as unknown[] | undefined) ?? []).length} check runs`} />
          </div>
        </Panel>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <SignalList title="Dependency Changes" items={result.dependency_changes} labelKey="path" />
        <SignalList title="API Changes" items={result.api_changes} labelKey="path" />
        <SignalList title="Security-Sensitive Changes" items={result.security_sensitive_changes} labelKey="path" />
      </div>
      <Panel title="PR Impact Timeline" eyebrow="commits, files, modules, services">
        <div className="space-y-3">
          {(result.pr_impact_timeline ?? []).slice(0, 8).map((event, index) => (
            <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-semibold text-white">{String(event.label ?? `Impact ${index + 1}`)}</p>
                {event.sha ? <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{String(event.sha)}</Badge> : null}
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-400">{((event.files as string[] | undefined) ?? (event.events as string[] | undefined) ?? []).slice(0, 6).join(" | ")}</p>
            </div>
          ))}
        </div>
      </Panel>
      <div className="grid gap-4 md:grid-cols-3">
        <Panel title="Affected Services" eyebrow="impact prediction">
          <div className="space-y-2">
            {(result.affected_services ?? []).slice(0, 6).map((service, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <p className="text-sm font-semibold text-white">{String(service.service)}</p>
                <p className="mt-1 text-xs text-slate-400">{String(service.role ?? service.risk ?? "service")}</p>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Recommended Reviewers" eyebrow="ownership routing">
          <div className="space-y-2">
            {(result.recommended_reviewers ?? []).map((reviewer) => <ChecklistItem key={reviewer} text={reviewer} />)}
          </div>
        </Panel>
        <Panel title="Test Impact" eyebrow={String(result.test_impact_analysis?.coverage_confidence ?? "unknown")}>
          <div className="space-y-2">
            {((result.test_impact_analysis?.related_tests as string[] | undefined) ?? []).slice(0, 6).map((test) => <ChecklistItem key={test} text={test} tone="test" />)}
            {!(result.test_impact_analysis?.related_tests as string[] | undefined)?.length ? <p className="text-sm text-slate-400">No directly related tests detected for changed files.</p> : null}
          </div>
        </Panel>
      </div>
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
      {result.drift_report ? <pre className="max-h-72 overflow-auto rounded-xl border border-white/10 bg-black/25 p-4 text-xs leading-5 text-slate-300">{result.drift_report}</pre> : null}
      <Panel title="Architecture Drift Timeline" eyebrow={result.compare_type ?? "repository"}>
        <div className="space-y-3">
          {(result.timeline ?? []).map((event, index) => (
            <div key={index} className="rounded-xl border border-cyan-300/15 bg-cyan-400/[0.06] p-3">
              <p className="text-sm font-semibold text-white">{String(event.label ?? `Step ${index + 1}`)}</p>
              <p className="mt-1 text-xs text-cyan-100/75">{((event.events as string[] | undefined) ?? []).join(" | ")}</p>
            </div>
          ))}
        </div>
      </Panel>
      <div className="grid gap-3 md:grid-cols-3">
        <DriftSignal label="Dependencies" value={result.dependency_surface_changes} />
        <DriftSignal label="Integrations" value={result.external_integration_changes} />
        <DriftSignal label="API Surface" value={result.api_surface_changes} />
      </div>
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

function DriftSignal({ label, value }: { label: string; value?: Record<string, unknown> }) {
  const added = (value?.added as unknown[] | undefined)?.length ?? 0;
  const removed = (value?.removed as unknown[] | undefined)?.length ?? 0;
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
      <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">+{added} / -{removed}</p>
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

function PacketItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
      <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function SignalList({ title, items, labelKey }: { title: string; items?: Array<Record<string, unknown>>; labelKey: string }) {
  return (
    <Panel title={title}>
      <div className="space-y-2">
        {(items ?? []).slice(0, 6).map((item, index) => (
          <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
            <p className="truncate text-sm font-semibold text-white">{String(item[labelKey] ?? item.path ?? title)}</p>
            <p className="mt-1 text-xs text-slate-500">{String(item.risk ?? item.surface ?? item.evidence ?? "change evidence")}</p>
          </div>
        ))}
        {!(items ?? []).length ? <p className="text-sm text-slate-400">No matching changes detected.</p> : null}
      </div>
    </Panel>
  );
}
