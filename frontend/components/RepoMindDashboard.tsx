"use client";

import { useEffect, useMemo, useState } from "react";
import { Building2, FileText, GitCompareArrows, GitPullRequest, LayoutDashboard, MessageSquare, Network, Search, ShieldCheck } from "lucide-react";
import {
  analyze,
  architectureDrift,
  cancelAnalysis,
  chat,
  cloneRepo,
  dueDiligence,
  fetchReport,
  importLocal,
  listRepositories,
  portfolioIntelligence,
  prRisk,
  repositoryStatus,
  summary,
  uploadZip,
  type Repository
} from "@/lib/api";
import { reports } from "@/components/dashboard/constants";
import { ChatExperience } from "@/components/repomind/ChatExperience";
import { DiligenceCenter } from "@/components/repomind/DiligenceCenter";
import { ExecutiveOverview } from "@/components/repomind/ExecutiveOverview";
import { KnowledgeGraphPanel } from "@/components/repomind/KnowledgeGraphPanel";
import { PortfolioPanel } from "@/components/repomind/PortfolioPanel";
import { RepositoryRail } from "@/components/repomind/RepositoryRail";
import { RiskAndDriftCenter } from "@/components/repomind/RiskAndDriftCenter";
import { ReportsCenter } from "@/components/repomind/ReportsCenter";
import { Badge, Button, EmptyState, Panel, SkeletonGrid } from "@/components/repomind/ui";
import type { ChatResult, DiligenceResult, DriftResult, NavItem, PortfolioIntelligence, PrRiskResult, RepositorySummary } from "@/components/repomind/types";
import { asScore, compactNumber, executiveScore } from "@/components/repomind/utils";

const navItems: NavItem[] = [
  { id: "overview", label: "Executive", eyebrow: "scores", icon: LayoutDashboard },
  { id: "portfolio", label: "Portfolio", eyebrow: "multi-repo", icon: Building2 },
  { id: "knowledge", label: "Knowledge", eyebrow: "graph", icon: Network },
  { id: "pr-risk", label: "PR Risk", eyebrow: "blast radius", icon: GitPullRequest },
  { id: "drift", label: "Drift", eyebrow: "baseline", icon: GitCompareArrows },
  { id: "diligence", label: "Diligence", eyebrow: "board pack", icon: ShieldCheck },
  { id: "reports", label: "Reports", eyebrow: "artifacts", icon: FileText },
  { id: "chat", label: "Chat", eyebrow: "citations", icon: MessageSquare }
];

