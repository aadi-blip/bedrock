import type {
  CrawlJob,
  GapAnalysisResponse,
  GraphData,
  Paper,
  SeedResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function seedPaper(url: string, depth: number = 2): Promise<SeedResponse> {
  return apiFetch<SeedResponse>("/seed", {
    method: "POST",
    body: JSON.stringify({ url, depth }),
  });
}

export async function getGraph(): Promise<GraphData> {
  return apiFetch<GraphData>("/graph");
}

export async function getPaper(id: number): Promise<Paper> {
  return apiFetch<Paper>(`/paper/${id}`);
}

export async function toggleRead(id: number, read: boolean): Promise<Paper> {
  return apiFetch<Paper>(`/paper/${id}/read`, {
    method: "PATCH",
    body: JSON.stringify({ read }),
  });
}

export async function getDigest(id: number): Promise<Paper> {
  return apiFetch<Paper>(`/paper/${id}/digest`, {
    method: "POST",
  });
}

export async function runGapAnalysis(): Promise<GapAnalysisResponse> {
  return apiFetch<GapAnalysisResponse>("/gap-analysis", {
    method: "POST",
  });
}

export async function getCrawlJob(jobId: number): Promise<CrawlJob> {
  return apiFetch<CrawlJob>(`/crawl/${jobId}`);
}
