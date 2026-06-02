"use client";

import { useEffect, useMemo, useState } from "react";
import { Building2, Clock3, FileText, GitCompareArrows, GitPullRequest, LayoutDashboard, MessageSquare, Network, Route, Search, ShieldAlert, ShieldCheck } from "lucide-react";
import {
  analyze,
  architectureExplorer,
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
  repositoryEvolution,
  repositoryStatus,
  summary,
  systemStatus,
  uploadZip,
  type Repository
} from "@/lib/api";
import { ArchitectureExplorerPanel } from "@/components/repomind/ArchitectureExplorerPanel";
import { reports } from "@/components/dashboard/constants";
import { ChatExperience } from "@/components/repomind/ChatExperience";
import { DiligenceCenter } from "@/components/repomind/DiligenceCenter";
import { ExecutiveOverview } from "@/components/repomind/ExecutiveOverview";
import { KnowledgeGraphPanel } from "@/components/repomind/KnowledgeGraphPanel";
import { PortfolioPanel } from "@/components/repomind/PortfolioPanel";
import { RepositoryRail } from "@/components/repomind/RepositoryRail";
import { RepositoryEvolutionPanel } from "@/components/repomind/RepositoryEvolutionPanel";
import { RiskAndDriftCenter } from "@/components/repomind/RiskAndDriftCenter";
import { ReportsCenter } from "@/components/repomind/ReportsCenter";
import { SecurityCenter } from "@/components/repomind/SecurityCenter";
import { SystemAdminPanel } from "@/components/repomind/SystemAdminPanel";
import { Badge, Button, EmptyState, Panel, SkeletonGrid } from "@/components/repomind/ui";
import type { ArchitectureExplorerResult, ChatResult, DiligenceResult, DriftResult, NavItem, PortfolioIntelligence, PrRiskResult, RepositoryEvolution, RepositorySummary, SystemStatus } from "@/components/repomind/types";
import { asScore, compactNumber, executiveScore } from "@/components/repomind/utils";

type PrimaryNavItem = NavItem & { target: string };

const primaryNavItems: PrimaryNavItem[] = [
  { id: "executive", target: "overview", label: "Executive", eyebrow: "cockpit", icon: LayoutDashboard },
  { id: "architecture", target: "architecture", label: "Architecture", eyebrow: "flows", icon: Route },
  { id: "knowledge", target: "knowledge", label: "Knowledge Graph", eyebrow: "map", icon: Network },
  { id: "risk", target: "security", label: "Risk Center", eyebrow: "security + PR", icon: ShieldAlert },
  { id: "diligence", target: "diligence", label: "Diligence", eyebrow: "board pack", icon: ShieldCheck },
  { id: "chat", target: "chat", label: "Chat", eyebrow: "citations", icon: MessageSquare }
];

const secondaryNavGroups: Record<string, NavItem[]> = {
  executive: [
    { id: "overview", label: "Overview", eyebrow: "scorecard", icon: LayoutDashboard },
    { id: "timeline", label: "Timeline", eyebrow: "evolution", icon: Clock3 },
    { id: "portfolio", label: "Portfolio", eyebrow: "multi-repo", icon: Building2 }
  ],
  architecture: [
    { id: "architecture", label: "Explorer", eyebrow: "flows", icon: Route },
    { id: "timeline", label: "Time Machine", eyebrow: "evolution", icon: Clock3 }
  ],
  knowledge: [
    { id: "knowledge", label: "Graph", eyebrow: "relationships", icon: Network },
    { id: "architecture", label: "Explorer", eyebrow: "flows", icon: Route }
  ],
  risk: [
    { id: "security", label: "Security", eyebrow: "OWASP/CWE", icon: ShieldAlert },
    { id: "pr-risk", label: "PR Risk", eyebrow: "blast radius", icon: GitPullRequest },
    { id: "drift", label: "Drift", eyebrow: "baseline", icon: GitCompareArrows }
  ],
  diligence: [
    { id: "diligence", label: "Due Diligence", eyebrow: "board pack", icon: ShieldCheck },
    { id: "reports", label: "Reports", eyebrow: "artifacts", icon: FileText },
    { id: "portfolio", label: "Portfolio", eyebrow: "multi-repo", icon: Building2 }
  ],
  chat: [{ id: "chat", label: "Chat", eyebrow: "citations", icon: MessageSquare }]
};

