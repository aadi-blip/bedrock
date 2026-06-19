export interface Paper {
  id: number;
  arxiv_id: string;
  title: string | null;
  abstract: string | null;
  authors: string[];
  year: number | null;
  url: string | null;
  pdf_url: string | null;
  read: boolean;
  seed: boolean;
  digest: string | null;
  digest_generated_at: string | null;
  crawled: boolean;
  crawl_depth: number | null;
  gap_score: number | null;
  is_frontier: boolean;
  created_at: string | null;
}

export interface Edge {
  source: number;
  target: number;
}

export interface GraphMeta {
  total_papers: number;
  read_count: number;
  gap_nodes: number[];
}

export interface GraphData {
  nodes: Paper[];
  edges: Edge[];
  meta: GraphMeta;
}

export interface CrawlJob {
  id: number;
  arxiv_id: string;
  status: "pending" | "running" | "done" | "error";
  depth: number;
  papers_found: number;
  edges_found: number;
  created_at: string | null;
  finished_at: string | null;
  error_msg: string | null;
}

export interface SeedResponse {
  job_id: number;
  arxiv_id: string;
  status: string;
}

export interface GapAnalysisResponse {
  gap_nodes: Paper[];
  frontier_count: number;
}
