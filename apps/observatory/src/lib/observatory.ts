import type {
  CognitiveScene,
  InboxStatus,
  ObservedGraphEdge,
  ObservatorySnapshot,
  OrganismProfile,
  SceneEdge,
  SceneKind,
  SceneLayer,
  SceneMetric,
  SceneNode,
  SceneZone,
} from "@/types/observatory";

const TAU = Math.PI * 2;
type Point = { x: number; y: number };

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function number(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

function text(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && Boolean(item.trim())) : [];
}

function timestamp(value: Record<string, unknown>): string | undefined {
  const candidate = value.updated_at ?? value.created_at ?? value.valid_from ?? value.known_at;
  return typeof candidate === "string" && candidate ? candidate : undefined;
}

function hash01(input: string): number {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967295;
}

function arc(
  id: string,
  centerX: number,
  centerY: number,
  radiusX: number,
  radiusY: number,
  start = 0,
  span = TAU
): Point {
  const angle = start + hash01(`${id}:angle`) * span;
  const variance = 0.94 + hash01(`${id}:radius`) * 0.12;
  return {
    x: clamp(centerX + Math.cos(angle) * radiusX * variance, 0.035, 0.965),
    y: clamp(centerY + Math.sin(angle) * radiusY * variance, 0.055, 0.945),
  };
}

function band(id: string, x0: number, x1: number, y0: number, y1: number): Point {
  return {
    x: x0 + hash01(`${id}:x`) * (x1 - x0),
    y: y0 + hash01(`${id}:y`) * (y1 - y0),
  };
}

function metric(label: string, value: unknown, tone?: SceneMetric["tone"]): SceneMetric {
  return { label, value: String(value), tone };
}

function idFor(kind: SceneKind, objectId: string): string {
  return `${kind}:${objectId}`;
}

function initialCounts(): Record<SceneKind, number> {
  return {
    organism: 0,
    signal: 0,
    belief: 0,
    prediction: 0,
    outcome: 0,
    contradiction: 0,
    curiosity: 0,
    source: 0,
    approval: 0,
    opportunity: 0,
    agency: 0,
    quarantine: 0,
    goal: 0,
    debate: 0,
    idea: 0,
    dream: 0,
    development: 0,
  };
}

export function inboxLoad(value: unknown): number {
  if (typeof value === "number") return Math.max(0, value);
  const inbox = record(value) as InboxStatus;
  return Math.max(0, number(inbox.pending) + number(inbox.processing));
}

export function inboxParts(value: unknown): InboxStatus {
  if (typeof value === "number") return { pending: Math.max(0, value), total: Math.max(0, value) };
  return record(value) as InboxStatus;
}

const DIAGNOSTIC_PATTERNS = [
  "production_smoke",
  "production smoke",
  "bff identity",
  "bff keyed",
  "auth smoke",
  "smoke probe",
  "verification probe",
  "deployment probe",
];

function isDiagnostic(value: unknown): boolean {
  const lowered = String(value ?? "").toLowerCase();
  return DIAGNOSTIC_PATTERNS.some((pattern) => lowered.includes(pattern));
}

function diagnosticPayload(payload: Record<string, unknown>, label = ""): boolean {
  const metadata = record(payload.metadata);
  return [
    label,
    payload.source_id,
    payload.source_key,
    payload.statement,
    payload.claim,
    payload.content,
    metadata.source,
    metadata.source_key,
    metadata.claim,
    metadata.content,
    metadata.kind,
  ].some(isDiagnostic);
}

function layerForPayload(payload: Record<string, unknown>, label = ""): SceneLayer {
  return diagnosticPayload(payload, label) ? "diagnostic" : "cognitive";
}

function cockpitArray(cockpit: Record<string, unknown>, key: string): string[] {
  return strings(cockpit[key]);
}