function primaryForView(view: string) {
  if (["architecture"].includes(view)) return "architecture";
  if (["knowledge"].includes(view)) return "knowledge";
  if (["security", "pr-risk", "drift"].includes(view)) return "risk";
  if (["diligence", "reports"].includes(view)) return "diligence";
  if (view === "chat") return "chat";
  return "executive";
}

function viewLabel(view: string) {
  const allItems = [...primaryNavItems, ...Object.values(secondaryNavGroups).flat()];
  return allItems.find((item) => item.id === view || ("target" in item && item.target === view))?.label ?? view;
}

export function RepoMindDashboard() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepo, setActiveRepo] = useState<Repository | null>(null);
  const [repoSummary, setRepoSummary] = useState<RepositorySummary | null>(null);
  const [view, setView] = useState("overview");
  const [githubUrl, setGithubUrl] = useState("");
  const [localPath, setLocalPath] = useState("sample_repos/python_fastapi_example");
  const [portfolio, setPortfolio] = useState<PortfolioIntelligence | null>(null);
  const [architectureData, setArchitectureData] = useState<ArchitectureExplorerResult | null>(null);
  const [evolutionData, setEvolutionData] = useState<RepositoryEvolution | null>(null);
  const [prResult, setPrResult] = useState<PrRiskResult | null>(null);
  const [driftResult, setDriftResult] = useState<DriftResult | null>(null);
  const [diligenceResult, setDiligenceResult] = useState<DiligenceResult | null>(null);
  const [chatResult, setChatResult] = useState<ChatResult | null>(null);
  const [systemData, setSystemData] = useState<SystemStatus | null>(null);
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
  const activePrimary = primaryForView(view);
  const secondaryNav = secondaryNavGroups[activePrimary] ?? [];

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
      <div className="mx-auto grid min-h-screen max-w-[1800px] grid-cols-1 gap-3 p-3 sm:gap-4 sm:p-4 lg:grid-cols-[330px_1fr]">
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
          <nav aria-label="Primary navigation" className="grid grid-cols-2 gap-2 rounded-2xl border border-white/10 bg-slate-950/70 p-2 shadow-panel backdrop-blur-xl md:grid-cols-3 xl:grid-cols-6">
            {primaryNavItems.map((item) => {
              const Icon = item.icon;
              const active = activePrimary === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setView(item.target)}
                  className={`min-h-[86px] rounded-xl border px-3 py-3 text-left transition ${
                    active ? "border-cyan-300/35 bg-cyan-300/10 text-white" : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.045] hover:text-slate-100"
                  }`}
                >
                  <div className="flex h-full flex-col justify-between gap-2">
                    <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg border ${active ? "border-cyan-200/30 bg-cyan-200/10 text-cyan-100" : "border-white/10 bg-white/[0.035] text-slate-400"}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0">
                      <span className="block whitespace-normal text-sm font-semibold leading-tight sm:text-[15px]">{item.label}</span>
                      <span className="mt-1 block truncate text-[10px] uppercase leading-tight tracking-[0.12em] opacity-70">{item.eyebrow}</span>
                    </span>
                  </div>
                </button>
              );
            })}
          </nav>
          <nav aria-label="Context navigation" className="flex flex-wrap items-center gap-2 rounded-2xl border border-white/10 bg-slate-950/55 p-2 shadow-panel backdrop-blur-xl">
            <span className="hidden px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 md:inline">{primaryNavItems.find((item) => item.id === activePrimary)?.label}</span>
            {secondaryNav.map((item) => {
              const Icon = item.icon;
              const active = view === item.id;
              return (
                <button
                  key={`${activePrimary}-${item.id}`}
                  onClick={() => setView(item.id)}
                  className={`inline-flex min-h-9 items-center gap-2 rounded-full border px-3 text-sm font-medium transition ${
                    active ? "border-white/15 bg-white/[0.09] text-white" : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.05] hover:text-slate-100"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{item.label}</span>
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
    if (!activeRepo && !["portfolio", "admin"].includes(view)) {
      return <EmptyState title="Connect a repository" text="Clone, upload, or import a repo to start the premium intelligence workflow." />;
    }
    if (activeRepo && activeRepo.status !== "complete" && !["portfolio", "admin"].includes(view)) {
      return <Panel title="Analysis in progress" eyebrow={activeRepo.analysis_job?.stage ?? activeRepo.status}><EmptyState title="Repository is not ready yet" text={activeRepo.analysis_job?.message ?? "Run analysis to generate scores, graphs, reports, and cited chat."} /></Panel>;
    }
    if (view === "overview") return <ExecutiveOverview summary={repoSummary} onNavigate={setView} />;
    if (view === "architecture") return <ArchitectureExplorerPanel data={architectureData} busy={busy === "architecture"} onGenerate={() => activeRepo && run("architecture", async () => setArchitectureData(await architectureExplorer(activeRepo.id)))} />;
    if (view === "timeline") return <RepositoryEvolutionPanel data={evolutionData} busy={busy === "timeline"} onGenerate={() => activeRepo && run("timeline", async () => setEvolutionData(await repositoryEvolution(activeRepo.id)))} />;
    if (view === "portfolio") return <PortfolioPanel data={portfolio} busy={busy === "portfolio"} onRefresh={() => run("portfolio", async () => setPortfolio(await portfolioIntelligence()))} />;
    if (view === "knowledge") return <KnowledgeGraphPanel summary={repoSummary} />;
    if (view === "security") return <SecurityCenter summary={repoSummary} />;
    if (view === "pr-risk" || view === "drift") {
      return (
        <RiskAndDriftCenter
          repositories={repositories}
          activeRepo={activeRepo}
          prResult={prResult}
          driftResult={driftResult}
          busy={Boolean(busy)}
          onPrRisk={(files, prUrl, repository, prNumber) => activeRepo && run("pr-risk", async () => setPrResult(await prRisk(activeRepo.id, files, "Frontend review", prUrl, repository, prNumber)))}
          onDrift={(baseline, compareType, baselineRef, targetRef) => activeRepo && run("drift", async () => setDriftResult(await architectureDrift(activeRepo.id, baseline, compareType, baselineRef, targetRef)))}
        />
      );
    }
    if (view === "diligence") return <DiligenceCenter data={diligenceResult} busy={busy === "diligence"} onGenerate={() => activeRepo && run("diligence", async () => setDiligenceResult(await dueDiligence(activeRepo.id)))} />;
    if (view === "reports") return <ReportsCenter repo={activeRepo} summary={repoSummary} reports={reports} activeReport={activeReport} reportText={reportText} onSelectReport={setActiveReport} />;
    if (view === "chat") return <ChatExperience summary={repoSummary} answer={chatResult} busy={busy === "chat"} error={error} onAsk={(question) => activeRepo && run("chat", async () => setChatResult(await chat(activeRepo.id, question)))} />;
    if (view === "admin") return <SystemAdminPanel data={systemData} busy={busy === "admin"} onRefresh={() => run("admin", async () => setSystemData(await systemStatus()))} />;
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
          <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{viewLabel(view)}</Badge>
        </div>
      </div>
      <div className="grid min-w-0 gap-2 md:grid-cols-[minmax(220px,1fr)_auto] xl:min-w-[640px]">
        <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300">
          <Search size={15} className="text-slate-500" />
          <input className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-slate-600" placeholder="Search graph, reports, risk, citations" onFocus={() => setView("knowledge")} />
        </label>
        <div className="grid grid-cols-3 gap-2 md:flex">
          {stats.map(([label, value]) => (
            <div key={label} className="min-w-0 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 md:min-w-20">
              <p className="truncate text-[10px] uppercase tracking-[0.12em] text-slate-500">{label}</p>
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
