"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { AlertTriangle, Boxes, Crosshair, Database, FileCode2, Filter, GitBranch, Network, Search, ShieldAlert, Sparkles, Workflow } from "lucide-react";
import type { Finding, RepositorySummary } from "./types";
import { Badge, EmptyState, Panel, SeverityBadge } from "./ui";
import { Heatmap, ScoreOrb } from "./visuals";

type GraphNode = {
  id: string;
  label: string;
  kind: string;
  group: "domain" | "file" | "symbol" | "dependency" | "security";
  description: string;
  relatedFiles: string[];
  dependencies: string[];
  dependents: string[];
  findings: Finding[];
  importance: number;
  complexity: number;
};

type GraphEdge = { source: string; target: string; relation: string };

const groupStyle = {
  domain: { color: "#38bdf8", icon: Network, label: "Domain" },
  file: { color: "#a78bfa", icon: FileCode2, label: "File" },
  symbol: { color: "#34d399", icon: Workflow, label: "Symbol" },
  dependency: { color: "#f59e0b", icon: Database, label: "Dependency" },
  security: { color: "#fb7185", icon: ShieldAlert, label: "Risk" }
};

export function KnowledgeGraphPanel({ summary }: { summary: RepositorySummary | null }) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const model = useMemo(() => buildGraphModel(summary), [summary]);
  const filtered = useMemo(() => filterGraph(model.nodes, query, group), [model.nodes, query, group]);
  const selected = model.nodes.find((node) => node.id === selectedId) ?? filtered[0] ?? null;
  const flow = useMemo(() => toFlow(filtered, model.edges, selected?.id, query), [filtered, model.edges, selected?.id, query]);

  if (!summary) {
    return <EmptyState title="Knowledge graph unavailable" text="Analyze a repository to build symbols, domains, hotspots, and dependency relationships." />;
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(56,189,248,0.16),rgba(255,255,255,0.045)_38%,rgba(52,211,153,0.08))] shadow-panel">
        <div className="grid gap-0 xl:grid-cols-[280px_1fr_330px]">
          <div className="grid place-items-center border-b border-white/10 bg-black/25 p-5 xl:border-b-0 xl:border-r">
            <ScoreOrb label="Graph IQ" score={model.graphScore} size="medium" sublabel="Evidence density" />
          </div>
          <div className="p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100"><Network size={20} /></span>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/80">Flagship capability</p>
                <h2 className="text-3xl font-semibold tracking-tight text-white">Repository Knowledge Graph</h2>
              </div>
            </div>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">A force-laid intelligence map of domains, files, symbols, dependencies, security findings, and blast-radius edges.</p>
            <div className="mt-5 grid gap-3 md:grid-cols-5">
              <GraphMetric label="Nodes" value={model.nodes.length} />
              <GraphMetric label="Edges" value={model.edges.length} />
              <GraphMetric label="Risks" value={model.findings.length} />
              <GraphMetric label="Files" value={model.nodes.filter((node) => node.group === "file").length} />
              <GraphMetric label="Dependencies" value={model.nodes.filter((node) => node.group === "dependency").length} />
            </div>
          </div>
          <div className="border-t border-white/10 bg-black/20 p-5 xl:border-l xl:border-t-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Executive insights</p>
            <div className="mt-3 space-y-2">
              <Insight label="Critical node" value={model.insights.critical?.label} tone="cyan" />
              <Insight label="Most connected" value={model.insights.connected?.label} tone="emerald" />
              <Insight label="Highest risk" value={model.insights.risk?.label} tone="rose" />
              <Insight label="Dependency hotspot" value={model.insights.dependency?.label} tone="amber" />
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <Panel title="GraphXR Workspace" eyebrow="Search, cluster, zoom, focus">
          <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
            <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300 focus-within:border-cyan-300/45">
              <Search size={15} className="text-slate-500" />
              <input className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-slate-600" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search nodes, files, risks, dependencies" />
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300">
              <Filter size={15} className="text-slate-500" />
              <select className="min-w-0 flex-1 bg-transparent outline-none" value={group} onChange={(event) => setGroup(event.target.value)}>
                {["all", "domain", "file", "symbol", "dependency", "security"].map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          </div>
          {flow.nodes.length ? (
            <div className="h-[720px] overflow-hidden rounded-2xl border border-cyan-300/15 bg-[#070b12] shadow-[inset_0_0_90px_rgba(56,189,248,0.07)]">
              <ReactFlow
                nodes={flow.nodes}
                edges={flow.edges}
                fitView
                minZoom={0.18}
                maxZoom={2}
                onNodeClick={(_, node) => setSelectedId(node.id)}
              >
                <Background color="rgba(148,163,184,0.15)" gap={22} />
                <MiniMap pannable zoomable className="premium-minimap" nodeColor={(node) => String(node.data.color ?? "#38bdf8")} />
                <Controls className="premium-controls" />
              </ReactFlow>
            </div>
          ) : (
            <EmptyState title="No matching graph nodes" text="Adjust search or filters to view available architecture domains." />
          )}
        </Panel>
        <NodeInspector node={selected} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.7fr_1.3fr]">
        <Panel title="Cluster Legend" eyebrow="Domain grouping">
          <div className="grid gap-3">
            {Object.entries(groupStyle).map(([key, value]) => {
              const Icon = value.icon;
              return (
                <div key={key} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] p-3">
                  <div className="flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-xl border text-white" style={{ borderColor: `${value.color}66`, background: `${value.color}22` }}><Icon size={16} /></span>
                    <span className="text-sm font-medium text-white">{value.label}</span>
                  </div>
                  <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{model.nodes.filter((node) => node.group === key).length}</Badge>
                </div>
              );
            })}
          </div>
        </Panel>
        <Panel title="Blast Radius Heatmap" eyebrow="Connectivity and risk concentration">
          <Heatmap values={model.nodes.map((node) => ({ label: node.label, value: Math.min(100, node.importance * 12 + node.findings.length * 30 + node.complexity * 8) }))} />
        </Panel>
      </div>
    </div>
  );
}

