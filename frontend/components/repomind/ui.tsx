"use client";

import type { ReactNode } from "react";
import { AlertTriangle, ArrowUpRight, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { asScore, scoreTone, severityTone } from "./utils";

export function Button({
  children,
  variant = "primary",
  className,
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  return (
    <button
      {...props}
      disabled={disabled}
      className={clsx(
        "inline-flex min-h-9 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium transition",
        "focus:outline-none focus:ring-2 focus:ring-cyan-300/35 disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-white text-slate-950 shadow-[0_12px_30px_rgba(255,255,255,0.14)] hover:bg-cyan-50",
        variant === "secondary" && "border border-white/10 bg-white/[0.06] text-slate-100 hover:bg-white/[0.1]",
        variant === "ghost" && "text-slate-300 hover:bg-white/[0.07] hover:text-white",
        variant === "danger" && "border border-rose-400/35 bg-rose-500/15 text-rose-100 hover:bg-rose-500/25",
        className
      )}
    >
      {children}
    </button>
  );
}

export function Panel({
  title,
  eyebrow,
  action,
  children,
  className
}: {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("rounded-2xl border border-white/10 bg-slate-950/70 shadow-panel backdrop-blur-xl", className)}>
      {(title || action) && (
        <div className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-4">
          <div>
            {eyebrow ? <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-200/75">{eyebrow}</p> : null}
            {title ? <h2 className="mt-1 text-base font-semibold text-white">{title}</h2> : null}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  score,
  icon
}: {
  label: string;
  value: string | number;
  detail?: string;
  score?: number;
  icon?: ReactNode;
}) {
  const tone = scoreTone(asScore(score ?? (typeof value === "number" ? value : 0)));
  return (
    <div className="rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.035))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-medium uppercase tracking-[0.14em] text-slate-400">{label}</span>
        {icon ? <span className="rounded-lg border border-white/10 bg-white/[0.04] p-2 text-cyan-200">{icon}</span> : null}
      </div>
      <div className="mt-4 flex items-end justify-between gap-3">
        <strong className="text-3xl font-semibold tracking-tight text-white">{value}</strong>
        {score !== undefined ? <Badge className={tone}>{asScore(score)}</Badge> : null}
      </div>
      {detail ? <p className="mt-2 min-h-8 text-sm leading-5 text-slate-400">{detail}</p> : null}
    </div>
  );
}

export function ScoreBar({ value, label }: { value: number; label?: string }) {
  const score = asScore(value);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span>{score}/100</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
        <div className="h-full rounded-full bg-[linear-gradient(90deg,#38bdf8,#34d399,#fbbf24)]" style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium", className ?? "border-white/10 bg-white/[0.05] text-slate-300")}>
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity?: string }) {
  return <Badge className={severityTone(severity)}>{severity ?? "info"}</Badge>;
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/[0.12] bg-white/[0.025] p-8 text-center">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.04] text-cyan-200">
        <ArrowUpRight size={20} />
      </div>
      <h3 className="mt-4 text-base font-semibold text-white">{title}</h3>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">{text}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function SkeletonGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="h-36 animate-pulse rounded-2xl border border-white/10 bg-white/[0.04]" />
      ))}
    </div>
  );
}

export function Alert({ children, tone = "warn" }: { children: ReactNode; tone?: "warn" | "danger" | "info" }) {
  return (
    <div
      className={clsx(
        "flex items-start gap-3 rounded-xl border p-3 text-sm",
        tone === "danger" && "border-rose-400/30 bg-rose-500/[0.12] text-rose-100",
        tone === "warn" && "border-amber-400/30 bg-amber-500/[0.12] text-amber-100",
        tone === "info" && "border-cyan-400/25 bg-cyan-500/10 text-cyan-100"
      )}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function LoadingInline({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-300">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </span>
  );
}

export function Timeline({ items }: { items: Array<{ title: string; text: string; tone?: string }> }) {
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="grid grid-cols-[24px_1fr] gap-3">
          <div className="relative flex justify-center">
            <span className="mt-1 h-3 w-3 rounded-full border border-cyan-300/45 bg-cyan-300/20" />
            {index < items.length - 1 ? <span className="absolute bottom-[-14px] top-5 w-px bg-white/10" /> : null}
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
            <p className="text-sm font-medium text-white">{item.title}</p>
            <p className="mt-1 text-sm leading-5 text-slate-400">{item.text}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
