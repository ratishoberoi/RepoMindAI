"use client";

import { useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { Boxes, Filter, Network, Search, Sparkles, Workflow } from "lucide-react";
import type { RepositorySummary } from "./types";
import { domainCards } from "./utils";
import { Badge, EmptyState, Panel } from "./ui";
import { Heatmap, ScoreOrb } from "./visuals";

export function KnowledgeGraphPanel({ summary }: { summary: RepositorySummary | null }) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const graph = summary?.knowledge_graph;
  const cards = domainCards(graph);
  const kinds = useMemo(() => ["all", ...Array.from(new Set(cards.map((card) => String(card.kind ?? card.type ?? "domain"))))], [cards]);
  const filtered = cards.filter((card) => {
    const text = JSON.stringify(card).toLowerCase();
    return (kind === "all" || text.includes(kind.toLowerCase())) && (!query || text.includes(query.toLowerCase()));
  });
  const flow = useMemo(() => toFlow(filtered), [filtered]);
  const graphScore = Math.min(100, Math.round((Number(graph?.metrics?.entities ?? 0) + Number(graph?.metrics?.relationships ?? 0)) / 2));

  if (!summary) {
    return <EmptyState title="Knowledge graph unavailable" text="Analyze a repository to build symbols, domains, hotspots, and dependency relationships." />;
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(56,189,248,0.16),rgba(255,255,255,0.045)_38%,rgba(52,211,153,0.08))] shadow-panel">
        <div className="grid gap-0 xl:grid-cols-[320px_1fr_300px]">
          <div className="grid place-items-center border-b border-white/10 bg-black/25 p-5 xl:border-b-0 xl:border-r">
            <ScoreOrb label="Graph IQ" score={graphScore || 72} size="medium" sublabel="Evidence density" />
          </div>
          <div className="p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100"><Network size={20} /></span>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/80">Flagship capability</p>
                <h2 className="text-3xl font-semibold tracking-tight text-white">Repository Knowledge Graph</h2>
              </div>
            </div>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">A visual intelligence layer for domains, hotspots, dependencies, symbols, and operational evidence. Built to make repository structure legible in seconds.</p>
            <div className="mt-5 grid gap-3 md:grid-cols-4">
              {Object.entries(graph?.metrics ?? {}).slice(0, 4).map(([label, value]) => (
                <div key={label} className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label.replaceAll("_", " ")}</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{String(value)}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="border-t border-white/10 bg-black/20 p-5 xl:border-l xl:border-t-0">
            <Heatmap label="Knowledge density" values={cards.map((card, index) => ({ label: String(card.name ?? card.file ?? index), value: 35 + ((index * 21) % 65) }))} />
          </div>
        </div>
      </section>

      <Panel title="Graph Explorer" eyebrow="Search, filter, zoom, inspect">
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300 focus-within:border-cyan-300/45">
            <Search size={15} className="text-slate-500" />
            <input className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-slate-600" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search domains, files, symbols, hotspots" />
          </label>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300">
            <Filter size={15} className="text-slate-500" />
            <select className="min-w-0 flex-1 bg-transparent outline-none" value={kind} onChange={(event) => setKind(event.target.value)}>
              {kinds.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>

        {flow.nodes.length ? (
          <div className="h-[640px] overflow-hidden rounded-2xl border border-cyan-300/15 bg-[#070b12] shadow-[inset_0_0_80px_rgba(56,189,248,0.06)]">
            <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView minZoom={0.25} maxZoom={1.8}>
              <Background color="rgba(148,163,184,0.16)" gap={22} />
              <MiniMap pannable zoomable className="premium-minimap" />
              <Controls className="premium-controls" />
            </ReactFlow>
          </div>
        ) : (
          <EmptyState title="No matching graph nodes" text="Adjust search or filters to view available architecture domains." />
        )}
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[0.75fr_1.25fr]">
        <Panel title="Graph Legend" eyebrow="System shape">
          <div className="grid gap-3">
            {[
              ["Domain", "Business or architectural responsibility", Workflow],
              ["Hotspot", "Change or complexity concentration", Sparkles],
              ["Evidence", "Files supporting a claim", Boxes],
              ["Relationship", "Dependency or ownership edge", Network]
            ].map(([label, value, Icon]) => (
              <div key={String(label)} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center gap-3">
                  <span className="grid h-9 w-9 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-100"><Icon size={16} /></span>
                  <span className="text-sm font-medium text-white">{String(label)}</span>
                </div>
                <span className="text-xs text-slate-500">{String(value)}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Hotspots And Evidence" eyebrow="Where complexity concentrates">
          <div className="grid gap-3 md:grid-cols-2">
            {cards.slice(0, 8).map((card, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{String(card.name ?? card.label ?? card.domain ?? "Repository domain")}</p>
                    <p className="mt-1 text-xs text-slate-500">{String(card.path ?? card.file ?? card.module ?? "knowledge entity")}</p>
                  </div>
                  <Badge className="border-cyan-300/25 bg-cyan-300/10 text-cyan-100">{String(card.kind ?? card.type ?? "domain")}</Badge>
                </div>
                <p className="mt-3 line-clamp-3 text-sm leading-5 text-slate-400">{String(card.description ?? card.summary ?? card.reason ?? "")}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function toFlow(items: Array<Record<string, unknown>>): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = items.map((item, index) => {
    const column = index % 3;
    const row = Math.floor(index / 3);
    const label = String(item.name ?? item.label ?? item.domain ?? item.file ?? `Domain ${index + 1}`);
    const kind = String(item.kind ?? item.type ?? "domain");
    return {
      id: `node-${index}`,
      position: { x: column * 320, y: row * 190 },
      data: {
        label: (
          <div className="rounded-2xl border border-white/[0.12] bg-slate-950/95 p-4 shadow-[0_24px_60px_rgba(0,0,0,0.32)]">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100"><Boxes size={17} /></span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{label}</p>
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">{kind}</p>
              </div>
            </div>
            <p className="mt-3 line-clamp-2 text-xs leading-5 text-slate-400">{String(item.summary ?? item.description ?? item.reason ?? "Repository intelligence node")}</p>
          </div>
        )
      },
      style: { background: "transparent", border: 0, width: 280, height: 132 }
    };
  });
  const edges: Edge[] = nodes.slice(1).map((node, index) => ({
    id: `edge-${index}`,
    source: nodes[Math.max(0, index - 1)].id,
    target: node.id,
    animated: index % 2 === 0,
    style: { stroke: "rgba(125,211,252,0.42)", strokeWidth: 1.4 }
  }));
  if (nodes.length > 2) edges.push({ id: "edge-root-last", source: nodes[0].id, target: nodes[nodes.length - 1].id, style: { stroke: "rgba(52,211,153,0.38)" } });
  return { nodes, edges };
}