function buildGraphModel(summary: RepositorySummary | null) {
  const rawGraph = (summary as any)?.graph ?? {};
  const findings = [...(summary?.security?.findings ?? []), ...(summary?.technical_debt?.findings ?? [])];
  const edges: GraphEdge[] = (rawGraph.edges ?? []).map((edge: any) => ({ source: String(edge.source), target: String(edge.target), relation: String(edge.relation ?? "depends") }));
  const degree = new Map<string, number>();
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  }
  const rawNodes: any[] = rawGraph.nodes?.length ? rawGraph.nodes : fallbackNodes(summary);
  const nodes = rawNodes.map((item) => {
    const id = String(item.id ?? item.name ?? item.relative_path);
    const nodeFindings = findings.filter((finding) => (finding.file ?? (finding as any).path ?? "").toLowerCase() === id.toLowerCase());
    const kind = String(item.kind ?? item.language ?? "domain");
    const group = inferGroup(id, kind, nodeFindings);
    const dependencies = edges.filter((edge) => edge.source === id).map((edge) => edge.target);
    const dependents = edges.filter((edge) => edge.target === id).map((edge) => edge.source);
    return {
      id,
      label: shortLabel(id),
      kind,
      group,
      description: describeNode(id, kind, group, item),
      relatedFiles: relatedFilesFor(id, summary),
      dependencies,
      dependents,
      findings: nodeFindings,
      importance: degree.get(id) ?? 0,
      complexity: Number(item.size ?? 0) > 0 ? Math.min(10, Math.ceil(Number(item.size) / 600)) : dependencies.length + dependents.length,
    } satisfies GraphNode;
  });
  for (const finding of findings) {
    const file = finding.file ?? (finding as any).path;
    if (file && !nodes.some((node) => node.id === file)) {
      nodes.push({
        id: file,
        label: shortLabel(file),
        kind: "security",
        group: "security",
        description: finding.message ?? finding.title ?? "Security finding",
        relatedFiles: [file],
        dependencies: [],
        dependents: [],
        findings: [finding],
        importance: 4,
        complexity: 2
      });
    }
  }
  const sorted = [...nodes].sort((a, b) => b.importance + b.findings.length * 4 - (a.importance + a.findings.length * 4));
  const graphScore = Math.min(100, Math.max(35, Math.round(nodes.length * 4 + edges.length * 2 - findings.length * 6)));
  return {
    nodes,
    edges,
    findings,
    graphScore,
    insights: {
      critical: sorted[0],
      connected: [...nodes].sort((a, b) => b.importance - a.importance)[0],
      risk: [...nodes].sort((a, b) => b.findings.length - a.findings.length)[0],
      dependency: [...nodes].filter((node) => node.group === "dependency").sort((a, b) => b.importance - a.importance)[0],
    }
  };
}

