const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_REPOMIND_API_KEY;

export type Repository = {
  id: string;
  name: string;
  source_type: string;
  source: string;
  status: string;
  error?: string | null;
  repository_deleted?: boolean;
  analysis_job?: AnalysisJob;
};

export type AnalysisJob = {
  id: string;
  status: string;
  progress: number;
  message: string;
  created_at?: number;
  updated_at?: number;
};

export async function listRepositories(): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/repositories`, { cache: "no-store", headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function importLocal(path: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/local`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ path })
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function cloneRepo(github_url: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/clone`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ github_url })
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function uploadZip(file: File): Promise<Repository> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_BASE}/repositories/upload`, { method: "POST", body, headers: authHeaders() });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function analyze(repoId: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/analysis`, { method: "POST", headers: authHeaders() });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function repositoryStatus(repoId: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/status`, { cache: "no-store", headers: authHeaders() });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function cancelAnalysis(repoId: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/analysis/cancel`, { method: "POST", headers: authHeaders() });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function summary(repoId: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/summary`, { cache: "no-store", headers: authHeaders() });
  if (!res.ok) return null;
  return res.json();
}

export async function chat(repoId: string, question: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/chat`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ question })
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function fetchReport(repoId: string, name: string): Promise<string> {
  const res = await fetch(reportUrl(repoId, name), { cache: "no-store", headers: authHeaders() });
  if (!res.ok) throw new Error(await errorText(res));
  return res.text();
}

export function reportUrl(repoId: string, name: string) {
  return withApiKey(`${API_BASE}/repositories/${repoId}/reports/${name}`);
}

export function exportUrl(repoId: string) {
  return withApiKey(`${API_BASE}/repositories/${repoId}/export`);
}

async function errorText(res: Response) {
  try {
    const payload = await res.json();
    return payload.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

function jsonHeaders(): Record<string, string> {
  return { "content-type": "application/json", ...authHeaders() };
}

function authHeaders(): Record<string, string> {
  return API_KEY ? { "x-api-key": API_KEY } : {};
}

function withApiKey(url: string) {
  if (!API_KEY) return url;
  const next = new URL(url);
  next.searchParams.set("api_key", API_KEY);
  return next.toString();
}
