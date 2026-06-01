"use client";

import { useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { Boxes, Filter, Network, Search } from "lucide-react";
import type { RepositorySummary } from "./types";
import { domainCards } from "./utils";
import { Badge, EmptyState, Panel } from "./ui";

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

  if (!summary) {
    return <EmptyState title="Knowledge graph unavailable" text="Analyze a repository to build symbols, domains, hotspots, and dependency relationships." />;
  }

  return (
    <div className="space-y-5">
      <Panel title="Repository Knowledge Graph" eyebrow="Flagship intelligence map">
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
          <div className="h-[610px] overflow-hidden rounded-2xl border border-white/10 bg-[#070b12]">
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
        <Panel title="Graph Metrics" eyebrow="System shape">
          <div className="grid gap-3">
            {Object.entries(graph?.metrics ?? {}).slice(0, 8).map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <span className="text-sm text-slate-400">{label.replaceAll("_", " ")}</span>
                <strong className="text-sm text-white">{String(value)}</strong>
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
