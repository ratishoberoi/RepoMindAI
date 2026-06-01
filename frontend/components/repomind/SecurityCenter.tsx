"use client";

import { AlertTriangle, FileWarning, ShieldAlert, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import type { Finding, RepositorySummary } from "./types";
import { Badge, EmptyState, MetricCard, Panel, SeverityBadge } from "./ui";
import { asScore } from "./utils";
import { Heatmap, RiskMatrix, ScoreOrb } from "./visuals";

const severities = ["critical", "high", "medium", "low"] as const;

export function SecurityCenter({ summary }: { summary: RepositorySummary | null }) {
  const model = buildSecurityModel(summary);
  if (!summary) {
    return (
      <EmptyState
        title="Security center unavailable"
        text="Analyze a repository to map findings to OWASP, CWE, evidence files, impact, and remediation."
      />
    );
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-3xl border border-rose-300/15 bg-[linear-gradient(135deg,rgba(251,113,133,0.16),rgba(255,255,255,0.04)_42%,rgba(56,189,248,0.08))] shadow-panel">
        <div className="grid gap-0 xl:grid-cols-[280px_1fr_360px]">
          <div className="grid place-items-center border-b border-white/10 bg-black/25 p-5 xl:border-b-0 xl:border-r">
            <ScoreOrb label="Security" score={model.score} size="medium" sublabel={model.riskLabel} />
          </div>
          <div className="p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-2xl border border-rose-300/25 bg-rose-300/10 text-rose-100">
                <ShieldAlert size={20} />
              </span>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-rose-100/75">Security Center 2.0</p>
                <h2 className="text-3xl font-semibold tracking-tight text-white">Evidence-backed exposure dashboard</h2>
              </div>
            </div>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
              Findings are normalized into severity, OWASP category, CWE mapping, impact, remediation, and affected source files.
            </p>
            <div className="mt-5 grid gap-3 md:grid-cols-4">
              <MetricCard label="Findings" value={model.findings.length} detail="Scanner and custom evidence" />
              <MetricCard label="OWASP mapped" value={model.owaspCount} detail="Findings with category mapping" />
              <MetricCard label="CWE mapped" value={model.cweCount} detail="Weakness taxonomy coverage" />
              <MetricCard label="High+" value={model.highImpact} detail="Critical and high findings" />
            </div>
          </div>
          <div className="border-t border-white/10 bg-black/20 p-5 xl:border-l xl:border-t-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Severity mix</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {severities.map((severity) => (
                <div key={severity} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                  <SeverityBadge severity={severity} />
                  <p className="mt-2 text-2xl font-semibold text-white">{model.severityCounts[severity] ?? 0}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Risk Matrix" eyebrow="Severity and likelihood">
          <RiskMatrix
            items={model.findings.slice(0, 14).map((finding, index) => ({
              label: finding.message ?? finding.title ?? finding.path ?? `Finding ${index + 1}`,
              severity: finding.severity,
              likelihood: likelihoodFor(finding)
            }))}
          />
        </Panel>
        <Panel title="Taxonomy Heatmap" eyebrow="OWASP and CWE concentration">
          <Heatmap
            values={[
              ...Object.entries(model.owasp).map(([label, value]) => ({ label, value: value * 18 })),
              ...Object.entries(model.cwe).map(([label, value]) => ({ label, value: value * 14 }))
            ]}
          />
        </Panel>
      </div>

      <Panel title="Security Findings" eyebrow="Impact, remediation, affected files">
        {model.findings.length ? (
          <div className="grid gap-3">
            {model.findings.slice(0, 40).map((finding, index) => (
              <div key={`${finding.path ?? finding.file}-${finding.line}-${index}`} className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={finding.severity} />
                      {finding.owasp ? <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">{finding.owasp}</Badge> : null}
                      {finding.cwe ? <Badge className="border-amber-300/20 bg-amber-300/10 text-amber-100">{finding.cwe}</Badge> : null}
                      {finding.cvss ? <Badge className="border-rose-300/20 bg-rose-300/10 text-rose-100">CVSS {finding.cvss}</Badge> : null}
                      {finding.scanner ? <Badge className="border-white/10 bg-black/20 text-slate-300">{finding.scanner}</Badge> : null}
                    </div>
                    <p className="mt-3 text-sm font-semibold text-white">{finding.message ?? finding.title ?? "Security finding"}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {finding.path ?? finding.file ?? "unknown file"}:{finding.line ?? 1}
                    </p>
                  </div>
                  <ShieldCheck className="h-5 w-5 text-cyan-200" />
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <EvidenceBox icon={<AlertTriangle size={14} />} title="Impact" text={finding.impact ?? "Impact requires manual triage."} />
                  <EvidenceBox icon={<FileWarning size={14} />} title="Remediation" text={finding.remediation ?? finding.recommendation ?? "Review and remediate this finding."} />
                  <EvidenceBox icon={<ShieldCheck size={14} />} title="Business impact" text={finding.business_impact ?? "Business impact requires triage."} />
                  <EvidenceBox icon={<ShieldAlert size={14} />} title="Exploitability" text={finding.exploitability ?? "unknown"} />
                </div>
                {(finding.affected_files ?? []).length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {finding.affected_files?.slice(0, 6).map((file) => (
                      <Badge key={file} className="border-white/10 bg-black/20 text-slate-300">{file}</Badge>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No security findings" text="Enabled scanners did not return high-confidence findings for this repository." />
        )}
      </Panel>
    </div>
  );
}

function EvidenceBox({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        <span className="text-cyan-200">{icon}</span>
        {title}
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-300">{text}</p>
    </div>
  );
}

function buildSecurityModel(summary: RepositorySummary | null) {
  const findings = summary?.security?.findings ?? [];
  const severityCounts = Object.fromEntries(
    severities.map((severity) => [
      severity,
      findings.filter((finding) => String(finding.severity ?? "").toLowerCase() === severity).length
    ])
  ) as Record<(typeof severities)[number], number>;
  const taxonomy = (field: "owasp" | "cwe") =>
    findings.reduce<Record<string, number>>((acc, finding) => {
      const key = finding[field] ?? "Unmapped";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
  const owasp = taxonomy("owasp");
  const cwe = taxonomy("cwe");
  const highImpact = severityCounts.critical + severityCounts.high;
  return {
    findings,
    severityCounts,
    owasp,
    cwe,
    owaspCount: findings.filter((finding) => finding.owasp).length,
    cweCount: findings.filter((finding) => finding.cwe).length,
    highImpact,
    score: asScore(summary?.scores?.security),
    riskLabel: highImpact ? `${highImpact} high-impact` : "controlled"
  };
}

function likelihoodFor(finding: Finding) {
  const severity = String(finding.severity ?? "").toLowerCase();
  if (severity === "critical") return 5;
  if (severity === "high") return 4;
  if (severity === "medium") return 3;
  return 2;
}
