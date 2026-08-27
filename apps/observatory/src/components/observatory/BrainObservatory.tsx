"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { CognitiveField } from "@/components/observatory/CognitiveField";
import { CognitionTimeline } from "@/components/observatory/CognitionTimeline";
import { ObservatoryDock } from "@/components/observatory/ObservatoryDock";
import { SystemPulse } from "@/components/observatory/SystemPulse";
import { ThoughtInspector } from "@/components/observatory/ThoughtInspector";
import { applyDiffToBirths, createBirthMap, type BirthMap } from "@/field/births";
import { diffScene, type FieldDiff } from "@/field/diffScene";
import { flaresFromErrors } from "@/field/flares";
import { useBrainObservatory } from "@/hooks/useBrainObservatory";
import { buildCognitiveScene } from "@/lib/observatory";
import type { CognitiveScene } from "@/types/observatory";

const EMPTY_SCENE: CognitiveScene = {
  nodes: [],
  edges: [],
  chronology: [],
  activity: 0,
  workingMemorySize: 0,
  memoryPressure: 0,
  counts: {
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
  },
  cognitiveCount: 0,
  diagnosticCount: 0,
  zones: [],
  organism: {
    focus: null,
    phase: null,
    assessment: null,
    stress: 0,
    dominantGoal: null,
    dominantGoalPressure: 0,
    protectOverridesExploit: false,
    activeGoals: [],
    workspaceItems: 0,
    workspaceCapacity: 0,
    pressures: {
      uncertainty: 0,
      contradiction: 0,
      curiosity: 0,
      revenue: 0,
      risk: 0,
      memory: 0,
      action: 0,
    },
  },
};

export function BrainObservatory() {
  const { snapshot, history, loading } = useBrainObservatory();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [scrubIndex, setScrubIndex] = useState<number | null>(null);
  const [births, setBirths] = useState<BirthMap>(() => createBirthMap());
  const previousSceneRef = useRef<CognitiveScene | null>(null);
  const lastDiffRef = useRef<FieldDiff>({
    added: [],
    removed: [],
    updated: [],
    cameraHintId: null,
  });

  const displayedSnapshot = scrubIndex === null ? snapshot : history[scrubIndex] ?? snapshot;
  const scene = useMemo(
    () => (displayedSnapshot ? buildCognitiveScene(displayedSnapshot) : EMPTY_SCENE),
    [displayedSnapshot],
  );

  useEffect(() => {
    const nextDiff = diffScene(previousSceneRef.current, scene);
    lastDiffRef.current = nextDiff;
    setBirths((current) => applyDiffToBirths(current, nextDiff));
    previousSceneRef.current = scene;
  }, [scene]);

  // Scrubbing rebuilds structure from history; reset birth ages so replay still morphs in.
  useEffect(() => {
    if (scrubIndex === null) return;
    const replayDiff = diffScene(null, scene);
    lastDiffRef.current = replayDiff;
    setBirths(applyDiffToBirths(createBirthMap(), replayDiff));
    previousSceneRef.current = scene;
  }, [scrubIndex]); // eslint-disable-line react-hooks/exhaustive-deps -- intentional scrub boundary

  const flares = useMemo(
    () => flaresFromErrors(displayedSnapshot?.errors ?? []),
    [displayedSnapshot?.errors],
  );

  const selectedNode = scene.nodes.find((node) => node.id === selectedId) ?? null;
  const diff = lastDiffRef.current;

  useEffect(() => {
    if (selectedId && !scene.nodes.some((node) => node.id === selectedId)) setSelectedId(null);
  }, [scene.nodes, selectedId]);

  return (
    <div className="observatory-root">
      <SystemPulse snapshot={displayedSnapshot} scene={scene} loading={loading} isLive={scrubIndex === null} />
      <ObservatoryDock />

      <main className="observatory-stage">
        <section className="observatory-field-shell" aria-label="Live cognitive field">
          <CognitiveField
            scene={scene}
            diff={diff}
            births={births}
            flares={flares}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />

          <div className="field-readout field-readout--left" aria-label="Cognitive field object counts">
            <span>COGNITIVE</span>
            <strong>{scene.cognitiveCount}</strong>
            <span className="field-readout__diagnostic">DIAGNOSTIC</span>
            <strong>{scene.diagnosticCount}</strong>
          </div>
          <div className="field-readout field-readout--right" aria-label="Mapped relation count">
            <span>MAPPED RELATIONS</span>
            <strong>{scene.edges.length}</strong>
          </div>
        </section>

        <ThoughtInspector node={selectedNode} scene={scene} onClose={() => setSelectedId(null)} />
        <CognitionTimeline history={history} selectedIndex={scrubIndex} scene={scene} onScrub={setScrubIndex} />
      </main>
    </div>
  );
}
