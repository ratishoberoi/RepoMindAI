"use client";

import type { ReactNode } from "react";

export function GlassPanel({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.07] p-4 shadow-panel backdrop-blur-xl">
      {title ? <h2 className="mb-3 text-sm font-semibold uppercase text-slate-300">{title}</h2> : null}
      {children}
    </section>
  );
}

export function IconButton(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { title: string }) {
  return <button {...props} className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white text-slate-950 disabled:opacity-50" />;
}

export function TextInput({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <input className="min-w-0 flex-1 rounded-md border border-white/10 bg-black/25 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-cyan-300/70" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />;
}

export function ControlLabel({ children }: { children: ReactNode }) {
  return <label className="mb-1 mt-3 block text-xs uppercase text-slate-400 first:mt-0">{children}</label>;
}

export function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-3">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm font-medium text-slate-100">{value}</div>
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="rounded-md border border-dashed border-white/15 bg-black/20 px-3 py-8 text-center text-sm text-slate-400">{text}</div>;
}

export function EvidenceList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <div className="mb-2 text-xs uppercase text-slate-500">{title}</div>
      <div className="space-y-1">{items.map((item) => <div key={item} className="rounded bg-white/5 px-2 py-1 text-slate-300">{item}</div>)}</div>
    </div>
  );
}
