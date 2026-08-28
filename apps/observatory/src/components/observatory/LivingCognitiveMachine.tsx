"use client";

import { FormEvent, useEffect, useMemo, useState, type CSSProperties } from "react";
import { submitBrainCommand } from "@/lib/api";
import { buildLivingBrainModel } from "@/lib/living-brain";
import type { BrainCommandMode } from "@/types/living-brain";
import type { CognitiveScene, ObservatorySnapshot } from "@/types/observatory";
import styles from "./LivingCognitiveMachine.module.css";

type InspectLevel = "whole" | "region" | "pathway" | "node" | "evidence";
type MotionMode = "auto" | "reduced" | "off";

interface Props {
  snapshot: ObservatorySnapshot | null;
  history: ObservatorySnapshot[];
  scene: CognitiveScene;
  loading: boolean;
  onOpenGraph: () => void;
}

const MODES: Array<{ id: BrainCommandMode; label: string; tone: string }> = [
  { id: "teach", label: "Teach", tone: "green" },
  { id: "solve", label: "Solve", tone: "blue" },
  { id: "inspect", label: "Inspect", tone: "cyan" },
  { id: "challenge", label: "Challenge", tone: "violet" },
  { id: "build_capability", label: "Build Capability", tone: "gold" },
  { id: "explain_change", label: "Explain What Changed", tone: "violet" },
];

const REGION_COPY: Record<string, string> = {
  attention: "Attention is derived from the live signal attention score and current self-state focus. No percentage is invented.",
  working: "Working memory shows the live runner working-set size plus organism workspace items when the runtime exposes them.",
  retrieval: "Retrieval ranks durable evidence using explicit lexical overlap and source reliability. The score is a transparent Observatory projection over stored evidence, not a claimed hidden memory score.",
  hypotheses: "Hypotheses are real Brain beliefs in hypothesis, provisional, contested, or rejected states, with evidence conflict attached when available.",
  predictions: "Prediction branches are persisted Brain predictions. Probabilities and resolution state come from the API; missing values remain missing.",
  action: "Action shows organism agency proposals and their real approval/execution state. The Observatory never invents an executed action.",
  feedback: "Feedback is built from recorded outcomes and prediction resolution data. Empty means the runtime has no attributable outcome on this surface.",
  learning: "Learning is reconstructed from durable attribution, rewire, prune, prediction-resolution, and outcome events.",
};

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function short(value: string, max = 92): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function displayDate(value?: string | null): string {
  if (!value) return "unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function payloadSummary(payload: Record<string, unknown>): string {
  const candidates = [payload.rationale, payload.reason, payload.operation, payload.reward_score, payload.prediction_error];
  for (const candidate of candidates) {
    if (Array.isArray(candidate) && candidate.length) return candidate.map(String).join(" · ");
    if (typeof candidate === "string" && candidate.trim()) return candidate;
    if (typeof candidate === "number") return String(candidate);
  }
  return "Recorded cognitive change";
}

