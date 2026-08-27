/**
 * Brain Runtime API client (browser-safe).
 *
 * All calls go to same-origin /api/brain/* which proxies to Railway and
 * attaches BRAIN_API_KEY on the server. The browser never sees the upstream secret.
 */

import type {
  Belief,
  HealthResponse,
  ListResponse,
  Prediction,
  ApprovalRequest,
  Contradiction,
  CuriosityTask,
  FormulaRun,
  Opportunity,
  Signal,
  Outcome,
  AcceptanceReport,
  Source,
  OrganismCockpit,
  OrganismSelfState,
  OrganismCuriosityTask,
  OrganismAgencyAction,
  OrganismQuarantineItem,
  OrganismPersistenceStatus,
} from "@/types/brain";

const BFF = "/api/brain";

export function isApiConfigured(): boolean {
  return true;
}

export function apiBase(): string {
  return BFF;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "content-type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${BFF}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Brain API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** Soft request: null on 404 only. Auth errors still throw so cockpit shows them. */
async function requestOptional<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BFF}${path}`, {
      headers: { "content-type": "application/json" },
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Brain API ${res.status}: ${body || res.statusText}`);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    if (e instanceof Error && e.message.includes("404")) return null;
    throw e;
  }
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function createBelief(statement: string, confidence = 0.5) {
  return request<{ id: string; statement: string; confidence: number; state: string }>(
    "/beliefs",
    { method: "POST", body: JSON.stringify({ statement, confidence }) }
  );
}

export async function learn(
  beliefId: string,
  claim: string,
  sourceId: string,
  reliability: number,
  supports: boolean
) {
  return request<{
    id: string;
    statement: string;
    confidence: number;
    state: string;
    version: number;
  }>("/learn", {
    method: "POST",
    body: JSON.stringify({
      belief_id: beliefId,
      claim,
      source_id: sourceId,
      reliability,
      supports,
    }),
  });
}

export async function getPrediction(id: string) {
  return request<Prediction>(`/predictions/${id}`);
}

export async function createPrediction(body: {
  statement: string;
  expected_value: number;
  confidence?: number;
  horizon_seconds?: number;
  belief_id?: string;
  action_id?: string;
}) {
  return request<Prediction>("/predictions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listBeliefs(): Promise<ListResponse<Belief> & { source?: string }> {
  return request<ListResponse<Belief> & { source?: string }>("/beliefs");
}

export async function getBelief(id: string): Promise<Belief> {
  return request<Belief>(`/beliefs/${id}`);
}

export async function listPredictions(): Promise<ListResponse<Prediction>> {
  return request<ListResponse<Prediction>>("/predictions");
}

export async function listSignals(): Promise<ListResponse<Signal>> {
  return request<ListResponse<Signal>>("/signals");
}

export async function listOpportunities(): Promise<ListResponse<Opportunity>> {
  return request<ListResponse<Opportunity>>("/opportunities");
}

export async function listApprovals(): Promise<ListResponse<ApprovalRequest>> {
  return request<ListResponse<ApprovalRequest>>("/approvals");
}

export async function listContradictions(): Promise<ListResponse<Contradiction>> {
  return request<ListResponse<Contradiction>>("/contradictions");
}

export async function listCuriosityTasks(): Promise<ListResponse<CuriosityTask>> {
  return request<ListResponse<CuriosityTask>>("/curiosity");
}

export async function listSources(): Promise<ListResponse<Source>> {
  return request<ListResponse<Source>>("/sources");
}

export async function listOutcomes(): Promise<ListResponse<Outcome>> {
  return request<ListResponse<Outcome>>("/outcomes");
}

export async function listFormulaRuns(): Promise<ListResponse<FormulaRun>> {
  return request<ListResponse<FormulaRun>>("/formula-runs");
}

export async function listAcceptanceReports(): Promise<ListResponse<AcceptanceReport>> {
  return request<ListResponse<AcceptanceReport>>("/acceptance-reports");
}

export async function getOrganismCockpit(): Promise<OrganismCockpit | null> {
  return requestOptional<OrganismCockpit>("/organism/cockpit");
}

export async function getOrganismSelfState(): Promise<OrganismSelfState | null> {
  return requestOptional<OrganismSelfState>("/organism/self-state");
}

export async function listOrganismCuriosity(): Promise<OrganismCuriosityTask[]> {
  const data = await requestOptional<{ items: OrganismCuriosityTask[] }>("/organism/curiosity");
  return data?.items ?? [];
}

export async function listOrganismAgencyActions(): Promise<OrganismAgencyAction[]> {
  const data = await requestOptional<{ items: OrganismAgencyAction[] }>("/organism/agency-actions");
  return data?.items ?? [];
}

export async function approveOrganismAgencyAction(actionId: string, approvedBy: string) {
  return request<Record<string, unknown>>("/organism/agency/approve", {
    method: "POST",
    body: JSON.stringify({ action_id: actionId, approved_by: approvedBy }),
  });
}

export async function listOrganismQuarantine(): Promise<OrganismQuarantineItem[]> {
  const data = await requestOptional<{ items: OrganismQuarantineItem[] }>("/organism/quarantine");
  return data?.items ?? [];
}

export async function getOrganismPersistenceStatus(): Promise<OrganismPersistenceStatus | null> {
  return requestOptional<OrganismPersistenceStatus>("/organism/persistence/status");
}

export async function getBffStatus(): Promise<{
  brain_api_key_configured: boolean;
  fix: string | null;
  sample_authed_beliefs: { status: number; detail?: string } | null;
}> {
  const res = await fetch("/api/brain-status", { cache: "no-store" });
  if (!res.ok) throw new Error(`status ${res.status}`);
  return res.json();
}
