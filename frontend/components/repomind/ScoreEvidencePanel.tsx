"use client";

import { useState } from "react";
import { FileSearch, Scale, ShieldCheck } from "lucide-react";
import type { ScoreEvidence } from "./types";
import { Badge, Panel, ScoreBar } from "./ui";
import { asScore } from "./utils";

export function ScoreEvidencePanel({ evidence }: { evidence?: Record<string, ScoreEvidence> }) {
  const items = Object.values(evidence ?? {});
  const [activeId, setActiveId] = useState(items[0]?.id ?? "health");
  if (!items.length) return null;
  const active = items.find((item) => item.id === activeId) ?? items[0];
  return (
    <Panel title="Evidence Engine" eyebrow="click any score to inspect calculation, weights, confidence, and source citations">
      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <div className="grid gap-2">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveId(String(item.id))}
              className={`rounded-xl border p-3 text-left transition ${active.id === item.id ? "border-cyan-300/35 bg-cyan-300/10" : "border-white/10 bg-white/[0.035] hover:bg-white/[0.06]"}`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-white">{item.label}</span>
                <Badge className="border-white/10 bg-white/[0.04] text-white">{asScore(item.score)}</Badge>
              </div>
              <div className="mt-3">
                <ScoreBar label={`Confidence ${asScore(item.confidence)}/100`} value={asScore(item.confidence)} />
              </div>
            </button>
          ))}
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xl font-semibold text-white">{active.label}</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">{active.calculation}</p>
            </div>
            <Badge className="border-emerald-300/25 bg-emerald-300/10 text-emerald-100">
              <ShieldCheck size={13} /> {asScore(active.confidence)} confidence
            </Badge>
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Weighted factors</p>
              <div className="space-y-2">
                {(active.factors ?? []).map((factor, index) => (
                  <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">{String(factor.name)}</p>
                      <Badge className="border-cyan-300/25 bg-cyan-300/10 text-cyan-100">{Math.round(Number(factor.weight ?? 0) * 100)}%</Badge>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-slate-400">{String(factor.reason ?? "")}</p>
                    <div className="mt-3"><ScoreBar label={`Value ${asScore(Number(factor.value ?? 0))}`} value={asScore(Number(factor.value ?? 0))} /></div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Source citations</p>
              <div className="space-y-2">
                {(active.citations ?? []).slice(0, 10).map((citation, index) => (
                  <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                    <div className="flex items-start gap-2">
                      <FileSearch className="mt-0.5 h-4 w-4 shrink-0 text-cyan-200" />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-white">{String(citation.file ?? "repository")}:{String(citation.line ?? 1)}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-400">{String(citation.evidence ?? citation.rule_id ?? "Repository evidence")}</p>
                      </div>
                    </div>
                  </div>
                ))}
                <div className="rounded-xl border border-amber-300/20 bg-amber-300/[0.08] p-3 text-sm leading-5 text-amber-50">
                  <Scale className="mb-2 h-4 w-4" />
                  Positive contributors: {(active.positive_contributors ?? []).join(" | ") || "None"}. Negative contributors: {(active.negative_contributors ?? []).join(" | ") || "None"}.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
