"use client";

import { Activity, Database, HardDrive, Users } from "lucide-react";
import type { SystemStatus } from "./types";
import { Button, MetricCard, Panel, ScoreBar } from "./ui";
import { compactNumber } from "./utils";

export function SystemAdminPanel({
  data,
  busy,
  onRefresh
}: {
  data: SystemStatus | null;
  busy: boolean;
  onRefresh: () => void;
}) {
  const storage = data?.storage ?? {};
  const requestP95 = Number(data?.requests?.p95_ms ?? 0);
  const queueDepth = Number(data?.jobs?.queue_depth ?? 0);
  const failures = Number(data?.jobs?.failure_count ?? 0);
  return (
    <div className="space-y-5">
      <Panel
        title="System Operations"
        eyebrow="production control plane"
        action={<Button onClick={onRefresh} disabled={busy}>{busy ? "Refreshing" : "Refresh"}</Button>}
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Request P95" value={`${requestP95}ms`} detail="Last 5 minutes" icon={<Activity size={18} />} score={Math.max(0, 100 - requestP95 / 20)} />
          <MetricCard label="Queue Depth" value={queueDepth} detail="Queued/running analysis jobs" icon={<Database size={18} />} score={Math.max(0, 100 - queueDepth * 12)} />
          <MetricCard label="Failures" value={failures} detail="Repo and job failures" score={Math.max(0, 100 - failures * 10)} />
          <MetricCard label="Active Routes" value={compactNumber(data?.active_users ?? 0)} detail="Recent API surface activity" icon={<Users size={18} />} />
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-3">
        <Panel title="Tenant Isolation" eyebrow="organizations, users, teams">
          <div className="space-y-3">
            {Object.entries(data?.tenancy ?? {}).map(([key, value]) => (
              <MetricRow key={key} label={key} value={value} />
            ))}
          </div>
        </Panel>
        <Panel title="Repository Throughput" eyebrow="status distribution">
          <div className="space-y-3">
            {Object.entries(data?.repositories ?? {}).map(([key, value]) => (
              <MetricRow key={key} label={key} value={value} />
            ))}
          </div>
        </Panel>
        <Panel title="Storage Footprint" eyebrow="data, reports, vectors">
          <div className="space-y-4">
            {Object.entries(storage).map(([key, value]) => (
              <div key={key}>
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <HardDrive size={14} className="text-slate-500" />
                  <span className="flex-1">{key.replaceAll("_", " ")}</span>
                  <span>{formatBytes(Number(value))}</span>
                </div>
                <ScoreBar label="" value={Math.min(100, Number(value) / 10_000_000)} />
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] p-3">
      <span className="text-sm capitalize text-slate-300">{label.replaceAll("_", " ")}</span>
      <span className="text-sm font-semibold text-white">{String(value)}</span>
    </div>
  );
}

function formatBytes(value: number) {
  if (value > 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} GB`;
  if (value > 1_000_000) return `${(value / 1_000_000).toFixed(1)} MB`;
  if (value > 1_000) return `${(value / 1_000).toFixed(1)} KB`;
  return `${value} B`;
}