function toFlow(items: GraphNode[], graphEdges: GraphEdge[], selectedId?: string, query = ""): { nodes: Node[]; edges: Edge[] } {
  const positions = forceLayout(items, graphEdges);
  const lowerQuery = query.toLowerCase();
  const nodes: Node[] = items.map((item) => {
    const style = groupStyle[item.group];
    const Icon = style.icon;
    const selected = item.id === selectedId;
    const highlighted = lowerQuery && `${item.id} ${item.label} ${item.description}`.toLowerCase().includes(lowerQuery);
    return {
      id: item.id,
      position: positions.get(item.id) ?? { x: 0, y: 0 },
      style: { background: "transparent", border: 0, width: selected ? 285 : 245, height: 126 },
      className: highlighted ? "graph-node-highlight" : "",
      data: {
        color: style.color,
        label: (
        <div
          className={`rounded-2xl border p-4 shadow-[0_24px_70px_rgba(0,0,0,0.34)] transition ${selected ? "scale-[1.04]" : ""}`}
          style={{ borderColor: `${style.color}${selected ? "cc" : "66"}`, background: `linear-gradient(135deg, ${style.color}24, rgba(15,23,42,0.96) 46%)` }}
          title={item.description}
        >
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl border text-white" style={{ borderColor: `${style.color}88`, background: `${style.color}22` }}><Icon size={17} /></span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{item.label}</p>
              <p className="text-[10px] uppercase tracking-[0.14em] text-slate-400">{style.label}</p>
            </div>
            {item.findings.length ? <ShieldAlert className="ml-auto h-4 w-4 text-rose-200" /> : null}
          </div>
          <div className="mt-3 flex gap-2">
            <Badge className="border-white/10 bg-black/20 text-slate-300">{item.importance} links</Badge>
            {item.findings.length ? <Badge className="border-rose-300/30 bg-rose-500/10 text-rose-100">{item.findings.length} risks</Badge> : null}
          </div>
        </div>
        )
      }
    };
  });
  const visible = new Set(items.map((item) => item.id));
  const edges: Edge[] = graphEdges
    .filter((edge) => visible.has(edge.source) && visible.has(edge.target))
    .map((edge, index) => ({
      id: `${edge.source}-${edge.target}-${index}`,
      source: edge.source,
      target: edge.target,
      animated: edge.relation === "imports" || edge.source === selectedId || edge.target === selectedId,
      label: edge.relation,
      style: { stroke: edgeColor(edge.relation), strokeWidth: edge.source === selectedId || edge.target === selectedId ? 2.6 : 1.4 },
      labelStyle: { fill: "#94a3b8", fontSize: 10 },
    }));
  return { nodes, edges };
}

function forceLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const groups = ["domain", "file", "symbol", "dependency", "security"];
  const points = new Map<string, { x: number; y: number; vx: number; vy: number }>();
  nodes.forEach((node, index) => {
    const groupIndex = groups.indexOf(node.group);
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1);
    points.set(node.id, {
      x: groupIndex * 285 + Math.cos(angle) * 120,
      y: groupIndex % 2 === 0 ? Math.sin(angle) * 170 + 260 : Math.sin(angle) * 170 + 450,
      vx: 0,
      vy: 0
    });
  });
  for (let step = 0; step < 90; step += 1) {
    for (const a of nodes) {
      const pa = points.get(a.id)!;
      for (const b of nodes) {
        if (a.id === b.id) continue;
        const pb = points.get(b.id)!;
        const dx = pa.x - pb.x || 1;
        const dy = pa.y - pb.y || 1;
        const distance = Math.max(90, Math.sqrt(dx * dx + dy * dy));
        const force = 2200 / (distance * distance);
        pa.vx += (dx / distance) * force;
        pa.vy += (dy / distance) * force;
      }
    }
    for (const edge of edges) {
      const a = points.get(edge.source);
      const b = points.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      a.vx += dx * 0.002;
      a.vy += dy * 0.002;
      b.vx -= dx * 0.002;
      b.vy -= dy * 0.002;
    }
    for (const node of nodes) {
      const point = points.get(node.id)!;
      point.x += point.vx;
      point.y += point.vy;
      point.vx *= 0.82;
      point.vy *= 0.82;
    }
  }
  return new Map(Array.from(points.entries()).map(([id, point]) => [id, { x: Math.round(point.x), y: Math.round(point.y) }]));
}

