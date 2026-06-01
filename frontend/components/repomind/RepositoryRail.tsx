"use client";

import { Archive, CloudUpload, FolderInput, GitBranch, KeyRound, Play, Search, Square } from "lucide-react";
import type { Repository } from "@/lib/api";
import type { ReactNode } from "react";
import { Button, Badge, Alert } from "./ui";

type Props = {
  repositories: Repository[];
  activeRepo: Repository | null;
  progress: number;
  busy: string | null;
  error: string | null;
  githubUrl: string;
  localPath: string;
  onGithubUrl: (value: string) => void;
  onLocalPath: (value: string) => void;
  onSelect: (repo: Repository) => void;
  onClone: () => void;
  onImport: () => void;
  onUpload: (file: File) => void;
  onAnalyze: () => void;
  onCancel: () => void;
};

export function RepositoryRail(props: Props) {
  return (
    <aside className="flex min-h-[calc(100vh-32px)] flex-col rounded-3xl border border-white/10 bg-slate-950/[0.82] shadow-panel backdrop-blur-xl">
      <div className="border-b border-white/10 p-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl bg-white text-slate-950 shadow-[0_16px_44px_rgba(255,255,255,0.18)]">
            <Archive size={20} />
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-200/70">RepoMindAI</p>
            <h1 className="text-lg font-semibold tracking-tight text-white">Intelligence OS</h1>
          </div>
        </div>
        <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.035] p-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{props.activeRepo?.name ?? "No repository"}</span>
            <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{props.activeRepo?.status ?? "idle"}</Badge>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/[0.06]">
            <div className="h-full rounded-full bg-cyan-300 transition-all" style={{ width: `${Math.max(0, Math.min(100, props.progress))}%` }} />
          </div>
        </div>
        {props.error ? <div className="mt-3"><Alert tone="danger">{props.error}</Alert></div> : null}
      </div>

      <div className="space-y-3 border-b border-white/10 p-4">
        <Field icon={<GitBranch size={15} />} value={props.githubUrl} placeholder="https://github.com/org/repo" onChange={props.onGithubUrl} />
        <div className="grid grid-cols-2 gap-2">
          <Button variant="secondary" onClick={props.onClone} disabled={Boolean(props.busy)}>Clone</Button>
          <label className="inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.06] px-3 text-sm font-medium text-slate-100 transition hover:bg-white/[0.1]">
            <CloudUpload size={15} />
            ZIP
            <input className="hidden" type="file" accept=".zip" onChange={(event) => event.target.files?.[0] && props.onUpload(event.target.files[0])} />
          </label>
        </div>
        <Field icon={<FolderInput size={15} />} value={props.localPath} placeholder="sample_repos/python_fastapi_example" onChange={props.onLocalPath} />
        <Button className="w-full" variant="secondary" onClick={props.onImport} disabled={Boolean(props.busy)}>Import local</Button>
      </div>

      <div className="flex items-center gap-2 border-b border-white/10 p-4">
        <Button className="flex-1" onClick={props.onAnalyze} disabled={!props.activeRepo || Boolean(props.busy)}>
          <Play size={15} />
          Analyze
        </Button>
        <Button variant="danger" onClick={props.onCancel} disabled={!props.activeRepo || Boolean(props.busy)}>
          <Square size={15} />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        <div className="mb-2 flex items-center gap-2 px-2 text-xs uppercase tracking-[0.16em] text-slate-500">
          <Search size={13} />
          Repositories
        </div>
        <div className="space-y-2">
          {props.repositories.map((repo) => (
            <button
              key={repo.id}
              onClick={() => props.onSelect(repo)}
              className={`w-full rounded-2xl border p-3 text-left transition ${
                props.activeRepo?.id === repo.id
                  ? "border-cyan-300/35 bg-cyan-300/10"
                  : "border-white/[0.08] bg-white/[0.025] hover:border-white/[0.16] hover:bg-white/[0.05]"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium text-white">{repo.name}</p>
                <Badge className="border-white/10 bg-white/[0.04] text-[10px] text-slate-300">{repo.source_type}</Badge>
              </div>
              <p className="mt-1 truncate text-xs text-slate-500">{repo.source}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-white/10 p-4 text-xs leading-5 text-slate-500">
        <KeyRound className="mb-2 h-4 w-4 text-slate-400" />
        Enterprise mode uses authenticated APIs, isolated artifacts, and auditable repository actions.
      </div>
    </aside>
  );
}

function Field({ icon, value, placeholder, onChange }: { icon: ReactNode; value: string; placeholder: string; onChange: (value: string) => void }) {
  return (
    <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300 focus-within:border-cyan-300/45">
      <span className="text-slate-500">{icon}</span>
      <input
        className="min-w-0 flex-1 bg-transparent text-slate-100 outline-none placeholder:text-slate-600"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
