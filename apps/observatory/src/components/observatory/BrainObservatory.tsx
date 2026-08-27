"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
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

const CognitiveField = dynamic(
  () => import("@/components/observatory/CognitiveField").then((mod) => mod.CognitiveField),
  {
    ssr: false,
    loading: () => (
      <div className="cognitive-field cognitive-field--loading" role="status" aria-label="Loading cognitive field">
        <div className="cognitive-field__quiet-state">
          <span>FIELD INITIALIZING</span>
          <strong>Loading cognitive field canvas…</strong>
        </div>
      </div>
    ),
  },
);

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

const EMPTY_DIFF: FieldDiff = {
  added: [],
  removed: [],
  updated: [],
  cameraHintId: null,
};

export function BrainObservatory() {
  const { snapshot, history, loading } = useBrainObservatory();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [scrubIndex, setScrubIndex] = useState<number | null>(null);
  const [births, setBirths] = useState<BirthMap>(() => createBirthMap());
  const [diff, setDiff] = useState<FieldDiff>(EMPTY_DIFF);
  const previousSceneRef = useRef<CognitiveScene | null>(null);
  const scrubBoundaryRef = useRef<number | null>(null);

  const displayedSnapshot = scrubIndex === null ? snapshot : history[scrubIndex] ?? snapshot;
  const scene = useMemo(
    () => (displayedSnapshot ? buildCognitiveScene(displayedSnapshot) : EMPTY_SCENE),
    [displayedSnapshot],
  );

  useEffect(() => {
    const scrubBoundary = scrubIndex !== scrubBoundaryRef.current;
    if (scrubBoundary) {
      scrubBoundaryRef.current = scrubIndex;
      if (scrubIndex !== null) {
        const replayDiff = diffScene(null, scene);
        setDiff(replayDiff);
        setBirths(applyDiffToBirths(createBirthMap(), replayDiff));
        previousSceneRef.current = scene;
        return;
      }
    }

    const nextDiff = diffScene(previousSceneRef.current, scene);
    setDiff(nextDiff);
    setBirths((current) => applyDiffToBirths(current, nextDiff));
    previousSceneRef.current = scene;
  }, [scene, scrubIndex]);

  const flares = useMemo(
    () => flaresFromErrors(displayedSnapshot?.errors ?? []),
    [displayedSnapshot?.errors],
  );

  const selectedNode = useMemo(
    () => scene.nodes.find((node) => node.id === selectedId) ?? null,
    [scene.nodes, selectedId],
  );

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
