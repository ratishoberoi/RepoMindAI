"use client";

import { useEffect, useId, useMemo, useState } from "react";
import type { ReactNode } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps
} from "@xyflow/react";
import {
  Activity,
  Archive,
  Bot,
  Boxes,
  Brain,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Code2,
  Cpu,
  Database,
  Download,
  Expand,
  FileCode2,
  FolderInput,
  Map as MapIcon,
  Network,
  Search,
  Server,
  ShieldAlert,
  Sparkles,
  Workflow
} from "lucide-react";
import {
  analyze,
  cancelAnalysis,
  chat,
  cloneRepo,
  exportUrl,
  fetchReport,
  importLocal,
  listRepositories,
  repositoryStatus,
  reportUrl,
  summary,
  uploadZip,
  type Repository
} from "@/lib/api";
import { ControlLabel, Empty, EvidenceList, GlassPanel, IconButton, Info, TextInput } from "@/components/dashboard/Controls";
import { DashboardSidebar, ExportBundleLink, RepositoryHeader } from "@/components/dashboard/ShellPanels";
import { reports } from "@/components/dashboard/constants";
import { buildTree, shortName } from "@/components/dashboard/tree";
const nodeTypes = { intelligence: IntelligenceNode };
const FLOW_NODE_WIDTH = 246;
const FLOW_NODE_HEIGHT = 112;

type IntelligenceNodeData = {
  label: string;
  subtitle?: string;
  kind: string;
  module?: string;
  files?: string[];
  color: string;
  icon?: string;
  layer?: string;
  count?: number;
  expanded?: boolean;
  purpose?: string;
  why?: string;
  dependents?: string[];
  failure?: string;
  importance?: "Critical" | "High" | "Medium" | "Low";
};

