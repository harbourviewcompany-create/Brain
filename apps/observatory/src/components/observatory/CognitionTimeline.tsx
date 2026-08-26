"use client";

import type { CognitiveScene, ObservatorySnapshot } from "@/types/observatory";

function deltaLabel(current: ObservatorySnapshot, previous?: ObservatorySnapshot): string {
  if (!previous) return "session observed";
  const deltas: string[] = [];
  const countDelta = (label: string, next: number, before: number) => {
    const delta = next - before;
    if (delta) deltas.push(`${delta > 0 ? "+" : ""}${delta} ${label}`);
  };
  countDelta("signal", current.signals.length, previous.signals.length);
  countDelta("belief", current.beliefs.length, previous.beliefs.length);
  countDelta("prediction", current.predictions.length, previous.predictions.length);
  countDelta("contradiction", current.contradictions.length, previous.contradictions.length);
  countDelta("outcome", current.outcomes.length, previous.outcomes.length);
  if ((current.selfState?.current_focus_summary ?? "") !== (previous.selfState?.current_focus_summary ?? "")) deltas.push("focus changed");
  if (current.errors.length !== previous.errors.length) deltas.push(`reads ${current.errors.length ? "partial" : "restored"}`);
  if ((current.health?.heartbeat?.ticks ?? 0) !== (previous.health?.heartbeat?.ticks ?? 0)) deltas.push("cycle advanced");
  return deltas.slice(0, 2).join(" · ") || "state changed";
}

export function CognitionTimeline({
  history,
  selectedIndex,
  scene,
  onScrub,
}: {
  history: ObservatorySnapshot[];
  selectedIndex: number | null;
  scene: CognitiveScene;
  onScrub: (index: number | null) => void;
}) {
  const effectiveIndex = selectedIndex ?? Math.max(0, history.length - 1);
  const current = history[effectiveIndex];
  const currentDelta = current ? deltaLabel(current, history[effectiveIndex - 1]) : "waiting for first observed state";
  const latestObject = scene.chronology[0];

  return (
    <section className="cognition-timeline" aria-label="Observed session timeline">
      <div className="cognition-timeline__head">
        <div>
          <span>SESSION OBSERVATION</span>
          <strong>{history.length} distinct state{history.length === 1 ? "" : "s"}</strong>
        </div>
        <div className="cognition-timeline__time">
          {current ? new Date(current.capturedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—"}
        </div>
        <button type="button" className={selectedIndex === null ? "is-live" : ""} onClick={() => onScrub(null)}>
          LIVE
        </button>
      </div>

      <div className="cognition-timeline__scrub">
        <div className="cognition-timeline__delta">
          <span>{selectedIndex === null ? "LATEST CHANGE" : "OBSERVED CHANGE"}</span>
          <strong>{currentDelta}</strong>
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(0, history.length - 1)}
          value={effectiveIndex}
          disabled={history.length < 2}
          onChange={(event) => onScrub(Number(event.target.value))}
          aria-label="Replay observed session state"
        />
        <div className="cognition-timeline__markers" aria-hidden="true">
          {history.map((item, index) => (
            <span key={`${item.signature}:${item.capturedAt}`} className={index === effectiveIndex ? "is-current" : ""} />
          ))}
        </div>
      </div>

      <div className="cognition-timeline__chronology" aria-label="Live object chronology">
        {scene.chronology.length === 0 ? (
          <span className="cognition-timeline__empty">NO TIMESTAMPED COGNITIVE OBJECTS EXPOSED</span>
        ) : (
          scene.chronology.slice(0, 10).map((node) => (
            <span key={node.id} title={node.label} className={node.layer === "diagnostic" ? "is-diagnostic" : undefined}>
              <time>{new Date(node.timestamp as string).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
              <b>{node.layer === "diagnostic" ? "diagnostic" : node.kind}</b>
              <em>{node.label}</em>
            </span>
          ))
        )}
      </div>

      <div className="cognition-timeline__mobile-object" aria-label="Latest timestamped object">
        <span>{latestObject ? (latestObject.layer === "diagnostic" ? "DIAGNOSTIC" : latestObject.kind.toUpperCase()) : "CHRONOLOGY"}</span>
        <strong>{latestObject?.label ?? "No timestamped object exposed"}</strong>
      </div>
    </section>
  );
}
