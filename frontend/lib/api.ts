export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type Task = {
  id: string;
  order_id: string;
  customer_id: string;
  expected_amount_minor_units: number;
  currency: string;
  notification_required: boolean;
  original_request: string;
  created_at: string;
};

export type PredicateResult = {
  field: string;
  operator: string;
  expected: unknown;
  observed: unknown;
  passed: boolean | null;
  reason: string | null;
};

export type Verdict = "VERIFIED" | "CONTRADICTED" | "INDETERMINATE" | "NOT_VERIFIABLE";

export type Run = {
  id: string;
  task_id: string;
  status: string;
  agent_identity: string;
  agent_model: string | null;
  created_at: string;
  raw_claim: string | null;
  claim_type: string | null;
  normalized_claim: Record<string, unknown> | null;
  normalization_error: string | null;
  proof_definition_id: string | null;
  proof_definition_version: string | null;
  systems_queried: string[] | null;
  credential_role_used: string | null;
  raw_evidence: Record<string, unknown> | null;
  normalized_evidence: Record<string, unknown> | null;
  predicate_results: PredicateResult[] | null;
  verdict: Verdict | null;
  verdict_explanation: string | null;
  verified_at: string | null;
  task: Task;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${init?.method || "GET"} ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export function createTask(body: {
  order_id: string;
  customer_id: string;
  expected_amount_minor_units: number;
  currency: string;
  notification_required: boolean;
  original_request: string;
}) {
  return request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(body) });
}

export function createRun(task_id: string) {
  return request<Run>("/api/runs", { method: "POST", body: JSON.stringify({ task_id }) });
}

export function claimRun(runId: string) {
  return request<Run>(`/api/runs/${runId}/claim`, { method: "POST", body: JSON.stringify({}) });
}

export function verifyRun(runId: string) {
  return request<Run>(`/api/runs/${runId}/verify`, { method: "POST" });
}

export function listRuns() {
  return request<Run[]>("/api/runs");
}

export function getRun(runId: string) {
  return request<Run>(`/api/runs/${runId}`);
}