export function RepoMindDashboard() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepo, setActiveRepo] = useState<Repository | null>(null);
  const [repoSummary, setRepoSummary] = useState<any>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [localPath, setLocalPath] = useState("sample_repos/python_fastapi_example");
  const [question, setQuestion] = useState("How does authentication work?");
  const [answer, setAnswer] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("Overview");
  const [activeReport, setActiveReport] = useState("ARCHITECTURE.md");
  const [reportText, setReportText] = useState("");
  const [expandedTree, setExpandedTree] = useState<Record<string, boolean>>({});

  useEffect(() => {
    refreshRepositories();
  }, []);

  useEffect(() => {
    if (!activeRepo || activeRepo.status !== "complete") {
      setRepoSummary(null);
      return;
    }
    summary(activeRepo.id).then(setRepoSummary);
  }, [activeRepo]);

  useEffect(() => {
    if (!activeRepo || !["queued", "analyzing", "cancel_requested"].includes(activeRepo.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await repositoryStatus(activeRepo.id);
        setActiveRepo(next);
        if (next.status === "complete") {
          const nextSummary = await summary(next.id);
          setRepoSummary(nextSummary);
          await refreshRepositories();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [activeRepo]);

  useEffect(() => {
    if (!activeRepo || activeRepo.status !== "complete" || tab !== "Reports") return;
    fetchReport(activeRepo.id, activeReport).then(setReportText).catch((err) => setReportText(String(err)));
  }, [activeRepo, activeReport, tab]);

  async function refreshRepositories() {
    const items = await listRepositories();
    setRepositories(items);
    setActiveRepo((current) => current ?? items[0] ?? null);
  }

  async function runAction(label: string, fn: () => Promise<any>) {
    setBusy(label);
    setError(null);
    try {
      const result = await fn();
      const repo = result.repository ?? result;
      if (repo?.id) {
        setActiveRepo(repo);
        await refreshRepositories();
      }
      if (result.summary) setRepoSummary(result.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  const scoreCards = useMemo(() => {
    const scores = repoSummary?.scores ?? {};
    return [
      ["Security", scores.security, ShieldAlert],
      ["Maintainability", scores.maintainability, Activity],
      ["Production", scores.production_readiness, CircleDot],
      ["CTO", scores.cto, Bot]
    ];
  }, [repoSummary]);

  const tree = useMemo(() => buildTree(repoSummary?.files ?? []), [repoSummary]);
  const progress = activeRepo?.analysis_job?.progress ?? (activeRepo?.status === "complete" ? 100 : busy ? 66 : activeRepo ? 30 : 0);

  return (
    <main className="min-h-screen overflow-hidden bg-void text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,211,238,0.18),transparent_28%),radial-gradient(circle_at_80%_0%,rgba(16,185,129,0.16),transparent_24%)]" />
      <div className="relative mx-auto grid min-h-screen max-w-[1500px] grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[320px_1fr]">
        <DashboardSidebar
          repositories={repositories}
          activeRepo={activeRepo}
          progress={progress}
          busy={busy}
          error={error}
          githubUrl={githubUrl}
          localPath={localPath}
          setGithubUrl={setGithubUrl}
          setLocalPath={setLocalPath}
          setActiveRepo={setActiveRepo}
          onClone={() => runAction("clone", () => cloneRepo(githubUrl))}
          onImport={() => runAction("import", () => importLocal(localPath))}
          onUpload={(file) => runAction("upload", () => uploadZip(file))}
        />

        <section className="space-y-4">
          <RepositoryHeader
            activeRepo={activeRepo}
            busy={busy}
            tab={tab}
            setTab={setTab}
            onAnalyze={() => activeRepo && runAction("analysis", () => analyze(activeRepo.id))}
            onCancel={() => activeRepo && runAction("cancel", () => cancelAnalysis(activeRepo.id))}
          />

          {!repoSummary ? (
            <GlassPanel title="Workspace">
              <Empty text="Analyze a repository to view diagrams, dependency graphs, scores, reports, and semantic chat." />
            </GlassPanel>
          ) : null}

          {repoSummary && tab === "Overview" ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                {scoreCards.map(([label, value, Icon]: any) => (
                  <GlassPanel key={label}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">{label}</span>
                      <Icon size={18} className="text-cyan-200" />
                    </div>
                    <div className="mt-3 text-3xl font-semibold">{value ?? "--"}</div>
                  </GlassPanel>
                ))}
              </div>
              <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
                <GlassPanel title="Repository Map">
                  <RepositoryMap components={repoSummary.architecture?.components ?? []} />
                </GlassPanel>
                <GlassPanel title="File Tree">
                  <FileTree tree={tree} expanded={expandedTree} setExpanded={setExpandedTree} />
                </GlassPanel>
              </div>
            </div>
          ) : null}

          {repoSummary && tab === "Architecture" ? (
            <div className="space-y-4">
              <GlassPanel title="Architecture Explorer">
                <div className="grid gap-3 md:grid-cols-2">
                  <Info label="Style" value={repoSummary.architecture?.style} />
                  <Info label="Primary language" value={repoSummary.languages?.primary} />
                  <Info label="Frameworks" value={(repoSummary.stack?.frameworks ?? []).join(", ") || "None detected"} />
                  <Info label="Routes" value={String(repoSummary.statistics?.routes ?? 0)} />
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-300">{repoSummary.architecture?.summary}</p>
              </GlassPanel>
              <GlassPanel title="Interactive Architecture Canvas">
                <ArchitectureCanvas summary={repoSummary} />
              </GlassPanel>
            </div>
          ) : null}

          {repoSummary && tab === "Knowledge" ? (
            <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
              <GlassPanel title="Repository Knowledge Graph">
                <div className="grid gap-3 md:grid-cols-4">
                  <Info label="Entities" value={String(repoSummary.knowledge_graph?.metrics?.entities ?? 0)} />
                  <Info label="Relations" value={String(repoSummary.knowledge_graph?.metrics?.relations ?? 0)} />
                  <Info label="Domains" value={String(repoSummary.knowledge_graph?.metrics?.domains ?? 0)} />
                  <Info label="Hotspots" value={String((repoSummary.knowledge_graph?.hotspots ?? []).length)} />
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {(repoSummary.knowledge_graph?.domains ?? []).slice(0, 10).map((domain: any) => (
                    <div key={domain.name} className="rounded-md border border-white/10 bg-black/20 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium text-cyan-100">{domain.name}</div>
                        <span className="rounded bg-white/10 px-2 py-1 text-xs text-slate-300">{domain.role}</span>
                      </div>
                      <div className="mt-2 text-xs text-slate-400">{domain.file_count} files · {domain.routes} routes · {domain.data_models} models · {domain.security_findings} security findings</div>
                      <div className="mt-2 space-y-1">
                        {(domain.sample_files ?? []).slice(0, 3).map((path: string) => <div key={path} className="truncate text-xs text-slate-300">{path}</div>)}
                      </div>
                    </div>
                  ))}
                </div>
              </GlassPanel>
              <GlassPanel title="Risk Hotspots">
                <div className="space-y-2">
                  {(repoSummary.knowledge_graph?.hotspots ?? []).slice(0, 12).map((item: any) => (
                    <div key={item.path} className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm">
                      <div className="break-words font-medium text-slate-100">{item.path}</div>
                      <div className="mt-1 text-xs text-slate-400">risk {item.risk_score} · connectivity {item.connectivity}</div>
                      <div className="mt-1 text-xs text-cyan-100">{item.reason}</div>
                    </div>
                  ))}
                </div>
              </GlassPanel>
            </div>
          ) : null}

          {repoSummary && tab === "Dependencies" ? (
            <GlassPanel title="Dependency Explorer">
              <DependencyGraph graph={repoSummary.graph} />
            </GlassPanel>
          ) : null}

          {repoSummary && tab === "Security" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <GlassPanel title="Security Score Evidence">
                <ScoreEvidence detail={repoSummary.scores?.details?.security} />
              </GlassPanel>
              <GlassPanel title="Findings">
                <FindingList items={(repoSummary.security?.findings ?? []).slice(0, 14)} />
              </GlassPanel>
            </div>
          ) : null}

          {repoSummary && tab === "Reports" ? (
            <div className="grid gap-4 xl:grid-cols-[280px_1fr]">
              <GlassPanel title="AI Reports">
                <div className="space-y-2">
                  {reports.map((name) => (
                    <button key={name} onClick={() => setActiveReport(name)} className={`flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left text-sm ${activeReport === name ? "border-cyan-300/60 bg-cyan-300/10" : "border-white/10 bg-white/[0.03]"}`}>
                      <Archive size={15} />
                      <span className="truncate">{name}</span>
                    </button>
                  ))}
                  <ExportBundleLink href={exportUrl(activeRepo!.id)} />
                </div>
              </GlassPanel>
              <GlassPanel title={activeReport}>
                <pre className="max-h-[650px] overflow-auto whitespace-pre-wrap rounded-md border border-white/10 bg-black/30 p-4 text-sm leading-6 text-slate-200">{reportText || "Select a report."}</pre>
                <a className="mt-3 inline-flex text-sm text-cyan-200" href={reportUrl(activeRepo!.id, activeReport)} target="_blank">Open raw report</a>
              </GlassPanel>
            </div>
          ) : null}

          {repoSummary && tab === "Chat" ? (
            <GlassPanel title="Semantic Repository Chat">
              <div className="flex gap-2">
                <TextInput value={question} onChange={setQuestion} />
                <IconButton title="Ask" disabled={!question || !!busy} onClick={() => activeRepo && runAction("chat", async () => {
                  const result = await chat(activeRepo.id, question);
                  setAnswer(result);
                  return activeRepo;
                })}>
                  <Search size={18} />
                </IconButton>
              </div>
              {answer ? (
                <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_360px]">
                  <AnswerPanel answer={answer.answer} />
                  <div className="space-y-3">
                    <MermaidDiagram chart={answer.diagram} />
                    <CitationList items={answer.citations ?? []} />
                  </div>
                </div>
              ) : null}
            </GlassPanel>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function RepositoryMap({ components }: { components: any[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {components.slice(0, 9).map((component) => (
        <div key={component.name} className="rounded-md border border-white/10 bg-black/20 p-3">
          <div className="flex items-center gap-2 text-sm font-semibold"><MapIcon size={16} className="text-cyan-200" />{component.name}</div>
          <div className="mt-1 text-xs text-slate-400">{component.role} · {component.file_count} files</div>
          <div className="mt-3 space-y-1 text-xs text-slate-300">
            {(component.files ?? []).slice(0, 4).map((file: string) => <div key={file} className="truncate">{file}</div>)}
          </div>
        </div>
      ))}
    </div>
  );
}

function MermaidDiagram({ chart }: { chart: string }) {
  const id = useId().replaceAll(":", "");
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function render() {
      setError("");
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "dark",
          themeVariables: {
            background: "#020617",
            primaryColor: "#0f172a",
            primaryTextColor: "#e2e8f0",
            primaryBorderColor: "#67e8f9",
            lineColor: "#7dd3fc",
            tertiaryColor: "#111827"
          }
        });
        const result = await mermaid.render(`diagram-${id}`, chart);
        if (!cancelled) setSvg(result.svg);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    }
    render();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-red-400/30 bg-red-500/10 p-3 text-xs text-red-100">{chart}</pre>;
  }
  return (
    <div className="min-h-48 overflow-auto rounded-md border border-white/10 bg-slate-950/70 p-3">
      {svg ? <div className="mermaid-svg" dangerouslySetInnerHTML={{ __html: svg }} /> : <div className="h-48 animate-pulse rounded bg-white/5" />}
    </div>
  );
}

function AnswerPanel({ answer }: { answer: string }) {
  const sections = parseAnswerSections(answer);
  return (
    <div className="space-y-3">
      {sections.map((section) => (
        <div key={section.title} className="rounded-lg border border-white/10 bg-black/25 p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-cyan-200">{section.title}</div>
          {section.title === "DIAGRAM" || section.title === "MERMAID DIAGRAM" ? (
            <div className="rounded-md border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-sm text-cyan-100">Rendered visually in the diagram panel.</div>
          ) : (
            <AnswerSectionBody body={section.body} />
          )}
        </div>
      ))}
    </div>
  );
}

function AnswerSectionBody({ body }: { body: string }) {
  const lines = body.split(/\r?\n/).filter(Boolean);
  const bulletLines = lines.filter((line) => line.trim().startsWith("- "));
  if (bulletLines.length === lines.length && lines.length > 0) {
    return (
      <ul className="space-y-1 text-sm leading-6 text-slate-200">
        {lines.map((line) => {
          const value = line.replace(/^-\s*/, "").replaceAll("`", "");
          return <li key={line} className="flex gap-2"><span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-300" /><span className="break-words">{value}</span></li>;
        })}
      </ul>
    );
  }
  return <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">{body.replaceAll("`", "")}</p>;
}

function parseAnswerSections(answer: string) {
  const headings = ["DIRECT ANSWER", "ARCHITECTURE IMPACT", "CRITICAL FILES", "DIAGRAM", "MERMAID DIAGRAM", "RISKS", "IMPROVEMENTS", "CITATIONS"];
  const lines = answer.split(/\r?\n/);
  const sections: { title: string; body: string }[] = [];
  let current: { title: string; body: string[] } | null = null;
  for (const line of lines) {
    const normalized = line.replace(/^#+\s*/, "").replace(/^\d+\.\s*/, "").trim().toUpperCase();
    if (headings.includes(normalized)) {
      if (current) sections.push({ title: current.title, body: current.body.join("\n").trim() });
      current = { title: normalized, body: [] };
    } else if (current) {
      current.body.push(line);
    }
  }
  if (current) sections.push({ title: current.title, body: current.body.join("\n").trim() });
  return sections.length ? sections : [{ title: "DIRECT ANSWER", body: answer }];
}

function DependencyGraph({ graph }: { graph: any }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const [focusLayer, setFocusLayer] = useState<string | null>(null);
  const flow = useMemo(() => buildLayeredDependencyFlow(graph, query, focusLayer, selected?.id), [graph, query, focusLayer, selected?.id]);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-white/10 bg-black/25 px-3 py-2">
          <Search size={16} className="text-slate-500" />
          <input className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search layer, module, dependency, or file" />
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setFocusLayer(null)} className={`rounded-md px-3 py-2 text-xs ${focusLayer === null ? "bg-white text-slate-950" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}>All layers</button>
          {dependencyLayers.map((layer) => (
            <button key={layer.id} onClick={() => setFocusLayer(layer.id)} className={`rounded-md px-3 py-2 text-xs ${focusLayer === layer.id ? "bg-white text-slate-950" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}>
              {layer.label}
            </button>
          ))}
        </div>
      </div>
      <div className="relative">
        <AutoLayoutFlow nodes={flow.nodes} edges={flow.edges} height="h-[660px]" direction="RIGHT" layout="manual" onNodeClick={setSelected} />
        {selected ? (
          <div className="absolute right-4 top-4 z-20 w-[360px] max-w-[calc(100%-32px)]">
            <NodeDetails node={selected} empty="Select a layer or module to inspect dependency responsibility, blast radius, and critical files." />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ArchitectureCanvas({ summary }: { summary: any }) {
  const [selected, setSelected] = useState<any>(null);
  const [view, setView] = useState("executive");
  const [search, setSearch] = useState("");
  const [focus, setFocus] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [fullscreen, setFullscreen] = useState(false);
  const flow = useMemo(() => buildArchitectureLevelFlow(summary, view, search, focus, expanded, selected?.id), [summary, view, search, focus, expanded, selected?.id]);
  const views = [
    ["executive", "Executive"],
    ["service", "Service"],
    ["module", "Module"],
    ["implementation", "Implementation"]
  ];

  function handleNodeClick(node: any) {
    setSelected(node);
    if (view === "module" && node.data.kind === "module") {
      setExpanded((current) => ({ ...current, [node.id]: !current[node.id] }));
    }
  }

  const canvas = (height = "h-[520px]") => (
    <div className="relative h-full">
      <AutoLayoutFlow nodes={flow.nodes} edges={flow.edges} height={height} direction={view === "service" ? "RIGHT" : "RIGHT"} onNodeClick={handleNodeClick} />
      {selected ? (
        <div className="absolute right-4 top-4 z-20 w-[360px] max-w-[calc(100%-32px)]">
          <NodeDetails node={selected} empty="Select a system, service, module, or implementation node to inspect impact and evidence." />
        </div>
      ) : null}
    </div>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 2xl:flex-row 2xl:items-center 2xl:justify-between">
        <div className="flex flex-wrap gap-2">
          {views.map(([id, label]) => (
            <button key={id} onClick={() => { setView(id); setSelected(null); setFocus(null); }} className={`rounded-md px-3 py-2 text-sm ${view === id ? "bg-white text-slate-950" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}>
              {label}
            </button>
          ))}
        </div>
        <div className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-2">
          <div className="flex min-w-[240px] flex-1 items-center gap-2 rounded-md border border-white/10 bg-black/25 px-3 py-2">
            <Search size={16} className="text-slate-500" />
            <input className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search module, service, or file" />
          </div>
          <button className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm text-slate-200 hover:bg-white/15" onClick={() => setFocus(selected?.id ?? null)}><CircleDot size={15} />Focus</button>
          <button className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm text-slate-200 hover:bg-white/15" onClick={() => { setFocus(null); setSearch(""); }}><Network size={15} />Reset</button>
          <button className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm text-slate-200 hover:bg-white/15" onClick={() => exportFlowSvg(flow.nodes, flow.edges, "architecture.svg")}><Download size={15} />SVG</button>
          <button className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm text-slate-200 hover:bg-white/15" onClick={() => exportFlowPng(flow.nodes, flow.edges, "architecture.png")}><Download size={15} />PNG</button>
          <button className="inline-flex items-center gap-2 rounded-md bg-cyan-300 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-200" onClick={() => setFullscreen(true)}><Expand size={15} />Fullscreen</button>
        </div>
      </div>
      <ArchitectureViewBrief view={view} summary={summary} />
      {canvas()}
      {fullscreen ? (
        <div className="fixed inset-0 z-50 bg-slate-950/95 p-5 backdrop-blur">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold">Architecture Canvas</div>
              <div className="text-xs uppercase text-slate-500">{view} view</div>
            </div>
            <button className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-950" onClick={() => setFullscreen(false)}>Close</button>
          </div>
          {canvas("h-[calc(100vh-110px)]")}
        </div>
      ) : null}
    </div>
  );
}

function FlowShell({ height, children }: { height: string; children: ReactNode }) {
  return <div className={`${height} overflow-hidden rounded-lg border border-white/10 bg-[#050814] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]`}>{children}</div>;
}

function AutoLayoutFlow({ nodes, edges, height, direction, layout = "auto", onNodeClick }: { nodes: Node[]; edges: Edge[]; height: string; direction: "RIGHT" | "DOWN"; layout?: "auto" | "manual"; onNodeClick: (node: any) => void }) {
  const [layoutNodes, setLayoutNodes] = useState(nodes);

  useEffect(() => {
    let cancelled = false;
    setLayoutNodes(nodes);
    if (layout === "manual") return () => {
      cancelled = true;
    };
    layoutWithElk(nodes, edges, direction)
      .then((nextNodes) => {
        if (!cancelled) setLayoutNodes(nextNodes);
      })
      .catch(() => {
        if (!cancelled) setLayoutNodes(layoutWithDagre(nodes, edges, direction));
      });
    return () => {
      cancelled = true;
    };
  }, [nodes, edges, direction, layout]);

  return (
    <FlowShell height={height}>
      <ReactFlowProvider>
        <AutoLayoutCanvas nodes={layoutNodes} edges={edges} onNodeClick={onNodeClick} />
      </ReactFlowProvider>
    </FlowShell>
  );
}

function AutoLayoutCanvas({ nodes, edges, onNodeClick }: { nodes: Node[]; edges: Edge[]; onNodeClick: (node: any) => void }) {
  const flow = useReactFlow();

  useEffect(() => {
    const id = window.setTimeout(() => flow.fitView({ padding: 0.16, duration: 260 }), 60);
    return () => window.clearTimeout(id);
  }, [flow, nodes]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.16 }}
      minZoom={0.2}
      maxZoom={2.4}
      onNodeClick={(_, node) => onNodeClick(node)}
      nodesDraggable
      proOptions={{ hideAttribution: true }}
    >
      <Background color="rgba(148,163,184,0.12)" gap={22} />
      <Controls className="flow-controls" />
      <MiniMap pannable zoomable position="top-right" maskColor="rgba(15,23,42,0.58)" nodeStrokeWidth={2} style={{ width: 150, height: 90 }} nodeColor={(node) => String(node.data.color ?? "#67e8f9")} className="flow-minimap" />
    </ReactFlow>
  );
}

function ArchitectureViewBrief({ view, summary }: { view: string; summary: any }) {
  const stats = summary?.statistics ?? {};
  const details: Record<string, { title: string; explanation: string; impact: string; services: string; risks: string }> = {
    executive: {
      title: "Executive Architecture",
      explanation: "A five-system map for understanding the product in seconds: frontend, backend, analysis engine, vector store, and local LLM.",
      impact: "Best for recruiters, CTOs, and first-time GitHub visitors who need the product shape without implementation noise.",
      services: "Frontend, Backend, Analysis Engine, Vector Store, Local LLM.",
      risks: "If this view needs files to make sense, the architecture abstraction is failing."
    },
    service: {
      title: "Service Architecture",
      explanation: "A workflow-level service map showing ingestion, AST extraction, dependency/security analysis, RAG, and reporting.",
      impact: "Best for senior engineers reviewing how repository evidence moves through the system.",
      services: "Repository Ingestion, AST Analysis, Dependency Engine, Security Engine, RAG Engine, Report Engine.",
      risks: "Weak service boundaries make report quality and answer quality harder to debug."
    },
    module: {
      title: "Module Architecture",
      explanation: "A collapsed module map for code ownership. Expand only when implementation evidence is needed.",
      impact: `Best for maintainers navigating ${stats.files ?? "the"} analyzed files without turning the graph into a file hairball.`,
      services: "frontend/*, ingestion/*, analysis/*, rag/*, reports/*, llm/*, storage/*.",
      risks: "Over-expansion can degrade readability; default view stays collapsed by design."
    },
    implementation: {
      title: "Implementation Architecture",
      explanation: "The only view that exposes files, routes, classes, functions, imports, and symbols.",
      impact: "Best for debugging or validating that high-level diagrams are backed by concrete source evidence.",
      services: "Important files, route symbols, class/function definitions, and dependency edges.",
      risks: "This level is intentionally technical and should not be used as the product's primary architecture story."
    }
  };
  const item = details[view] ?? details.executive;
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <Info label={item.title} value={item.explanation} />
      <Info label="Impact" value={item.impact} />
      <Info label="Critical services" value={item.services} />
      <Info label="Risk analysis" value={item.risks} />
    </div>
  );
}

function IntelligenceNode({ data }: NodeProps) {
  const nodeData = data as IntelligenceNodeData;
  const Icon = iconFor(nodeData.icon);
  return (
    <div className="intelligence-node group" style={{ ["--node-color" as any]: nodeData.color }}>
      <Handle type="target" position={Position.Left} className="flow-handle" />
      <div className="flex items-start gap-3">
        <div className="node-icon"><Icon size={17} /></div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="truncate text-sm font-semibold text-slate-100">{nodeData.label}</div>
            {nodeData.importance ? <span className="node-badge">{nodeData.importance}</span> : null}
          </div>
          {nodeData.subtitle ? <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-400">{nodeData.subtitle}</div> : null}
          <div className="mt-3 flex items-center justify-between gap-2 text-[11px] uppercase text-slate-500">
            <span>{nodeData.layer ?? nodeData.kind}</span>
            {typeof nodeData.count === "number" ? <span>{nodeData.count} items</span> : null}
            {nodeData.expanded !== undefined ? <span>{nodeData.expanded ? "expanded" : "collapsed"}</span> : null}
          </div>
        </div>
      </div>
      <div className="node-hover-card">
        <ImpactLine label="Does" value={nodeData.purpose} />
        <ImpactLine label="Exists" value={nodeData.why} />
        <ImpactLine label="Depends" value={(nodeData.dependents ?? []).join(", ") || "No downstream service detected"} />
        <ImpactLine label="Failure" value={nodeData.failure} />
      </div>
      <Handle type="source" position={Position.Right} className="flow-handle" />
    </div>
  );
}

function ImpactLine({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <span className="text-slate-500">{label}: </span>
      <span className="text-slate-200">{value ?? "No evidence available"}</span>
    </div>
  );
}

function NodeDetails({ node, empty }: { node: any; empty: string }) {
  if (!node) {
    return <div className="rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-slate-400">{empty}</div>;
  }
  const data = node.data as IntelligenceNodeData;
  const files = Array.isArray(data.files) ? data.files : [];
  return (
    <aside className="rounded-lg border border-white/10 bg-black/20 p-4">
      <div className="text-xs uppercase text-slate-500">{data.kind}</div>
      <div className="mt-1 break-words text-lg font-semibold text-slate-100">{data.label}</div>
      {data.subtitle ? <div className="mt-2 text-sm leading-6 text-slate-400">{data.subtitle}</div> : null}
      <div className="mt-4 grid gap-2 text-sm">
        <Info label="What it does" value={data.purpose ?? "No evidence available"} />
        <Info label="Why it exists" value={data.why ?? "No evidence available"} />
        <Info label="Depends on it" value={(data.dependents ?? []).join(", ") || "No downstream service detected"} />
        <Info label="If it fails" value={data.failure ?? "Unknown impact"} />
        <Info label="Importance" value={data.importance ?? "Medium"} />
      </div>
      {files.length ? (
        <div className="mt-4">
          <div className="mb-2 text-xs uppercase text-slate-500">Evidence files</div>
          <div className="space-y-2">
            {files.slice(0, 14).map((file: string) => <div key={file} className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-300">{file}</div>)}
          </div>
        </div>
      ) : null}
    </aside>
  );
}

function buildArchitectureLevelFlow(summary: any, view: string, query: string, focus: string | null, expanded: Record<string, boolean>, selectedId?: string): { nodes: Node[]; edges: Edge[] } {
  const level = view === "service" ? serviceArchitecture() : view === "module" ? moduleArchitecture(summary, expanded) : view === "implementation" ? implementationArchitecture(summary) : executiveArchitecture(summary);
  return applyFlowState(level.nodes, level.edges, query, focus, selectedId);
}

async function layoutWithElk(nodes: Node[], edges: Edge[], direction: "RIGHT" | "DOWN") {
  const { default: ELK } = await import("elkjs/lib/elk.bundled.js");
  const elk = new ELK();
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.spacing.nodeNodeBetweenLayers": "92",
      "elk.spacing.nodeNode": "54",
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
    },
    children: nodes.map((node) => ({
      id: node.id,
      width: FLOW_NODE_WIDTH,
      height: FLOW_NODE_HEIGHT,
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };
  const layout = await elk.layout(graph);
  const positions = new Map((layout.children ?? []).map((child: any) => [child.id, { x: child.x ?? 0, y: child.y ?? 0 }]));
  return nodes.map((node) => ({ ...node, position: positions.get(node.id) ?? node.position }));
}

function layoutWithDagre(nodes: Node[], edges: Edge[], direction: "RIGHT" | "DOWN") {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({
    rankdir: direction === "RIGHT" ? "LR" : "TB",
    ranksep: 92,
    nodesep: 54,
    marginx: 20,
    marginy: 20,
  });
  nodes.forEach((node) => graph.setNode(node.id, { width: FLOW_NODE_WIDTH, height: FLOW_NODE_HEIGHT }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);
  return nodes.map((node) => {
    const point = graph.node(node.id);
    return {
      ...node,
      position: point ? { x: point.x - FLOW_NODE_WIDTH / 2, y: point.y - FLOW_NODE_HEIGHT / 2 } : node.position,
    };
  });
}

function executiveArchitecture(summary: any): { nodes: Node[]; edges: Edge[] } {
  const repoName = summary?.repository?.name ?? "Repository";
  const nodes = [
    intelNode("executive-frontend", "Frontend", "Operator workspace", "system", 0, 70, "#67e8f9", "frontend", [], "Accepts GitHub URLs, shows progress, diagrams, reports, and chat.", "Gives reviewers one visual surface for repository intelligence.", ["Backend"], "Users cannot ingest repositories or inspect results.", "High"),
    intelNode("executive-backend", "Backend", "FastAPI orchestration API", "system", 300, 70, "#93c5fd", "server", [], "Coordinates ingestion, analysis, report access, and repository chat.", "Keeps the UI thin and centralizes repository processing.", ["Frontend", "Analysis Engine", "Vector Store", "LLM"], "Analysis jobs, summaries, and chat responses stop.", "Critical"),
    intelNode("executive-analysis", "Analysis Engine", "AST, dependency, security, and scoring", "system", 600, 0, "#a7f3d0", "analysis", [], "Turns repository contents into structured architecture, security, and quality evidence.", `Produces the intelligence layer for ${repoName}.`, ["Backend", "Report Engine", "RAG"], "Reports lose evidence and diagrams become shallow.", "Critical"),
    intelNode("executive-vector", "Vector Store", "Chroma semantic index", "system", 900, 70, "#fca5a5", "database", [], "Stores embeddings for grounded repository retrieval.", "Makes repository questions evidence-backed instead of generic.", ["RAG Engine"], "Chat cannot cite the right files or may return no evidence.", "High"),
    intelNode("executive-llm", "Local LLM", "qwen-judge inference", "system", 900, 170, "#f0abfc", "llm", [], "Generates reviews, explanations, and answers from retrieved evidence.", "Provides local model output without routing or fallback generation.", ["Report Engine", "RAG Engine"], "AI reviews and repository answers fail visibly.", "High")
  ];
  const edges = [
    intelEdge("executive-frontend", "executive-backend", "uses"),
    intelEdge("executive-backend", "executive-analysis", "analyzes"),
    intelEdge("executive-analysis", "executive-vector", "indexes"),
    intelEdge("executive-analysis", "executive-llm", "prompts"),
    intelEdge("executive-backend", "executive-vector", "reads"),
    intelEdge("executive-backend", "executive-llm", "generates")
  ];
  return { nodes, edges };
}

function serviceArchitecture(): { nodes: Node[]; edges: Edge[] } {
  const nodes = [
    intelNode("svc-ingestion", "Repository Ingestion Service", "Clone, upload, import, cleanup lifecycle", "service", 0, 170, "#67e8f9", "ingestion", [], "Creates a temporary working copy and persists repository metadata.", "Normalizes GitHub, ZIP, and local path inputs into one analysis flow.", ["AST Analysis Service", "Report Engine"], "New repositories cannot enter the system.", "Critical"),
    intelNode("svc-ast", "AST Analysis Service", "Tree-sitter and language parsing", "service", 300, 80, "#a7f3d0", "code", [], "Extracts symbols, routes, models, imports, and implementation evidence.", "Gives downstream engines structured facts instead of raw text.", ["Dependency Engine", "Security Engine", "RAG Engine", "Report Engine"], "Architecture and explanations degrade to missing or weak evidence.", "Critical"),
    intelNode("svc-dependency", "Dependency Engine", "Import and module graph", "service", 600, 40, "#93c5fd", "dependency", [], "Builds relationships between code modules, symbols, and imports.", "Shows how changes propagate across the repository.", ["Architecture Canvas", "Report Engine"], "Dependency diagrams and blast-radius views become unreliable.", "High"),
    intelNode("svc-security", "Security Engine", "Bandit, Semgrep, and custom rule aggregation", "service", 600, 210, "#fca5a5", "security", [], "Scores security findings and links them to evidence files.", "Separates real risk from broad repository commentary.", ["Report Engine", "CTO Review"], "Security score and audit report lose credibility.", "High"),
    intelNode("svc-rag", "RAG Engine", "Embedding search, reranking, citations", "service", 900, 120, "#fde68a", "rag", [], "Retrieves relevant repository evidence for user questions.", "Prevents generic answers by forcing citations.", ["Repository Chat", "Architecture Explainer"], "Answers may be empty or visibly fail when evidence is missing.", "Critical"),
    intelNode("svc-report", "Report Engine", "CTO, recruiter, debt, roadmap outputs", "service", 1200, 120, "#f0abfc", "reports", [], "Turns analysis evidence and model inference into review artifacts.", "Creates the shareable output recruiters and engineers judge.", ["Frontend", "Export Bundle"], "The product loses its primary deliverable.", "Critical")
  ];
  const edges = [
    intelEdge("svc-ingestion", "svc-ast", "source"),
    intelEdge("svc-ast", "svc-dependency", "imports"),
    intelEdge("svc-ast", "svc-security", "findings"),
    intelEdge("svc-ast", "svc-rag", "chunks"),
    intelEdge("svc-dependency", "svc-report", "architecture evidence"),
    intelEdge("svc-security", "svc-report", "risk evidence"),
    intelEdge("svc-rag", "svc-report", "grounding"),
    intelEdge("svc-rag", "svc-report", "citations")
  ];
  return { nodes, edges };
}

function moduleArchitecture(summary: any, expanded: Record<string, boolean>): { nodes: Node[]; edges: Edge[] } {
  const groups = collectModuleGroups(summary);
  const specs = [
    ["mod-frontend", "frontend/*", "User interface and architecture explorer", "frontend", 0, 80, "#67e8f9"],
    ["mod-ingestion", "ingestion/*", "Repository lifecycle and cleanup", "ingestion", 260, 250, "#93c5fd"],
    ["mod-analysis", "analysis/*", "AST, dependency, architecture, security signals", "analysis", 520, 80, "#a7f3d0"],
    ["mod-rag", "rag/*", "Semantic retrieval and answer formatting", "rag", 780, 250, "#fde68a"],
    ["mod-reports", "reports/*", "Generated reviews and markdown artifacts", "reports", 1040, 80, "#f0abfc"],
    ["mod-llm", "llm/*", "Local qwen-judge inference adapter", "llm", 1040, 300, "#c4b5fd"],
    ["mod-storage", "storage/*", "Metadata, reports, and vector persistence", "storage", 780, 430, "#fca5a5"]
  ];
  const nodes: Node[] = [];
  const edges: Edge[] = [
    intelEdge("mod-frontend", "mod-ingestion", "submits"),
    intelEdge("mod-ingestion", "mod-analysis", "materializes"),
    intelEdge("mod-analysis", "mod-rag", "chunks"),
    intelEdge("mod-analysis", "mod-reports", "evidence"),
    intelEdge("mod-rag", "mod-llm", "prompts"),
    intelEdge("mod-rag", "mod-storage", "indexes"),
    intelEdge("mod-reports", "mod-llm", "generates"),
    intelEdge("mod-reports", "mod-storage", "persists")
  ];
  specs.forEach(([id, label, subtitle, module, x, y, color]) => {
    const files = groups.get(String(module)) ?? [];
    const isExpanded = Boolean(expanded[String(id)]);
    nodes.push(intelNode(String(id), String(label), String(subtitle), "module", Number(x), Number(y), String(color), String(module), files, modulePurpose(String(module)), "Groups implementation files into a reviewable subsystem instead of rendering every file.", moduleDependents(String(module)), moduleFailure(String(module)), moduleImportance(String(module)), { count: files.length, expanded: isExpanded, layer: String(module) }));
    if (isExpanded) {
      files.slice(0, 5).forEach((file, index) => {
        const childId = `${id}-${file}`;
        nodes.push(intelNode(childId, shortName(file), file, "implementation", Number(x), Number(y) + 115 + index * 88, String(color), "file", [file], "Concrete implementation file inside this module.", "Shown only after module expansion to preserve architecture readability.", [String(label)], "Localized implementation behavior may fail.", "Medium", { layer: String(module) }));
        edges.push(intelEdge(String(id), childId, "contains"));
      });
    }
  });
  return { nodes, edges };
}

function implementationArchitecture(summary: any): { nodes: Node[]; edges: Edge[] } {
  const graph = summary?.graph ?? {};
  const important = new Set((graph.important_nodes ?? []).map((item: any) => item.id));
  const rawNodes = (graph.nodes ?? []).filter((node: any) => important.has(node.id) || ["route", "database_model", "class", "function", "method"].includes(node.kind)).slice(0, 36);
  const nodeIds = new Set(rawNodes.map((node: any) => node.id));
  const rawEdges = (graph.edges ?? []).filter((edge: any) => nodeIds.has(edge.source) && nodeIds.has(edge.target)).slice(0, 70);
  const kindOrder: Record<string, number> = { file: 0, route: 1, class: 2, function: 3, method: 3, database_model: 4, module: 5 };
  const rowsByKind = new Map<string, number>();
  const nodes = rawNodes.map((node: any) => {
    const kind = String(node.kind ?? "file");
    const column = kindOrder[kind] ?? 0;
    const row = rowsByKind.get(kind) ?? 0;
    rowsByKind.set(kind, row + 1);
    return intelNode(node.id, shortName(node.id), kind === "file" ? node.id : String(node.id).split("::").pop() ?? node.id, "implementation", column * 260, row * 110, moduleColor(kind), implementationIcon(kind), [String(node.id).split("::")[0]], implementationPurpose(kind), "Implementation nodes are shown only in Level 4 for debugging and verification.", [], "A failure here affects the owning module or route.", kind === "file" ? "High" : "Medium", { layer: kind });
  });
  const edges = rawEdges.map((edge: any, index: number) => intelEdge(edge.source, edge.target, edge.relation ?? `edge-${index}`));
  return { nodes, edges };
}

function buildLayeredDependencyFlow(graph: any, query: string, focusLayer: string | null, selectedId?: string): { nodes: Node[]; edges: Edge[] } {
  const fileNodes = (graph?.nodes ?? []).filter((node: any) => node.kind === "file");
  const fileIds = new Set(fileNodes.map((node: any) => node.id));
  const buckets = new Map<string, { id: string; label: string; layer: string; files: string[] }>();
  fileNodes.forEach((node: any) => {
    const layer = classifyLayer(node.id);
    const label = moduleBucket(node.id);
    const id = `dep-${layer}-${label}`;
    const bucket = buckets.get(id) ?? { id, label, layer, files: [] };
    bucket.files.push(node.id);
    buckets.set(id, bucket);
  });
  const edgesByKey = new Map<string, { source: string; target: string; count: number; critical: boolean }>();
  (graph?.edges ?? []).filter((edge: any) => edge.relation === "imports").forEach((edge: any) => {
    const sourcePath = String(edge.source);
    if (!fileIds.has(sourcePath)) return;
    const targetPath = fileIds.has(edge.target) ? String(edge.target) : String(edge.target);
    const sourceLayer = classifyLayer(sourcePath);
    const targetLayer = classifyLayer(targetPath);
    const source = `dep-${sourceLayer}-${moduleBucket(sourcePath)}`;
    const target = `dep-${targetLayer}-${moduleBucket(targetPath)}`;
    if (source === target || !buckets.has(source)) return;
    if (!buckets.has(target)) buckets.set(target, { id: target, label: moduleBucket(targetPath), layer: targetLayer, files: [targetPath] });
    const key = `${source}->${target}`;
    const current = edgesByKey.get(key) ?? { source, target, count: 0, critical: isCriticalLayerPath(sourceLayer, targetLayer) };
    current.count += 1;
    edgesByKey.set(key, current);
  });
  const nodes: Node[] = [];
  dependencyLayers.forEach((layer, layerIndex) => {
    const layerBuckets = Array.from(buckets.values()).filter((bucket) => bucket.layer === layer.id).slice(0, 5);
    nodes.push(intelNode(`layer-${layer.id}`, layer.label, "Layer grouping", "layer", layerIndex * 240, 0, layer.color, layer.icon, [], layerPurpose(layer.id), "Layers make the dependency graph readable by grouping modules before files.", layerBuckets.map((bucket) => bucket.label), layerFailure(layer.id), layerImportance(layer.id), { count: layerBuckets.reduce((sum, bucket) => sum + bucket.files.length, 0), layer: layer.label }));
    layerBuckets.forEach((bucket, row) => {
      nodes.push(intelNode(bucket.id, bucket.label, `${bucket.files.length} files`, "module", layerIndex * 240, 125 + row * 112, layer.color, layer.icon, bucket.files, layerPurpose(layer.id), "This module belongs to the layered dependency path.", outgoingBucketNames(bucket.id, edgesByKey, buckets), layerFailure(layer.id), layerImportance(layer.id), { count: bucket.files.length, layer: layer.label }));
    });
  });
  const layerHeaderEdges = dependencyLayers.slice(0, -1).map((layer, index) => intelEdge(`layer-${layer.id}`, `layer-${dependencyLayers[index + 1].id}`, "layer order", true));
  const dependencyEdges = Array.from(edgesByKey.values()).slice(0, 80).map((edge) => intelEdge(edge.source, edge.target, `${edge.count}`, edge.critical));
  return applyFlowState(nodes, [...layerHeaderEdges, ...dependencyEdges], query, null, selectedId, focusLayer);
}

function applyFlowState(nodes: Node[], edges: Edge[], query: string, focus: string | null, selectedId?: string, focusLayer?: string | null): { nodes: Node[]; edges: Edge[] } {
  const lowerQuery = query.trim().toLowerCase();
  const neighborhood = flowNeighborhood(edges, focus ?? selectedId);
  const queryMatches = new Set(nodes.filter((node) => nodeMatches(node, lowerQuery)).map((node) => node.id));
  if (lowerQuery) {
    for (const edge of edges) {
      if (queryMatches.has(edge.source)) queryMatches.add(edge.target);
      if (queryMatches.has(edge.target)) queryMatches.add(edge.source);
    }
  }
  const nextNodes = nodes.map((node) => {
    const data = node.data as IntelligenceNodeData;
    const layerMatches = !focusLayer || data.layer === dependencyLayers.find((layer) => layer.id === focusLayer)?.label || node.id === `layer-${focusLayer}`;
    const focused = !focus || neighborhood.has(node.id);
    const queried = !lowerQuery || queryMatches.has(node.id);
    const active = layerMatches && focused && queried;
    return {
      ...node,
      className: `${node.className ?? ""} ${node.id === selectedId ? "flow-node-selected" : ""} ${active ? "" : "flow-node-muted"}`
    };
  });
  const nextEdges = edges.map((edge) => {
    const active = (!focus || (neighborhood.has(edge.source) && neighborhood.has(edge.target))) && (!lowerQuery || (queryMatches.has(edge.source) && queryMatches.has(edge.target)));
    const critical = Boolean(edge.data?.critical);
    return {
      ...edge,
      animated: active && (critical || Boolean(focus || selectedId)),
      className: active ? "flow-edge-active" : "flow-edge-muted",
      style: { stroke: active ? (critical ? "#22d3ee" : "#94a3b8") : "rgba(148,163,184,0.18)", strokeWidth: active ? (critical ? 2.6 : 1.6) : 1 }
    };
  });
  return { nodes: nextNodes, edges: nextEdges };
}

function intelNode(id: string, label: string, subtitle: string, kind: string, x: number, y: number, color: string, icon: string, files: string[], purpose: string, why: string, dependents: string[], failure: string, importance: IntelligenceNodeData["importance"], extra: Partial<IntelligenceNodeData> = {}): Node<IntelligenceNodeData> {
  return {
    id,
    type: "intelligence",
    position: { x, y },
    data: { label, subtitle, kind, files, color, icon, purpose, why, dependents, failure, importance, ...extra },
    className: "flow-node"
  };
}

function intelEdge(source: string, target: string, label?: string, critical = false): Edge {
  return {
    id: `${source}->${target}-${label ?? "edge"}`,
    source,
    target,
    label,
    type: "smoothstep",
    data: { critical },
    style: { stroke: critical ? "#22d3ee" : "rgba(148,163,184,0.5)", strokeWidth: critical ? 2.4 : 1.5 },
    labelStyle: { fill: "#94a3b8", fontSize: 10 },
    labelBgStyle: { fill: "rgba(2,6,23,0.86)" }
  };
}

function flowNeighborhood(edges: Edge[], selectedId?: string | null) {
  const ids = new Set<string>();
  if (!selectedId) return ids;
  ids.add(selectedId);
  for (const edge of edges) {
    if (edge.source === selectedId) ids.add(edge.target);
    if (edge.target === selectedId) ids.add(edge.source);
  }
  return ids;
}

function nodeMatches(node: Node, query: string) {
  if (!query) return true;
  const data = node.data as IntelligenceNodeData;
  return [node.id, data.label, data.subtitle, data.kind, data.layer, ...(data.files ?? [])].some((value) => String(value ?? "").toLowerCase().includes(query));
}

const dependencyLayers = [
  { id: "frontend", label: "Frontend", color: "#67e8f9", icon: "frontend" },
  { id: "api", label: "API", color: "#93c5fd", icon: "server" },
  { id: "business", label: "Business Logic", color: "#c4b5fd", icon: "workflow" },
  { id: "analysis", label: "Analysis", color: "#a7f3d0", icon: "analysis" },
  { id: "rag", label: "RAG", color: "#fde68a", icon: "rag" },
  { id: "storage", label: "Storage", color: "#fca5a5", icon: "database" },
  { id: "llm", label: "LLM", color: "#f0abfc", icon: "llm" }
];

function collectModuleGroups(summary: any) {
  const groups = new Map<string, string[]>();
  for (const file of summary?.files ?? []) {
    const path = String(file.relative_path ?? "");
    const group = moduleGroup(path);
    groups.set(group, [...(groups.get(group) ?? []), path]);
  }
  return groups;
}

function moduleGroup(path: string) {
  if (path.startsWith("frontend/") || path.includes("/components/")) return "frontend";
  if (path.includes("/ingestion/") || path.includes("/clone") || path.includes("/cleanup")) return "ingestion";
  if (path.includes("/analysis/") || path.includes("/security/")) return "analysis";
  if (path.includes("/rag/")) return "rag";
  if (path.includes("/reports/") || path.includes("report")) return "reports";
  if (path.includes("/llm/") || path.includes("model")) return "llm";
  if (path.includes("/store") || path.includes("/storage") || path.includes("/core/")) return "storage";
  return "analysis";
}

function classifyLayer(path: string) {
  if (path.startsWith("frontend/") || path.includes("/components/")) return "frontend";
  if (path.includes("main.py") || path.includes("/api") || path.includes("/routes")) return "api";
  if (path.includes("/analysis/") || path.includes("/security/")) return "analysis";
  if (path.includes("/rag/")) return "rag";
  if (path.includes("/llm/") || /qwen|model|inference/i.test(path)) return "llm";
  if (path.includes("/store") || path.includes("/storage") || path.includes("metadata") || path.includes("chroma")) return "storage";
  if (!path.includes("/") || path.startsWith("@") || /^[a-z0-9_.-]+$/i.test(path)) return "business";
  return "business";
}

function moduleBucket(path: string) {
  if (!path.includes("/")) return path;
  const parts = path.split("/");
  if (parts[0] === "backend" && parts[1] === "repomind" && parts[2]) return parts.slice(0, 3).join("/");
  if (parts[0] === "frontend" && parts[1]) return parts.slice(0, 2).join("/");
  return parts.slice(0, Math.min(2, parts.length)).join("/");
}

function outgoingBucketNames(id: string, edges: Map<string, { source: string; target: string }>, buckets: Map<string, { label: string }>) {
  return Array.from(edges.values()).filter((edge) => edge.source === id).map((edge) => buckets.get(edge.target)?.label ?? edge.target).slice(0, 4);
}

function isCriticalLayerPath(source: string, target: string) {
  return new Set(["frontend>api", "api>business", "business>analysis", "analysis>rag", "rag>storage", "rag>llm", "analysis>business", "business>storage"]).has(`${source}>${target}`);
}

function modulePurpose(module: string) {
  const values: Record<string, string> = {
    frontend: "Presents repository intelligence, architecture views, reports, and chat.",
    ingestion: "Moves repository sources into the analysis lifecycle.",
    analysis: "Extracts structured code facts and quality evidence.",
    rag: "Finds evidence and formats grounded repository answers.",
    reports: "Builds shareable CTO, recruiter, security, and debt reports.",
    llm: "Runs local model inference for generated analysis.",
    storage: "Persists metadata, reports, and vector indexes."
  };
  return values[module] ?? "Owns a repository subsystem.";
}

function moduleDependents(module: string) {
  const values: Record<string, string[]> = {
    frontend: ["Reviewers"],
    ingestion: ["Analysis"],
    analysis: ["RAG", "Reports", "Architecture"],
    rag: ["Chat", "Reports"],
    reports: ["Frontend", "Export"],
    llm: ["RAG", "Reports"],
    storage: ["API", "RAG", "Reports"]
  };
  return values[module] ?? [];
}

function moduleFailure(module: string) {
  const values: Record<string, string> = {
    frontend: "The product remains technically present but unusable for reviewers.",
    ingestion: "New repositories cannot be analyzed.",
    analysis: "Architecture, security, and quality evidence becomes incomplete.",
    rag: "Repository chat cannot return grounded answers.",
    reports: "The user loses the primary deliverable.",
    llm: "Generated reviews and explanations fail visibly.",
    storage: "Analysis artifacts cannot be recovered after cleanup."
  };
  return values[module] ?? "The owning subsystem becomes unreliable.";
}

function moduleImportance(module: string): IntelligenceNodeData["importance"] {
  return ["ingestion", "analysis", "rag", "reports", "storage"].includes(module) ? "Critical" : "High";
}

function layerPurpose(layer: string) {
  const values: Record<string, string> = {
    frontend: "Renders the reviewer-facing product surface.",
    api: "Accepts user actions and serves repository artifacts.",
    business: "Coordinates product workflows and domain decisions.",
    analysis: "Extracts repository structure and quality evidence.",
    rag: "Retrieves evidence for grounded answers.",
    storage: "Persists metadata, reports, and indexes.",
    llm: "Generates natural-language reviews and explanations."
  };
  return values[layer] ?? "Groups related dependencies.";
}

function layerFailure(layer: string) {
  const values: Record<string, string> = {
    frontend: "Users cannot operate the product.",
    api: "No analysis, report, or chat request can be served.",
    business: "Core workflows become inconsistent.",
    analysis: "The system loses repository intelligence.",
    rag: "Answers lose citations and grounding.",
    storage: "Artifacts and indexes are unavailable.",
    llm: "Generated reviews and explanations fail."
  };
  return values[layer] ?? "Layer behavior degrades.";
}

function layerImportance(layer: string): IntelligenceNodeData["importance"] {
  return ["api", "analysis", "rag", "storage"].includes(layer) ? "Critical" : "High";
}

function implementationPurpose(kind: string) {
  const values: Record<string, string> = {
    file: "Owns concrete source code or configuration.",
    route: "Exposes an HTTP or app route.",
    class: "Defines reusable behavior or domain structure.",
    function: "Implements callable behavior.",
    method: "Implements class behavior.",
    database_model: "Defines persisted data shape.",
    module: "External or internal import dependency."
  };
  return values[kind] ?? "Implementation detail.";
}

function implementationIcon(kind: string) {
  const values: Record<string, string> = {
    file: "file",
    route: "server",
    class: "code",
    function: "cpu",
    method: "cpu",
    database_model: "database",
    module: "boxes"
  };
  return values[kind] ?? "file";
}

function iconFor(icon?: string) {
  const icons: Record<string, any> = {
    analysis: Brain,
    boxes: Boxes,
    code: Code2,
    cpu: Cpu,
    database: Database,
    dependency: Network,
    file: FileCode2,
    frontend: Sparkles,
    ingestion: FolderInput,
    llm: Bot,
    rag: Search,
    reports: Archive,
    security: ShieldAlert,
    server: Server,
    storage: Database,
    workflow: Workflow
  };
  return icons[icon ?? "boxes"] ?? Boxes;
}

function moduleColor(module: string) {
  const colors = ["#67e8f9", "#a7f3d0", "#f0abfc", "#fde68a", "#c4b5fd", "#fca5a5", "#93c5fd"];
  return colors[Math.abs(hashCode(module)) % colors.length];
}

function hashCode(value: string) {
  return value.split("").reduce((acc, char) => ((acc << 5) - acc + char.charCodeAt(0)) | 0, 0);
}

function exportFlowSvg(nodes: Node[], edges: Edge[], filename: string) {
  const svg = flowToSvg(nodes, edges);
  downloadBlob(new Blob([svg], { type: "image/svg+xml" }), filename);
}

function exportFlowPng(nodes: Node[], edges: Edge[], filename: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 1600;
  canvas.height = 1000;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "rgba(103,232,249,0.45)";
  for (const edge of edges) {
    const source = nodes.find((node) => node.id === edge.source);
    const target = nodes.find((node) => node.id === edge.target);
    if (!source || !target) continue;
    ctx.beginPath();
    ctx.moveTo(source.position.x + 100, source.position.y + 28);
    ctx.lineTo(target.position.x + 100, target.position.y + 28);
    ctx.stroke();
  }
  for (const node of nodes) {
    ctx.fillStyle = "#0f172a";
    ctx.strokeStyle = String(node.data.color ?? "#67e8f9");
    ctx.lineWidth = 2;
    ctx.fillRect(node.position.x, node.position.y, 210, 56);
    ctx.strokeRect(node.position.x, node.position.y, 210, 56);
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "13px sans-serif";
    ctx.fillText(String(node.data.label).slice(0, 24), node.position.x + 12, node.position.y + 32);
  }
  canvas.toBlob((blob) => blob && downloadBlob(blob, filename));
}

function flowToSvg(nodes: Node[], edges: Edge[]) {
  const edgeLines = edges.map((edge) => {
    const source = nodes.find((node) => node.id === edge.source);
    const target = nodes.find((node) => node.id === edge.target);
    if (!source || !target) return "";
    return `<line x1="${source.position.x + 105}" y1="${source.position.y + 28}" x2="${target.position.x + 105}" y2="${target.position.y + 28}" stroke="#67e8f9" stroke-opacity="0.55"/>`;
  }).join("");
  const nodeRects = nodes.map((node) => `<g><rect x="${node.position.x}" y="${node.position.y}" width="210" height="56" rx="8" fill="#0f172a" stroke="${node.data.color ?? "#67e8f9"}"/><text x="${node.position.x + 12}" y="${node.position.y + 33}" fill="#e2e8f0" font-family="Arial" font-size="13">${escapeXml(String(node.data.label))}</text></g>`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="-320 -40 1600 1000"><rect width="100%" height="100%" fill="#020617"/>${edgeLines}${nodeRects}</svg>`;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function escapeXml(value: string) {
  return value.replace(/[<>&'"]/g, (char) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", '"': "&quot;" }[char] ?? char));
}

function FindingList({ items }: { items: any[] }) {
  if (!items.length) return <Empty text="No findings returned by enabled scanners." />;
  return (
    <div className="space-y-2">
      {items.map((item, index) => (
        <div key={`${item.path}-${item.line}-${index}`} className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm">
          <div className="font-medium text-red-100">{item.severity ?? item.type ?? "finding"} · {item.rule_id}</div>
          <div className="break-words text-xs text-slate-400">{item.path}{item.line ? `:${item.line}` : ""}</div>
          <div className="mt-1 text-slate-300">{item.message}</div>
        </div>
      ))}
    </div>
  );
}

function ScoreEvidence({ detail }: { detail?: any }) {
  if (!detail) return <Empty text="No score evidence available." />;
  return (
    <div className="space-y-3 text-sm">
      <p className="text-slate-300">{detail.calculation}</p>
      <EvidenceList title="Positive" items={detail.positive_contributors ?? []} />
      <EvidenceList title="Negative" items={detail.negative_contributors ?? []} />
    </div>
  );
}

function CitationList({ items }: { items: any[] }) {
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={`${item.path}-${item.line_start}`} className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">
          <div className="break-words text-cyan-100">{item.path}:{item.line_start}-{item.line_end}</div>
          <div>score {item.score}</div>
        </div>
      ))}
    </div>
  );
}

function FileTree({ tree, expanded, setExpanded }: { tree: any; expanded: Record<string, boolean>; setExpanded: (value: Record<string, boolean>) => void }) {
  return <div className="max-h-[520px] overflow-auto text-sm">{renderTree(tree, "", expanded, setExpanded)}</div>;
}

function renderTree(node: any, path: string, expanded: Record<string, boolean>, setExpanded: (value: Record<string, boolean>) => void) {
  return Object.entries(node.children ?? {}).slice(0, 120).map(([name, child]: any) => {
    const nextPath = path ? `${path}/${name}` : name;
    const isOpen = expanded[nextPath] ?? path.split("/").length < 1;
    const isDir = child.children && Object.keys(child.children).length > 0;
    return (
      <div key={nextPath} className="ml-2">
        <button className="flex w-full items-center gap-1 rounded px-1 py-1 text-left text-slate-300 hover:bg-white/5" onClick={() => isDir && setExpanded({ ...expanded, [nextPath]: !isOpen })}>
          {isDir ? (isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span className="w-[14px]" />}
          <span className="truncate">{name}</span>
        </button>
        {isDir && isOpen ? <div className="border-l border-white/10">{renderTree(child, nextPath, expanded, setExpanded)}</div> : null}
      </div>
    );
  });
}
