"use client";

import { useEffect, useRef, useState } from "react";
import {
  getHealth,
  getOrganismCockpit,
  getOrganismPersistenceStatus,
  getOrganismSelfState,
  getWorkingMemoryObservation,
  listApprovals,
  listBeliefs,
  listContradictions,
  listCuriosityTasks,
  listEvidence,
  listLearningEvents,
  listOpportunities,
  listOrganismAgencyActions,
  listOrganismCuriosity,
  listOrganismQuarantine,
  listOutcomes,
  listPredictions,
  listSignals,
  listSources,
} from "@/lib/api";
import type { ListResponse } from "@/types/brain";
import type { ObservedGraphEdge, ObservatorySnapshot, RunnerStatus } from "@/types/observatory";

const LIVE_POLL_MS = 5_000;
const HIDDEN_POLL_MS = 20_000;
const MAX_SNAPSHOTS = 120;

async function fetchBff<T>(path: string): Promise<T> {
  const response = await fetch(`/api/brain${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${path} ${response.status}: ${body || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function valueOr<T>(result: PromiseSettledResult<T>, fallback: T, label: string, errors: string[]): T {
  if (result.status === "fulfilled") return result.value;
  errors.push(`${label}: ${result.reason instanceof Error ? result.reason.message : String(result.reason)}`);
  return fallback;
}

function listOr<T>(result: PromiseSettledResult<ListResponse<T>>, fallback: T[], label: string, errors: string[]): T[] {
  return valueOr(result, { items: fallback }, label, errors).items ?? fallback;
}

function entityKey(value: unknown): string {
  if (!value || typeof value !== "object") return String(value ?? "");
  const item = value as Record<string, unknown>;
  return [
    item.id,
    item.updated_at,
    item.created_at,
    item.occurred_at,
    item.state,
    item.status,
    item.confidence,
    item.reliability,
    item.attention_score,
    item.forecast_probability,
    item.actual_outcome,
    item.event_type,
  ].map((part) => String(part ?? "")).join(":");
}

function signatureOf(snapshot: Omit<ObservatorySnapshot, "signature">): string {
  return JSON.stringify({
    health: [
      snapshot.health?.status,
      snapshot.health?.version,
      snapshot.health?.database,
      snapshot.health?.persistence,
      snapshot.health?.heartbeat?.ticks,
      snapshot.health?.heartbeat?.inbox,
      snapshot.health?.heartbeat?.working_memory_size,
    ],
    runner: [snapshot.runner?.ticks, snapshot.runner?.total_processed, snapshot.runner?.inbox, snapshot.runner?.working_memory_size],
    signals: snapshot.signals.map(entityKey),
    evidence: snapshot.evidence.map(entityKey),
    workingMemory: snapshot.workingMemory
      ? [
          snapshot.workingMemory.observed_at,
          snapshot.workingMemory.size,
          snapshot.workingMemory.capacity,
          snapshot.workingMemory.cycle_id,
          snapshot.workingMemory.evicted_count,
        ]
      : null,
    beliefs: snapshot.beliefs.map(entityKey),
    predictions: snapshot.predictions.map(entityKey),
    contradictions: snapshot.contradictions.map(entityKey),
    curiosity: snapshot.curiosity.map(entityKey),
    approvals: snapshot.approvals.map(entityKey),
    outcomes: snapshot.outcomes.map(entityKey),
    learningEvents: snapshot.learningEvents.map(entityKey),
    organismFocus: snapshot.selfState?.current_focus_summary ?? null,
    organismPressures: snapshot.selfState
      ? [
          snapshot.selfState.uncertainty_load,
          snapshot.selfState.contradiction_load,
          snapshot.selfState.curiosity_pressure,
          snapshot.selfState.memory_pressure,
          snapshot.selfState.risk_pressure,
        ]
      : null,
    organismCuriosity: snapshot.organismCuriosity.map(entityKey),
    agency: snapshot.agencyActions.map(entityKey),
    quarantine: snapshot.quarantine.map(entityKey),
    errors: snapshot.errors,
  });
}

export function useBrainObservatory() {
  const [snapshot, setSnapshot] = useState<ObservatorySnapshot | null>(null);
  const [history, setHistory] = useState<ObservatorySnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const currentRef = useRef<ObservatorySnapshot | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timeout: ReturnType<typeof setTimeout> | null = null;

    const clearTimer = () => {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
    };

    const schedule = () => {
      clearTimer();
      if (cancelled) return;
      timeout = setTimeout(poll, document.hidden ? HIDDEN_POLL_MS : LIVE_POLL_MS);
    };

    const poll = async () => {
      const previous = currentRef.current;
      const reads = await Promise.allSettled([
        getHealth(),
        fetchBff<RunnerStatus>("/runner/status"),
        listSignals(),
        listEvidence(),
        getWorkingMemoryObservation(),
        listBeliefs(),
        listPredictions(),
        fetchBff<ListResponse<ObservedGraphEdge>>("/edges"),
        listContradictions(),
        listCuriosityTasks(),
        listSources(),
        listApprovals(),
        listOpportunities(),
        listOutcomes(),
        listLearningEvents(),
        getOrganismCockpit(),
        getOrganismSelfState(),
        listOrganismCuriosity(),
        listOrganismAgencyActions(),
        listOrganismQuarantine(),
        getOrganismPersistenceStatus(),
      ] as const);

      if (cancelled) return;
      const errors: string[] = [];
      const nextWithoutSignature: Omit<ObservatorySnapshot, "signature"> = {
        capturedAt: new Date().toISOString(),
        health: valueOr(reads[0], previous?.health ?? null, "health", errors),
        runner: valueOr(reads[1], previous?.runner ?? null, "runner", errors),
        signals: listOr(reads[2], previous?.signals ?? [], "signals", errors),
        evidence: listOr(reads[3], previous?.evidence ?? [], "evidence", errors),
        workingMemory: valueOr(reads[4], previous?.workingMemory ?? null, "working memory", errors),
        beliefs: listOr(reads[5], previous?.beliefs ?? [], "beliefs", errors),
        predictions: listOr(reads[6], previous?.predictions ?? [], "predictions", errors),
        edges: listOr(reads[7], previous?.edges ?? [], "edges", errors),
        contradictions: listOr(reads[8], previous?.contradictions ?? [], "contradictions", errors),
        curiosity: listOr(reads[9], previous?.curiosity ?? [], "curiosity", errors),
        sources: listOr(reads[10], previous?.sources ?? [], "sources", errors),
        approvals: listOr(reads[11], previous?.approvals ?? [], "approvals", errors),
        opportunities: listOr(reads[12], previous?.opportunities ?? [], "opportunities", errors),
        outcomes: listOr(reads[13], previous?.outcomes ?? [], "outcomes", errors),
        learningEvents: listOr(reads[14], previous?.learningEvents ?? [], "learning events", errors),
        organism: valueOr(reads[15], previous?.organism ?? null, "organism cockpit", errors),
        selfState: valueOr(reads[16], previous?.selfState ?? null, "organism self-state", errors),
        organismCuriosity: valueOr(reads[17], previous?.organismCuriosity ?? [], "organism curiosity", errors),
        agencyActions: valueOr(reads[18], previous?.agencyActions ?? [], "organism agency", errors),
        quarantine: valueOr(reads[19], previous?.quarantine ?? [], "organism quarantine", errors),
        persistence: valueOr(reads[20], previous?.persistence ?? null, "organism persistence", errors),
        errors,
      };
      const next: ObservatorySnapshot = {
        ...nextWithoutSignature,
        signature: signatureOf(nextWithoutSignature),
      };

      currentRef.current = next;
      setSnapshot(next);
      setHistory((existing) => {
        if (existing.at(-1)?.signature === next.signature) return existing;
        return [...existing, next].slice(-MAX_SNAPSHOTS);
      });
      setLoading(false);

      schedule();
    };

    const onVisibility = () => {
      if (cancelled || document.hidden) return;
      clearTimer();
      void poll();
    };

    void poll();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      clearTimer();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return { snapshot, history, loading };
}