export function RepoMindDashboard() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepo, setActiveRepo] = useState<Repository | null>(null);
  const [repoSummary, setRepoSummary] = useState<RepositorySummary | null>(null);
  const [view, setView] = useState("overview");
  const [githubUrl, setGithubUrl] = useState("");
  const [localPath, setLocalPath] = useState("sample_repos/python_fastapi_example");
  const [portfolio, setPortfolio] = useState<PortfolioIntelligence | null>(null);
  const [prResult, setPrResult] = useState<PrRiskResult | null>(null);
  const [driftResult, setDriftResult] = useState<DriftResult | null>(null);
  const [diligenceResult, setDiligenceResult] = useState<DiligenceResult | null>(null);
  const [chatResult, setChatResult] = useState<ChatResult | null>(null);
  const [activeReport, setActiveReport] = useState("CTO_DUE_DILIGENCE.md");
  const [reportText, setReportText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refreshRepositories().catch((err) => setError(messageOf(err)));
  }, []);

  useEffect(() => {
    if (!activeRepo) {
      setRepoSummary(null);
      return;
    }
    if (activeRepo.status === "complete") {
      summary(activeRepo.id).then(setRepoSummary).catch((err) => setError(messageOf(err)));
    } else {
      setRepoSummary(null);
    }
  }, [activeRepo]);

  useEffect(() => {
    if (!activeRepo || !["queued", "analyzing", "cancel_requested"].includes(activeRepo.status)) return;
    const timer = window.setInterval(async () => {
      const next = await repositoryStatus(activeRepo.id);
      setActiveRepo(next);
      setRepositories((items) => items.map((item) => (item.id === next.id ? next : item)));
      if (next.status === "complete") {
        setRepoSummary(await summary(next.id));
        await refreshRepositories(next.id);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [activeRepo]);

  useEffect(() => {
    if (!activeRepo || activeRepo.status !== "complete" || view !== "reports") return;
    fetchReport(activeRepo.id, activeReport).then(setReportText).catch((err) => setReportText(messageOf(err)));
  }, [activeRepo, activeReport, view]);

  const progress = activeRepo?.analysis_job?.progress ?? (activeRepo?.status === "complete" ? 100 : busy ? 42 : 0);
  const commandStats = useMemo(() => {
    const scores = repoSummary?.scores ?? {};
    return [
      ["Health", executiveScore(repoSummary)],
      ["Security", asScore(scores.security)],
      ["Files", compactNumber(repoSummary?.statistics?.files ?? repoSummary?.files?.length)]
    ] satisfies Array<[string, string | number]>;
  }, [repoSummary]);

  async function refreshRepositories(preferredId?: string) {
    const items = await listRepositories();
    setRepositories(items);
    setActiveRepo((current) => items.find((item) => item.id === (preferredId ?? current?.id)) ?? items[0] ?? null);
  }

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(messageOf(err));
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function ingest(label: string, fn: () => Promise<Repository>) {
    const repo = await run(label, fn);
    if (repo && typeof repo === "object" && "id" in repo) {
      setActiveRepo(repo as Repository);
      await refreshRepositories((repo as Repository).id);
    }
  }

  async function startAnalysis() {
    if (!activeRepo) return;
    const result = await run("analysis", () => analyze(activeRepo.id));
    const next = (result as { repository?: Repository } | null)?.repository;
    if (next) {
      setActiveRepo(next);
      await refreshRepositories(next.id);
    }
  }

  const activeView = renderView();

  return (
    <main className="min-h-screen bg-[#080b10] text-slate-100">
      <div className="mx-auto grid min-h-screen max-w-[1800px] grid-cols-1 gap-4 p-4 lg:grid-cols-[330px_1fr]">
        <RepositoryRail
          repositories={repositories}
          activeRepo={activeRepo}
          progress={progress}
          busy={busy}
          error={error}
          githubUrl={githubUrl}
          localPath={localPath}
          onGithubUrl={setGithubUrl}
          onLocalPath={setLocalPath}
          onSelect={setActiveRepo}
          onClone={() => ingest("clone", () => cloneRepo(githubUrl))}
          onImport={() => ingest("import", () => importLocal(localPath))}
          onUpload={(file) => ingest("upload", () => uploadZip(file))}
          onAnalyze={startAnalysis}
          onCancel={() => activeRepo && run("cancel", () => cancelAnalysis(activeRepo.id))}
        />

        <section className="min-w-0 space-y-4">
          <TopCommandBar activeRepo={activeRepo} view={view} setView={setView} stats={commandStats} />
          <nav className="grid gap-2 rounded-2xl border border-white/10 bg-slate-950/70 p-2 shadow-panel backdrop-blur-xl md:grid-cols-4 xl:grid-cols-8">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = view === item.id || (item.id === "drift" && view === "pr-risk");
              return (
                <button
                  key={item.id}
                  onClick={() => setView(item.id)}
                  className={`rounded-xl border px-3 py-3 text-left transition ${
                    active ? "border-cyan-300/35 bg-cyan-300/10 text-white" : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.045] hover:text-slate-100"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <p className="mt-2 text-sm font-semibold">{item.label}</p>
                  <p className="mt-0.5 text-[10px] uppercase tracking-[0.14em] opacity-70">{item.eyebrow}</p>
                </button>
              );
            })}
          </nav>
          {busy && !repoSummary ? <SkeletonGrid /> : activeView}
        </section>
      </div>
    </main>
  );

  function renderView() {
    if (!activeRepo && view !== "portfolio") {
      return <EmptyState title="Connect a repository" text="Clone, upload, or import a repo to start the premium intelligence workflow." />;
    }
    if (activeRepo && activeRepo.status !== "complete" && view !== "portfolio") {
      return <Panel title="Analysis in progress" eyebrow={activeRepo.analysis_job?.stage ?? activeRepo.status}><EmptyState title="Repository is not ready yet" text={activeRepo.analysis_job?.message ?? "Run analysis to generate scores, graphs, reports, and cited chat."} /></Panel>;
    }
    if (view === "overview") return <ExecutiveOverview summary={repoSummary} onNavigate={setView} />;
    if (view === "portfolio") return <PortfolioPanel data={portfolio} busy={busy === "portfolio"} onRefresh={() => run("portfolio", async () => setPortfolio(await portfolioIntelligence()))} />;
    if (view === "knowledge") return <KnowledgeGraphPanel summary={repoSummary} />;
    if (view === "pr-risk" || view === "drift") {
      return (
        <RiskAndDriftCenter
          repositories={repositories}
          activeRepo={activeRepo}
          prResult={prResult}
          driftResult={driftResult}
          busy={Boolean(busy)}
          onPrRisk={(files) => activeRepo && run("pr-risk", async () => setPrResult(await prRisk(activeRepo.id, files, "Frontend review")))}
          onDrift={(baseline) => activeRepo && run("drift", async () => setDriftResult(await architectureDrift(activeRepo.id, baseline)))}
        />
      );
    }
    if (view === "diligence") return <DiligenceCenter data={diligenceResult} busy={busy === "diligence"} onGenerate={() => activeRepo && run("diligence", async () => setDiligenceResult(await dueDiligence(activeRepo.id)))} />;
    if (view === "reports") return <ReportsCenter repo={activeRepo} summary={repoSummary} reports={reports} activeReport={activeReport} reportText={reportText} onSelectReport={setActiveReport} />;
    if (view === "chat") return <ChatExperience summary={repoSummary} answer={chatResult} busy={busy === "chat"} error={error} onAsk={(question) => activeRepo && run("chat", async () => setChatResult(await chat(activeRepo.id, question)))} />;
    return <ExecutiveOverview summary={repoSummary} onNavigate={setView} />;
  }
}

function TopCommandBar({
  activeRepo,
  view,
  setView,
  stats
}: {
  activeRepo: Repository | null;
  view: string;
  setView: (view: string) => void;
  stats: Array<[string, string | number]>;
}) {
  return (
    <header className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.09),rgba(255,255,255,0.035))] p-4 shadow-panel backdrop-blur-xl xl:flex-row xl:items-center xl:justify-between">
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-200/75">Premium repository intelligence</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h2 className="truncate text-2xl font-semibold tracking-tight text-white">{activeRepo?.name ?? "Command workspace"}</h2>
          <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{view}</Badge>
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-[1fr_auto] xl:min-w-[680px]">
        <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300">
          <Search size={15} className="text-slate-500" />
          <input className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-slate-600" placeholder="Command search: graph, reports, risk, citations" onFocus={() => setView("knowledge")} />
        </label>
        <div className="flex gap-2">
          {stats.map(([label, value]) => (
            <div key={label} className="min-w-20 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2">
              <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p>
              <p className="mt-1 text-sm font-semibold text-white">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}

function messageOf(err: unknown) {
  return err instanceof Error ? err.message : String(err);
}