function NodeInspector({ node }: { node: GraphNode | null }) {
  if (!node) return <Panel title="Focus Mode" eyebrow="Node intelligence"><EmptyState title="Select a node" text="Click a graph node to inspect dependencies, risk, evidence, and architectural importance." /></Panel>;
  return (
    <Panel title="Focus Mode" eyebrow={node.group}>
      <div className="space-y-4">
        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xl font-semibold text-white">{node.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">{node.description}</p>
            </div>
            <Badge className="border-cyan-300/25 bg-cyan-300/10 text-cyan-100">{node.importance} links</Badge>
          </div>
        </div>
        <InspectorBlock title="Related files" items={node.relatedFiles} icon={<FileCode2 size={14} />} />
        <InspectorBlock title="Dependencies" items={node.dependencies} icon={<GitBranch size={14} />} />
        <InspectorBlock title="Dependents" items={node.dependents} icon={<Crosshair size={14} />} />
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Security and debt</p>
          {node.findings.length ? node.findings.map((finding, index) => (
            <div key={index} className="mb-2 rounded-xl border border-white/10 bg-white/[0.035] p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-white">{finding.title ?? finding.message ?? "Finding"}</p>
                <SeverityBadge severity={finding.severity} />
              </div>
              <p className="mt-2 text-xs text-slate-500">{finding.file}</p>
            </div>
          )) : <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3 text-sm text-slate-400">No linked security or debt findings.</div>}
        </div>
        <div className="rounded-xl border border-amber-300/20 bg-amber-300/[0.08] p-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-100"><AlertTriangle size={15} /> Architectural importance</div>
          <p className="mt-2 text-sm leading-5 text-slate-300">Importance {node.importance}/10, complexity {node.complexity}/10. Prioritize this node when it combines high connectivity with security findings.</p>
        </div>
      </div>
    </Panel>
  );
}

function InspectorBlock({ title, items, icon }: { title: string; items: string[]; icon: ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <div className="space-y-2">
        {items.slice(0, 6).map((item) => (
          <div key={item} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] p-2 text-sm text-slate-300">
            <span className="text-slate-500">{icon}</span>
            <span className="truncate">{item}</span>
          </div>
        ))}
        {!items.length ? <div className="rounded-xl border border-white/10 bg-white/[0.025] p-2 text-sm text-slate-500">None detected</div> : null}
      </div>
    </div>
  );
}

function GraphMetric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-white/10 bg-black/20 p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-white">{value}</p></div>;
}

function Insight({ label, value, tone }: { label: string; value?: string; tone: "cyan" | "emerald" | "rose" | "amber" }) {
  const colors = { cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100", emerald: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100", rose: "border-rose-300/25 bg-rose-300/10 text-rose-100", amber: "border-amber-300/25 bg-amber-300/10 text-amber-100" };
  return <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3"><Badge className={colors[tone]}>{label}</Badge><p className="mt-2 truncate text-sm font-medium text-white">{value ?? "No signal"}</p></div>;
}

function filterGraph(nodes: GraphNode[], query: string, group: string) {
  const lower = query.toLowerCase();
  return nodes.filter((node) => (group === "all" || node.group === group) && (!lower || `${node.id} ${node.label} ${node.description} ${node.findings.map((finding) => finding.message).join(" ")}`.toLowerCase().includes(lower))).slice(0, 80);
}

function inferGroup(id: string, kind: string, findings: Finding[]): GraphNode["group"] {
  if (findings.length) return "security";
  if (kind === "module" || (!id.includes("/") && !id.includes("::"))) return "dependency";
  if (id.includes("::")) return "symbol";
  if (kind === "file" || /\.[a-z0-9]+$/i.test(id)) return "file";
  return "domain";
}

function describeNode(id: string, kind: string, group: GraphNode["group"], item: any) {
  if (item.description || item.summary) return String(item.description ?? item.summary);
  if (group === "dependency") return `${id} is an external or imported dependency connected to repository code.`;
  if (group === "symbol") return `${id} is a function, route, class, or exported symbol detected during parsing.`;
  if (group === "security") return `${id} has linked security or technical debt findings.`;
  if (group === "file") return `${id} is a repository file participating in dependencies, routes, or evidence retrieval.`;
  return `${id} is an architectural domain inferred from repository structure.`;
}

function relatedFilesFor(id: string, summary: RepositorySummary | null) {
  if (/\.[a-z0-9]+$/i.test(id)) return [id];
  const files = summary?.files?.map((file) => file.relative_path).filter(Boolean) as string[] | undefined;
  return (files ?? []).filter((file) => id.includes(file) || file.includes(id.split("::")[0])).slice(0, 6);
}

function fallbackNodes(summary: RepositorySummary | null) {
  const files = summary?.files ?? [];
  return files.map((file) => ({ id: file.relative_path, kind: "file", language: file.language, size: file.size })).filter((item) => item.id);
}

function edgeColor(relation: string) {
  if (relation === "imports") return "rgba(245,158,11,0.62)";
  if (relation === "exposes") return "rgba(56,189,248,0.62)";
  if (relation === "defines") return "rgba(52,211,153,0.58)";
  return "rgba(148,163,184,0.38)";
}

function shortLabel(id: string) {
  const parts = id.split("/");
  return parts.slice(-2).join("/").replace("::", " / ");
}
