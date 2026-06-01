"use client";

import { Download, FileText, GanttChartSquare, Rows3 } from "lucide-react";
import type { ReactNode } from "react";
import type { Repository } from "@/lib/api";
import { exportUrl, reportUrl } from "@/lib/api";
import type { RepositorySummary } from "./types";
import { reportSections, topFindings } from "./utils";
import { Badge, Button, EmptyState, Panel, SeverityBadge, Timeline } from "./ui";

export function ReportsCenter({
  repo,
  summary,
  reports,
  activeReport,
  reportText,
  onSelectReport
}: {
  repo: Repository | null;
  summary: RepositorySummary | null;
  reports: string[];
  activeReport: string;
  reportText: string;
  onSelectReport: (report: string) => void;
}) {
  const sections = reportSections(reportText);
  const findings = topFindings(summary, 6);

  return (
    <div className="space-y-5">
      <Panel
        title="Enterprise Report Center"
        eyebrow="Board, diligence, and engineering packets"
        action={repo ? <Button variant="secondary" onClick={() => window.open(exportUrl(repo.id), "_blank")}><Download size={15} /> Export bundle</Button> : null}
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {reports.map((report) => (
            <button
              key={report}
              onClick={() => onSelectReport(report)}
              className={`rounded-2xl border p-4 text-left transition ${
                activeReport === report ? "border-cyan-300/35 bg-cyan-300/10" : "border-white/10 bg-white/[0.035] hover:border-white/20 hover:bg-white/[0.06]"
              }`}
            >
              <FileText className="h-5 w-5 text-cyan-200" />
              <p className="mt-3 truncate text-sm font-semibold text-white">{report}</p>
              <p className="mt-1 text-xs text-slate-500">{report.endsWith(".html") ? "Interactive summary" : report.endsWith(".sarif") ? "Security exchange" : "Markdown packet"}</p>
            </button>
          ))}
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Report Scorecard" eyebrow="What an executive sees first">
          <div className="grid gap-3">
            <ReportSignal icon={<Rows3 size={17} />} label="Sections" value={sections.length} />
            <ReportSignal icon={<GanttChartSquare size={17} />} label="Priority findings" value={findings.length} />
            <ReportSignal icon={<FileText size={17} />} label="Artifact type" value={activeReport.split(".").pop()?.toUpperCase() ?? "MD"} />
          </div>
          {repo ? (
            <a href={reportUrl(repo.id, activeReport)} target="_blank" className="mt-4 inline-flex text-sm font-medium text-cyan-200 hover:text-cyan-100">
              Open raw artifact
            </a>
          ) : null}
        </Panel>

        <Panel title="Executive Summary" eyebrow={activeReport}>
          {sections.length ? (
            <div className="space-y-3">
              {sections.slice(0, 4).map((section, index) => (
                <details key={index} open={index === 0} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                  <summary className="cursor-pointer text-sm font-semibold text-white">{section.title}</summary>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-400">{section.body.slice(0, 1800)}</p>
                </details>
              ))}
            </div>
          ) : (
            <EmptyState title="No report loaded" text="Select a report artifact to render its executive summary, scorecard, and evidence panels." />
          )}
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Risk Matrix" eyebrow="Report-linked findings">
          <div className="space-y-3">
            {findings.map((finding, index) => (
              <div key={index} className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-white">{finding.title ?? finding.message ?? "Finding"}</p>
                  <SeverityBadge severity={finding.severity} />
                </div>
                <p className="mt-2 text-xs text-slate-500">{finding.file}</p>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Recommendation Timeline" eyebrow="Narrative converted to execution">
          <Timeline
            items={[
              { title: "Executive readout", text: "Use the first page for investor, CTO, and board alignment." },
              { title: "Evidence review", text: "Validate high-risk findings against source citations and affected files." },
              { title: "Remediation sprint", text: "Turn report recommendations into tracked engineering work." }
            ]}
          />
        </Panel>
      </div>
    </div>
  );
}

function ReportSignal({ icon, label, value }: { icon: ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-100">{icon}</span>
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <Badge className="border-white/10 bg-white/[0.04] text-white">{value}</Badge>
    </div>
  );
}