export function LivingCognitiveMachine({ snapshot, history, scene, loading, onOpenGraph }: Props) {
  const model = useMemo(() => buildLivingBrainModel(snapshot, scene), [snapshot, scene]);
  const [command, setCommand] = useState("");
  const [mode, setMode] = useState<BrainCommandMode>("solve");
  const [submitting, setSubmitting] = useState(false);
  const [commandStatus, setCommandStatus] = useState<string | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [region, setRegion] = useState("attention");
  const [inspectLevel, setInspectLevel] = useState<InspectLevel>("whole");
  const [inspectId, setInspectId] = useState<string | null>(null);
  const [motion, setMotion] = useState<MotionMode>("auto");

  useEffect(() => {
    const saved = window.localStorage.getItem("brain-observatory-motion");
    if (saved === "auto" || saved === "reduced" || saved === "off") setMotion(saved);
  }, []);

  const updateMotion = (next: MotionMode) => {
    setMotion(next);
    window.localStorage.setItem("brain-observatory-motion", next);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = command.trim();
    if (!content || submitting) return;
    setSubmitting(true);
    setCommandError(null);
    setCommandStatus("Submitting to the canonical perception pipeline…");
    try {
      const receipt = await submitBrainCommand(content, mode);
      const id = String(receipt.inbox_id ?? receipt.id ?? "").trim();
      setCommandStatus(id ? `Accepted into durable cognition · ${id}` : "Accepted into durable cognition");
    } catch (error) {
      setCommandStatus(null);
      setCommandError(error instanceof Error ? error.message : String(error));
    } finally {
      setSubmitting(false);
    }
  };

  const setInspection = (level: InspectLevel, id?: string | null) => {
    setInspectLevel(level);
    setInspectId(id ?? null);
  };

  const activeEvidence = snapshot?.evidence.find((item) => item.id === inspectId) ?? model.trace.evidence[0] ?? null;
  const inspectPathways = useMemo(() => {
    if (model.trace.pathways.length) return model.trace.pathways;
    return (snapshot?.edges ?? []).slice(0, 12).map((edge, index) => ({
      id: edge.id ?? `${edge.source ?? edge.source_node_id ?? "?"}:${edge.target ?? edge.target_node_id ?? "?"}:${index}`,
      relation: edge.relation ?? "related",
      weight: Number(edge.weight ?? 0),
      confidence: Number(edge.confidence ?? 0),
      source: edge.source ?? edge.source_node_id ?? "unknown",
      target: edge.target ?? edge.target_node_id ?? "unknown",
    }));
  }, [model.trace.pathways, snapshot?.edges]);
  const activePathway = inspectPathways.find((item) => item.id === inspectId) ?? null;
  const activeNode = scene.nodes.find((item) => item.id === inspectId || item.objectId === inspectId) ?? null;

  const motionClass = motion === "off" ? styles.motionOff : motion === "reduced" ? styles.motionReduced : "";

  return (
    <div className={`${styles.machine} ${motionClass}`} data-state={model.state}>
      <header className={styles.topbar}>
        <div className={styles.identity}>
          <span className={styles.brainMark} aria-hidden="true"><i /><i /><i /><i /><i /></span>
          <div><strong>BRAIN</strong><small>LIVING COGNITIVE MACHINE</small></div>
        </div>
        <div className={styles.liveMetrics} aria-label="Live Brain status">
          <span><small>STATE</small><b>{loading ? "SYNC" : model.state.toUpperCase()}</b></span>
          <span><small>CYCLES</small><b>{snapshot?.runner?.ticks ?? snapshot?.health?.heartbeat?.ticks ?? 0}</b></span>
        </div>
        <button className={styles.graphButton} type="button" onClick={onOpenGraph}>Graph</button>
      </header>

      <section className={styles.commandIntake} aria-labelledby="command-intake-title">
        <div className={styles.conduitLabel} id="command-intake-title">COMMAND INTAKE · DURABLE PERCEPTION CONDUIT</div>
        <form onSubmit={submit} className={styles.commandForm}>
          <label className={styles.srOnly} htmlFor="brain-command">Command the Brain</label>
          <textarea
            id="brain-command"
            rows={2}
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            placeholder="Teach, solve, inspect, challenge, or ask what changed…"
            maxLength={8000}
          />
          <div className={styles.commandActions}>
            <button type="button" disabled title="Binary attachment ingestion is not exposed by the canonical Brain API yet" aria-label="Attachments unavailable">＋</button>
            <button type="button" disabled title="Voice ingestion is not exposed by the canonical Brain API yet" aria-label="Voice input unavailable">◉</button>
            <button className={styles.send} type="submit" disabled={submitting || !command.trim()} aria-label="Submit command">{submitting ? "…" : "➤"}</button>
          </div>
        </form>
        <div className={styles.modeStrip} aria-label="Command modes">
          {MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              data-tone={item.tone}
              aria-pressed={mode === item.id}
              onClick={() => setMode(item.id)}
            >{item.label}</button>
          ))}
        </div>
        <div className={styles.commandState} aria-live="polite">
          <span className={commandError ? styles.errorDot : styles.liveDot} />
          {commandError ?? commandStatus ?? (model.commandHistory[0] ? `Latest durable command: ${short(model.commandHistory[0].content, 120)}` : "Ready for operator input")}
        </div>
        <details className={styles.historyDrawer}>
          <summary>Command history <b>{model.commandHistory.length}</b></summary>
          {model.commandHistory.length ? model.commandHistory.map((item) => (
            <button key={item.id} type="button" onClick={() => setCommand(item.content)}>
              <span>{item.mode.toUpperCase()}</span><strong>{short(item.content, 110)}</strong><small>{displayDate(item.createdAt)} · attention {item.attention.toFixed(2)}</small>
            </button>
          )) : <p>No operator commands are present in the durable signal stream.</p>}
        </details>
      </section>

      <main className={styles.brainStage}>
        <div className={styles.cortex} aria-hidden="true">
          <span className={styles.leftCortex} /><span className={styles.rightCortex} /><span className={styles.midline} />
          {Array.from({ length: 18 }, (_, index) => <i key={index} style={{ "--i": index } as CSSProperties} />)}
        </div>

        <section className={styles.goalField} aria-label="Goal attractor field">
          <div><span>GOALS</span><small>{model.goals.length ? `${model.goals.length} ACTIVE` : "NO EXPOSED GOALS"}</small></div>
          <div className={styles.goalList}>{model.goals.slice(0, 3).map((goal) => <b key={goal}>{short(goal, 42)}</b>)}</div>
          {model.goalTension !== null && <small>Tension {pct(model.goalTension)}</small>}
        </section>

        <button className={`${styles.region} ${styles.attention}`} type="button" onClick={() => { setRegion("attention"); setInspection("region"); }} aria-label="Inspect attention region">
          <span className={styles.step}>1</span><strong>ATTENTION</strong><small>ACTIVE FOCUS</small>
          <div className={styles.attentionBeam} />
          <em>{model.attentionScore === null ? "No scored signal" : `score ${model.attentionScore.toFixed(2)}`}</em>
          <p>{short(model.focus ?? "No active focus reported", 120)}</p>
        </button>

        <div className={styles.cognitionGrid}>
          <button className={`${styles.region} ${styles.retrieval}`} type="button" onClick={() => { setRegion("retrieval"); setInspection("region"); }}>
            <span className={styles.step}>3</span><strong>MEMORY RETRIEVAL</strong><small>DURABLE EVIDENCE SEARCH</small>
            <div className={styles.stack}>
              {model.retrieval.slice(0, 4).map((item) => (
                <span key={item.evidence.id}><b>{Math.round(item.score * 100)}%</b>{short(item.evidence.claim, 52)}<small>{item.evidence.source_id} · rel {pct(item.evidence.reliability)}</small></span>
              ))}
              {!model.retrieval.length && <span className={styles.empty}>No retrievable evidence for the current focus.</span>}
            </div>
          </button>

          <button className={`${styles.region} ${styles.working}`} type="button" onClick={() => { setRegion("working"); setInspection("region"); }}>
            <span className={styles.step}>2</span><strong>WORKING MEMORY</strong><small>LIVE · CAPACITY LIMITED</small>
            <div className={styles.activeProblem}><small>ACTIVE FOCUS</small><p>{short(model.focus ?? "No current focus", 180)}</p></div>
            <div className={styles.workspace}>
              {model.workspaceItems.length ? model.workspaceItems.map((item) => <span key={item}>{short(item, 80)}</span>) : <span>No workspace item payload is exposed by the live cockpit.</span>}
            </div>
            <div className={styles.capacity}><span>WORKING SET</span><b>{model.workingMemorySize ?? "—"}{model.workingMemoryCapacity ? ` / ${model.workingMemoryCapacity}` : ""}</b></div>
            <div className={styles.pressureTrack}><i style={{ width: `${Math.round(Math.max(0, Math.min(1, model.workingMemoryPressure ?? 0)) * 100)}%` }} /></div>
          </button>

          <button className={`${styles.region} ${styles.hypotheses}`} type="button" onClick={() => { setRegion("hypotheses"); setInspection("region"); }}>
            <span className={styles.step}>4</span><strong>HYPOTHESES</strong><small>COMPETING BELIEFS</small>
            <div className={styles.stack}>
              {model.hypotheses.slice(0, 4).map((item, index) => (
                <span key={item.belief.id} data-contested={item.belief.state === "contested"}>
                  <b>H{index + 1} · {pct(item.belief.confidence)}</b>{short(item.belief.statement, 58)}
                  <small>{item.supporting} support · {item.contradicting} contradict · {item.belief.state}</small>
                </span>
              ))}
              {!model.hypotheses.length && <span className={styles.empty}>No active hypothesis beliefs.</span>}
            </div>
          </button>
        </div>

        <button className={`${styles.region} ${styles.predictions}`} type="button" onClick={() => { setRegion("predictions"); setInspection("region"); }}>
          <span className={styles.step}>5</span><strong>PREDICTIONS</strong><small>PERSISTED FUTURE BRANCHES</small>
          <div className={styles.predictionGrid}>
            {model.predictions.slice(0, 4).map((prediction) => (
              <span key={prediction.id}><b>{pct(prediction.forecast_probability)}</b><strong>{short(prediction.statement ?? "Prediction", 55)}</strong><small>{prediction.status ?? "open"}{prediction.actual_outcome === null || prediction.actual_outcome === undefined ? "" : ` · actual ${String(prediction.actual_outcome)}`}</small></span>
            ))}
            {!model.predictions.length && <span className={styles.empty}>No persisted predictions.</span>}
          </div>
        </button>

        <div className={styles.actionRow}>
          <button className={`${styles.region} ${styles.action}`} type="button" onClick={() => { setRegion("action"); setInspection("region"); }}>
            <span className={styles.step}>6</span><strong>ACTION</strong><small>AGENCY STATE</small>
            {snapshot?.agencyActions[0] ? <p>{short(String(snapshot.agencyActions[0].proposal ?? snapshot.agencyActions[0].action_type ?? "Agency action"), 110)}<em>{String(snapshot.agencyActions[0].state ?? snapshot.agencyActions[0].approval_status ?? "observed")}</em></p> : <p>No agency action is currently exposed.</p>}
          </button>
          <button className={`${styles.region} ${styles.feedback}`} type="button" onClick={() => { setRegion("feedback"); setInspection("region"); }}>
            <span className={styles.step}>7</span><strong>FEEDBACK</strong><small>OUTCOME ATTRIBUTION</small>
            {model.outcomes[0] ? <p>Value {model.outcomes[0].value_created.toFixed(2)}<em>prediction accuracy {pct(model.outcomes[0].prediction_accuracy)}</em></p> : <p>No attributable outcome recorded.</p>}
          </button>
        </div>

        <button className={`${styles.region} ${styles.learning}`} type="button" onClick={() => { setRegion("learning"); setInspection("region"); }}>
          <span className={styles.step}>8</span><strong>LEARNING</strong><small>DURABLE STRUCTURAL CHANGE</small>
          <div className={styles.learningFlow}>
            {model.learningEvents.slice(0, 4).map((event) => <span key={event.id}><i /><b>{event.event_type.replaceAll(".", " ")}</b><small>{short(payloadSummary(event.payload), 56)}</small></span>)}
            {!model.learningEvents.length && <span className={styles.empty}>No structural learning event is available on the read model.</span>}
          </div>
        </button>

        <section className={styles.systemConditions} aria-label="Cognitive conditions">
          <h2>COGNITIVE CONDITIONS</h2>
          {model.warnings.length ? model.warnings.map((warning) => (
            <div key={`${warning.label}:${warning.detail}`} data-severity={warning.severity}><b>{warning.label}</b><span>{warning.detail}</span></div>
          )) : <div data-severity="ok"><b>NOMINAL</b><span>No degraded condition is reported by current read surfaces.</span></div>}
        </section>
      </main>

      <section className={styles.inspector} aria-labelledby="inspect-title">
        <header><div><small>INSPECT MODE</small><h2 id="inspect-title">Evidence-backed cognition</h2></div><button type="button" onClick={onOpenGraph}>Open full graph</button></header>
        <nav aria-label="Inspection depth">
          {(["whole", "region", "pathway", "node", "evidence"] as InspectLevel[]).map((level) => <button key={level} type="button" aria-current={inspectLevel === level ? "page" : undefined} onClick={() => setInspection(level)}>{level}</button>)}
        </nav>

        {inspectLevel === "whole" && <div className={styles.inspectContent}>
          <h3>Whole brain state</h3><div className={styles.metricGrid}>{model.health.map((item) => <span key={item.label}><small>{item.label}</small><b>{item.value}</b></span>)}</div>
          <p>{scene.cognitiveCount} cognitive objects · {scene.edges.length} mapped relations · {history.length} observed session snapshots.</p>
        </div>}

        {inspectLevel === "region" && <div className={styles.inspectContent}><h3>{region.toUpperCase()}</h3><p>{REGION_COPY[region]}</p><p className={styles.provenanceNote}>Every value above is either an API value, a named deterministic projection over API objects, or an explicit unavailable/empty state.</p></div>}

        {inspectLevel === "pathway" && <div className={styles.inspectContent}><h3>Reasoning / learning pathways</h3>
          <div className={styles.inspectList}>{inspectPathways.map((edge) => (
            <button key={edge.id} type="button" onClick={() => setInspection("pathway", edge.id)}><b>{edge.relation}</b><span>{short(edge.source, 20)} → {short(edge.target, 20)}</span><small>weight {edge.weight.toFixed(2)} · confidence {edge.confidence.toFixed(2)}</small></button>
          ))}</div>
          {activePathway && inspectId && <pre>{JSON.stringify(activePathway, null, 2)}</pre>}
          {!inspectPathways.length && <p>No graph pathways are available.</p>}
        </div>}

        {inspectLevel === "node" && <div className={styles.inspectContent}><h3>Cognitive nodes</h3><div className={styles.inspectList}>{scene.nodes.slice(0, 18).map((node) => <button key={node.id} type="button" onClick={() => setInspection("node", node.id)}><b>{node.kind}</b><span>{short(node.label, 75)}</span><small>{short(node.summary, 100)}</small></button>)}</div>{activeNode && inspectId && <pre>{JSON.stringify(activeNode.payload, null, 2)}</pre>}</div>}

        {inspectLevel === "evidence" && <div className={styles.inspectContent}><h3>Memory / evidence</h3><div className={styles.inspectList}>{snapshot?.evidence.slice(0, 24).map((evidence) => <button key={evidence.id} type="button" onClick={() => setInspection("evidence", evidence.id)}><b>{evidence.source_id} · reliability {pct(evidence.reliability)}</b><span>{short(evidence.claim, 100)}</span><small>{evidence.supports === null ? "stance not linked" : evidence.supports ? "supporting" : "contradicting"} · {evidence.belief_ids.length} linked belief{evidence.belief_ids.length === 1 ? "" : "s"}</small></button>)}</div>{activeEvidence && <pre>{JSON.stringify(activeEvidence, null, 2)}</pre>}{!snapshot?.evidence.length && <p>No durable evidence is available.</p>}</div>}

        <div className={styles.traceBox}>
          <small>SELECTED CONCLUSION TRACE</small>
          {model.trace.conclusion ? <>
            <h3>{short(model.trace.conclusion.statement, 150)}</h3>
            <div className={styles.traceChain}>
              <span><b>{model.trace.evidence.length}</b> evidence</span><i>→</i><span><b>{model.trace.pathways.length}</b> pathways</span><i>→</i><span><b>{model.trace.predictions.length}</b> predictions</span><i>→</i><span><b>{model.trace.outcomes.length}</b> outcomes</span><i>→</i><span><b>{model.trace.learning.length}</b> learning events</span>
            </div>
            <p>Confidence {pct(model.trace.conclusion.confidence)} · state {model.trace.conclusion.state}. Missing links remain zero instead of being inferred.</p>
          </> : <p>No belief is available to trace.</p>}
        </div>
      </section>

      <section className={styles.evolution} aria-labelledby="evolution-title">
        <header><div><small>DURABLE HISTORY</small><h2 id="evolution-title">BRAIN EVOLUTION</h2></div><span>{model.learningEvents.length} recent changes</span></header>
        <div className={styles.evolutionTrack}>
          {model.learningEvents.map((event) => <button key={event.id} type="button" onClick={() => { setInspection("pathway", event.aggregate_id); document.getElementById("inspect-title")?.scrollIntoView({ behavior: motion === "off" ? "auto" : "smooth", block: "start" }); }}><i /><b>{event.event_type.replaceAll(".", " ")}</b><span>{short(payloadSummary(event.payload), 80)}</span><small>{displayDate(event.occurred_at)}</small></button>)}
          {!model.learningEvents.length && <p>No durable learning-history events are available yet.</p>}
        </div>
      </section>

      <footer className={styles.footer}>
        <span>Observed {snapshot ? displayDate(snapshot.capturedAt) : "not yet"}</span>
        <label>Motion <select value={motion} onChange={(event) => updateMotion(event.target.value as MotionMode)}><option value="auto">Auto</option><option value="reduced">Reduced</option><option value="off">Off</option></select></label>
      </footer>
    </div>
  );
}
