"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Archive, ChevronDown, ChevronRight, CloudUpload, Filter, FolderInput, GitBranch, Github, Heart, History, LayoutList, Play, Search, Square, Star } from "lucide-react";
import type { Repository } from "@/lib/api";
import { Alert, Badge, Button } from "./ui";

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

const sourceLabels: Record<string, string> = { github: "GitHub", local: "Local", zip: "Imported" };

export function RepositoryRail(props: Props) {
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [compact, setCompact] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({ local: true, github: true, imported: true });
  const [favorites, setFavorites] = useState<string[]>([]);

  useEffect(() => {
    try {
      setFavorites(JSON.parse(localStorage.getItem("repomind:favorites") ?? "[]"));
    } catch {
      setFavorites([]);
    }
  }, []);

  const filtered = useMemo(() => {
    const lower = query.toLowerCase();
    return props.repositories.filter((repo) => {
      const matchesQuery = !lower || `${repo.name} ${repo.source} ${repo.source_type}`.toLowerCase().includes(lower);
      const matchesSource = sourceFilter === "all" || repo.source_type === sourceFilter;
      return matchesQuery && matchesSource;
    });
  }, [props.repositories, query, sourceFilter]);

  const groups = useMemo(() => {
    const recent = filtered.slice(0, 6);
    const favoriteRepos = filtered.filter((repo) => favorites.includes(repo.id));
    const bySource = filtered.reduce<Record<string, Repository[]>>((acc, repo) => {
      const key = repo.source_type === "zip" ? "imported" : repo.source_type;
      acc[key] = [...(acc[key] ?? []), repo];
      return acc;
    }, {});
    return [
      { id: "favorites", label: "Favorites", icon: Star, repos: favoriteRepos },
      { id: "recent", label: "Recent", icon: History, repos: recent },
      { id: "local", label: "Local", icon: FolderInput, repos: bySource.local ?? [] },
      { id: "github", label: "GitHub", icon: Github, repos: bySource.github ?? [] },
      { id: "imported", label: "Imported", icon: Archive, repos: bySource.imported ?? [] },
    ].filter((group) => group.repos.length || group.id === "favorites");
  }, [filtered, favorites]);

  const toggleFavorite = (repoId: string) => {
    const next = favorites.includes(repoId) ? favorites.filter((id) => id !== repoId) : [repoId, ...favorites].slice(0, 20);
    setFavorites(next);
    localStorage.setItem("repomind:favorites", JSON.stringify(next));
  };

  return (
    <aside className={`flex max-h-[72vh] flex-col rounded-3xl border border-white/10 bg-slate-950/[0.86] shadow-panel backdrop-blur-xl lg:max-h-none lg:min-h-[calc(100vh-32px)] ${compact ? "lg:w-[92px]" : ""}`}>
      <div className="border-b border-white/10 p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white text-slate-950 shadow-[0_16px_44px_rgba(255,255,255,0.18)]">
              <Archive size={20} />
            </div>
            {!compact ? (
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-200/70">RepoMindAI</p>
                <h1 className="truncate text-lg font-semibold tracking-tight text-white">Intelligence OS</h1>
              </div>
            ) : null}
          </div>
          <button onClick={() => setCompact((value) => !value)} className="rounded-lg border border-white/10 bg-white/[0.04] p-2 text-slate-400 hover:text-white">
            <LayoutList size={15} />
          </button>
        </div>

        {!compact ? (
          <>
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.035] p-3">
              <div className="flex items-center justify-between gap-2 text-xs text-slate-400">
                <span className="truncate">{props.activeRepo?.name ?? "No repository selected"}</span>
                <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{props.activeRepo?.status ?? "idle"}</Badge>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/[0.06]">
                <div className="h-full rounded-full bg-cyan-300 transition-all" style={{ width: `${Math.max(0, Math.min(100, props.progress))}%` }} />
              </div>
            </div>
            {props.error ? <div className="mt-3"><Alert tone="danger">{props.error}</Alert></div> : null}
          </>
        ) : null}
      </div>

      {!compact ? (
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
      ) : null}

      <div className={`flex items-center gap-2 border-b border-white/10 p-4 ${compact ? "flex-col" : ""}`}>
        <Button className={compact ? "w-full px-2" : "flex-1"} onClick={props.onAnalyze} disabled={!props.activeRepo || Boolean(props.busy)}>
          <Play size={15} />
          {!compact ? "Analyze" : null}
        </Button>
        <Button variant="danger" onClick={props.onCancel} disabled={!props.activeRepo || Boolean(props.busy)}>
          <Square size={15} />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {!compact ? (
          <div className="sticky top-0 z-10 space-y-2 bg-slate-950/[0.92] pb-3">
            <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-300 focus-within:border-cyan-300/45">
              <Search size={14} className="text-slate-500" />
              <input className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-slate-600" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search repositories" />
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-slate-400">
              <Filter size={13} className="text-slate-500" />
              <select className="min-w-0 flex-1 bg-transparent outline-none" value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
                {["all", "local", "github", "zip"].map((item) => <option key={item} value={item}>{item === "all" ? "All sources" : sourceLabels[item] ?? item}</option>)}
              </select>
            </label>
          </div>
        ) : null}

        <div className="space-y-3">
          {groups.map((group) => {
            const Icon = group.icon;
            const closed = collapsed[group.id];
            const visibleLimit = compact ? 14 : 7;
            const visibleRepos = group.repos.slice(0, visibleLimit);
            const hiddenCount = Math.max(0, group.repos.length - visibleRepos.length);
            return (
              <section key={group.id}>
                {!compact ? (
                  <button onClick={() => setCollapsed((current) => ({ ...current, [group.id]: !closed }))} className="mb-2 flex min-h-9 w-full items-center justify-between rounded-lg px-2 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 hover:bg-white/[0.04]">
                    <span className="flex items-center gap-2"><Icon size={13} />{group.label}</span>
                    <span className="flex items-center gap-2">{group.repos.length}{closed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}</span>
                  </button>
                ) : null}
                {!closed ? (
                  <div className="space-y-1.5">
                    {visibleRepos.map((repo) => (
                      <RepositoryCard key={`${group.id}-${repo.id}`} repo={repo} active={props.activeRepo?.id === repo.id} compact={compact} favorite={favorites.includes(repo.id)} onSelect={() => props.onSelect(repo)} onFavorite={() => toggleFavorite(repo.id)} />
                    ))}
                    {!compact && hiddenCount ? (
                      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs font-medium text-slate-500">
                        +{hiddenCount} more repositories. Use search or filters to narrow.
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </section>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

function RepositoryCard({ repo, active, compact, favorite, onSelect, onFavorite }: { repo: Repository; active: boolean; compact: boolean; favorite: boolean; onSelect: () => void; onFavorite: () => void }) {
  const source = repo.source_type === "zip" ? "imported" : repo.source_type;
  const Icon = source === "github" ? Github : source === "local" ? FolderInput : Archive;
  return (
    <div className={`group flex items-center gap-2 rounded-xl border transition ${active ? "border-cyan-300/35 bg-cyan-300/10" : "border-white/[0.08] bg-white/[0.025] hover:border-white/[0.16] hover:bg-white/[0.05]"} ${compact ? "justify-center p-2" : "p-2.5"}`}>
      <button onClick={onSelect} className="flex min-w-0 flex-1 items-center gap-2 text-left">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-black/20 text-slate-300"><Icon size={14} /></span>
        {!compact ? (
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-white">{repo.name}</span>
            <span className="block truncate text-xs text-slate-500">{repo.source}</span>
          </span>
        ) : null}
      </button>
      {!compact ? (
        <button onClick={onFavorite} className={`rounded-lg p-1.5 opacity-70 hover:bg-white/[0.08] hover:opacity-100 ${favorite ? "text-amber-200" : "text-slate-500"}`}>
          <Heart size={13} fill={favorite ? "currentColor" : "none"} />
        </button>
      ) : null}
    </div>
  );
}

function Field({ icon, value, placeholder, onChange }: { icon: ReactNode; value: string; placeholder: string; onChange: (value: string) => void }) {
  return (
    <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300 focus-within:border-cyan-300/45">
      <span className="text-slate-500">{icon}</span>
      <input className="min-w-0 flex-1 bg-transparent text-slate-100 outline-none placeholder:text-slate-600" value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