function buildOrganismProfile(snapshot: ObservatorySnapshot): OrganismProfile {
  const cockpit = record(snapshot.organism);
  const explicitSelf = record(snapshot.selfState);
  const cockpitSelf = record(cockpit.self_state);
  const workspace = record(cockpit.conscious_focus);
  const focusItems = Array.isArray(workspace.active_focus) ? workspace.active_focus.map(record) : [];
  const goalPressure = record(cockpit.goal_pressure);

  const focus = text(
    explicitSelf.current_focus_summary,
    text(cockpitSelf.focus, text(focusItems[0]?.title, ""))
  ) || null;
  const pressures = {
    uncertainty: clamp(number(explicitSelf.uncertainty_load)),
    contradiction: clamp(number(explicitSelf.contradiction_load)),
    curiosity: clamp(number(explicitSelf.curiosity_pressure)),
    revenue: clamp(number(explicitSelf.revenue_pressure)),
    risk: clamp(number(explicitSelf.risk_pressure)),
    memory: clamp(number(explicitSelf.memory_pressure)),
    action: clamp(number(explicitSelf.action_backlog_pressure)),
  };
  const pressureValues = Object.values(pressures);
  const inferredStress = pressureValues.length ? pressureValues.reduce((sum, value) => sum + value, 0) / pressureValues.length : 0;

  return {
    focus,
    phase: text(cockpitSelf.phase, "") || null,
    assessment: text(cockpitSelf.self_assessment, "") || null,
    stress: clamp(number(cockpitSelf.stress_index, inferredStress)),
    dominantGoal: text(goalPressure.dominant_goal, "") || null,
    dominantGoalPressure: clamp(number(goalPressure.dominant_pressure)),
    protectOverridesExploit: goalPressure.protect_overrides_exploit === true,
    activeGoals: strings(goalPressure.active_goals),
    workspaceItems: Math.max(0, number(workspace.workspace_items)),
    workspaceCapacity: Math.max(0, number(workspace.capacity)),
    pressures,
  };
}

function zone(id: SceneZone["id"], label: string, count: number, state: SceneZone["state"], detail: string): SceneZone {
  return { id, label, count, state, detail };
}

