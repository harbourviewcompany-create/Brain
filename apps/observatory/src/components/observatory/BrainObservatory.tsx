"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { CognitionTimeline } from "@/components/observatory/CognitionTimeline";
import { LivingCognitiveMachine } from "@/components/observatory/LivingCognitiveMachine";
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
  const [graphOpen, setGraphOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [scrubIndex, setScrubIndex] = useState<number | null>(null);
  const [births, setBirths] = useState<BirthMap>(() => createBirthMap());
  const [diff, setDiff] = useState<FieldDiff>(EMPTY_DIFF);
  const previousSceneRef = useRef<CognitiveScene | null>(null);
  const scrubBoundaryRef = useRef<number | null>(null);

  const liveScene = useMemo(
    () => (snapshot ? buildCognitiveScene(snapshot) : EMPTY_SCENE),
    [snapshot],
  );
  const graphSnapshot = scrubIndex === null ? snapshot : history[scrubIndex] ?? snapshot;
  const graphScene = useMemo(
    () => (graphSnapshot ? buildCognitiveScene(graphSnapshot) : EMPTY_SCENE),
    [graphSnapshot],
  );

  useEffect(() => {
    const scrubBoundary = scrubIndex !== scrubBoundaryRef.current;
    if (scrubBoundary) {
      scrubBoundaryRef.current = scrubIndex;
      if (scrubIndex !== null) {
        const replayDiff = diffScene(null, graphScene);
        setDiff(replayDiff);
        setBirths(applyDiffToBirths(createBirthMap(), replayDiff));
        previousSceneRef.current = graphScene;
        return;
      }
    }

    const nextDiff = diffScene(previousSceneRef.current, graphScene);
    setDiff(nextDiff);
    setBirths((current) => applyDiffToBirths(current, nextDiff));
    previousSceneRef.current = graphScene;
  }, [graphScene, scrubIndex]);

  const flares = useMemo(
    () => flaresFromErrors(graphSnapshot?.errors ?? []),
    [graphSnapshot?.errors],
  );

  const selectedNode = useMemo(
    () => graphScene.nodes.find((node) => node.id === selectedId) ?? null,
    [graphScene.nodes, selectedId],
  );

  useEffect(() => {
    if (selectedId && !graphScene.nodes.some((node) => node.id === selectedId)) setSelectedId(null);
  }, [graphScene.nodes, selectedId]);

  useEffect(() => {
    if (!graphOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setGraphOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [graphOpen]);

  return (
    <>
      <LivingCognitiveMachine
        snapshot={snapshot}
        history={history}
        scene={liveScene}
        loading={loading}
        onOpenGraph={() => setGraphOpen(true)}
      />

      {graphOpen ? (
        <section
          className="observatory-graph-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Brain cognitive graph inspector"
        >
          <header className="observatory-graph-overlay__bar">
            <div>
              <strong>COGNITIVE GRAPH</strong>
              <span>{scrubIndex === null ? "LIVE" : "OBSERVED SESSION REPLAY"}</span>
            </div>
            <button type="button" onClick={() => setGraphOpen(false)} aria-label="Close cognitive graph inspector">
              Close
            </button>
          </header>

          <div className="observatory-graph-overlay__stage">
            <section className="observatory-field-shell observatory-graph-overlay__field" aria-label="Live cognitive field">
              <CognitiveField
                scene={graphScene}
                diff={diff}
                births={births}
                flares={flares}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />

              <div className="field-readout field-readout--left" aria-label="Cognitive field object counts">
                <span>COGNITIVE</span>
                <strong>{graphScene.cognitiveCount}</strong>
                <span className="field-readout__diagnostic">DIAGNOSTIC</span>
                <strong>{graphScene.diagnosticCount}</strong>
              </div>
              <div className="field-readout field-readout--right" aria-label="Mapped relation count">
                <span>MAPPED RELATIONS</span>
                <strong>{graphScene.edges.length}</strong>
              </div>
            </section>

            <ThoughtInspector node={selectedNode} scene={graphScene} onClose={() => setSelectedId(null)} />
            <CognitionTimeline
              history={history}
              selectedIndex={scrubIndex}
              scene={graphScene}
              onScrub={setScrubIndex}
            />
          </div>
        </section>
      ) : null}
    </>
  );
}
