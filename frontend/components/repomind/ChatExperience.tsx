"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Bot, FileSearch, RefreshCw, Send, Sparkles } from "lucide-react";
import type { ChatResult, RepositorySummary } from "./types";
import { citationLineRange, citationPath, evidenceFiles } from "./utils";
import { Alert, Badge, Button, EmptyState, LoadingInline, Panel } from "./ui";

const suggestions = [
  "What are the riskiest files to change?",
  "Explain the architecture in executive terms.",
  "Where could secrets or sensitive data leak?",
  "Which tests should I run before a release?"
];

export function ChatExperience({
  summary,
  answer,
  busy,
  error,
  onAsk
}: {
  summary: RepositorySummary | null;
  answer: ChatResult | null;
  busy: boolean;
  error?: string | null;
  onAsk: (question: string) => void;
}) {
  const [question, setQuestion] = useState("What are the highest leverage risks in this repository?");
  const [selectedCitation, setSelectedCitation] = useState(0);
  const files = useMemo(() => answer?.related_files?.length ? answer.related_files : evidenceFiles(summary, 7), [answer?.related_files, summary]);
  const citations = answer?.citations ?? [];
  const activeCitation = citations[selectedCitation] ?? citations[0];
  const modelMode = String(answer?.model_status?.mode ?? "");
  const ask = (nextQuestion = question) => {
    setQuestion(nextQuestion);
    onAsk(nextQuestion);
  };

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
      <Panel
        title="Repository Intelligence Chat"
        eyebrow="Evidence-first answers"
        action={answer ? <Badge className={modelMode === "deterministic_fallback" ? "border-amber-300/30 bg-amber-300/10 text-amber-100" : "border-emerald-300/30 bg-emerald-300/10 text-emerald-100"}>{modelMode || "ready"}</Badge> : null}
      >
        {error ? <div className="mb-3"><Alert tone="danger"><span className="font-medium">Chat request failed.</span> {error}</Alert></div> : null}
        <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
          <textarea
            className="min-h-24 w-full resize-y bg-transparent text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about architecture, risks, data flow, dependencies, or due diligence."
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
            <div className="flex flex-wrap gap-2">
              {suggestions.slice(0, 2).map((item) => <button key={item} onClick={() => setQuestion(item)} className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.08]">{item}</button>)}
            </div>
            <div className="flex items-center gap-2">
              {error ? <Button variant="secondary" onClick={() => ask()} disabled={busy || !question.trim()}><RefreshCw size={15} /> Retry</Button> : null}
              <Button onClick={() => ask()} disabled={busy || !question.trim()}><Send size={15} /> Ask</Button>
            </div>
          </div>
        </div>

        <div className="mt-5 min-h-[380px] rounded-2xl border border-white/10 bg-white/[0.035] p-5">
          {busy ? (
            <div className="grid min-h-80 place-items-center rounded-2xl border border-white/10 bg-black/20">
              <LoadingInline label="Retrieving evidence and composing cited answer..." />
            </div>
          ) : answer?.answer ? (
            <div className="prose prose-invert max-w-none">
              <div className="mb-4 flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100"><Bot size={18} /></span>
                <div>
                  <p className="text-sm font-semibold text-white">RepoMind answer</p>
                  <p className="text-xs text-slate-500">Grounded by {citations.length} citations, {answer.evidence?.length ?? 0} evidence records, confidence {Math.round((answer.confidence ?? 0) * 100)}%</p>
                </div>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{answer.answer}</p>
            </div>
          ) : (
            <EmptyState title="Ask a repository question" text="Answers render with a citation panel, source previews, and related file exploration." />
          )}
        </div>
      </Panel>

      <div className="space-y-5">
        <Panel title="Citations" eyebrow="Trust boundary">
          {citations.length ? (
            <div className="space-y-3">
              {citations.map((citation, index) => (
                <button key={`${citationPath(citation)}-${index}`} onClick={() => setSelectedCitation(index)} className={`w-full rounded-xl border p-3 text-left transition ${activeCitation === citation ? "border-cyan-300/35 bg-cyan-300/10" : "border-white/10 bg-white/[0.035] hover:bg-white/[0.06]"}`}>
                  <div className="flex items-start justify-between gap-3">
                    <p className="truncate text-sm font-medium text-white">{citationPath(citation)}{citationLineRange(citation)}</p>
                    <Badge className="border-cyan-300/25 bg-cyan-300/10 text-cyan-100">#{citation.id ?? index + 1}</Badge>
                  </div>
                  {citation.text ? <p className="mt-2 line-clamp-4 text-xs leading-5 text-slate-400">{citation.text}</p> : null}
                </button>
              ))}
            </div>
          ) : (
            <EmptyState title="No citations yet" text="Source evidence appears here after a cited answer is generated." action={error ? <AlertTriangle className="mx-auto h-5 w-5 text-amber-200" /> : null} />
          )}
        </Panel>

        <Panel title="Source Preview" eyebrow="click citation to inspect evidence">
          {activeCitation ? (
            <div className="rounded-xl border border-white/10 bg-black/25 p-3">
              <p className="text-sm font-semibold text-white">{citationPath(activeCitation)}{citationLineRange(activeCitation)}</p>
              <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-black/30 p-3 text-xs leading-5 text-slate-300">{activeCitation.text || "No source preview text returned for this citation."}</pre>
            </div>
          ) : (
            <EmptyState title="No source selected" text="Ask a question and click a citation to inspect the file and line evidence." />
          )}
        </Panel>

        <Panel title="Evidence Explorer" eyebrow="Related files">
          <div className="space-y-2">
            {(answer?.affected_services ?? []).slice(0, 5).map((service, index) => (
              <div key={`service-${index}`} className="rounded-xl border border-cyan-300/20 bg-cyan-300/[0.06] p-3">
                <p className="text-sm font-semibold text-cyan-50">{String(service.service ?? "Affected service")}</p>
                <p className="mt-1 text-xs text-cyan-100/70">{String(service.role ?? service.risk ?? "repository service")}</p>
              </div>
            ))}
            {(answer?.evidence ?? []).slice(0, 5).map((item, index) => (
              <div key={`evidence-${index}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-start justify-between gap-3">
                  <p className="truncate text-sm font-semibold text-white">{String(item.file ?? item.kind ?? "Evidence")}</p>
                  <Badge className="border-white/10 bg-white/[0.04] text-slate-300">{String(item.kind ?? "evidence")}</Badge>
                </div>
                <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-400">{String(item.evidence ?? "")}</p>
              </div>
            ))}
            {files.map((file) => (
              <div key={file} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.035] p-3">
                <FileSearch className="h-4 w-4 text-slate-500" />
                <span className="truncate text-sm text-slate-300">{file}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Follow-up Prompts" eyebrow="Analysis loops">
          <div className="space-y-2">
            {[...(answer?.follow_ups ?? []), ...suggestions].slice(0, 5).map((item) => (
              <button key={item} onClick={() => ask(item)} disabled={busy} className="flex w-full items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] p-3 text-left text-sm text-slate-300 hover:bg-white/[0.07] disabled:cursor-not-allowed disabled:opacity-50">
                <Sparkles className="h-4 w-4 text-cyan-200" />
                {item}
              </button>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
