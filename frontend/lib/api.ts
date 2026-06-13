/** Browser calls the published host port; SSR inside Docker uses the backend service name. */
function getApiUrl(): string {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  }
  return (
    process.env.INTERNAL_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  );
}

/** Public API URL for client-side code (forms, browser fetch). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Crisis = {
  id: string;
  title: string;
  summary: string | null;
  type: string | null;
  country_iso: string | null;
  lat: number | null;
  lng: number | null;
  severity: number | null;
  urgency: string | null;
  tags: string[];
  source: string;
  source_report_id: string | null;
  created_at: string;
  grounding_id?: string | null;
  has_legal_support?: boolean | null;
  legal_match_count?: number;
  user_match_count?: number;
  task_count?: number;
};

export type MatchedChunk = {
  chunk_id: string;
  source_id: string;
  title: string | null;
  article_ref: string | null;
  url: string | null;
  relevance_score: number;
  covers_crisis: boolean;
  reason: string;
  excerpt: string;
};

export type MatchedUser = {
  ansar_id: string;
  name: string | null;
  skills: string[];
  languages: string[];
  trust_tier: string;
  relevance_score: number;
  is_relevant: boolean;
  reason: string;
  matched_skills: string[];
};

export type Grounding = {
  grounding_id: string;
  crisis_id: string;
  has_legal_support: boolean;
  summary: string | null;
  matched_chunks: MatchedChunk[];
  matched_users: MatchedUser[];
  created_at: string;
};

export type Task = {
  id: string;
  crisis_id: string;
  title: string;
  description: string | null;
  required_skills: string[];
  task_type: string | null;
  status: string;
  legal_review_needed: boolean;
  created_at: string;
};

export type TaskMatch = {
  id: string;
  task_id: string;
  ansar_id: string;
  score: number;
  rank: number;
  name: string | null;
  skills: string[];
  trust_tier: string;
  languages: string[];
  task_title?: string | null;
  task_status?: string | null;
  notified_at?: string | null;
  created_at: string;
};

export type TaskMatchGroup = {
  task_id: string;
  task_title: string | null;
  task_status: string | null;
  matches: TaskMatch[];
};

export type TaskMatchResult = {
  crisis_id: string;
  task_count: number;
  match_count: number;
  tasks: TaskMatchGroup[];
  summary: string;
  cached?: boolean;
  elapsed_seconds?: number;
};

export type AnsarUser = {
  id: string;
  name: string;
  skills: string[];
  lat: number | null;
  lng: number | null;
  languages: string[];
  trust_tier: string;
  capacity: number;
  created_at: string;
};

export type LegalSource = {
  id: string;
  title: string;
  jurisdiction: string | null;
  source_type: string | null;
  url: string | null;
  slug: string | null;
  topic_tags: string[];
  leverage_routes: unknown[];
  chunk_count: number;
  created_at: string;
};

export type LegalChunk = {
  id: string;
  source_id: string;
  chunk_text: string | null;
  article_ref: string | null;
  topic_tags: string[];
  chunk_index: number | null;
  source_title: string;
  jurisdiction: string | null;
  source_url: string | null;
};

export type Report = {
  id: string;
  narrative: string;
  incident_at: string | null;
  location_text: string | null;
  country_iso: string;
  type: string | null;
  tags: string[];
  status: string;
  promoted_crisis_id: string | null;
  triage_notes: string | null;
  created_at: string;
  reporter_name?: string | null;
  is_anonymous?: boolean;
  evidence?: { id: string; evidence_type: string; file_url: string | null; description: string | null }[];
};

export type NotifyResult = {
  crisis_id: string;
  match_id?: string;
  chat_id?: string;
  helper_name?: string;
  task_title?: string;
  sent: number;
  skipped: number;
  failed: number;
  cached?: boolean;
  summary: string;
  elapsed_seconds?: number;
};

export async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function postApi<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`, { method: "POST", cache: "no-store" });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `API error: ${res.status}`);
  }
  return res.json();
}
