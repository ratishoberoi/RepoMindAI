"use client";

import { Archive, FileArchive, FolderInput, GitBranch, Loader2, Play, Sparkles } from "lucide-react";
import type { Repository } from "@/lib/api";
import { ControlLabel, Empty, GlassPanel, IconButton, TextInput } from "@/components/dashboard/Controls";
import { tabs } from "@/components/dashboard/constants";

type SidebarProps = {
  repositories: Repository[];
  activeRepo: Repository | null;
  progress: number;
  busy: string | null;
  error: string | null;
  githubUrl: string;
  localPath: string;
  setGithubUrl: (value: string) => void;
  setLocalPath: (value: string) => void;
  setActiveRepo: (repo: Repository) => void;
  onClone: () => void;
  onImport: () => void;
  onUpload: (file: File) => void;
};

export function DashboardSidebar(props: SidebarProps) {
  return (
    <aside className="space-y-4">
      <GlassPanel>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-cyan-200">RepoMind AI</div>
            <h1 className="mt-1 text-2xl font-semibold">Repository Intel</h1>
          </div>
          <Sparkles className="text-emerald-300" size={22} />
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
          <div className={`h-2 rounded-full bg-cyan-300 transition-all duration-500 ${props.busy ? "animate-pulse" : ""}`} style={{ width: `${props.progress}%` }} />
        </div>
        <div className="mt-2 text-xs text-slate-400">{props.busy ? `Running ${props.busy}` : props.activeRepo?.analysis_job?.message ?? props.activeRepo?.status ?? "Waiting for repository"}</div>
      </GlassPanel>

      <GlassPanel title="Ingest">
        <ControlLabel>GitHub URL</ControlLabel>
        <div className="flex gap-2">
          <TextInput value={props.githubUrl} onChange={props.setGithubUrl} placeholder="https://github.com/org/repo" />
          <IconButton title="Clone" disabled={!props.githubUrl || !!props.busy} onClick={props.onClone}>
            <GitBranch size={18} />
          </IconButton>
        </div>
        <ControlLabel>Local Path</ControlLabel>
        <div className="flex gap-2">
          <TextInput value={props.localPath} onChange={props.setLocalPath} />
          <IconButton title="Import" disabled={!props.localPath || !!props.busy} onClick={props.onImport}>
            <FolderInput size={18} />
          </IconButton>
        </div>
        <label className="mt-3 flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-cyan-300/40 bg-cyan-300/10 px-3 py-3 text-sm font-medium text-cyan-100 hover:bg-cyan-300/15">
          <FileArchive size={18} />
          Upload ZIP
          <input className="hidden" type="file" accept=".zip" onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) props.onUpload(file);
          }} />
        </label>
        {props.error ? <div className="mt-3 rounded-md border border-red-400/40 bg-red-500/10 px-3 py-2 text-sm text-red-100">{props.error}</div> : null}
      </GlassPanel>

      <GlassPanel title="Repositories">
        <div className="space-y-2">
          {props.repositories.length === 0 ? <Empty text="No repositories ingested." /> : null}
          {props.repositories.map((repo) => (
            <button key={repo.id} onClick={() => props.setActiveRepo(repo)} className={`w-full rounded-md border px-3 py-2 text-left text-sm transition ${props.activeRepo?.id === repo.id ? "border-cyan-300/70 bg-cyan-300/10" : "border-white/10 bg-white/[0.03] hover:border-white/25"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium text-slate-100">{repo.name}</span>
                <span className="shrink-0 rounded bg-white/10 px-2 py-1 text-xs text-slate-300">{repo.status}</span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2 text-xs text-slate-400">
                <span>{repo.source_type}</span>
                {repo.repository_deleted ? <span>repo files deleted</span> : null}
              </div>
            </button>
          ))}
        </div>
      </GlassPanel>
    </aside>
  );
}

type HeaderProps = {
  activeRepo: Repository | null;
  busy: string | null;
  tab: string;
  setTab: (value: string) => void;
  onAnalyze: () => void;
  onCancel: () => void;
};

export function RepositoryHeader(props: HeaderProps) {
  return (
    <GlassPanel>
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="truncate text-2xl font-semibold">{props.activeRepo?.name ?? "No repository selected"}</div>
          <div className="mt-1 truncate text-sm text-slate-400">{props.activeRepo?.source ?? "Paste a GitHub URL, upload a ZIP, or import a local repository."}</div>
        </div>
        <button disabled={!props.activeRepo || !!props.busy} onClick={props.onAnalyze} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-cyan-300 px-4 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50">
          {props.busy === "analysis" ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
          Analyze
        </button>
        {props.activeRepo && ["queued", "analyzing"].includes(props.activeRepo.status) ? (
          <button disabled={!!props.busy} onClick={props.onCancel} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white/10 px-4 text-sm font-semibold text-slate-100 transition hover:bg-white/15 disabled:opacity-50">
            Cancel
          </button>
        ) : null}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button key={item} onClick={() => props.setTab(item)} className={`rounded-md px-3 py-2 text-sm ${props.tab === item ? "bg-white text-slate-950" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}>
            {item}
          </button>
        ))}
      </div>
    </GlassPanel>
  );
}

export function ExportBundleLink({ href }: { href: string }) {
  return (
    <a className="flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-950" href={href}>
      <Archive size={16} />
      Export Bundle
    </a>
  );
}