export function buildCognitiveScene(snapshot: ObservatorySnapshot): CognitiveScene {
  const nodes: SceneNode[] = [];
  const edges: SceneEdge[] = [];
  const counts = initialCounts();
  const sceneByObject = new Map<string, string>();
  const organism = buildOrganismProfile(snapshot);

  const addNode = (node: SceneNode) => {
    nodes.push(node);
    counts[node.kind] += 1;
    if (!sceneByObject.has(node.objectId)) sceneByObject.set(node.objectId, node.id);
  };

  const addEdge = (
    source: string | undefined,
    target: string | undefined,
    relation: string,
    strength = 0.5,
    tension = false
  ) => {
    if (!source || !target || source === target) return;
    if (edges.some((edge) => edge.source === source && edge.target === target && edge.relation === relation)) return;
    edges.push({
      id: `${relation}:${source}:${target}:${edges.length}`,
      source,
      target,
      relation,
      strength: clamp(strength, 0.12, 1),
      tension,
    });
  };

  const heartbeat = snapshot.health?.heartbeat ?? snapshot.runner ?? {};
  const cockpit = record(snapshot.organism);
  const self = record(snapshot.selfState);
  const organismPayload: Record<string, unknown> = {
    ...cockpit,
    explicit_self_state: self,
    health: snapshot.health,
    runner: snapshot.runner,
    persistence: snapshot.persistence,
  };
  addNode({
    id: "organism:runtime",
    objectId: "runtime",
    kind: "organism",
    layer: "organism",
    label: organism.focus || "Cognitive organism",
    summary: organism.phase
      ? `${organism.phase} · ${organism.assessment || "functional self-state"}`
      : "Runtime center · no self-state snapshot is currently exposed",
    x: 0.5,
    y: 0.49,
    size: 24 + Math.min(9, number(heartbeat.working_memory_size) * 1.5) + organism.stress * 4,
    importance: 1,
    state: organism.phase ?? (snapshot.health?.status === "ok" ? "connected" : snapshot.health?.status ?? "unknown"),
    route: "/organism",
    metrics: [
      metric("self phase", organism.phase ?? "not snapshotted"),
      metric("goal", organism.dominantGoal ?? "none reported"),
      metric("goal pressure", organism.dominantGoalPressure.toFixed(2), organism.dominantGoalPressure > 0.65 ? "warning" : "neutral"),
      metric("stress", organism.stress.toFixed(2), organism.stress > 0.7 ? "danger" : organism.stress > 0.45 ? "warning" : "neutral"),
      metric("working memory", heartbeat.working_memory_size ?? 0),
      metric("persistence", snapshot.health?.persistence ?? snapshot.persistence?.store ?? "unknown"),
    ],
    payload: organismPayload,
  });

  if (organism.dominantGoal) {
    const goalId = `goal:${organism.dominantGoal}`;
    addNode({
      id: goalId,
      objectId: organism.dominantGoal,
      kind: "goal",
      layer: "organism",
      label: organism.dominantGoal.replaceAll("_", " "),
      summary: `Dominant goal reported by the organism goal-pressure system`,
      x: 0.5,
      y: 0.235,
      size: 9 + organism.dominantGoalPressure * 8,
      importance: 0.62 + organism.dominantGoalPressure * 0.28,
      state: "dominant",
      route: "/organism",
      metrics: [
        metric("pressure", organism.dominantGoalPressure.toFixed(2), organism.dominantGoalPressure > 0.65 ? "warning" : "attention"),
        metric("active goals", organism.activeGoals.length),
        metric("protect override", organism.protectOverridesExploit ? "active" : "inactive"),
      ],
      payload: record(cockpit.goal_pressure),
    });
    addEdge(goalId, "organism:runtime", "drives focus", Math.max(0.3, organism.dominantGoalPressure));
  }

  const sourceByName = new Map<string, string>();
  [...snapshot.sources].sort((a, b) => a.id.localeCompare(b.id)).forEach((source) => {
    const payload = record(source);
    const trust = clamp(number(source.trust_score, 0.5));
    const layer = layerForPayload(payload, source.name);
    const nodeId = idFor("source", source.id);
    sourceByName.set(source.name.toLowerCase(), nodeId);
    addNode({
      id: nodeId,
      objectId: source.id,
      kind: "source",
      layer,
      label: source.name,
      summary: `${source.kind} source · ${source.status}`,
      ...(layer === "diagnostic" ? band(source.id, 0.1, 0.18, 0.82, 0.91) : arc(source.id, 0.085, 0.5, 0.045, 0.34, Math.PI / 2, Math.PI)),
      size: 6 + trust * 5,
      importance: layer === "diagnostic" ? 0.3 : 0.35 + trust * 0.35,
      timestamp: timestamp(payload),
      state: source.status,
      route: "/sources",
      metrics: [metric("trust", trust.toFixed(2)), metric("status", source.status), metric("channel", layer)],
      payload,
    });
  });

  [...snapshot.signals].sort((a, b) => a.id.localeCompare(b.id)).forEach((signal) => {
    const payload = record(signal);
    const metadata = record(signal.metadata);
    const label = text(metadata.claim ?? metadata.content, signal.source_id || "Signal");
    const layer: SceneLayer = isDiagnostic(signal.source_id) || diagnosticPayload(payload, label) ? "diagnostic" : "cognitive";
    const attention = clamp(number(signal.attention_score));
    const urgency = clamp(number(signal.urgency));
    const nodeId = idFor("signal", signal.id);
    addNode({
      id: nodeId,
      objectId: signal.id,
      kind: "signal",
      layer,
      label,
      summary: layer === "diagnostic" ? `Operational observation from ${signal.source_id}` : `Perception from ${signal.source_id}`,
      ...(layer === "diagnostic" ? band(signal.id, 0.16, 0.39, 0.84, 0.92) : arc(signal.id, 0.235, 0.49, 0.11, 0.31, Math.PI / 2, Math.PI)),
      size: layer === "diagnostic" ? 6 + attention * 5 : 8 + attention * 11,
      importance: layer === "diagnostic" ? 0.28 + attention * 0.16 : 0.45 + attention * 0.5,
      timestamp: timestamp(payload),
      route: "/perception",
      metrics: [
        metric("attention", attention.toFixed(2), "attention"),
        metric("novelty", number(signal.novelty).toFixed(2)),
        metric("urgency", urgency.toFixed(2), urgency > 0.65 ? "warning" : "neutral"),
        metric("source", signal.source_id),
        metric("channel", layer),
      ],
      payload,
    });
    addEdge(sourceByName.get(signal.source_id.toLowerCase()), nodeId, "origin", Math.max(0.3, attention));
  });

  [...snapshot.beliefs].sort((a, b) => a.id.localeCompare(b.id)).forEach((belief) => {
    const payload = record(belief);
    const confidence = clamp(number(belief.confidence, 0.5));
    addNode({
      id: idFor("belief", belief.id),
      objectId: belief.id,
      kind: "belief",
      layer: "cognitive",
      label: belief.statement,
      summary: `${belief.state} belief · version ${belief.version ?? 1}`,
      ...arc(belief.id, 0.43, 0.49, 0.105, 0.21),
      size: 9 + confidence * 13,
      importance: 0.55 + confidence * 0.4,
      timestamp: timestamp(payload),
      state: belief.state,
      route: `/beliefs/${belief.id}`,
      metrics: [
        metric("confidence", `${Math.round(confidence * 100)}%`, confidence > 0.75 ? "success" : "neutral"),
        metric("state", belief.state),
        metric("evidence", belief.evidence_ids?.length ?? 0),
        metric("contradictions", belief.contradiction_ids?.length ?? 0),
      ],
      payload,
    });
  });

  [...snapshot.contradictions].sort((a, b) => a.id.localeCompare(b.id)).forEach((item) => {
    const payload = record(item);
    const pressure = clamp(number(item.investigation_pressure, 0.6));
    const linkedBelief = item.belief_ids.map((objectId) => sceneByObject.get(objectId)).find(Boolean);
    const linkedNode = linkedBelief ? nodes.find((node) => node.id === linkedBelief) : undefined;
    const fallback = arc(item.id, 0.44, 0.49, 0.18, 0.25);
    const point = linkedNode
      ? {
          x: clamp(linkedNode.x + (hash01(`${item.id}:x`) - 0.5) * 0.11, 0.055, 0.945),
          y: clamp(linkedNode.y + (hash01(`${item.id}:y`) - 0.5) * 0.11, 0.065, 0.935),
        }
      : fallback;
    const nodeId = idFor("contradiction", item.id);
    addNode({
      id: nodeId,
      objectId: item.id,
      kind: "contradiction",
      layer: "cognitive",
      label: "Contradiction",
      summary: `${item.belief_ids.length} belief relation${item.belief_ids.length === 1 ? "" : "s"} under tension`,
      ...point,
      size: 9 + pressure * 8,
      importance: 0.72 + pressure * 0.25,
      timestamp: timestamp(payload),
      state: item.status,
      route: "/contradictions",
      metrics: [
        metric("status", item.status, "danger"),
        metric("pressure", pressure.toFixed(2), "danger"),
        metric("supporting", item.supporting_evidence_ids.length),
        metric("contradicting", item.contradicting_evidence_ids.length),
      ],
      payload,
    });
    item.belief_ids.forEach((beliefId) => addEdge(nodeId, sceneByObject.get(beliefId), "contradicts", pressure, true));
  });

  [...snapshot.curiosity].sort((a, b) => a.id.localeCompare(b.id)).forEach((task) => {
    const payload = record(task);
    const priority = clamp(number(task.priority, 0.5));
    const nodeId = idFor("curiosity", task.id);
    addNode({
      id: nodeId,
      objectId: task.id,
      kind: "curiosity",
      layer: "cognitive",
      label: task.title,
      summary: "Runtime curiosity task",
      ...arc(task.id, 0.48, 0.12, 0.27, 0.055, Math.PI, Math.PI),
      size: 7 + priority * 7,
      importance: 0.45 + priority * 0.45,
      timestamp: timestamp(payload),
      state: task.status,
      route: "/curiosity",
      metrics: [metric("priority", priority.toFixed(2), "warning"), metric("status", task.status), metric("action", task.suggested_action ?? "—")],
      payload,
    });
    addEdge(nodeId, sceneByObject.get(task.linked_object_id), "questions", priority);
  });

  const organismCuriosity = snapshot.organismCuriosity.length
    ? snapshot.organismCuriosity.map((item, index) => ({ payload: record(item), index }))
    : cockpitArray(cockpit, "curiosity_queue").map((question, index) => ({ payload: { question, status: "reported" }, index }));
  organismCuriosity.forEach(({ payload, index }) => {
    const rawId = text(payload.id, `organism-curiosity-${index}`);
    const priority = clamp(number(payload.expected_value ?? payload.priority, 0.5));
    const nodeId = idFor("curiosity", rawId);
    addNode({
      id: nodeId,
      objectId: rawId,
      kind: "curiosity",
      layer: "organism",
      label: text(payload.question ?? payload.trigger_type, "Organism curiosity"),
      summary: "Organism curiosity queue",
      ...arc(rawId, 0.56, 0.12, 0.22, 0.05, Math.PI, Math.PI),
      size: 7 + priority * 7,
      importance: 0.45 + priority * 0.45,
      timestamp: timestamp(payload),
      state: typeof payload.status === "string" ? payload.status : undefined,
      route: "/organism",
      metrics: [
        metric("expected value", priority.toFixed(2), "warning"),
        metric("uncertainty", number(payload.uncertainty).toFixed(2)),
        metric("status", payload.status ?? "reported"),
      ],
      payload,
    });
  });

  [...snapshot.predictions].sort((a, b) => a.id.localeCompare(b.id)).forEach((prediction) => {
    const payload = record(prediction);
    const label = text(payload.statement ?? payload.metric, "Prediction");
    const layer = layerForPayload(payload, label);
    const confidence = clamp(number(payload.confidence ?? payload.forecast_probability, 0.5));
    const beliefId = typeof payload.belief_id === "string" ? payload.belief_id : undefined;
    const nodeId = idFor("prediction", prediction.id);
    addNode({
      id: nodeId,
      objectId: prediction.id,
      kind: "prediction",
      layer,
      label,
      summary: layer === "diagnostic" ? "Operational verification prediction" : `${text(payload.status, "open")} prediction`,
      ...(layer === "diagnostic" ? band(prediction.id, 0.4, 0.47, 0.84, 0.92) : arc(prediction.id, 0.78, 0.47, 0.14, 0.28, -Math.PI / 2, Math.PI)),
      size: layer === "diagnostic" ? 7 : 9 + confidence * 10,
      importance: layer === "diagnostic" ? 0.34 : 0.5 + confidence * 0.42,
      timestamp: timestamp(payload),
      state: typeof payload.status === "string" ? payload.status : undefined,
      route: "/predictions",
      metrics: [
        metric("confidence", `${Math.round(confidence * 100)}%`, "future"),
        metric("expected value", payload.expected_value ?? "—"),
        metric("status", payload.status ?? "open"),
        metric("resolve by", payload.resolve_by ?? "—"),
        metric("channel", layer),
      ],
      payload,
    });
    addEdge(sceneByObject.get(beliefId ?? ""), nodeId, "forecasts", confidence);
  });

  [...snapshot.outcomes].sort((a, b) => a.id.localeCompare(b.id)).forEach((outcome) => {
    const payload = record(outcome);
    const layer = layerForPayload(payload);
    const accuracy = clamp(number(outcome.prediction_accuracy));
    const nodeId = idFor("outcome", outcome.id);
    addNode({
      id: nodeId,
      objectId: outcome.id,
      kind: "outcome",
      layer,
      label: `Outcome · ${Math.round(accuracy * 100)}% accuracy`,
      summary: `Value created ${number(outcome.value_created).toFixed(2)}`,
      ...(layer === "diagnostic" ? band(outcome.id, 0.48, 0.54, 0.84, 0.92) : arc(outcome.id, 0.71, 0.79, 0.15, 0.09, 0, Math.PI)),
      size: layer === "diagnostic" ? 7 : 8 + accuracy * 9,
      importance: layer === "diagnostic" ? 0.34 : 0.5 + accuracy * 0.38,
      timestamp: timestamp(payload),
      route: "/learning",
      metrics: [
        metric("accuracy", `${Math.round(accuracy * 100)}%`, accuracy > 0.7 ? "success" : "warning"),
        metric("value", number(outcome.value_created).toFixed(2)),
        metric("trust impact", number(outcome.trust_impact).toFixed(2)),
        metric("legal risk", number(outcome.legal_risk).toFixed(2)),
        metric("channel", layer),
      ],
      payload,
    });
    addEdge(sceneByObject.get(outcome.prediction_id ?? ""), nodeId, "resolves", Math.max(0.35, accuracy));
    addEdge(nodeId, "organism:runtime", "feeds learning", Math.max(0.35, accuracy));
  });

  [...snapshot.opportunities].sort((a, b) => a.id.localeCompare(b.id)).forEach((opportunity) => {
    const payload = record(opportunity);
    const expected = clamp(number(opportunity.expected_value, 0.5));
    const nodeId = idFor("opportunity", opportunity.id);
    addNode({
      id: nodeId,
      objectId: opportunity.id,
      kind: "opportunity",
      layer: "cognitive",
      label: opportunity.title,
      summary: `${opportunity.status} opportunity`,
      ...arc(opportunity.id, 0.62, 0.69, 0.12, 0.12, 0, Math.PI),
      size: 8 + expected * 8,
      importance: 0.45 + expected * 0.4,
      timestamp: timestamp(payload),
      state: opportunity.status,
      route: "/opportunities",
      metrics: [metric("expected value", opportunity.expected_value), metric("risk", opportunity.risk_score), metric("status", opportunity.status)],
      payload,
    });
    opportunity.belief_ids.forEach((beliefId) => addEdge(sceneByObject.get(beliefId), nodeId, "supports", expected));
  });

  [...snapshot.approvals].sort((a, b) => a.id.localeCompare(b.id)).forEach((approval) => {
    const payload = record(approval);
    const nodeId = idFor("approval", approval.id);
    addNode({
      id: nodeId,
      objectId: approval.id,
      kind: "approval",
      layer: "cognitive",
      label: `Approval · ${approval.state}`,
      summary: approval.external_consequence ? "External consequence requires operator authority" : "Operator approval gate",
      ...arc(approval.id, 0.46, 0.855, 0.14, 0.035, 0, Math.PI),
      size: approval.state === "requested" ? 13 : 9,
      importance: approval.state === "requested" ? 0.92 : 0.5,
      timestamp: timestamp(payload),
      state: approval.state,
      route: "/approvals",
      metrics: [
        metric("state", approval.state, approval.state === "requested" ? "warning" : "neutral"),
        metric("approver", approval.required_approver),
        metric("external", approval.external_consequence),
      ],
      payload,
    });
    addEdge("organism:runtime", nodeId, "governed action", approval.state === "requested" ? 0.9 : 0.4);
  });

  const agency = snapshot.agencyActions.length
    ? snapshot.agencyActions.map((action, index) => ({ payload: record(action), index }))
    : cockpitArray(cockpit, "proposed_actions").map((state, index) => ({ payload: { status: state, proposal: `Organism action · ${state}` }, index }));
  agency.forEach(({ payload, index }) => {
    const rawId = text(payload.id, `agency-${index}`);
    const risk = clamp(number(payload.risk_score));
    const nodeId = idFor("agency", rawId);
    addNode({
      id: nodeId,
      objectId: rawId,
      kind: "agency",
      layer: "organism",
      label: text(payload.proposal ?? payload.action_type, "Agency action"),
      summary: `${payload.tier ?? "governed"} · ${payload.status ?? payload.state ?? "reported"}`,
      ...arc(rawId, 0.58, 0.84, 0.13, 0.04, 0, Math.PI),
      size: 9 + risk * 7,
      importance: 0.55 + risk * 0.3,
      state: text(payload.status ?? payload.state, "reported"),
      route: "/organism",
      metrics: [
        metric("tier", payload.tier ?? "—"),
        metric("status", payload.status ?? payload.state ?? "reported"),
        metric("risk", risk.toFixed(2), risk > 0.6 ? "warning" : "neutral"),
      ],
      payload,
    });
    addEdge("organism:runtime", nodeId, "proposes", 0.55 + risk * 0.3);
  });

  const quarantine = snapshot.quarantine.length
    ? snapshot.quarantine.map((item, index) => ({ payload: record(item), index }))
    : cockpitArray(cockpit, "immune_quarantine").map((reason, index) => ({ payload: { reason, item_type: "organism_report" }, index }));
  quarantine.forEach(({ payload, index }) => {
    const rawId = text(payload.id, `quarantine-${index}`);
    addNode({
      id: idFor("quarantine", rawId),
      objectId: rawId,
      kind: "quarantine",
      layer: "organism",
      label: text(payload.reason, "Quarantined item"),
      summary: `${payload.item_type ?? "item"} · ${payload.item_ref ?? "reported by organism"}`,
      ...arc(rawId, 0.15, 0.75, 0.06, 0.08, Math.PI, Math.PI),
      size: 11,
      importance: 0.85,
      route: "/organism",
      metrics: [metric("type", payload.item_type ?? "—"), metric("reference", payload.item_ref ?? "—"), metric("reason", payload.reason ?? "—", "danger")],
      payload,
    });
  });

  cockpitArray(cockpit, "internal_debates").forEach((verdict, index) => {
    const rawId = `debate-${index}-${verdict}`;
    addNode({
      id: idFor("debate", rawId), objectId: rawId, kind: "debate", layer: "organism",
      label: verdict.replaceAll("_", " "), summary: "Internal debate verdict reported by organism",
      ...arc(rawId, 0.36, 0.31, 0.08, 0.07), size: 9, importance: 0.68, route: "/organism",
      metrics: [metric("verdict", verdict)], payload: { verdict },
    });
    addEdge(idFor("debate", rawId), "organism:runtime", "challenges", 0.55, true);
  });

  cockpitArray(cockpit, "original_ideas").forEach((idea, index) => {
    const rawId = `idea-${index}-${idea}`;
    addNode({
      id: idFor("idea", rawId), objectId: rawId, kind: "idea", layer: "organism",
      label: idea, summary: "Original idea reported by organism",
      ...arc(rawId, 0.64, 0.31, 0.08, 0.07), size: 9, importance: 0.7, route: "/organism",
      metrics: [metric("state", "reported")], payload: { idea },
    });
    addEdge("organism:runtime", idFor("idea", rawId), "generates", 0.58);
  });

  cockpitArray(cockpit, "dream_insights").forEach((insight, index) => {
    const rawId = `dream-${index}-${insight}`;
    addNode({
      id: idFor("dream", rawId), objectId: rawId, kind: "dream", layer: "organism",
      label: insight, summary: "Consolidation insight reported by organism",
      ...arc(rawId, 0.34, 0.69, 0.08, 0.07), size: 8, importance: 0.62, route: "/organism",
      metrics: [metric("state", "insight")], payload: { insight },
    });
    addEdge(idFor("dream", rawId), "organism:runtime", "consolidates", 0.48);
  });

  cockpitArray(cockpit, "development_timeline").forEach((change, index) => {
    const rawId = `development-${index}-${change}`;
    addNode({
      id: idFor("development", rawId), objectId: rawId, kind: "development", layer: "organism",
      label: change, summary: "Development change reported by organism",
      ...arc(rawId, 0.48, 0.73, 0.08, 0.05), size: 7, importance: 0.55, route: "/organism",
      metrics: [metric("state", "recorded")], payload: { change },
    });
    addEdge(idFor("development", rawId), "organism:runtime", "revises", 0.45);
  });

  snapshot.edges.forEach((graphEdge: ObservedGraphEdge, index) => {
    const sourceObject = String(graphEdge.source_node_id ?? graphEdge.source ?? "");
    const targetObject = String(graphEdge.target_node_id ?? graphEdge.target ?? "");
    const before = edges.length;
    addEdge(
      sceneByObject.get(sourceObject),
      sceneByObject.get(targetObject),
      String(graphEdge.relation ?? "related"),
      number(graphEdge.confidence ?? graphEdge.weight, 0.5)
    );
    if (edges.length > before) edges[edges.length - 1].id = `graph:${graphEdge.id ?? index}:${sourceObject}:${targetObject}`;
  });

  const chronology = nodes
    .filter((node) => node.timestamp && Number.isFinite(Date.parse(node.timestamp)))
    .sort((a, b) => Date.parse(b.timestamp as string) - Date.parse(a.timestamp as string));

  const cognitiveSignals = nodes.filter((node) => node.kind === "signal" && node.layer === "cognitive");
  const recentSignals = cognitiveSignals.filter((node) => Boolean(node.timestamp && Date.now() - Date.parse(node.timestamp) < 5 * 60 * 1000)).length;
  const activeInbox = inboxLoad(snapshot.runner?.inbox ?? snapshot.health?.heartbeat?.inbox);
  const activePressure =
    snapshot.contradictions.filter((item) => item.status !== "resolved_with_note").length +
    snapshot.curiosity.filter((item) => item.status === "open" || item.status === "in_progress").length +
    snapshot.approvals.filter((item) => item.state === "requested").length +
    quarantine.length +
    activeInbox;

  const cognitiveCount = nodes.filter((node) => node.layer === "cognitive").length;
  const diagnosticCount = nodes.filter((node) => node.layer === "diagnostic").length;
  const cognitivePredictions = nodes.filter((node) => node.kind === "prediction" && node.layer === "cognitive").length;
  const cognitiveOutcomes = nodes.filter((node) => node.kind === "outcome" && node.layer === "cognitive").length;
  const agencyCount = nodes.filter((node) => ["approval", "agency"].includes(node.kind)).length;
  const curiosityCount = nodes.filter((node) => node.kind === "curiosity").length;

  const zones: SceneZone[] = [
    zone("perception", "PERCEPTION", cognitiveSignals.length, cognitiveSignals.length ? "active" : "quiet", cognitiveSignals.length ? "Non-diagnostic signals are in attention." : "No non-diagnostic signals are currently exposed."),
    zone("belief", "BELIEF LATTICE", snapshot.beliefs.length, snapshot.beliefs.length ? "active" : "unformed", snapshot.beliefs.length ? "Persisted beliefs form the stable knowledge field." : "Brain reports zero persisted beliefs."),
    zone("curiosity", "CURIOSITY FRONTIER", curiosityCount, curiosityCount ? "active" : "quiet", curiosityCount ? "Unresolved questions are applying exploratory pressure." : "No curiosity task is currently exposed."),
    zone("prediction", "PREDICTION HORIZON", cognitivePredictions, cognitivePredictions ? "active" : "clear", cognitivePredictions ? "Live non-diagnostic forecasts extend into the horizon." : "No non-diagnostic prediction is currently open."),
    zone("learning", "OUTCOME / LEARNING", cognitiveOutcomes, cognitiveOutcomes ? "active" : "quiet", cognitiveOutcomes ? "Observed outcomes can return into learning." : "No non-diagnostic outcome is currently exposed."),
    zone("agency", "AGENCY GATE", agencyCount, agencyCount ? "active" : "quiet", agencyCount ? "Governed actions or approvals are present." : "No governed action is waiting at the gate."),
    zone("diagnostic", "SYSTEM DIAGNOSTICS", diagnosticCount, diagnosticCount ? "active" : "quiet", diagnosticCount ? "Operational and verification records are visible but excluded from cognitive activity." : "No diagnostic records are present."),
  ];

  return {
    nodes,
    edges,
    chronology,
    activity: clamp((recentSignals + activePressure) / 6),
    workingMemorySize: Math.max(0, number(snapshot.runner?.working_memory_size ?? snapshot.health?.heartbeat?.working_memory_size)),
    memoryPressure: organism.pressures.memory,
    counts,
    cognitiveCount,
    diagnosticCount,
    zones,
    organism,
  };
}
