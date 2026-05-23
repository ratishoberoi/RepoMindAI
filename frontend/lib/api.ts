const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Repository = {
  id: string;
  name: string;
  source_type: string;
  source: string;
  status: string;
  error?: string | null;
  repository_deleted?: boolean;
};

export async function listRepositories(): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/repositories`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export async function importLocal(path: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/local`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ path })
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function cloneRepo(github_url: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/clone`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ github_url })
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function uploadZip(file: File): Promise<Repository> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_BASE}/repositories/upload`, { method: "POST", body });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function analyze(repoId: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/analysis`, { method: "POST" });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function summary(repoId: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/summary`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

export async function chat(repoId: string, question: string) {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question })
  });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

export async function fetchReport(repoId: string, name: string): Promise<string> {
  const res = await fetch(reportUrl(repoId, name), { cache: "no-store" });
  if (!res.ok) throw new Error(await errorText(res));
  return res.text();
}

export function reportUrl(repoId: string, name: string) {
  return `${API_BASE}/repositories/${repoId}/reports/${name}`;
}

export function exportUrl(repoId: string) {
  return `${API_BASE}/repositories/${repoId}/export`;
}

async function errorText(res: Response) {
  try {
    const payload = await res.json();
    return payload.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}
