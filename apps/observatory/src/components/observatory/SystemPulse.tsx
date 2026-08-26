import { inboxParts } from "@/lib/observatory";
import type { CognitiveScene, ObservatorySnapshot } from "@/types/observatory";

const READ_SURFACES = 18;

function healthMode(snapshot: ObservatorySnapshot | null, loading: boolean): "OBSERVING" | "HEALTHY" | "DEGRADED" | "OFFLINE" {
  if (loading || !snapshot) return "OBSERVING";
  if (!snapshot.health) return "OFFLINE";
  return snapshot.health.status === "ok" ? "HEALTHY" : "DEGRADED";
}

function surfaceName(error: string): string {
  const name = error.split(":", 1)[0]?.trim();
  return name || "read surface";
}

export function SystemPulse({
  snapshot,
  scene,
  loading,
  isLive,
}: {
  snapshot: ObservatorySnapshot | null;
  scene: CognitiveScene;
  loading: boolean;
  isLive: boolean;
}) {
  const health = healthMode(snapshot, loading);
  const activity = loading || !snapshot ? "OBSERVING" : scene.activity > 0 ? "ACTIVE" : "QUIET";
  const heartbeat = snapshot?.health?.heartbeat ?? snapshot?.runner ?? {};
  const inbox = inboxParts(heartbeat.inbox);
  const inboxActive = Number(inbox.pending ?? 0) + Number(inbox.processing ?? 0);
  const focus = scene.organism.focus;
  const failedReads = snapshot?.errors.length ?? 0;
  const successfulReads = Math.max(0, READ_SURFACES - failedReads);
  const degradedSurfaces = snapshot?.errors.map(surfaceName) ?? [];

  return (
    <header className="system-pulse" aria-label="Brain system pulse">
      <div className="system-pulse__brand">
        <span className="system-pulse__eyebrow">BRAIN</span>
        <strong>OBSERVATORY</strong>
      </div>

      <div className="system-pulse__states" aria-label={`Brain health ${health}; cognitive field ${activity}`}>
        <span className={`system-health health-${health.toLowerCase()}`}>
          <i aria-hidden="true" />
          {health}
        </span>
        <span className={`system-activity activity-${activity.toLowerCase()}`}>{activity}</span>
      </div>

      <div className="system-pulse__focus">
        <span>FOCUS</span>
        <strong>{focus || "No self-state focus declared"}</strong>
        {scene.organism.dominantGoal ? (
          <em>goal {scene.organism.dominantGoal.replaceAll("_", " ")} · {scene.organism.dominantGoalPressure.toFixed(2)}</em>
        ) : null}
      </div>

      <div className={`system-observability ${failedReads ? "is-partial" : "is-complete"}`} title={degradedSurfaces.join(", ") || "All Observatory read surfaces succeeded"}>
        <span>OBS</span>
        <strong>{successfulReads}/{READ_SURFACES}</strong>
        <em>{failedReads ? degradedSurfaces.slice(0, 2).join(" · ") : "complete"}</em>
      </div>

      <dl className="system-pulse__metrics">
        <div>
          <dt>CYCLE</dt>
          <dd>{String(heartbeat.ticks ?? 0)}</dd>
        </div>
        <div>
          <dt>INBOX</dt>
          <dd>{inboxActive} active</dd>
        </div>
        <div>
          <dt>WORKING</dt>
          <dd>{String(heartbeat.working_memory_size ?? 0)}</dd>
        </div>
        <div className="system-pulse__desktop-metric">
          <dt>STORE</dt>
          <dd>{snapshot?.health?.persistence ?? snapshot?.persistence?.store ?? "—"}</dd>
        </div>
        <div className="system-pulse__desktop-metric">
          <dt>VERSION</dt>
          <dd>{snapshot?.health?.version ?? "—"}</dd>
        </div>
      </dl>

      <div className={`system-pulse__timeline ${isLive ? "is-live" : "is-replay"}`}>{isLive ? "LIVE" : "REPLAY"}</div>
    </header>
  );
}
