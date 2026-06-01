"use client";

import { ArrowDownRight, ArrowUpRight, Minus, type LucideIcon } from "lucide-react";
import { clsx } from "clsx";
import { asScore, severityTone } from "./utils";
import { Badge } from "./ui";

export function ScoreOrb({
  label,
  score,
  sublabel,
  size = "large"
}: {
  label: string;
  score: number;
  sublabel?: string;
  size?: "large" | "medium";
}) {
  const value = asScore(score);
  const radius = size === "large" ? 78 : 52;
  const stroke = size === "large" ? 10 : 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  return (
    <div className="relative grid place-items-center">
      <svg className={size === "large" ? "h-56 w-56" : "h-36 w-36"} viewBox="0 0 190 190" aria-label={`${label} ${value}`}>
        <circle cx="95" cy="95" r={radius} fill="rgba(255,255,255,0.035)" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <circle
          cx="95"
          cy="95"
          r={radius}
          fill="transparent"
          stroke="url(#scoreGradient)"
          strokeLinecap="round"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 95 95)"
        />
        <defs>
          <linearGradient id="scoreGradient" x1="12" x2="178" y1="30" y2="160">
            <stop stopColor="#38bdf8" />
            <stop offset="0.55" stopColor="#34d399" />
            <stop offset="1" stopColor="#fbbf24" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute text-center">
        <div className={clsx("font-semibold tracking-[-0.02em] text-white", size === "large" ? "text-6xl" : "text-4xl")}>{value}</div>
        <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</div>
        {sublabel ? <div className="mt-2 text-xs text-cyan-100">{sublabel}</div> : null}
      </div>
    </div>
  );
}

export function ExecutiveSignalCard({
  label,
  value,
  detail,
  icon: Icon,
  delta = "stable"
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  delta?: "up" | "down" | "stable";
}) {
  const DeltaIcon = delta === "up" ? ArrowUpRight : delta === "down" ? ArrowDownRight : Minus;
  return (
    <div className="group rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.035))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition hover:border-cyan-300/30 hover:bg-white/[0.075]">
      <div className="flex items-start justify-between gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-black/20 text-cyan-100">
          <Icon size={18} />
        </span>
        <span className={clsx("inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[11px]", delta === "down" ? "border-rose-300/25 bg-rose-500/10 text-rose-100" : delta === "up" ? "border-emerald-300/25 bg-emerald-500/10 text-emerald-100" : "border-white/10 bg-white/[0.04] text-slate-300")}>
          <DeltaIcon size={12} />
          {delta}
        </span>
      </div>
      <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <div className="mt-2 text-3xl font-semibold tracking-tight text-white">{value}</div>
      <p className="mt-2 min-h-10 text-sm leading-5 text-slate-400">{detail}</p>
    </div>
  );
}

export function RadarChart({ axes }: { axes: Array<{ label: string; value: number }> }) {
  const size = 260;
  const center = size / 2;
  const radius = 94;
  const points = axes.map((axis, index) => {
    const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
    const distance = (asScore(axis.value) / 100) * radius;
    return `${center + Math.cos(angle) * distance},${center + Math.sin(angle) * distance}`;
  });
  const rings = [0.25, 0.5, 0.75, 1].map((scale) =>
    axes.map((_, index) => {
      const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
      return `${center + Math.cos(angle) * radius * scale},${center + Math.sin(angle) * radius * scale}`;
    }).join(" ")
  );
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[300px]">
      <svg viewBox={`0 0 ${size} ${size}`} className="h-full w-full">
        {rings.map((ring, index) => <polygon key={index} points={ring} fill="none" stroke="rgba(255,255,255,0.09)" />)}
        {axes.map((_, index) => {
          const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
          return <line key={index} x1={center} y1={center} x2={center + Math.cos(angle) * radius} y2={center + Math.sin(angle) * radius} stroke="rgba(255,255,255,0.08)" />;
        })}
        <polygon points={points.join(" ")} fill="rgba(56,189,248,0.18)" stroke="#38bdf8" strokeWidth="2" />
        {axes.map((axis, index) => {
          const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
          return (
            <text key={axis.label} x={center + Math.cos(angle) * 118} y={center + Math.sin(angle) * 118} fill="#cbd5e1" fontSize="11" textAnchor="middle" dominantBaseline="middle">
              {axis.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

export function RiskMatrix({ items }: { items: Array<{ label: string; severity?: string; impact?: number; likelihood?: number }> }) {
  const cells = Array.from({ length: 25 }, (_, index) => {
    const x = index % 5;
    const y = 4 - Math.floor(index / 5);
    const cellItems = items.filter((item) => Math.round(item.impact ?? severityImpact(item.severity)) === x + 1 && Math.round(item.likelihood ?? 3) === y + 1);
    const heat = cellItems.length;
    return { x, y, heat, items: cellItems };
  });
  return (
    <div>
      <div className="grid grid-cols-5 gap-1.5">
        {cells.map((cell) => (
          <div
            key={`${cell.x}-${cell.y}`}
            className={clsx(
              "min-h-16 rounded-lg border p-2 transition",
              cell.heat > 2 && "border-rose-300/[0.35] bg-rose-500/20",
              cell.heat === 2 && "border-amber-300/[0.35] bg-amber-500/[0.18]",
              cell.heat === 1 && "border-cyan-300/30 bg-cyan-500/[0.14]",
              cell.heat === 0 && "border-white/[0.08] bg-white/[0.025]"
            )}
            title={cell.items.map((item) => item.label).join(", ")}
          >
            <span className="text-[10px] text-slate-500">{cell.y + 1}.{cell.x + 1}</span>
            {cell.heat ? <div className="mt-1 text-sm font-semibold text-white">{cell.heat}</div> : null}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] uppercase tracking-[0.14em] text-slate-500">
        <span>Low likelihood</span>
        <span>High impact</span>
      </div>
    </div>
  );
}

export function Heatmap({ values, label }: { values: Array<{ label: string; value: number; severity?: string }>; label?: string }) {
  const normalized = values.length ? values : Array.from({ length: 24 }, (_, index) => ({ label: `Signal ${index + 1}`, value: (index * 17) % 100 }));
  return (
    <div>
      {label ? <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p> : null}
      <div className="grid grid-cols-8 gap-1.5">
        {normalized.slice(0, 40).map((item, index) => {
          const value = asScore(item.value);
          return (
            <div
              key={`${item.label}-${index}`}
              className="aspect-square rounded-md border border-white/[0.08]"
              title={`${item.label}: ${value}`}
              style={{ background: `rgba(${value > 70 ? "251,113,133" : value > 45 ? "245,158,11" : "56,189,248"}, ${0.12 + value / 160})` }}
            />
          );
        })}
      </div>
    </div>
  );
}

export function InsightTicker({ insights }: { insights: Array<{ label: string; severity?: string; text: string }> }) {
  return (
    <div className="grid gap-2">
      {insights.slice(0, 5).map((insight, index) => (
        <div key={`${insight.label}-${index}`} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.035] p-3">
          <Badge className={severityTone(insight.severity)}>{insight.label}</Badge>
          <p className="text-sm leading-5 text-slate-300">{insight.text}</p>
        </div>
      ))}
    </div>
  );
}

function severityImpact(severity?: string) {
  const value = (severity ?? "info").toLowerCase();
  if (value === "critical") return 5;
  if (value === "high") return 4;
  if (value === "medium") return 3;
  if (value === "low") return 2;
  return 1;
}
